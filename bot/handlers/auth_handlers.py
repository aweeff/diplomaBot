from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.services import api_client
from bot.states import session_manager
from conversation_states import LOGIN_EMAIL, LOGIN_PASSWORD, REGISTER_FULL_NAME, REGISTER_EMAIL, REGISTER_PASSWORD
from bot.utils.helpers import handle_api_error
from bot.handlers.menu import show_menu

async def start_login_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("📧 Введите ваш email:")
    return LOGIN_EMAIL

async def received_email_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    session_manager.set_session_data(user_id, "email_attempt", update.message.text)
    await update.message.reply_text("🔑 Введите пароль:")
    return LOGIN_PASSWORD

async def received_password_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    email = session_manager.get_session_data(user_id, "email_attempt")
    password = update.message.text

    result = api_client.login_user(email, password)

    if result.get("success"):
        user_data = result.get("data", {})
        session_manager.set_session_data(user_id, "user", user_data) #
        session_manager.set_session_data(user_id, "cookies", result.get("cookies")) #
        session_manager.clear_session_data(user_id, "email_attempt") #
        await update.message.reply_text(f"✅ Успешный вход, {user_data.get('fullName', 'пользователь')}!") #
        await show_menu(update, context)
    else:
        session_manager.clear_entire_session(user_id)
        await handle_api_error(update, result, "❌ Неверные данные. Попробуйте /login заново.") #
    return ConversationHandler.END #

async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    session_manager.clear_session_data(update.effective_user.id, "email_attempt") #
    await update.message.reply_text("❎ Вход отменен.") #
    return ConversationHandler.END

async def start_register_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("📝 Введите ваше полное имя:")
    return REGISTER_FULL_NAME

async def received_fullname_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    session_manager.set_session_data(update.effective_user.id, "fullName_reg", update.message.text) #
    await update.message.reply_text("📧 Введите ваш email:")
    return REGISTER_EMAIL

async def received_email_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    session_manager.set_session_data(update.effective_user.id, "email_reg", update.message.text) #
    await update.message.reply_text("🔐 Введите пароль (мин. 6 символов):")
    return REGISTER_PASSWORD

async def received_password_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    password = update.message.text
    fullName = session_manager.get_session_data(user_id, "fullName_reg")
    email = session_manager.get_session_data(user_id, "email_reg")

    if len(password) < 6:
        await update.message.reply_text("⚠️ Пароль должен быть не менее 6 символов. Попробуйте снова.")
        return REGISTER_PASSWORD

    result = api_client.register_user(fullName, email, password)

    if result.get("success"):
        user_data = result.get("data", {})
        session_manager.set_session_data(user_id, "user", user_data)
        session_manager.set_session_data(user_id, "cookies", result.get("cookies"))
        await update.message.reply_text(f"✅ Регистрация успешна, {user_data.get('fullName', 'новый пользователь')}!")
        await show_menu(update, context)
    else:
        await handle_api_error(update, result, f"❌ Ошибка регистрации.")
        session_manager.clear_entire_session(user_id)

    session_manager.clear_session_data(user_id, "fullName_reg")
    session_manager.clear_session_data(user_id, "email_reg")
    return ConversationHandler.END

async def cancel_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    session_manager.clear_session_data(user_id, "fullName_reg")
    session_manager.clear_session_data(user_id, "email_reg")
    await update.message.reply_text("❎ Регистрация отменена.")
    return ConversationHandler.END

async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    cookies = session_manager.get_cookies(user_id)

    if not cookies:
        await update.message.reply_text("❌ Вы не вошли в систему.")
        return

    result = api_client.logout_user(cookies)

    if result.get("success"):
        session_manager.clear_entire_session(user_id) #
        await update.message.reply_text("🚪 Вы успешно вышли из системы.")
        await show_menu(update, context)
    else:
        session_manager.clear_entire_session(user_id) #
        await handle_api_error(update, result, "⚠️ Не удалось выйти из системы на сервере, но локальная сессия очищена.") #

        await show_menu(update, context)