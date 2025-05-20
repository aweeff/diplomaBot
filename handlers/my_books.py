from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from state.session_store import sessions
import requests
import db

def format_book(book):
    title = book.get("title", "Без названия")
    author = book.get("author", "Неизвестен")
    categories = ", ".join(book.get("categories", []))
    return f"📚 <b>{title}</b>\n✍️ {author}\n🏷️ Категории: {categories}\n"

async def my_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = sessions.get(user_id)

    if not session or "cookies" not in session:
        await update.message.reply_text("❌ Вы не вошли в систему. Используйте /login.")
        return

    try:
        response = requests.get(
            f"{db.BACKEND_URL}/api/books/my-books",
            cookies=session["cookies"]
        )

        if response.status_code == 200:
            books = response.json()
            if not books:
                await update.message.reply_text("📭 У вас пока нет книг.")
                return

            message = "\n\n".join([format_book(book) for book in books])
            await update.message.reply_text(message, parse_mode="HTML")
        else:
            await update.message.reply_text("⚠️ Не удалось получить список книг. Попробуйте позже.")
    except Exception as e:
        await update.message.reply_text(f"🚫 Ошибка: {str(e)}")

my_books_handler = CommandHandler("mybooks", my_books)
