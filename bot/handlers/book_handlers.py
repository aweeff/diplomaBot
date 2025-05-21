from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from bot.services import api_client
from bot.states import session_manager
from bot.utils.helpers import (
    check_user_logged_in,
    handle_api_error,
    encode_image_to_base64,
    format_book_message
)
from bot.keyboards import reply_keyboards
from conversation_states import (
    CREATE_BOOK_TITLE, CREATE_BOOK_DESC, CREATE_BOOK_AUTHOR, CREATE_BOOK_DATE,
    CREATE_BOOK_LANG, CREATE_BOOK_CATEGORIES, CREATE_BOOK_TYPE, CREATE_BOOK_PRICE,
    CREATE_BOOK_IMAGE,
    MY_BOOKS_CHOOSE_ACTION, MY_BOOKS_CHOOSE_BOOK_INDEX, MY_BOOKS_CONFIRM_DELETE,
    MY_BOOKS_EDIT_TITLE, MY_BOOKS_EDIT_DESCRIPTION, MY_BOOKS_EDIT_AUTHOR,
    MY_BOOKS_EDIT_DATE, MY_BOOKS_EDIT_LANGUAGE, MY_BOOKS_EDIT_CATEGORIES,
    MY_BOOKS_EDIT_IMAGE, MY_BOOKS_EDIT_TYPE, MY_BOOKS_EDIT_PRICE
)
from bot.handlers.menu import show_menu


async def start_create_book_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await check_user_logged_in(update, context):
        return ConversationHandler.END
    await update.message.reply_text(
        "📘 Введите название книги:",
        reply_markup=reply_keyboards.create_book_cancel_markup
    )
    context.user_data['new_book_data'] = {}
    return CREATE_BOOK_TITLE


async def title_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_book_data']['title'] = update.message.text
    await update.message.reply_text(
        "✏️ Введите описание:",
        reply_markup=reply_keyboards.create_book_cancel_markup
    )
    return CREATE_BOOK_DESC


async def desc_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_book_data']['description'] = update.message.text
    await update.message.reply_text(
        "👤 Введите имя автора:",
        reply_markup=reply_keyboards.create_book_cancel_markup
    )
    return CREATE_BOOK_AUTHOR


async def author_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_book_data']['author'] = update.message.text
    await update.message.reply_text(
        "📅 Введите дату публикации (например, 2025-05-20):",
        reply_markup=reply_keyboards.create_book_cancel_markup
    )
    return CREATE_BOOK_DATE


async def date_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_book_data']['publishedDate'] = update.message.text + "T00:00:00.000Z"
    await update.message.reply_text(
        "🌐 Введите язык:",
        reply_markup=reply_keyboards.create_book_cancel_markup
    )
    return CREATE_BOOK_LANG


async def lang_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_book_data']['language'] = update.message.text
    await update.message.reply_text(
        "🏷 Введите категории (через запятую):",
        reply_markup=reply_keyboards.create_book_cancel_markup
    )
    return CREATE_BOOK_CATEGORIES


async def categories_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    categories = [cat.strip() for cat in update.message.text.split(",") if cat.strip()]
    context.user_data['new_book_data']['categories'] = categories
    await update.message.reply_text(
        "📦 Введите тип книги (например, forSale или free):",
        reply_markup=reply_keyboards.create_book_cancel_markup
    )
    return CREATE_BOOK_TYPE


async def type_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_book_data']['type'] = update.message.text
    await update.message.reply_text(
        "💰 Введите цену:",
        reply_markup=reply_keyboards.create_book_cancel_markup
    )
    return CREATE_BOOK_PRICE


async def price_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        price_text = update.message.text.replace(',', '.')
        context.user_data['new_book_data']['price'] = float(price_text)
        await update.message.reply_text(
            "📷 Отправьте изображение книги:",
            reply_markup=reply_keyboards.create_book_cancel_markup
        )
        return CREATE_BOOK_IMAGE
    except ValueError:
        await update.message.reply_text(
            "⚠️ Введите корректную цену (число):",
            reply_markup=reply_keyboards.create_book_cancel_markup
        )
        return CREATE_BOOK_PRICE


async def image_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await check_user_logged_in(update, context):
        context.user_data.pop('new_book_data', None)
        return ConversationHandler.END

    if not update.message.photo:
        await update.message.reply_text(
            "⚠️ Пожалуйста, отправьте изображение.",
            reply_markup=reply_keyboards.create_book_cancel_markup
        )
        return CREATE_BOOK_IMAGE

    user_id = update.effective_user.id
    cookies = session_manager.get_cookies(user_id)
    if not cookies:
        await update.message.reply_text("❌ Ошибка сессии. Попробуйте войти снова.", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop('new_book_data', None)
        await show_menu(update, context)
        return ConversationHandler.END

    photo = await update.message.photo[-1].get_file()
    photo_bytes = await photo.download_as_bytearray()
    image_data_url = encode_image_to_base64(photo_bytes, mime_type="image/jpeg")
    context.user_data['new_book_data']['image'] = image_data_url

    await update.message.reply_text("⏳ Добавляю книгу...", reply_markup=ReplyKeyboardRemove())
    result = api_client.create_book(cookies, context.user_data['new_book_data'])

    if result.get("success"):
        await update.message.reply_text("✅ Книга успешно добавлена!")
    else:
        await handle_api_error(update, result, "❌ Ошибка при добавлении книги.")

    context.user_data.pop('new_book_data', None)
    await show_menu(update, context)
    return ConversationHandler.END


async def cancel_create_book_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop('new_book_data', None)
    await update.message.reply_text("❌ Добавление книги отменено.", reply_markup=ReplyKeyboardRemove())
    await show_menu(update, context)
    return ConversationHandler.END


async def my_books_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await check_user_logged_in(update, context):
        return ConversationHandler.END

    user_id = update.effective_user.id
    cookies = session_manager.get_cookies(user_id)
    await update.message.reply_text("⏳ Загружаю ваши книги...", reply_markup=ReplyKeyboardRemove())
    result = api_client.get_my_books(cookies)

    if result.get("success"):
        books = result.get("data")
        if not books:
            await update.message.reply_text("📭 У вас пока нет книг.")
            await show_menu(update, context)
            return ConversationHandler.END

        context.user_data['my_books_cache'] = books
        message_parts = ["Ваши книги:\n"]
        for i, book_item in enumerate(books):
            message_parts.append(f"<b>{i}.</b> {format_book_message(book_item, owner_name='Вы')}")

        full_message = "\n\n".join(message_parts)
        if len(full_message) > 4096:
            parts_to_send = []
            current_part = "Ваши книги (часть):\n"
            for book_msg in message_parts[1:]:
                if len(current_part) + len(book_msg) + 2 > 4096:
                    parts_to_send.append(current_part)
                    current_part = "Ваши книги (продолжение):\n" + book_msg
                else:
                    current_part += "\n\n" + book_msg
            parts_to_send.append(current_part)

            for part in parts_to_send:
                await update.message.reply_text(part, parse_mode="HTML", reply_markup=reply_keyboards.my_books_action_markup if part == parts_to_send[-1] else ReplyKeyboardRemove())
        else:
            await update.message.reply_text(
                full_message,
                reply_markup=reply_keyboards.my_books_action_markup,
                parse_mode="HTML"
            )
        return MY_BOOKS_CHOOSE_ACTION
    else:
        await handle_api_error(update, result, "⚠️ Не удалось получить список ваших книг.")
        await show_menu(update, context)
        return ConversationHandler.END


async def choose_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    context.user_data.pop('edit_mode', None)
    context.user_data.pop('delete_mode', None)

    if choice == "✏️ Редактировать":
        if not context.user_data.get('my_books_cache'):
             await update.message.reply_text("Сначала нужно загрузить книги. Пожалуйста, используйте команду /mybooks снова.", reply_markup=ReplyKeyboardRemove())
             await show_menu(update, context)
             return ConversationHandler.END
        await update.message.reply_text("Введите номер книги из списка выше, которую хотите редактировать:",
                                        reply_markup=ReplyKeyboardRemove())
        context.user_data['edit_mode'] = True
        return MY_BOOKS_CHOOSE_BOOK_INDEX
    elif choice == "🗑 Удалить":
        if not context.user_data.get('my_books_cache'):
             await update.message.reply_text("Сначала нужно загрузить книги. Пожалуйста, используйте команду /mybooks снова.", reply_markup=ReplyKeyboardRemove())
             await show_menu(update, context)
             return ConversationHandler.END
        await update.message.reply_text("Введите номер книги из списка выше, которую хотите удалить:",
                                        reply_markup=ReplyKeyboardRemove())
        context.user_data['delete_mode'] = True
        return MY_BOOKS_CHOOSE_BOOK_INDEX
    elif choice == "❌ Отмена":
        await update.message.reply_text("❌ Действие отменено.", reply_markup=ReplyKeyboardRemove())
        context.user_data.clear()
        await show_menu(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Неизвестный выбор. Пожалуйста, используйте кнопки.", reply_markup=reply_keyboards.my_books_action_markup)
        return MY_BOOKS_CHOOSE_ACTION


async def choose_book_index_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        index = int(update.message.text)
        books = context.user_data.get('my_books_cache')
        if not books or not (0 <= index < len(books)):
            await update.message.reply_text("🚫 Неверный номер книги. Пожалуйста, введите номер из списка или /cancel.")
            return MY_BOOKS_CHOOSE_BOOK_INDEX

        context.user_data['selected_book_original'] = books[index].copy()
        context.user_data['selected_book_id'] = books[index]['_id']

        if context.user_data.get('delete_mode'):
            await update.message.reply_text(
                f"Вы уверены, что хотите удалить книгу \"{books[index].get('title', 'Без названия')}\"? (да/нет)",
                reply_markup=ReplyKeyboardRemove()
            )
            return MY_BOOKS_CONFIRM_DELETE
        elif context.user_data.get('edit_mode'):
            context.user_data['edited_book_data'] = {}
            first_edit_state = _EDIT_STATES_SEQUENCE[0]
            context.user_data['_current_edit_state_marker'] = first_edit_state
            await update.message.reply_text(
                f"Редактирование книги: <b>{books[index].get('title', 'Без названия')}</b>\n"
                f"{_EDIT_PROMPTS.get(first_edit_state, 'Введите новое значение:')}",
                parse_mode="HTML",
                reply_markup=reply_keyboards.create_book_cancel_markup
            )
            return first_edit_state
        else:
            await update.message.reply_text("Ошибка: режим не выбран (ни удаление, ни редактирование).", reply_markup=ReplyKeyboardRemove())
            context.user_data.clear()
            await show_menu(update, context)
            return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("🚫 Пожалуйста, введите корректный номер (число) или /cancel.")
        return MY_BOOKS_CHOOSE_BOOK_INDEX


async def confirm_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    confirmation = update.message.text.lower()
    if confirmation in ["да", "yes"]:
        cookies = session_manager.get_cookies(user_id)
        book_id = context.user_data.get('selected_book_id')
        if not cookies or not book_id:
            await update.message.reply_text("Ошибка сессии или ID книги. Попробуйте снова.", reply_markup=ReplyKeyboardRemove())
            context.user_data.clear()
            await show_menu(update, context)
            return ConversationHandler.END

        await update.message.reply_text("⏳ Удаляю книгу...", reply_markup=ReplyKeyboardRemove())
        result = api_client.delete_book(cookies, book_id)
        if result.get("success"):
            await update.message.reply_text("✅ Книга удалена.")
        else:
            await handle_api_error(update, result, "⚠️ Не удалось удалить книгу.")
    else:
        await update.message.reply_text("❌ Удаление отменено.")

    context.user_data.clear()
    await show_menu(update, context)
    return ConversationHandler.END


_EDIT_STATES_SEQUENCE = [
    MY_BOOKS_EDIT_TITLE, MY_BOOKS_EDIT_DESCRIPTION, MY_BOOKS_EDIT_AUTHOR,
    MY_BOOKS_EDIT_DATE, MY_BOOKS_EDIT_LANGUAGE, MY_BOOKS_EDIT_CATEGORIES,
    MY_BOOKS_EDIT_IMAGE, MY_BOOKS_EDIT_TYPE, MY_BOOKS_EDIT_PRICE
]
_EDIT_PROMPTS = {
    MY_BOOKS_EDIT_TITLE: "Введите новое название или /skip:",
    MY_BOOKS_EDIT_DESCRIPTION: "Введите новое описание или /skip:",
    MY_BOOKS_EDIT_AUTHOR: "Введите нового автора или /skip:",
    MY_BOOKS_EDIT_DATE: "Введите новую дату публикации (ГГГГ-ММ-ДД) или /skip:",
    MY_BOOKS_EDIT_LANGUAGE: "Введите новый язык или /skip:",
    MY_BOOKS_EDIT_CATEGORIES: "Введите новые категории (через запятую) или /skip:",
    MY_BOOKS_EDIT_IMAGE: "Отправьте URL нового изображения, 'нет' для удаления, или /skip:",
    MY_BOOKS_EDIT_TYPE: "Введите новый тип (например, forSale, free) или /skip:",
    MY_BOOKS_EDIT_PRICE: "Введите новую цену или /skip:",
}
_EDIT_DATA_KEYS = {
    MY_BOOKS_EDIT_TITLE: "title", MY_BOOKS_EDIT_DESCRIPTION: "description",
    MY_BOOKS_EDIT_AUTHOR: "author", MY_BOOKS_EDIT_DATE: "publishedDate",
    MY_BOOKS_EDIT_LANGUAGE: "language", MY_BOOKS_EDIT_CATEGORIES: "categories",
    MY_BOOKS_EDIT_IMAGE: "image", MY_BOOKS_EDIT_TYPE: "type",
    MY_BOOKS_EDIT_PRICE: "price",
}


def _process_field_data(context: ContextTypes.DEFAULT_TYPE, current_state: int, value: str) -> bool:
    data_key = _EDIT_DATA_KEYS.get(current_state)
    if not data_key: return False

    edited_data = context.user_data.setdefault('edited_book_data', {})

    if current_state == MY_BOOKS_EDIT_CATEGORIES:
        edited_data[data_key] = [c.strip() for c in value.split(",") if c.strip()]
    elif current_state == MY_BOOKS_EDIT_PRICE:
        try:
            price_text = value.replace(',', '.')
            edited_data[data_key] = float(price_text)
        except ValueError:
            return False
    elif current_state == MY_BOOKS_EDIT_DATE:
        edited_data[data_key] = value + "T00:00:00.000Z"
    elif current_state == MY_BOOKS_EDIT_IMAGE:
        if value.lower() == 'нет':
            edited_data[data_key] = None
        else:
            edited_data[data_key] = value
    else:
        edited_data[data_key] = value
    return True


async def _prompt_next_edit_or_save(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                    current_field_state_being_left: int) -> int:
    try:
        current_index = _EDIT_STATES_SEQUENCE.index(current_field_state_being_left)
        next_index = current_index + 1

        if next_index < len(_EDIT_STATES_SEQUENCE):
            next_state = _EDIT_STATES_SEQUENCE[next_index]
            prompt_message = _EDIT_PROMPTS.get(next_state, "Введите следующее значение или /skip:")
            await update.message.reply_text(
                prompt_message,
                reply_markup=reply_keyboards.create_book_cancel_markup
            )
            context.user_data['_current_edit_state_marker'] = next_state
            return next_state
        else:
            return await save_edited_book_handler(update, context)
    except ValueError:
        await update.message.reply_text("Произошла ошибка в последовательности редактирования. Попробуйте /cancel и начните заново.")
        context.user_data.clear()
        await show_menu(update, context)
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"Произошла неожиданная ошибка: {e}. Попробуйте /cancel и начните заново.")
        context.user_data.clear()
        await show_menu(update, context)
        return ConversationHandler.END


async def universal_edit_field_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    current_field_state = context.user_data.get('_current_edit_state_marker')
    if current_field_state is None:
        await update.message.reply_text("Ошибка: не удалось определить текущий шаг редактирования. Пожалуйста, /cancel и начните заново.")
        context.user_data.clear()
        await show_menu(update, context)
        return ConversationHandler.END

    value = update.message.text
    if not _process_field_data(context, current_field_state, value):
        if current_field_state == MY_BOOKS_EDIT_PRICE:
            await update.message.reply_text(
                "⚠️ Неверный формат цены. Введите число (например, 10.99) или /skip.",
                reply_markup=reply_keyboards.create_book_cancel_markup
            )
            return current_field_state
        await update.message.reply_text(
            "⚠️ Введены некорректные данные. Пожалуйста, попробуйте снова или /skip.",
            reply_markup=reply_keyboards.create_book_cancel_markup
        )
        return current_field_state

    return await _prompt_next_edit_or_save(update, context, current_field_state)


async def skip_edit_field_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    current_field_state = context.user_data.get('_current_edit_state_marker')
    if current_field_state is None:
        await update.message.reply_text("Ошибка: не удалось определить текущий шаг для пропуска. Пожалуйста, /cancel и начните заново.")
        context.user_data.clear()
        await show_menu(update, context)
        return ConversationHandler.END

    return await _prompt_next_edit_or_save(update, context, current_field_state)


async def save_edited_book_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    cookies = session_manager.get_cookies(user_id)
    book_id = context.user_data.get('selected_book_id')
    complete_payload = context.user_data.get('selected_book_original', {}).copy()
    edited_data_from_user = context.user_data.get('edited_book_data', {})
    complete_payload.update(edited_data_from_user)

    if not cookies or not book_id:
        await update.message.reply_text("Ошибка сессии или ID книги для сохранения. Попробуйте снова.", reply_markup=ReplyKeyboardRemove())
        context.user_data.clear()
        await show_menu(update, context)
        return ConversationHandler.END

    await update.message.reply_text("⏳ Сохраняю изменения...", reply_markup=ReplyKeyboardRemove())
    result = api_client.update_book(cookies, book_id, complete_payload)

    if result.get("success"):
        await update.message.reply_text("✅ Книга успешно обновлена.")
    else:
        await handle_api_error(update, result, "⚠️ Не удалось обновить книгу.")

    context.user_data.clear()
    await show_menu(update, context)
    return ConversationHandler.END


async def cancel_my_books_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ Действие с книгами отменено.", reply_markup=ReplyKeyboardRemove())
    await show_menu(update, context)
    return ConversationHandler.END