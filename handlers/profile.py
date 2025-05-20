from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from state.session_store import sessions # Assuming this is your session management
import requests
import db # Assuming this is your db/config module
import base64

# State
WAITING_FOR_PROFILE_PIC = 1

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = sessions.get(user_id)

    if not session or "cookies" not in session:
        await update.message.reply_text("❌ Вы не вошли в систему. Используйте /login.")
        return ConversationHandler.END

    try:
        response = requests.get(
            f"{db.BACKEND_URL}/api/auth/check", # Ensure db.BACKEND_URL is correctly defined
            cookies=session["cookies"]
        )

        if response.status_code == 200:
            user_data = response.json()
            full_name = user_data.get("fullName", "Неизвестно")
            email = user_data.get("email", "—")
            profile_pic = user_data.get("profilePic")

            text = f"👤 Вы вошли как: <b>{full_name}</b>\n📧 Email: {email}"

            keyboard = ReplyKeyboardMarkup([
                ["🖼 Изменить фото профиля"],
                ["❌ Отмена"]
            ], one_time_keyboard=True, resize_keyboard=True)

            if profile_pic:
                await update.message.reply_photo(
                    photo=profile_pic,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)

            return WAITING_FOR_PROFILE_PIC

        else:
            await update.message.reply_text("⚠️ Сессия истекла или недействительна. Войдите снова с помощью /login.")
            if user_id in sessions: # Clear potentially invalid session
                del sessions[user_id]
            return ConversationHandler.END

    except requests.exceptions.RequestException as e: # More specific exception handling
        await update.message.reply_text(f"🚫 Ошибка соединения с сервером: {str(e)}")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"🚫 Ошибка проверки авторизации: {str(e)}")
        return ConversationHandler.END

async def request_new_profile_pic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Изменить фото профиля' button press."""
    await update.message.reply_text(
        "🖼 Пожалуйста, отправьте новое изображение для вашего профиля.",
        reply_markup=ReplyKeyboardRemove() # Optionally remove the keyboard
    )
    # The state remains WAITING_FOR_PROFILE_PIC, now specifically waiting for a photo
    return WAITING_FOR_PROFILE_PIC


async def update_profile_picture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = sessions.get(user_id)

    if not session or "cookies" not in session:
        await update.message.reply_text("❌ Вы не вошли в систему. Используйте /login.")
        return ConversationHandler.END

    if not update.message.photo:
        await update.message.reply_text(
            "⚠️ Пожалуйста, отправьте изображение. Если передумали, нажмите /cancel или отправьте '❌ Отмена'."
        )
        # Stay in the same state to allow user to send a photo or cancel
        return WAITING_FOR_PROFILE_PIC

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        image_base64 = base64.b64encode(photo_bytes).decode("utf-8")
        # Backend from diploma-25c1befecf7e381202d52b5ea57474f257429b9b/backend/src/controllers/auth.controller.js
        # for updateProfile expects a base64 string which it then uploads.
        # The frontend also sends a base64 string (data URL)
        # Let's ensure we send a data URL as the frontend does.
        image_data_url = f"data:image/jpeg;base64,{image_base64}" # Assuming JPEG, adjust if needed

        await update.message.reply_text("⏳ Обновляю ваше фото профиля...")

        response = requests.put(
            f"{db.BACKEND_URL}/api/auth/update-profile",
            json={"profilePic": image_data_url},
            cookies=session["cookies"]
        )
        print("updateprofile response")
        print(response.json())

        if response.status_code == 200:
            await update.message.reply_text("✅ Фото профиля успешно обновлено!")
        else:
            error_message = response.text
            try:
                error_json = response.json()
                error_message = error_json.get("message", error_message)
            except ValueError:
                pass # Keep original text if not JSON
            await update.message.reply_text(f"❌ Не удалось обновить фото. Сервер ответил: {response.status_code} - {error_message}")

    except AttributeError: # If update.message.photo is None or similar
        await update.message.reply_text("⚠️ Ошибка: Сообщение не содержит фото. Пожалуйста, отправьте изображение.")
        return WAITING_FOR_PROFILE_PIC
    except requests.exceptions.RequestException as e:
        await update.message.reply_text(f"🚫 Ошибка соединения при обновлении фото: {str(e)}")
    except Exception as e:
        await update.message.reply_text(f"🚫 Произошла непредвиденная ошибка: {str(e)}")

    return ConversationHandler.END


async def cancel_profile_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Обновление профиля отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

profile_handler = ConversationHandler(
    entry_points=[CommandHandler("me", profile)],
    states={
        WAITING_FOR_PROFILE_PIC: [
            MessageHandler(filters.Regex("^🖼 Изменить фото профиля$"), request_new_profile_pic),
            MessageHandler(filters.PHOTO, update_profile_picture),
            MessageHandler(filters.Regex("^❌ Отмена$"), cancel_profile_update),
            MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: update.message.reply_text("Пожалуйста, выберите действие с клавиатуры или отправьте фото для обновления.")), # Catch-all for other text
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_profile_update), # Allow /cancel command
        MessageHandler(filters.Regex("^❌ Отмена$"), cancel_profile_update) # Keep this for keyboard button
    ],
)