from telegram import Update
from telegram.ext import (
    CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)
import requests
from state.session_store import sessions
import db

FULL_NAME, EMAIL, PASSWORD = range(3)

async def start_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Введите ваше полное имя:")
    return FULL_NAME

async def received_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sessions[update.effective_user.id] = {"fullName": update.message.text}
    await update.message.reply_text("📧 Введите ваш email:")
    return EMAIL

async def received_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sessions[update.effective_user.id]["email"] = update.message.text
    await update.message.reply_text("🔐 Введите пароль (мин. 6 символов):")
    return PASSWORD

async def received_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text
    session = sessions[user_id]

    if len(password) < 6:
        await update.message.reply_text("⚠️ Пароль должен быть не менее 6 символов. Попробуйте снова.")
        return PASSWORD

    try:
        s = requests.Session()
        response = s.post(f"{db.BACKEND_URL}/api/auth/signup", json={
            "fullName": session["fullName"],
            "email": session["email"],
            "password": password
        })

        if response.status_code == 201:
            user_data = response.json()
            sessions[user_id].update({
                "user": user_data,
                "cookies": s.cookies.get_dict()
            })
            await update.message.reply_text(f"✅ Регистрация успешна, {user_data['fullName']}!")
        else:
            await update.message.reply_text(f"❌ Ошибка регистрации: {response.json().get('message')}")
            sessions.pop(user_id, None)
    except Exception as e:
        await update.message.reply_text(f"❗ Ошибка при регистрации: {str(e)}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❎ Регистрация отменена.")
    return ConversationHandler.END

register_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("register", start_register)],
    states={
        FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_fullname)],
        EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_email)],
        PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_password)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
