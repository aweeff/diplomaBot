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
    await update.message.reply_text(f"⚠️ {error_msg}")


def encode_image_to_base64(photo_bytes: bytearray, mime_type: str = "image/jpeg") -> str:
    image_base64 = base64.b64encode(photo_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{image_base64}"

def format_book_message(book: dict, owner_name: str = "Неизвестен") -> str:
    title = book.get("title", "Без названия")
    author = book.get("author", "Автор неизвестен")
    categories = ", ".join(book.get("categories", []))
    price = book.get("price", "N/A")

    return (
        f"\U0001F4D6 <b>{title}</b>\n"
        f"✍️ Автор: {author}\n"
        f"🏷 Категории: {categories}\n"
        f"💰 Цена: {price} у.е.\n"
        f"👤 Владелец: {owner_name}"
    )

def login_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not await check_user_logged_in(update, context):
            return ConversationHandler.END
        return await func(update, context, *args, **kwargs)
    return wrapper