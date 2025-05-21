from telegram import Update
from telegram.ext import ContextTypes
from bot.states import session_manager
from bot.keyboards import reply_keyboards

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_logged_in = False
    user_name = "Гость"
    menu_markup = reply_keyboards.guest_menu_markup

    session = session_manager.get_session(user_id)
    if session and session_manager.get_cookies(user_id) and "user" in session:
        is_logged_in = True
        user_name = session["user"].get("fullName", "Пользователь")

    if is_logged_in:
        greeting_message = f"С возвращением, {user_name}!\n📋 Что бы вы хотели сделать?"
        menu_markup = reply_keyboards.logged_in_menu_markup
    else:
        greeting_message = f"Добро пожаловать, {user_name}!\n📋 Пожалуйста, войдите или зарегистрируйтесь, чтобы получить доступ ко всем функциям."

    await update.message.reply_text(greeting_message, reply_markup=menu_markup, parse_mode="HTML")