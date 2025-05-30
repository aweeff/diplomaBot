# In aweeff/diplomabot/diplomaBot-ac4a0d2651b7e9c7d585310ef9fb97f87d4bf1ed/bot/handlers/general_handlers.py
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from bot.keyboards import reply_keyboards, inline_keyboards  # inline_keyboards is used for genre selection
from bot.services import api_client
from bot.states import session_manager
from bot.utils.helpers import handle_api_error, format_book_message  # Removed check_user_logged_in if not used directly
from .conversation_states import RECOMMENDATIONS_SELECTING_GENRES  # Keep this if recommendations flow is kept
from bot.handlers.menu import show_menu


# This is the version of list_all_books_command before reply-keyboard pagination
# It uses embedded owner details and shows the first 5 books.
async def list_all_books_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    cookies = session_manager.get_cookies(user_id)

    await update.message.reply_text("⏳ Загружаю список книг...", reply_markup=ReplyKeyboardRemove())
    result = api_client.get_all_books(cookies=cookies)

    if result.get("success"):
        books_data = result.get("data")
        if not books_data:
            await update.message.reply_text("❗️Нет доступных книг в каталоге.")
            # Optionally, show main menu
            # await show_menu(update, context)
            return

        await update.message.reply_text(f"📚 Найдено книг: {len(books_data)}. Показываю первые несколько (до 5):")
        for book in books_data[:5]:  # Display first 5 books
            owner_name_display = "Неизвестен"
            embedded_owner_info = book.get("owner")
            if embedded_owner_info and isinstance(embedded_owner_info, dict):
                owner_email = embedded_owner_info.get("email")
                if owner_email:
                    owner_name_display = owner_email

            message_text = format_book_message(book, owner_name=owner_name_display)
            image_url = book.get("image")

            try:
                if image_url:
                    await update.message.reply_photo(photo=image_url, caption=message_text, parse_mode="HTML")
                else:
                    await update.message.reply_text(message_text, parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"📖 {book.get('title', 'Книга')} (ошибка отображения деталей: {e})")
        # After listing books, you might want to show the main menu again
        # await show_menu(update, context) # Or let the user issue a new command
    else:
        await handle_api_error(update, result, "⚠️ Ошибка при получении списка книг.")
        # await show_menu(update, context)


# --- Recommendations Handlers ---
# recommendations_start_command remains the same as it initiates genre selection
async def recommendations_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    # Re-add check_user_logged_in if it was removed and is needed here
    # if not await check_user_logged_in(update, context): # Assuming this helper exists and works
    #     return ConversationHandler.END

    # Check login status manually or via a decorator if check_user_logged_in is not used
    if not session_manager.get_cookies(user_id):
        await update.message.reply_text("❌ Вы не вошли в систему. Используйте /login или команду из меню.")
        return ConversationHandler.END

    cookies = session_manager.get_cookies(user_id)
    await update.message.reply_text("⏳ Загружаю список жанров...", reply_markup=ReplyKeyboardRemove())
    categories_result = api_client.get_all_categories(cookies)

    if not categories_result.get("success") or not categories_result.get("data"):
        await handle_api_error(update, categories_result, "⚠️ Не удалось загрузить жанры.")
        context.user_data.pop('all_categories_map', None)
        context.user_data.pop('selected_rec_category_ids', None)
        await show_menu(update, context)
        return ConversationHandler.END

    all_categories_list = categories_result.get("data")
    if not isinstance(all_categories_list, list) or not all(
            isinstance(cat, dict) and '_id' in cat and 'name' in cat for cat in all_categories_list):
        await update.message.reply_text("⚠️ Получен некорректный формат жанров от сервера.")
        # ... (cleanup context.user_data)
        await show_menu(update, context)
        return ConversationHandler.END

    context.user_data['all_categories_map'] = {cat['_id']: cat['name'] for cat in all_categories_list}
    context.user_data.setdefault('selected_rec_category_ids', set())

    user_prefs_result = api_client.get_user_current_preferences(cookies)
    if user_prefs_result.get("success") and user_prefs_result.get("data"):
        raw_preferences = user_prefs_result.get("data")
        # ... (your existing preference loading logic) ...
        if isinstance(raw_preferences, list):  # Assuming preferences are list of IDs
            context.user_data['selected_rec_category_ids'] = {
                pref_id for pref_id in raw_preferences
                if pref_id in context.user_data['all_categories_map']
            }
        # Add other checks for raw_preferences if necessary

    keyboard = inline_keyboards.create_genre_selection_keyboard(
        context.user_data['all_categories_map'],
        context.user_data['selected_rec_category_ids']
    )
    await update.message.reply_text(
        "👇 Выберите интересующие вас жанры для рекомендации и нажмите '✅ Готово':",
        reply_markup=keyboard
    )
    return RECOMMENDATIONS_SELECTING_GENRES


# handle_genre_selection_callback - this function will call the reverted show_recommendations_after_selection
async def handle_genre_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    cookies = session_manager.get_cookies(user_id)

    if not cookies:
        await query.edit_message_text("Сессия истекла. Пожалуйста, /login и попробуйте снова.")
        context.user_data.pop('all_categories_map', None)
        context.user_data.pop('selected_rec_category_ids', None)
        return ConversationHandler.END

    # Ensure all_categories_map is loaded if not present (from your existing code)
    if 'all_categories_map' not in context.user_data or not context.user_data['all_categories_map']:
        categories_result = api_client.get_all_categories(cookies)
        if categories_result.get("success") and categories_result.get("data"):
            all_categories_list = categories_result.get("data")
            if isinstance(all_categories_list, list) and all(
                    isinstance(cat, dict) and '_id' in cat and 'name' in cat for cat in all_categories_list):
                context.user_data['all_categories_map'] = {cat['_id']: cat['name'] for cat in all_categories_list}
            else:
                await query.edit_message_text(
                    "⚠️ Ошибка: не удалось обновить список жанров (неверный формат). Попробуйте отменить и начать заново.")
                return RECOMMENDATIONS_SELECTING_GENRES
        else:
            await query.edit_message_text(
                "⚠️ Ошибка: не удалось получить список жанров. Попробуйте отменить и начать заново.")
            return RECOMMENDATIONS_SELECTING_GENRES

    selected_ids = context.user_data.setdefault('selected_rec_category_ids', set())
    all_categories_map = context.user_data['all_categories_map']
    callback_data = query.data

    if callback_data == "rec_genre_done":
        if not selected_ids:
            await query.edit_message_text(
                "⚠️ Вы не выбрали ни одного жанра. Пожалуйста, выберите хотя бы один или нажмите '❌ Отмена'."
            )
            keyboard = inline_keyboards.create_genre_selection_keyboard(all_categories_map,
                                                                        selected_ids)  # Re-show keyboard
            try:
                await query.edit_message_reply_markup(reply_markup=keyboard)
            except Exception:
                pass  # If message is not modified, it's fine
            return RECOMMENDATIONS_SELECTING_GENRES

        await query.edit_message_text("💾 Сохраняю ваши предпочтения...")  # Edit the message from genre selection
        update_prefs_result = api_client.update_user_preferences(cookies, list(selected_ids))

        if update_prefs_result.get("success"):
            await query.message.reply_text("✅ Ваши предпочтения по жанрам сохранены!")  # Send new message
            # Now call the function that displays books (which ends the conversation)
            # Ensure show_recommendations_after_selection uses query.message or a new Update object
            return await show_recommendations_after_selection(query.message, context, cookies)
        else:
            # Use query.message to send the error as a new message after editing the original
            await handle_api_error(query.message, update_prefs_result, "⚠️ Не удалось сохранить предпочтения.")
            context.user_data.pop('all_categories_map', None)
            context.user_data.pop('selected_rec_category_ids', None)
            return ConversationHandler.END  # End conversation

    elif callback_data == "rec_genre_cancel":
        return await recommendations_cancel_action(update, context)  # This should handle cleanup and end

    elif callback_data.startswith("rec_genre_"):
        cat_id = callback_data.split("_")[-1]
        if cat_id in selected_ids:
            selected_ids.remove(cat_id)
        else:
            selected_ids.add(cat_id)
        context.user_data['selected_rec_category_ids'] = selected_ids
        new_keyboard = inline_keyboards.create_genre_selection_keyboard(all_categories_map, selected_ids)
        try:
            await query.edit_message_reply_markup(reply_markup=new_keyboard)
        except Exception as e:
            print(f"Ошибка обновления клавиатуры рекомендаций: {e}")
            await query.answer()  # Acknowledge callback
        return RECOMMENDATIONS_SELECTING_GENRES

    await query.edit_message_text("Неизвестное действие.")  # Fallback, should ideally not be reached
    return ConversationHandler.END


# This is the version of show_recommendations_after_selection before reply-keyboard pagination.
# It displays first 5 recommended books and ends the conversation.
async def show_recommendations_after_selection(message_object_or_update_message, context: ContextTypes.DEFAULT_TYPE,
                                               cookies: dict) -> int:
    # If called from a callback, message_object_or_update_message is likely query.message
    # If called directly after a command, it's update.message
    # We will assume message_object_or_update_message can call .reply_text()

    # This message indicates the start of fetching, not the UI for pagination
    await message_object_or_update_message.reply_text("🔍 Ищу книги по вашим предпочтениям...")

    user_prefs_result = api_client.get_user_current_preferences(cookies)
    if not user_prefs_result.get("success") or user_prefs_result.get("data") is None:
        await message_object_or_update_message.reply_text("⚠️ Не удалось загрузить ваши предпочтения...")
        # Clean up context data related to this flow
        context.user_data.pop('all_categories_map', None)
        context.user_data.pop('selected_rec_category_ids', None)
        # Consider calling show_menu here
        return ConversationHandler.END

    preferred_category_ids = user_prefs_result.get("data")
    if not preferred_category_ids:
        await message_object_or_update_message.reply_text("Вы еще не выбрали предпочтительные жанры...")
        context.user_data.pop('all_categories_map', None)
        context.user_data.pop('selected_rec_category_ids', None)
        return ConversationHandler.END

    all_categories_map_id_to_name = context.user_data.get('all_categories_map')
    if not all_categories_map_id_to_name:  # Attempt to reload if missing
        cats_res = api_client.get_all_categories(cookies)
        if cats_res.get("success") and cats_res.get("data"):
            all_categories_list = cats_res.get("data")
            if isinstance(all_categories_list, list) and all(
                    isinstance(cat, dict) and '_id' in cat and 'name' in cat for cat in all_categories_list):
                all_categories_map_id_to_name = {cat['_id']: cat['name'] for cat in all_categories_list}
                context.user_data['all_categories_map'] = all_categories_map_id_to_name
            else:
                all_categories_map_id_to_name = {}
        else:
            all_categories_map_id_to_name = {}

    preferred_category_names = {
        all_categories_map_id_to_name.get(pref_id)
        for pref_id in preferred_category_ids
        if all_categories_map_id_to_name.get(pref_id)
    }
    if not preferred_category_names:
        await message_object_or_update_message.reply_text(
            "Не удалось сопоставить ваши предпочтения с известными жанрами...")
        context.user_data.pop('all_categories_map', None)
        context.user_data.pop('selected_rec_category_ids', None)
        return ConversationHandler.END

    all_books_result = api_client.get_all_books(cookies)
    if not all_books_result.get("success") or not all_books_result.get("data"):
        await message_object_or_update_message.reply_text("⚠️ Не удалось загрузить список книг для рекомендаций.")
        context.user_data.pop('all_categories_map', None)
        context.user_data.pop('selected_rec_category_ids', None)
        return ConversationHandler.END

    all_books = all_books_result.get("data")
    recommended_books = []
    if not all_books:
        await message_object_or_update_message.reply_text("❗️ На данный момент нет доступных книг в каталоге.")
        # ... cleanup ...
        return ConversationHandler.END

    for book_item_data in all_books:
        book_category_names = book_item_data.get("categories", [])
        if not isinstance(book_category_names, list): book_category_names = []
        if any(cat_name in preferred_category_names for cat_name in book_category_names):
            recommended_books.append(book_item_data)

    if not recommended_books:
        pref_names_str = ", ".join(sorted(list(preferred_category_names))) or "выбранным"
        await message_object_or_update_message.reply_text(
            f"😔 К сожалению, по вашим {pref_names_str} предпочтениям ничего не найдено.")
    else:
        await message_object_or_update_message.reply_text(
            f"📚 Вот книги по вашим предпочтениям ({len(recommended_books)} шт.). Показываю первые несколько (до 5):")
        for book_to_display in recommended_books[:5]:  # Display first 5
            owner_name_display = "Неизвестен"
            embedded_owner_info = book_to_display.get("owner")
            if embedded_owner_info and isinstance(embedded_owner_info, dict):
                owner_email = embedded_owner_info.get("email")
                if owner_email:
                    owner_name_display = owner_email
            message_text = format_book_message(book_to_display, owner_name=owner_name_display)
            image_url = book_to_display.get("image")
            try:
                if image_url:
                    await message_object_or_update_message.reply_photo(photo=image_url, caption=message_text,
                                                                       parse_mode="HTML")
                else:
                    await message_object_or_update_message.reply_text(message_text, parse_mode="HTML")
            except Exception as e_send:
                await message_object_or_update_message.reply_text(
                    f"Не удалось отобразить книгу: {book_to_display.get('title', '')} (ошибка: {e_send})")

    # Clean up context data specific to this recommendation flow
    context.user_data.pop('all_categories_map', None)
    context.user_data.pop('selected_rec_category_ids', None)
    # context.user_data.pop('final_preferred_category_names_for_recommendations', None) # if you added this

    # Show main menu keyboard after recommendations
    final_menu_markup = reply_keyboards.logged_in_menu_markup if cookies else reply_keyboards.guest_menu_markup
    await message_object_or_update_message.reply_text("Просмотр рекомендаций завершен.", reply_markup=final_menu_markup)
    # No more /menu prompt here as we set the keyboard directly
    return ConversationHandler.END  # This function now ends the conversation.


async def recommendations_cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    cookies = session_manager.get_cookies(user_id)
    current_menu_markup = reply_keyboards.logged_in_menu_markup if cookies else reply_keyboards.guest_menu_markup

    message_to_use = update.message
    if update.callback_query:
        await update.callback_query.answer()
        message_to_use = update.callback_query.message
        try:
            await update.callback_query.edit_message_text("❌ Получение рекомендаций отменено.")
        except Exception:  # If editing failed (e.g. message too old)
            # Still send a new message to confirm cancellation and show menu
            await message_to_use.reply_text("❌ Получение рекомендаций отменено.", reply_markup=current_menu_markup)

    else:  # If it's a command
        await message_to_use.reply_text("❌ Получение рекомендаций отменено.", reply_markup=current_menu_markup)

    # If the message was edited and the new text doesn't include the menu prompt, send it.
    # Or, always ensure the menu prompt is there after cancellation.
    # Simplified: show_menu will handle the text and markup.
    await show_menu(message_to_use, context)

    context.user_data.pop('all_categories_map', None)
    context.user_data.pop('selected_rec_category_ids', None)
    # Clear any other recommendation specific data
    # context.user_data.pop('final_preferred_category_names_for_recommendations', None)
    return ConversationHandler.END