import base64
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.states import session_manager

async def check_user_logged_in(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    if not session_manager.get_cookies(user_id):
        await update.message.reply_text("❌ Вы не вошли в систему. Используйте /login или команду из меню.")
        return False
    return True

async def handle_api_error(update: Update, result: dict, default_message: str = "⚠️ Произошла ошибка."):
    error_msg = result.get("error", default_message)
    status_code = result.get("status_code")
    full_error_message = f"⚠️ {error_msg}"
    if status_code:
        full_error_message += f" (Код: {status_code})"
    await update.message.reply_text(full_error_message)


def encode_image_to_base64(photo_bytes: bytearray, mime_type: str = "image/jpeg") -> str:
    image_base64 = base64.b64encode(photo_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{image_base64}"

def format_book_message(book: dict, owner_name: str = "Неизвестен") -> str:
    title = book.get("title", "Без названия")
    author = book.get("author", "Автор неизвестен")
    categories_list = book.get("categories", [])
    if categories_list and isinstance(categories_list[0], dict):
        categories = ", ".join([cat.get("name", "N/A") for cat in categories_list])
    elif categories_list and isinstance(categories_list[0], str):
        categories = ", ".join(categories_list)
    else:
        categories = "Не указаны"

    price_value = book.get("price")
    price = f"{price_value} у.е." if price_value is not None else "Не указана"
    description = book.get("description", "Описание отсутствует.")
    language = book.get("language", "Не указан")
    published_date_raw = book.get("publishedDate")
    published_date = published_date_raw.split("T")[0] if published_date_raw else "Не указана"


    message = (
        f"📖 <b>{title}</b>\n"
        f"✍️ Автор: {author}\n"
        f"📝 Описание: {description}\n"
        f"🏷 Категории: {categories}\n"
        f"💰 Цена: {price}\n"
        f"👤 Владелец: {owner_name}\n"
        f"🌐 Язык: {language}\n"
        f"📅 Дата публикации: {published_date}"
    )
    return message

def login_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not await check_user_logged_in(update, context):
            return ConversationHandler.END
        return await func(update, context, *args, **kwargs)
    return wrapper