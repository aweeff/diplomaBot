from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import requests
import db
from state.session_store import sessions

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = sessions.get(user_id)

    if not session or "cookies" not in session:
        await update.message.reply_text("❌ Вы не вошли в систему.")
        return

    try:
        response = requests.post(
            f"{db.BACKEND_URL}/api/auth/logout",
            cookies=session["cookies"]
        )

        if response.status_code == 200:
            sessions.pop(user_id, None)
            await update.message.reply_text("🚪 Вы успешно вышли из системы.")
        else:
            await update.message.reply_text("⚠️ Не удалось выйти из системы.")

    except Exception as e:
        await update.message.reply_text(f"Ошибка при выходе: {str(e)}")

logout_handler = CommandHandler("logout", logout)
