from state.session_store import sessions
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)
import base64
import requests
import db  # Your own module where BACKEND_URL is defined

# Conversation states
(
    TITLE, DESC, AUTHOR, DATE, LANG,
    CATEGORIES, TYPE, PRICE, IMAGE
) = range(9)


async def start_create_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📘 Введите название книги:")
    return TITLE


async def title_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['title'] = update.message.text
    await update.message.reply_text("✏️ Введите описание:")
    return DESC


async def desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("👤 Введите имя автора:")
    return AUTHOR


async def author_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['author'] = update.message.text
    await update.message.reply_text("📅 Введите дату публикации (например, 2025-05-20):")
    return DATE


async def date_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['publishedDate'] = update.message.text + "T00:00:00.000Z"
    await update.message.reply_text("🌐 Введите язык:")
    return LANG


async def lang_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['language'] = update.message.text
    await update.message.reply_text("🏷 Введите категории (через запятую):")
    return CATEGORIES


async def categories_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    categories = [cat.strip() for cat in update.message.text.split(",")]
    context.user_data['categories'] = categories
    await update.message.reply_text("📦 Введите тип книги (например, forSale или free):")
    return TYPE


async def type_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['type'] = update.message.text
    await update.message.reply_text("💰 Введите цену:")
    return PRICE


async def price_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['price'] = float(update.message.text)
        await update.message.reply_text("📷 Отправьте изображение книги:")
        return IMAGE
    except ValueError:
        await update.message.reply_text("⚠️ Введите корректную цену:")
        return PRICE


async def image_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("⚠️ Пожалуйста, отправьте изображение.")
        return IMAGE

    photo = await update.message.photo[-1].get_file()
    photo_bytes = await photo.download_as_bytearray()
    image_base64 = base64.b64encode(photo_bytes).decode("utf-8")
    image_data_url = f"data:image/webp;base64,{image_base64}"

    context.user_data['image'] = image_data_url

    user_id = update.effective_user.id
    session = sessions.get(user_id)

    if not session or "cookies" not in session:
        await update.message.reply_text("❌ Вы не вошли в систему. Используйте /login.")
        return

    # Send to backend
    try:
        response = requests.post(f"{db.BACKEND_URL}/api/books/create"
                                 f"", json=context.user_data,
                                 cookies=session["cookies"])
        if response.status_code == 201:
            await update.message.reply_text("✅ Книга успешно добавлена!")
        else:
            await update.message.reply_text(f"❌ Ошибка от сервера: {response.text}")
    except Exception as e:
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Добавление книги отменено.")
    return ConversationHandler.END


# Add this to your bot setup
def get_create_book_handler():

    return ConversationHandler(
        entry_points=[CommandHandler("createbook", start_create_book)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, title_received)],
            DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, desc_received)],
            AUTHOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, author_received)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, date_received)],
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_received)],
            CATEGORIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, categories_received)],
            TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_received)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, price_received)],
            IMAGE: [MessageHandler(filters.PHOTO, image_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
