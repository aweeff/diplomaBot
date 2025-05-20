import requests
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

# States for conversation
TITLE, DESC, AUTHOR, DATE, LANG, CATEGORIES, IMAGE, TYPE, PRICE = range(9)

async def start_create_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название книги:")
    return TITLE

async def title_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['title'] = update.message.text
    await update.message.reply_text("Введите описание:")
    return DESC

async def desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("Введите имя автора :")
    return AUTHOR

async def author_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['author'] = update.message.text
    await update.message.reply_text("Введите дату выхода книги :")
    return DATE

async def date_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['date'] = update.message.text
    await update.message.reply_text("Введите язык :")
    return LANG

async def lang_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['lang'] = update.message.text
    await update.message.reply_text("Введите жанр:")
    return LANG

# Similarly add handlers for DESC, AUTHOR, DATE, LANG, CATEGORIES, IMAGE, TYPE, PRICE...

async def price_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text

    # Prepare data for API
    data = {
        "title": context.user_data.get('title'),
        "description": context.user_data.get('description'),
        "author": context.user_data.get('author'),
        "publishedDate": context.user_data.get('published_date'),
        "language": context.user_data.get('language'),
        "categories": context.user_data.get('categories').split(','),  # assume comma-separated
        "image": context.user_data.get('image'),  # base64 string
        "type": context.user_data.get('type'),
        "price": int(context.user_data.get('price')),
    }

    # You need to pass authentication info here (cookies, token, etc)
    # Example: if you use a token stored in context.user_data['token']:
    headers = {
        "Authorization": f"Bearer {context.user_data.get('token')}"
    }

    # Call backend API
    response = requests.post(f"{BACKEND_URL}/api/books", json=data, headers=headers)

    if response.status_code == 201:
        await update.message.reply_text("Книга успешно создана!")
    else:
        await update.message.reply_text(f"Ошибка при создании книги: {response.text}")

    return ConversationHandler.END

# Setup ConversationHandler with all states and handlers...
