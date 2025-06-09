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

    command_list_text = (
        "<b>Основные команды:</b>\n"
        "/start - Запустить бота и показать главное меню\n"
        "/menu - Показать главное меню\n"
        "/login - Войти в систему\n"
        "/register - Зарегистрироваться\n"
        "/logout - Выйти из системы\n"
        "/mybooks - Ваши книги (просмотр, редактирование, удаление)\n"
        "/createbook - Добавить новую книгу\n"
        "/books - Посмотреть все книги\n"
        "/myrecommendations - Рекомендации для вас\n"
        "/me - Ваш профиль\n"
        "/cancel - Отменить текущее действие\n\n"
        "Или используйте кнопки меню:"
    )

    if is_logged_in:
        greeting_message = f"С возвращением, {user_name}!\n\n{command_list_text}"
        menu_markup = reply_keyboards.logged_in_menu_markup
    else:
        greeting_message = f"Добро пожаловать, {user_name}!\n\n{command_list_text}"

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=greeting_message,
        reply_markup=menu_markup,
        parse_mode="HTML"
    )