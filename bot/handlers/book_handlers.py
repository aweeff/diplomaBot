# bot/handlers/book_handlers.py
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
from .conversation_states import (
    CREATE_BOOK_TITLE, CREATE_BOOK_DESC, CREATE_BOOK_AUTHOR, CREATE_BOOK_DATE,
    CREATE_BOOK_LANG, CREATE_BOOK_CATEGORIES, CREATE_BOOK_TYPE, CREATE_BOOK_PRICE,
    CREATE_BOOK_IMAGE,
    MY_BOOKS_CHOOSE_ACTION, MY_BOOKS_CHOOSE_BOOK_INDEX, MY_BOOKS_CONFIRM_DELETE,
    MY_BOOKS_EDIT_TITLE, MY_BOOKS_EDIT_DESCRIPTION, MY_BOOKS_EDIT_AUTHOR,
    MY_BOOKS_EDIT_DATE, MY_BOOKS_EDIT_LANGUAGE, MY_BOOKS_EDIT_CATEGORIES,
    MY_BOOKS_EDIT_IMAGE, MY_BOOKS_EDIT_TYPE, MY_BOOKS_EDIT_PRICE
)


# --- Create Book Conversation ---
# ... (Create Book functions remain the same as previously provided - I'll skip repeating them for brevity) ...
async def start_create_book_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await check_user_logged_in(update, context):
        return ConversationHandler.END
    await update.message.reply_text("📘 Введите название книги:")
    context.user_data['new_book_data'] = {}
    return CREATE_BOOK_TITLE


async def title_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_book_data']['title'] = update.message.text
    await update.message.reply_text("✏️ Введите описание:")
    return CREATE_BOOK_DESC


async def desc_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_book_data']['description'] = update.message.text
    await update.message.reply_text("👤 Введите имя автора:")
    return CREATE_BOOK_AUTHOR


async def author_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_book_data']['author'] = update.message.text
    await update.message.reply_text("📅 Введите дату публикации (например, 2025-05-20):")
    return CREATE_BOOK_DATE


async def date_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_book_data']['publishedDate'] = update.message.text + "T00:00:00.000Z"
    await update.message.reply_text("🌐 Введите язык:")
    return CREATE_BOOK_LANG


async def lang_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_book_data']['language'] = update.message.text
    await update.message.reply_text("🏷 Введите категории (через запятую):")
    return CREATE_BOOK_CATEGORIES


async def categories_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    categories = [cat.strip() for cat in update.message.text.split(",")]
    context.user_data['new_book_data']['categories'] = categories
    await update.message.reply_text("📦 Введите тип книги (например, forSale или free):")
    return CREATE_BOOK_TYPE


async def type_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_book_data']['type'] = update.message.text
    await update.message.reply_text("💰 Введите цену:")
    return CREATE_BOOK_PRICE


async def price_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['new_book_data']['price'] = float(update.message.text)
        await update.message.reply_text("📷 Отправьте изображение книги:")
        return CREATE_BOOK_IMAGE
    except ValueError:
        await update.message.reply_text("⚠️ Введите корректную цену (число):")
        return CREATE_BOOK_PRICE


async def image_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await check_user_logged_in(update, context):  # Ensure still logged in
        context.user_data.pop('new_book_data', None)
        return ConversationHandler.END

    if not update.message.photo:
        await update.message.reply_text("⚠️ Пожалуйста, отправьте изображение.")
        return CREATE_BOOK_IMAGE

    user_id = update.effective_user.id
    cookies = session_manager.get_cookies(user_id)
    if not cookies:
        await update.message.reply_text("❌ Ошибка сессии. Попробуйте войти снова.")
        context.user_data.pop('new_book_data', None)
        return ConversationHandler.END

    photo = await update.message.photo[-1].get_file()
    photo_bytes = await photo.download_as_bytearray()
    image_data_url = encode_image_to_base64(photo_bytes, mime_type="image/jpeg")
    context.user_data['new_book_data']['image'] = image_data_url

    result = api_client.create_book(cookies, context.user_data['new_book_data'])

    if result.get("success"):
        await update.message.reply_text("✅ Книга успешно добавлена!")
    else:
        await handle_api_error(update, result, "❌ Ошибка при добавлении книги.")

    context.user_data.pop('new_book_data', None)
    return ConversationHandler.END


async def cancel_create_book_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop('new_book_data', None)
    await update.message.reply_text("❌ Добавление книги отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# --- My Books (View, Edit, Delete) Conversation ---
async def my_books_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        print(f"CRITICAL: update.message is None in my_books_command. Update: {update}")
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Произошла внутренняя ошибка (update.message is None). Пожалуйста, попробуйте еще раз."
            )
        return ConversationHandler.END
    # ... (rest of my_books_command from previous correct version)
    user_id = update.effective_user.id
    if not await check_user_logged_in(update, context):
        return ConversationHandler.END

    cookies = session_manager.get_cookies(user_id)
    result = api_client.get_my_books(cookies)

    if result.get("success"):
        books = result.get("data")
        if not books:  # Handles if books is None or empty list
            await update.message.reply_text("📭 У вас пока нет книг.")
            return ConversationHandler.END

        context.user_data['my_books_cache'] = books
        message_parts = []
        for i, book_item in enumerate(books):  # Renamed book to book_item to avoid conflict
            message_parts.append(f"{i}. {format_book_message(book_item, owner_name='Вы')}")

        full_message = "Ваши книги:\n\n" + "\n\n".join(message_parts)
        await update.message.reply_text(
            full_message,
            reply_markup=reply_keyboards.my_books_action_markup,
            parse_mode="HTML"
        )
        return MY_BOOKS_CHOOSE_ACTION
    else:
        await handle_api_error(update, result, "⚠️ Не удалось получить список ваших книг.")
        return ConversationHandler.END


async def choose_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (choose_action_handler from previous correct version) ...
    choice = update.message.text
    if choice == "✏️ Редактировать":
        await update.message.reply_text("Введите номер книги из списка выше, которую хотите редактировать:",
                                        reply_markup=ReplyKeyboardRemove())
        context.user_data['edit_mode'] = True
        context.user_data.pop('delete_mode', None)  # Clear other mode
        return MY_BOOKS_CHOOSE_BOOK_INDEX
    elif choice == "🗑 Удалить":
        await update.message.reply_text("Введите номер книги из списка выше, которую хотите удалить:",
                                        reply_markup=ReplyKeyboardRemove())
        context.user_data['delete_mode'] = True
        context.user_data.pop('edit_mode', None)  # Clear other mode
        return MY_BOOKS_CHOOSE_BOOK_INDEX
    else:
        await update.message.reply_text("❌ Действие отменено.", reply_markup=ReplyKeyboardRemove())
        context.user_data.clear()
        return ConversationHandler.END


async def choose_book_index_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (choose_book_index_handler with logging as previously suggested) ...
    try:
        index = int(update.message.text)
        books = context.user_data.get('my_books_cache')
        if not books or not (0 <= index < len(books)):
            await update.message.reply_text("🚫 Неверный номер книги. Пожалуйста, введите номер из списка.")
            return MY_BOOKS_CHOOSE_BOOK_INDEX

        context.user_data['selected_book_original'] = books[index].copy()
        context.user_data['selected_book_id'] = books[index]['_id']

        if context.user_data.get('delete_mode'):
            await update.message.reply_text(
                f"Вы уверены, что хотите удалить книгу \"{books[index].get('title', 'Без названия')}\"? (да/нет)"
            )
            return MY_BOOKS_CONFIRM_DELETE
        elif context.user_data.get('edit_mode'):
            context.user_data['edited_book_data'] = {}
            first_edit_state = _EDIT_STATES_SEQUENCE[0]
            # LOGGING: Setting initial marker
            print(
                f"[choose_book_index_handler] INITIATING EDIT. Setting _current_edit_state_marker to: {first_edit_state} ({_EDIT_PROMPTS.get(first_edit_state, 'Unknown Prompt')})")
            context.user_data['_current_edit_state_marker'] = first_edit_state
            await update.message.reply_text(
                f"Редактирование книги: <b>{books[index].get('title', 'Без названия')}</b>\n"
                f"{_EDIT_PROMPTS[first_edit_state]}",
                parse_mode="HTML"
            )
            return first_edit_state
        else:
            await update.message.reply_text("Неизвестное действие.", reply_markup=ReplyKeyboardRemove())
            context.user_data.clear()
            return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("🚫 Пожалуйста, введите корректный номер (число).")
        return MY_BOOKS_CHOOSE_BOOK_INDEX


async def confirm_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (confirm_delete_handler from previous correct version) ...
    user_id = update.effective_user.id
    confirmation = update.message.text.lower()
    if confirmation in ["да", "yes"]:
        cookies = session_manager.get_cookies(user_id)
        book_id = context.user_data.get('selected_book_id')
        if not cookies or not book_id:
            await update.message.reply_text("Ошибка сессии или ID книги. Попробуйте снова.")
            context.user_data.clear()
            return ConversationHandler.END

        result = api_client.delete_book(cookies, book_id)
        if result.get("success"):
            await update.message.reply_text("✅ Книга удалена.")
        else:
            await handle_api_error(update, result, "⚠️ Не удалось удалить книгу.")
    else:
        await update.message.reply_text("❌ Удаление отменено.")
    context.user_data.clear()
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
    MY_BOOKS_EDIT_DATE: "Введите новую дату публикации (YYYY-MM-DD) или /skip:",
    MY_BOOKS_EDIT_LANGUAGE: "Введите новый язык или /skip:",
    MY_BOOKS_EDIT_CATEGORIES: "Введите новые категории (через запятую) или /skip:",
    MY_BOOKS_EDIT_IMAGE: "Отправьте URL нового изображения, 'none' для удаления, или /skip:",
    MY_BOOKS_EDIT_TYPE: "Введите новый тип (например, forSale) или /skip:",
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
    data_key = _EDIT_DATA_KEYS[current_state]
    edited_data = context.user_data.setdefault('edited_book_data', {})
    print(f"[_process_field_data] Processing data for state {current_state}, key '{data_key}', value '{value}'")

    if current_state == MY_BOOKS_EDIT_CATEGORIES:
        edited_data[data_key] = [c.strip() for c in value.split(",") if c.strip()]
    elif current_state == MY_BOOKS_EDIT_PRICE:
        try:
            edited_data[data_key] = float(value)
        except ValueError:
            print(f"[_process_field_data] ValueError for price. Not assigning.")
            return False
    elif current_state == MY_BOOKS_EDIT_DATE:
        edited_data[data_key] = value + "T00:00:00.000Z"
    elif current_state == MY_BOOKS_EDIT_IMAGE and value.lower() == 'none':
        edited_data[data_key] = None
    else:
        edited_data[data_key] = value
    print(f"[_process_field_data] New edited_book_data: {context.user_data['edited_book_data']}")
    return True


async def _prompt_next_edit_or_save(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                    current_field_state_being_left: int) -> int:
    print(f"[_prompt_next_edit_or_save] Attempting to move from state: {current_field_state_being_left}")
    try:
        current_index = _EDIT_STATES_SEQUENCE.index(current_field_state_being_left)
        print(
            f"[_prompt_next_edit_or_save] current_index for state {current_field_state_being_left} is: {current_index}")
        next_index = current_index + 1
        print(f"[_prompt_next_edit_or_save] next_index is: {next_index}")

        if next_index < len(_EDIT_STATES_SEQUENCE):
            next_state = _EDIT_STATES_SEQUENCE[next_index]
            prompt_message = _EDIT_PROMPTS[next_state]
            print(f"[_prompt_next_edit_or_save] Next state: {next_state}. Prompt: '{prompt_message}'")
            await update.message.reply_text(prompt_message)
            context.user_data['_current_edit_state_marker'] = next_state
            print(f"[_prompt_next_edit_or_save] Set _current_edit_state_marker to: {next_state}")
            return next_state
        else:
            print(f"[_prompt_next_edit_or_save] All fields processed. Calling save_edited_book_handler.")
            return await save_edited_book_handler(update, context)
    except ValueError:
        error_msg = f"[_prompt_next_edit_or_save] ValueError: State {current_field_state_being_left} not found in _EDIT_STATES_SEQUENCE."
        print(error_msg)
        await update.message.reply_text("Произошла ошибка в последовательности редактирования (индекс не найден).")
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        error_msg = f"[_prompt_next_edit_or_save] Unexpected error: {e}"
        print(error_msg)
        await update.message.reply_text(f"Произошла неожиданная ошибка: {e}")
        context.user_data.clear()
        return ConversationHandler.END


async def universal_edit_field_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    current_field_state = context.user_data.get('_current_edit_state_marker')
    print(
        f"[universal_edit_field_handler] Current marker: {current_field_state}, Received text: '{update.message.text}'")

    if current_field_state is None:
        await update.message.reply_text("Ошибка: не удалось определить текущий шаг редактирования.")
        print(f"[universal_edit_field_handler] _current_edit_state_marker is None. Ending conversation.")
        context.user_data.clear()
        return ConversationHandler.END

    if current_field_state == MY_BOOKS_EDIT_PRICE:
        try:
            float(update.message.text)
        except ValueError:
            await update.message.reply_text("⚠️ Неверный формат цены. Введите число или /skip.")
            print(
                f"[universal_edit_field_handler] Invalid price format. Returning current state: {current_field_state}")
            return current_field_state

    success = _process_field_data(context, current_field_state, update.message.text)
    if not success and current_field_state == MY_BOOKS_EDIT_PRICE:  # Special case for price validation failure
        print(f"[universal_edit_field_handler] Price processing failed. Returning current state: {current_field_state}")
        return current_field_state

    print(
        f"[universal_edit_field_handler] Data processed. Calling _prompt_next_edit_or_save from state {current_field_state}.")
    return await _prompt_next_edit_or_save(update, context, current_field_state)


async def skip_edit_field_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    current_field_state = context.user_data.get('_current_edit_state_marker')
    print(f"[skip_edit_field_handler] Current marker: {current_field_state}")

    if current_field_state is None:
        await update.message.reply_text("Ошибка: не удалось определить текущий шаг для пропуска.")
        print(f"[skip_edit_field_handler] _current_edit_state_marker is None. Ending conversation.")
        context.user_data.clear()
        return ConversationHandler.END

    print(
        f"[skip_edit_field_handler] Skipping field for state {current_field_state}. Calling _prompt_next_edit_or_save.")
    return await _prompt_next_edit_or_save(update, context, current_field_state)


async def save_edited_book_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (save_edited_book_handler as previously provided, ensure thorough context cleanup)
    print("[save_edited_book_handler] Entered.")
    user_id = update.effective_user.id
    cookies = session_manager.get_cookies(user_id)
    book_id = context.user_data.get('selected_book_id')
    original_book = context.user_data.get('selected_book_original', {})
    edited_data_from_user = context.user_data.get('edited_book_data', {})

    if not cookies or not book_id:
        await update.message.reply_text("Ошибка сессии или ID книги для сохранения. Попробуйте снова.")
        print("[save_edited_book_handler] Missing cookies or book_id.")
        context.user_data.clear()
        return ConversationHandler.END

    complete_payload = original_book.copy()
    for data_key_name, edited_value in edited_data_from_user.items():
        complete_payload[data_key_name] = edited_value

    print(f"[save_edited_book_handler] Final payload for update: {complete_payload}")
    result = api_client.update_book(cookies, book_id, complete_payload)

    if result.get("success"):
        await update.message.reply_text("✅ Книга успешно обновлена.")
    else:
        await handle_api_error(update, result, "⚠️ Не удалось обновить книгу.")

    print("[save_edited_book_handler] Clearing context and ending conversation.")
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_my_books_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print("[cancel_my_books_action] Cancelling and clearing context.")
    context.user_data.clear()
    await update.message.reply_text("❌ Действие с книгами отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END