from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from bot.keyboards import reply_keyboards, inline_keyboards
from bot.services import api_client
from bot.states import session_manager
from bot.utils.helpers import check_user_logged_in, handle_api_error, format_book_message
from .conversation_states import RECOMMENDATIONS_SELECTING_GENRES
from bot.handlers.menu import show_menu


async def list_all_books_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    cookies = session_manager.get_cookies(user_id)

    await update.message.reply_text("⏳ Загружаю список книг...")
    result = api_client.get_all_books(cookies=cookies)

    if result.get("success"):
        books = result.get("data")
        if not books:
            await update.message.reply_text("❗️Нет доступных книг в каталоге.")
            return

        await update.message.reply_text(f"📚 Найдено книг: {len(books)}. Показываю первые несколько:")
        for book in books[:5]:
            owner_name_display = "Неизвестен"
            owner_id = book.get("owner")
            if owner_id and cookies:
                owner_info_res = await api_client.get_user_by_id_async(owner_id, cookies=cookies)
                if owner_info_res.get("success") and owner_info_res.get("data"):
                    owner_data = owner_info_res.get("data")
                    owner_name_display = owner_data.get("fullName") or owner_data.get("telegramId", "Владелец")

            message_text = format_book_message(book, owner_name=owner_name_display)
            image_url = book.get("image")

            try:
                if image_url:
                    await update.message.reply_photo(photo=image_url, caption=message_text, parse_mode="HTML")
                else:
                    await update.message.reply_text(message_text, parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"📖 {book.get('title', 'Книга')} (ошибка отображения деталей: {e})")
    else:
        await handle_api_error(update, result, "⚠️ Ошибка при получении списка книг.")


async def recommendations_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if not await check_user_logged_in(update, context):
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
        context.user_data.pop('all_categories_map', None)
        context.user_data.pop('selected_rec_category_ids', None)
        await show_menu(update, context)
        return ConversationHandler.END

    context.user_data['all_categories_map'] = {cat['_id']: cat['name'] for cat in all_categories_list}
    context.user_data.setdefault('selected_rec_category_ids', set())

    user_prefs_result = api_client.get_user_current_preferences(cookies)
    if user_prefs_result.get("success") and user_prefs_result.get("data"):
        raw_preferences = user_prefs_result.get("data")
        if isinstance(raw_preferences, list):
            context.user_data['selected_rec_category_ids'] = {pref_id for pref_id in raw_preferences if
                                                              pref_id in context.user_data['all_categories_map']}
        elif isinstance(raw_preferences, dict):
            context.user_data['selected_rec_category_ids'] = {pref_id for pref_id in raw_preferences.keys() if
                                                              pref_id in context.user_data['all_categories_map']}

    keyboard = inline_keyboards.create_genre_selection_keyboard(
        context.user_data['all_categories_map'],
        context.user_data['selected_rec_category_ids']
    )
    await update.message.reply_text(
        "👇 Выберите интересующие вас жанры для рекомендации и нажмите '✅ Готово':",
        reply_markup=keyboard
    )
    return RECOMMENDATIONS_SELECTING_GENRES


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

    if 'all_categories_map' not in context.user_data or not context.user_data['all_categories_map']:
        categories_result = api_client.get_all_categories(cookies)
        if categories_result.get("success") and categories_result.get("data"):
            all_categories_list = categories_result.get("data")
            if isinstance(all_categories_list, list) and all(
                    isinstance(cat, dict) and '_id' in cat and 'name' in cat for cat in all_categories_list):
                context.user_data['all_categories_map'] = {cat['_id']: cat['name'] for cat in all_categories_list}
            else:
                await query.edit_message_text(
                    "⚠️ Ошибка: не удалось обновить список жанров. Попробуйте отменить и начать заново.")
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
            keyboard = inline_keyboards.create_genre_selection_keyboard(all_categories_map, selected_ids)
            await query.edit_message_reply_markup(reply_markup=keyboard)
            return RECOMMENDATIONS_SELECTING_GENRES

        await query.edit_message_text("💾 Сохраняю ваши предпочтения...")
        update_prefs_result = api_client.update_user_preferences(cookies, list(selected_ids))

        if update_prefs_result.get("success"):
            await query.message.reply_text("✅ Ваши предпочтения по жанрам сохранены!")
            return await show_recommendations_after_selection(query.message, context, cookies)
        else:
            await handle_api_error(query.message, update_prefs_result, "⚠️ Не удалось сохранить предпочтения.")
            context.user_data.pop('all_categories_map', None)
            context.user_data.pop('selected_rec_category_ids', None)
            return ConversationHandler.END

    elif callback_data == "rec_genre_cancel":
        await query.edit_message_text("❌ Выбор жанров отменен.")
        context.user_data.pop('all_categories_map', None)
        context.user_data.pop('selected_rec_category_ids', None)
        await query.message.reply_text("Введите /menu для возврата в главное меню.",
                                       reply_markup=reply_keyboards.logged_in_menu_markup if cookies else reply_keyboards.guest_menu_markup)
        return ConversationHandler.END

    elif callback_data.startswith("rec_genre_"):
        cat_id = callback_data.split("_")[-1]

        if cat_id in selected_ids:
            selected_ids.remove(cat_id)
        else:
            selected_ids.add(cat_id)
        context.user_data['selected_rec_category_ids'] = selected_ids

        new_keyboard = inline_keyboards.create_genre_selection_keyboard(
            all_categories_map,
            selected_ids
        )
        try:
            await query.edit_message_reply_markup(reply_markup=new_keyboard)
        except Exception as e:
            print(f"Ошибка обновления клавиатуры рекомендаций: {e}")
        return RECOMMENDATIONS_SELECTING_GENRES

    await query.edit_message_text("Неизвестное действие.")
    return ConversationHandler.END


async def show_recommendations_after_selection(message_object, context: ContextTypes.DEFAULT_TYPE,
                                               cookies: dict) -> int:
    await message_object.reply_text("🔍 Ищу книги по вашим предпочтениям...")

    user_prefs_result = api_client.get_user_current_preferences(cookies)
    if not user_prefs_result.get("success") or user_prefs_result.get("data") is None:
        await message_object.reply_text(
            "⚠️ Не удалось загрузить ваши предпочтения для показа книг или они не установлены.")
        context.user_data.pop('all_categories_map', None)
        context.user_data.pop('selected_rec_category_ids', None)
        return ConversationHandler.END

    preferred_category_ids = user_prefs_result.get("data")
    if not preferred_category_ids:
        await message_object.reply_text(
            "Вы еще не выбрали предпочтительные жанры. Используйте команду /myrecommendations (или кнопку меню) снова, чтобы выбрать их.")
        context.user_data.pop('all_categories_map', None)
        context.user_data.pop('selected_rec_category_ids', None)
        return ConversationHandler.END

    all_categories_map_id_to_name = context.user_data.get('all_categories_map')
    if not all_categories_map_id_to_name:
        cats_res = api_client.get_all_categories(cookies)
        if cats_res.get("success") and cats_res.get("data"):
            all_categories_list = cats_res.get("data")
            if isinstance(all_categories_list, list) and all(
                    isinstance(cat, dict) and '_id' in cat and 'name' in cat for cat in all_categories_list):
                all_categories_map_id_to_name = {cat['_id']: cat['name'] for cat in cats_res.get("data")}
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
        await message_object.reply_text(
            "Не удалось сопоставить ваши предпочтения с известными жанрами. Попробуйте выбрать жанры снова.")
        context.user_data.pop('all_categories_map', None)
        context.user_data.pop('selected_rec_category_ids', None)
        return ConversationHandler.END

    all_books_result = api_client.get_all_books(cookies)
    if not all_books_result.get("success") or not all_books_result.get("data"):
        await message_object.reply_text("⚠️ Не удалось загрузить список книг для рекомендаций.")
        context.user_data.pop('all_categories_map', None)
        context.user_data.pop('selected_rec_category_ids', None)
        return ConversationHandler.END

    all_books = all_books_result.get("data")
    recommended_books = []

    if not all_books:
        await message_object.reply_text("❗️ На данный момент нет доступных книг в каталоге.")
        context.user_data.pop('all_categories_map', None)
        context.user_data.pop('selected_rec_category_ids', None)
        return ConversationHandler.END

    for book in all_books:
        book_category_names = book.get("categories", [])
        if not isinstance(book_category_names, list): book_category_names = []
        if any(cat_name in preferred_category_names for cat_name in book_category_names):
            recommended_books.append(book)

    if not recommended_books:
        pref_names_str = ", ".join(sorted(list(preferred_category_names))) or "выбранным"
        await message_object.reply_text(f"😔 К сожалению, по вашим {pref_names_str} предпочтениям ничего не найдено.")
    else:
        await message_object.reply_text(f"📚 Вот книги по вашим предпочтениям ({len(recommended_books)} шт.):")
        for book in recommended_books[:5]:
            owner_name_display = "Неизвестен"
            owner_id = book.get("owner")
            if owner_id and cookies:
                owner_info_res = await api_client.get_user_by_id_async(owner_id, cookies=cookies)
                if owner_info_res.get("success") and owner_info_res.get("data"):
                    owner_data = owner_info_res.get("data")
                    owner_name_display = owner_data.get("fullName") or owner_data.get("telegramId", "Владелец")

            message_text = format_book_message(book, owner_name=owner_name_display)
            image_url = book.get("image")
            try:
                if image_url:
                    await message_object.reply_photo(photo=image_url, caption=message_text, parse_mode="HTML")
                else:
                    await message_object.reply_text(message_text, parse_mode="HTML")
            except Exception as e_send:
                await message_object.reply_text(
                    f"Не удалось отобразить книгу: {book.get('title', '')} (ошибка: {e_send})")

    context.user_data.pop('all_categories_map', None)
    context.user_data.pop('selected_rec_category_ids', None)
    await message_object.reply_text("Просмотр рекомендаций завершен. Введите /menu для возврата в главное меню.",
                                    reply_markup=reply_keyboards.logged_in_menu_markup if cookies else reply_keyboards.guest_menu_markup)
    return ConversationHandler.END


async def recommendations_cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    cookies = session_manager.get_cookies(user_id)
    current_menu_markup = reply_keyboards.guest_menu_markup if not cookies else reply_keyboards.logged_in_menu_markup

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Получение рекомендаций отменено.")
        await update.callback_query.message.reply_text(
            "Введите /menu для возврата в главное меню.",
            reply_markup=current_menu_markup
        )
    else:
        await update.message.reply_text(
            "❌ Получение рекомендаций отменено. Введите /menu для возврата в главное меню.",
            reply_markup=current_menu_markup
        )

    context.user_data.pop('all_categories_map', None)
    context.user_data.pop('selected_rec_category_ids', None)
    return ConversationHandler.END