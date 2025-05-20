from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from state.session_store import sessions
import requests
import db

# States for conversation
CHOOSE_ACTION, CHOOSE_BOOK_INDEX, CONFIRM_DELETE, EDIT_TITLE, EDIT_DESCRIPTION, EDIT_AUTHOR, EDIT_DATE, EDIT_LANGUAGE, EDIT_CATEGORIES, EDIT_IMAGE, EDIT_TYPE, EDIT_PRICE = range(12)

# Temporary book cache per user
user_books_cache = {}

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
        return ConversationHandler.END

    try:
        response = requests.get(
            f"{db.BACKEND_URL}/api/books/my-books",
            cookies=session["cookies"]
        )

        if response.status_code == 200:
            books = response.json()
            if not books:
                await update.message.reply_text("📭 У вас пока нет книг.")
                return ConversationHandler.END

            user_books_cache[user_id] = books

            message = "\n\n".join([f"{i}. {format_book(book)}" for i, book in enumerate(books)])
            await update.message.reply_text(
                f"Ваши книги:\n\n{message}\n\nВыберите действие:",
                reply_markup=ReplyKeyboardMarkup([
                    ["✏️ Редактировать", "🗑 Удалить"],
                    ["❌ Отмена"]
                ], one_time_keyboard=True, resize_keyboard=True),
                parse_mode="HTML"
            )
            return CHOOSE_ACTION

        else:
            await update.message.reply_text("⚠️ Не удалось получить список книг. Попробуйте позже.")
            return ConversationHandler.END

    except Exception as e:
        await update.message.reply_text(f"🚫 Ошибка: {str(e)}")
        return ConversationHandler.END

# User chooses edit/delete/cancel
async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice == "✏️ Редактировать":
        await update.message.reply_text("Введите номер книги, которую хотите редактировать:")
        return CHOOSE_BOOK_INDEX
    elif choice == "🗑 Удалить":
        await update.message.reply_text("Введите номер книги, которую хотите удалить:")
        context.user_data['delete_mode'] = True
        return CHOOSE_BOOK_INDEX
    else:
        await update.message.reply_text("❌ Действие отменено.")
        return ConversationHandler.END

# User inputs book index
async def choose_book_index(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    try:
        index = int(text)
        books = user_books_cache.get(user_id)
        if books is None or index < 0 or index >= len(books):
            await update.message.reply_text("🚫 Неверный номер книги.")
            return ConversationHandler.END

        selected_book = books[index]
        context.user_data['selected_book'] = selected_book

        if context.user_data.get('delete_mode'):
            await update.message.reply_text(
                f"Вы уверены, что хотите удалить книгу '{selected_book['title']}'? (да/нет)"
            )
            return CONFIRM_DELETE
        else:
            # Start editing flow by asking for new title
            await update.message.reply_text(
                f"Редактирование книги: <b>{selected_book['title']}</b>\n"
                "Введите новое название книги или отправьте /skip, чтобы пропустить:",
                parse_mode="HTML"
            )
            return EDIT_TITLE

    except ValueError:
        await update.message.reply_text("🚫 Пожалуйста, введите корректный номер.")
        return ConversationHandler.END

# Confirm delete yes/no
async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    confirmation = update.message.text.lower()
    if confirmation in ["да", "yes"]:
        session = sessions.get(user_id)
        book = context.user_data.get('selected_book')

        try:
            res = requests.delete(
                f"{db.BACKEND_URL}/api/books/{book['_id']}",
                cookies=session["cookies"]
            )
            if res.status_code == 200:
                await update.message.reply_text("✅ Книга удалена.")
            else:
                await update.message.reply_text("⚠️ Не удалось удалить книгу.")
        except Exception as e:
            await update.message.reply_text(f"🚫 Ошибка при удалении: {str(e)}")
    else:
        await update.message.reply_text("❌ Удаление отменено.")
    return ConversationHandler.END

# Skip handler for editing steps
async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await next_edit_step(update, context)

# Helper to move to next edit step, or finish editing
async def next_edit_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('edit_state', EDIT_TITLE)

    # We'll implement a linear sequence of editing:
    # EDIT_TITLE -> EDIT_DESCRIPTION -> EDIT_AUTHOR -> EDIT_DATE -> EDIT_LANGUAGE -> EDIT_CATEGORIES -> EDIT_IMAGE -> EDIT_TYPE -> EDIT_PRICE -> finish
    states_sequence = [
        EDIT_TITLE,
        EDIT_DESCRIPTION,
        EDIT_AUTHOR,
        EDIT_DATE,
        EDIT_LANGUAGE,
        EDIT_CATEGORIES,
        EDIT_IMAGE,
        EDIT_TYPE,
        EDIT_PRICE,
    ]

    current_index = states_sequence.index(state)
    if current_index + 1 >= len(states_sequence):
        # All done, send update to backend
        return await save_edited_book(update, context)

    next_state = states_sequence[current_index + 1]
    context.user_data['edit_state'] = next_state

    prompts = {
        EDIT_DESCRIPTION: "Введите новое описание или /skip:",
        EDIT_AUTHOR: "Введите новое имя автора или /skip:",
        EDIT_DATE: "Введите новую дату публикации (YYYY-MM-DD) или /skip:",
        EDIT_LANGUAGE: "Введите новый язык книги или /skip:",
        EDIT_CATEGORIES: "Введите новые категории через запятую или /skip:",
        EDIT_IMAGE: "Отправьте новое изображение (URL) или /skip:",
        EDIT_TYPE: "Введите новый тип книги (например, forSale) или /skip:",
        EDIT_PRICE: "Введите новую цену или /skip:",
    }
    prompt = prompts.get(next_state, "Введите данные или /skip:")

    await update.message.reply_text(prompt)
    return next_state

# Edit handlers for each field (example for title, similarly others)
async def edit_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text != "/skip":
        context.user_data.setdefault('edited_data', {})['title'] = text
    context.user_data['edit_state'] = EDIT_TITLE
    return await next_edit_step(update, context)

async def edit_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text != "/skip":
        context.user_data.setdefault('edited_data', {})['description'] = text
    context.user_data['edit_state'] = EDIT_DESCRIPTION
    return await next_edit_step(update, context)

async def edit_author(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text != "/skip":
        context.user_data.setdefault('edited_data', {})['author'] = text
    context.user_data['edit_state'] = EDIT_AUTHOR
    return await next_edit_step(update, context)

async def edit_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text != "/skip":
        context.user_data.setdefault('edited_data', {})['publishedDate'] = text
    context.user_data['edit_state'] = EDIT_DATE
    return await next_edit_step(update, context)

async def edit_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text != "/skip":
        context.user_data.setdefault('edited_data', {})['language'] = text
    context.user_data['edit_state'] = EDIT_LANGUAGE
    return await next_edit_step(update, context)

async def edit_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text != "/skip":
        # save categories as list splitted by comma and stripped
        categories = [c.strip() for c in text.split(",") if c.strip()]
        context.user_data.setdefault('edited_data', {})['categories'] = categories
    context.user_data['edit_state'] = EDIT_CATEGORIES
    return await next_edit_step(update, context)

async def edit_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text != "/skip":
        context.user_data.setdefault('edited_data', {})['image'] = text
    context.user_data['edit_state'] = EDIT_IMAGE
    return await next_edit_step(update, context)

async def edit_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text != "/skip":
        context.user_data.setdefault('edited_data', {})['type'] = text
    context.user_data['edit_state'] = EDIT_TYPE
    return await next_edit_step(update, context)

async def edit_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text != "/skip":
        try:
            price = float(text)
            context.user_data.setdefault('edited_data', {})['price'] = price
        except ValueError:
            await update.message.reply_text("Введите число для цены или /skip")
            return EDIT_PRICE
    # After price, finish editing
    return await save_edited_book(update, context)

# Send update request to backend
async def save_edited_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = sessions.get(user_id)
    edited_data = context.user_data.get('edited_data', {})
    original_book = context.user_data.get('selected_book')

    if not original_book or not session or "cookies" not in session:
        await update.message.reply_text("❌ Ошибка сессии или книга не найдена.")
        return ConversationHandler.END

    # Merge original book data with edited data, keeping original values if not edited
    updated_book = {
        "title": edited_data.get("title", original_book.get("title")),
        "description": edited_data.get("description", original_book.get("description")),
        "author": edited_data.get("author", original_book.get("author")),
        "publishedDate": edited_data.get("publishedDate", original_book.get("publishedDate")),
        "language": edited_data.get("language", original_book.get("language")),
        "categories": edited_data.get("categories", original_book.get("categories")),
        "image": edited_data.get("image", original_book.get("image")),
        "type": edited_data.get("type", original_book.get("type")),
        "price": edited_data.get("price", original_book.get("price")),
    }

    try:
        res = requests.post(
            f"{db.BACKEND_URL}/api/books/update/{original_book['_id']}",
            json=updated_book,
            cookies=session["cookies"]
        )
        print("A KAKOGO HUYA")
        print(res.json())
        if res.status_code == 200:
            await update.message.reply_text("✅ Книга успешно обновлена.")
        else:
            await update.message.reply_text("⚠️ Не удалось обновить книгу. Попробуйте позже.")
    except Exception as e:
        await update.message.reply_text(f"🚫 Ошибка при обновлении: {str(e)}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Действие отменено.")
    return ConversationHandler.END

# ConversationHandler setup
my_books_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("mybooks", my_books)],
    states={
        CHOOSE_ACTION: [MessageHandler(filters.Regex("^(✏️ Редактировать|🗑 Удалить|❌ Отмена)$"), choose_action)],
        CHOOSE_BOOK_INDEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_book_index)],
        CONFIRM_DELETE: [MessageHandler(filters.Regex("^(да|нет|yes|no|Да|Нет)$"), confirm_delete)],
        EDIT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_title), CommandHandler("skip", skip)],
        EDIT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_description), CommandHandler("skip", skip)],
        EDIT_AUTHOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_author), CommandHandler("skip", skip)],
        EDIT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_date), CommandHandler("skip", skip)],
        EDIT_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_language), CommandHandler("skip", skip)],
        EDIT_CATEGORIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_categories), CommandHandler("skip", skip)],
        EDIT_IMAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_image), CommandHandler("skip", skip)],
        EDIT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_type), CommandHandler("skip", skip)],
        EDIT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_price), CommandHandler("skip", skip)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


