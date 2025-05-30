# In aweeff/diplomabot/diplomaBot-ac4a0d2651b7e9c7d585310ef9fb97f87d4bf1ed/bot/handlers/auth_handlers.py
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.services import api_client
from bot.states import session_manager
# Import new states
from .conversation_states import (
    LOGIN_EMAIL, LOGIN_PASSWORD,
    REGISTER_FULL_NAME, REGISTER_EMAIL, REGISTER_PASSWORD, REGISTER_COUNTRY, REGISTER_CITY
)
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
        session_manager.set_session_data(user_id, "user", user_data)
        session_manager.set_session_data(user_id, "cookies", result.get("cookies"))
        session_manager.clear_session_data(user_id, "email_attempt")
        await update.message.reply_text(f"✅ Успешный вход, {user_data.get('fullName', 'пользователь')}!")
        await show_menu(update, context)
    else:
        session_manager.clear_entire_session(user_id)
        await handle_api_error(update, result, "❌ Неверные данные. Попробуйте /login заново.")
    return ConversationHandler.END


async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    session_manager.clear_session_data(update.effective_user.id, "email_attempt")
    await update.message.reply_text("❎ Вход отменен.")
    await show_menu(update, context)
    return ConversationHandler.END

async def start_register_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("📝 Введите ваше полное имя:")
    return REGISTER_FULL_NAME


async def received_fullname_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    session_manager.set_session_data(update.effective_user.id, "reg_fullName", update.message.text)
    await update.message.reply_text("📧 Введите ваш email:")
    return REGISTER_EMAIL


async def received_email_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    session_manager.set_session_data(update.effective_user.id, "reg_email", update.message.text)
    await update.message.reply_text("🔐 Введите пароль (мин. 6 символов):")
    return REGISTER_PASSWORD


async def received_password_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    password = update.message.text

    if len(password) < 6:
        await update.message.reply_text("⚠️ Пароль должен быть не менее 6 символов. Попробуйте снова.")
        return REGISTER_PASSWORD

    session_manager.set_session_data(user_id, "reg_password", password)
    await update.message.reply_text("🌍 Введите вашу страну (необязательно, можно пропустить /skip):")
    return REGISTER_COUNTRY


async def received_country_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.lower() != "/skip":
        session_manager.set_session_data(update.effective_user.id, "reg_country", update.message.text)
    await update.message.reply_text("🏙 Введите ваш город (необязательно, можно пропустить /skip):")
    return REGISTER_CITY


async def received_city_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if update.message.text.lower() != "/skip":  # Allow skipping city
        session_manager.set_session_data(user_id, "reg_city", update.message.text)

    # Retrieve all collected data
    fullName = session_manager.get_session_data(user_id, "reg_fullName")
    email = session_manager.get_session_data(user_id, "reg_email")
    password = session_manager.get_session_data(user_id, "reg_password")
    country = session_manager.get_session_data(user_id, "reg_country")
    city = session_manager.get_session_data(user_id, "reg_city")

    # Fetch Telegram username instead of ID
    # update.effective_user.username can be None if the user doesn't have one
    telegram_username = update.effective_user.username

    preferences = []  # Send empty list for preferences for now

    if not fullName or not email or not password:
        await update.message.reply_text(
            "⚠️ Произошла ошибка, не все обязательные данные были собраны. Пожалуйста, начните регистрацию заново с /register.")
        # Clear potentially partially filled data
        session_manager.clear_session_data(user_id, "reg_fullName")
        session_manager.clear_session_data(user_id, "reg_email")
        session_manager.clear_session_data(user_id, "reg_password")
        session_manager.clear_session_data(user_id, "reg_country")
        session_manager.clear_session_data(user_id, "reg_city")
        return ConversationHandler.END

    # Call api_client.register_user, passing telegram_username to the 'telegram_id' parameter
    # The api_client.register_user function will use "telegramId" as the key in the payload.
    result = api_client.register_user(
        full_name=fullName,
        email=email,
        password=password,
        telegram_id=telegram_username,  # Pass the username here
        country=country,
        city=city,
        preferences=preferences
    )

    if result.get("success"):
        user_data = result.get("data", {})
        session_manager.set_session_data(user_id, "user", user_data)
        session_manager.set_session_data(user_id, "cookies", result.get("cookies"))
        # The success message can still use fullName
        success_message = f"✅ Регистрация успешна, {user_data.get('fullName', 'новый пользователь')}!"
        if telegram_username:
            success_message += f" (Telegram: @{telegram_username})"
        await update.message.reply_text(success_message)
        await show_menu(update, context)
    else:
        await handle_api_error(update, result, "❌ Ошибка регистрации.")
        session_manager.clear_entire_session(user_id)

    # Clear registration-specific data after attempt
    session_manager.clear_session_data(user_id, "reg_fullName")
    session_manager.clear_session_data(user_id, "reg_email")
    session_manager.clear_session_data(user_id, "reg_password")
    session_manager.clear_session_data(user_id, "reg_country")
    session_manager.clear_session_data(user_id, "reg_city")

    return ConversationHandler.END

async def skip_optional_register_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    current_state = context.user_data.get('_current_reg_state_marker')
    await update.message.reply_text("Поле пропущено.")
    if context.user_data.get('current_reg_step') == REGISTER_COUNTRY:
        await update.message.reply_text("🏙 Введите ваш город (необязательно, можно пропустить /skip):")
        return REGISTER_CITY
    return ConversationHandler.END


async def cancel_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    session_manager.clear_session_data(user_id, "reg_fullName")
    session_manager.clear_session_data(user_id, "reg_email")
    session_manager.clear_session_data(user_id, "reg_password")
    session_manager.clear_session_data(user_id, "reg_country")
    session_manager.clear_session_data(user_id, "reg_city")
    await update.message.reply_text("❎ Регистрация отменена.")
    await show_menu(update, context)
    return ConversationHandler.END


async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    cookies = session_manager.get_cookies(user_id)

    if not cookies:
        await update.message.reply_text("❌ Вы не вошли в систему.")
        await show_menu(update, context)
        return

    result = api_client.logout_user(cookies)

    if result.get("success"):
        session_manager.clear_entire_session(user_id)
        await update.message.reply_text("🚪 Вы успешно вышли из системы.")
    else:
        session_manager.clear_entire_session(user_id)
        await handle_api_error(update, result,
                               "⚠️ Не удалось выйти из системы на сервере, но локальная сессия очищена.")
    await show_menu(update, context)