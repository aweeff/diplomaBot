from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import requests
import db

books_handler = CommandHandler("books", lambda update, context: get_books(update, context))

async def get_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(f"{db.BACKEND_URL}/api/books")

        if response.status_code == 200:
            books = response.json()

            if not books:
                await update.message.reply_text("❗️Нет доступных книг.")
                return

            for book in books[:]:
                title = book.get("title", "Без названия")
                author = book.get("author", "Автор неизвестен")
                categories = ", ".join(book.get("categories", []))
                price = book.get("price", "N/A")
                image_url = book.get("image", [None])  # First image

                message = (
                    f"\U0001F4D6 <b>{title}</b>\n"
                    f"✍️ Автор: {author}\n"
                    f"🏷 Категории: {categories}\n"
                    f"💰 Цена: {price} у.е."
                )

                if image_url:
                    await update.message.reply_photo(photo=image_url, caption=message, parse_mode="HTML")
                else:
                    await update.message.reply_text(message, parse_mode="HTML")
        else:
            await update.message.reply_text("⚠️ Ошибка при получении книг с бэкенда.")

    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")
