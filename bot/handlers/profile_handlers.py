from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from bot.services import api_client
from bot.states import session_manager
from bot.utils.helpers import (
    check_user_logged_in,
    handle_api_error,
    encode_image_to_base64
)
from bot.keyboards import reply_keyboards # For profile actions
from .conversation_states import PROFILE_WAITING_FOR_PIC

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if not await check_user_logged_in(update, context):
        return ConversationHandler.END # End if not logged in

    cookies = session_manager.get_cookies(user_id)
    result = api_client.check_auth_status(cookies)

    if result.get("success"):
        user_data = result.get("data")
        if not user_data:
            await update.message.reply_text("⚠️ Не удалось получить данные профиля.")
            return ConversationHandler.END

        full_name = user_data.get("fullName", "Неизвестно")
        email = user_data.get("email", "—")
        profile_pic_url = user_data.get("profilePic") # This is a URL from backend

        text = f"👤 Вы вошли как: <b>{full_name}</b>\n📧 Email: {email}"

        if profile_pic_url:
            try:
                await update.message.reply_photo(
                    photo=profile_pic_url,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=reply_keyboards.profile_action_markup
                )
            except Exception as e:
                await update.message.reply_text(
                    f"{text}\n\n(Не удалось загрузить фото профиля)",
                    parse_mode="HTML",
                    reply_markup=reply_keyboards.profile_action_markup
                )
        else:
            await update.message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=reply_keyboards.profile_action_markup
            )
        return PROFILE_WAITING_FOR_PIC
    else:
        await handle_api_error(update, result, "⚠️ Сессия истекла или недействительна. Войдите снова.")
        session_manager.clear_entire_session(user_id)
        return ConversationHandler.END


async def request_new_profile_pic_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await check_user_logged_in(update, context):
        return ConversationHandler.END
    await update.message.reply_text(
        "🖼 Пожалуйста, отправьте новое изображение для вашего профиля.",
        reply_markup=ReplyKeyboardRemove()
    )
    return PROFILE_WAITING_FOR_PIC


async def update_profile_picture_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if not await check_user_logged_in(update, context):
        return ConversationHandler.END

    if not update.message.photo:
        await update.message.reply_text(
            "⚠️ Пожалуйста, отправьте изображение. Если передумали, нажмите /cancel или кнопку 'Отмена' из меню профиля."
        )
        await profile_command(update, context)
        return PROFILE_WAITING_FOR_PIC


    cookies = session_manager.get_cookies(user_id)
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    image_data_url = encode_image_to_base64(photo_bytes, mime_type="image/jpeg")

    await update.message.reply_text("⏳ Обновляю ваше фото профиля...")
    profile_update_payload = {"profilePic": image_data_url}

    result = api_client.update_user_profile(cookies, profile_update_payload)

    if result.get("success"):
        await update.message.reply_text("✅ Фото профиля успешно обновлено!")
        await profile_command(update, context)
        return PROFILE_WAITING_FOR_PIC
    else:
        await handle_api_error(update, result, "❌ Не удалось обновить фото.")
        await profile_command(update, context)
        return PROFILE_WAITING_FOR_PIC

async def cancel_profile_update_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Действия с профилем отменены.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END