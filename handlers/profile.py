from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from state.session_store import sessions
import requests
import db

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = sessions.get(user_id)

    if not session or "cookies" not in session:
        await update.message.reply_text("❌ Вы не вошли в систему. Используйте /login.")
        return

    try:
        response = requests.get(
            f"{db.BACKEND_URL}/api/auth/check",
            cookies=session["cookies"]
        )

        if response.status_code == 200:
            user_data = response.json()
            full_name = user_data.get("fullName", "Неизвестно")
            email = user_data.get("email", "—")
            profile_pic = user_data.get("profilePic")

            text = f"👤 Вы вошли как: <b>{full_name}</b>\n📧 Email: {email}"

            if profile_pic:
                await update.message.reply_photo(
                    photo=profile_pic,
                    caption=text,
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text(text, parse_mode="HTML")
        else:
            await update.message.reply_text("⚠️ Сессия истекла или недействительна. Войдите снова с помощью /login.")
    except Exception as e:
        await update.message.reply_text(f"🚫 Ошибка проверки авторизации: {str(e)}")

profile_handler = CommandHandler("me", profile)
