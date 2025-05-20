"""
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)
import requests
from state.session_store import sessions
import db
import base64
import aiohttp
import magic

FULL_NAME, EMAIL, PROFILE_PIC = range(3)

async def start_update_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in sessions or "cookies" not in sessions[user_id]:
        await update.message.reply_text("❌ Вы не вошли в систему. Используйте /login.")
        return ConversationHandler.END

    await update.message.reply_text("✏️ Введите новое полное имя (или отправьте /skip):")
    return FULL_NAME

async def received_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["fullName"] = update.message.text
    await update.message.reply_text("📧 Введите новый email (или отправьте /skip):")
    return EMAIL

async def skip_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📧 Введите новый email (или отправьте /skip):")
    return EMAIL

async def received_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["email"] = update.message.text
    await update.message.reply_text("🖼️ Отправьте новое фото профиля (или отправьте /skip):")
    return PROFILE_PIC

async def skip_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🖼️ Отправьте новое фото профиля (или отправьте /skip):")
    return PROFILE_PIC

async def received_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    file_url = photo_file.file_path

    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as resp:
            if resp.status == 200:
                image_bytes = await resp.read()

                # Detect image type (jpeg, png, etc.)
                image_type = imghdr.what(None, h=image_bytes)
                if image_type not in ["jpeg", "png"]:
                    await update.message.reply_text("❌ Поддерживаются только изображения JPEG или PNG.")
                    return PROFILE_PIC

                mime_type = f"image/{'jpeg' if image_type == 'jpeg' else 'png'}"
                base64_data = base64.b64encode(image_bytes).decode('utf-8')
                context.user_data["profilePic"] = f"data:{mime_type};base64,{base64_data}"
            else:
                await update.message.reply_text("⚠️ Не удалось загрузить фото. Попробуйте снова.")
                return PROFILE_PIC

    return await send_update_request(update, context)

async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await send_update_request(update, context)

async def send_update_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = sessions[user_id]
    payload = {k: v for k, v in context.user_data.items() if k in ["fullName", "email", "profilePic"]}

    try:
        response = requests.put(
            f"{db.BACKEND_URL}/api/auth/update-profile",
            json=payload,
            cookies=session["cookies"]
        )
        if response.status_code == 200:
            await update.message.reply_text("✅ Профиль успешно обновлён!", reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text(f"⚠️ Не удалось обновить профиль: {response.json().get('message')}")
    except Exception as e:
        await update.message.reply_text(f"🚫 Ошибка при обновлении профиля: {str(e)}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❎ Обновление профиля отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

update_profile_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("updateprofile", start_update_profile)],
    states={
        FULL_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, received_fullname),
            CommandHandler("skip", skip_fullname)
        ],
        EMAIL: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, received_email),
            CommandHandler("skip", skip_email)
        ],
        PROFILE_PIC: [
            MessageHandler(filters.PHOTO, received_photo),
            CommandHandler("skip", skip_photo)
        ]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)

"""