from telegram import Update
from telegram.ext import (
    CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)
from state.session_store import sessions
import requests
import db

EMAIL, PASSWORD = range(2)

async def start_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📧 Введите ваш email:")
    return EMAIL

async def received_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sessions[update.effective_user.id] = {"email": update.message.text}
    await update.message.reply_text("🔑 Введите пароль:")
    return PASSWORD

async def received_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = sessions.get(user_id)
    email = session.get("email")
    password = update.message.text

    try:
        s = requests.Session()
        response = s.post(f"{db.BACKEND_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })

        if response.status_code == 200:
            user_data = response.json()
            sessions[user_id].update({
                "user": user_data,
                "cookies": s.cookies.get_dict()
            })

            await update.message.reply_text(
                f"✅ Успешный вход, {user_data.get('fullName', 'пользователь')}!"
            )
        else:
            sessions.pop(user_id, None)
            await update.message.reply_text("❌ Неверные данные. Попробуйте /login заново.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка входа: {str(e)}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❎ Вход отменен.")
    return ConversationHandler.END

login_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("login", start_login)],
    states={
        EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_email)],
        PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_password)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
