import math
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.keyboards.inline_keyboards import create_pagination_keyboard

BOOKS_PER_PAGE = 5


async def send_or_edit_paginated_books(update: Update, context: ContextTypes.DEFAULT_TYPE, view_key: str, page: int):

    query = update.callback_query
    if query:
        await query.answer()

    book_list = context.user_data.get(view_key, [])
    if not book_list:
        text = "Нет книг для отображения."
        if query:
            await query.edit_message_text(text, reply_markup=None)
        else:
            await update.message.reply_text(text)
        return

    context.user_data[f'{view_key}_page'] = page

    start_index = page * BOOKS_PER_PAGE
    end_index = start_index + BOOKS_PER_PAGE
    paginated_books = book_list[start_index:end_index]

    total_pages = math.ceil(len(book_list) / BOOKS_PER_PAGE)

    message_parts = [f"📚 Страница {page + 1}/{total_pages}\n"]
    if not paginated_books:
        message_parts.append("На этой странице нет книг.")
    else:
        for book in paginated_books:
            # Using a more compact format for the list view
            title = book.get("title", "Без названия")
            author = book.get("author", "Автор неизвестен")
            price_value = book.get("price")
            price = f"{price_value} тг" if price_value is not None else "Бесплатно"
            book_line = f"🔹 {title} - {author} (Цена: {price})"
            message_parts.append(book_line)

    full_message = "\n".join(message_parts)
    keyboard = create_pagination_keyboard(page, total_pages, view_key)

    if query:
        try:
            await query.edit_message_text(full_message, parse_mode="HTML", reply_markup=keyboard)
        except Exception as e:
            if "Message is not modified" not in str(e):
                print(f"Error editing message: {e}")
    else:
        await update.message.reply_text(full_message, parse_mode="HTML", reply_markup=keyboard)