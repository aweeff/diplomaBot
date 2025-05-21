from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler
from bot.keyboards import reply_keyboards, inline_keyboards
from bot.services import api_client
from bot.states import session_manager
from bot.utils.helpers import check_user_logged_in, handle_api_error, format_book_message
from .conversation_states import RECOMMENDATIONS_SELECTING_GENRES

async def show_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📋 Главное меню:",
        reply_markup=reply_keyboards.main_menu_markup
    )

async def list_all_books_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    cookies = session_manager.get_cookies(user_id)

    result = api_client.get_all_books(cookies=cookies)

    if result.get("success"):
        books = result.get("data")
        if not books:
            await update.message.reply_text("❗️Нет доступных книг в каталоge.")
            return

        await update.message.reply_text("📚 Вот некоторые книги из нашего каталога:")
        for book in books[:5]:
            owner_name_display = "Неизвестен"
            owner_id = book.get("owner")
            if owner_id and cookies:
                owner_info_res = await api_client.get_user_by_id_async(owner_id, cookies=cookies)
                if owner_info_res.get("success") and owner_info_res.get("data"):
                    owner_data = owner_info_res.get("data")
                    owner_name_display = owner_data.get("fullName") or owner_data.get("telegramId", "Неизвестен")

            message_text = format_book_message(book, owner_name=owner_name_display)
            image_url = book.get("image")

            try:
                if image_url:
                    await update.message.reply_photo(photo=image_url, caption=message_text, parse_mode="HTML")
                else:
                    await update.message.reply_text(message_text, parse_mode="HTML")
            except Exception as e:
                await update.message.reply_text(f"📖 {book.get('title', 'Книга')} (ошибка отображения деталей)")
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
        return ConversationHandler.END

    all_categories_list = categories_result.get("data")
    context.user_data['all_categories_map'] = {cat['_id']: cat['name'] for cat in all_categories_list}
    context.user_data['selected_rec_category_ids'] = set()

    keyboard = inline_keyboards.create_genre_selection_keyboard(
        context.user_data['all_categories_map'],
        context.user_data['selected_rec_category_ids']
    )
    await update.message.reply_text(
        "👇 Выберите интересующие вас жанры для рекомендации и нажмите 'Готово':",
        reply_markup=keyboard
    )
    return RECOMMENDATIONS_SELECTING_GENRES

async def handle_genre_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id # query.from_user.id
    cookies = session_manager.get_cookies(user_id)

    if not cookies:
        await query.edit_message_text("Ошибка сессии. Пожалуйста, попробуйте команду снова.")
        return ConversationHandler.END

    callback_data = query.data

    if callback_data == "rec_genre_done":
        selected_ids = list(context.user_data.get('selected_rec_category_ids', []))
        if not selected_ids:
            await query.edit_message_text(
                "⚠️ Вы не выбрали ни одного жанра. Пожалуйста, выберите хотя бы один или нажмите 'Отмена'."
            )
            return RECOMMENDATIONS_SELECTING_GENRES

        await query.edit_message_text("💾 Сохраняю ваши предпочтения...")
        update_prefs_result = api_client.update_user_preferences(cookies, selected_ids)

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
        return ConversationHandler.END

    elif callback_data.startswith("rec_genre_"):
        cat_id = callback_data.split("_")[-1]
        selected_ids: set = context.user_data.get('selected_rec_category_ids', set())

        if cat_id in selected_ids:
            selected_ids.remove(cat_id)
        else:
            selected_ids.add(cat_id)
        context.user_data['selected_rec_category_ids'] = selected_ids

        new_keyboard = inline_keyboards.create_genre_selection_keyboard(
            context.user_data.get('all_categories_map', {}),
            selected_ids
        )
        try:
            await query.edit_message_reply_markup(reply_markup=new_keyboard)
        except Exception as e:
            print(f"Error updating recommendation keyboard: {e}")
        return RECOMMENDATIONS_SELECTING_GENRES

    return ConversationHandler.END

async def show_recommendations_after_selection(message_to_reply_to, context: ContextTypes.DEFAULT_TYPE, cookies: dict) -> int:
    await message_to_reply_to.reply_text("🔍 Ищу книги по вашим предпочтениям...")

    user_prefs_result = api_client.get_user_current_preferences(cookies)
    if not user_prefs_result.get("success") or not user_prefs_result.get("data"):
        await message_to_reply_to.reply_text("⚠️ Не удалось загрузить ваши предпочтения для показа книг.")
        return ConversationHandler.END

    preferred_category_ids_obj = user_prefs_result.get("data")
    if not preferred_category_ids_obj:
        await message_to_reply_to.reply_text("Вы еще не выбрали предпочтительные жанры. Используйте команду /myrecommendations снова.")
        return ConversationHandler.END

    all_categories_map_id_to_name = context.user_data.get('all_categories_map')
    if not all_categories_map_id_to_name:
        cats_res = api_client.get_all_categories(cookies)
        if cats_res.get("success") and cats_res.get("data"):
            all_categories_map_id_to_name = {cat['_id']: cat['name'] for cat in cats_res.get("data")}
        else:
            all_categories_map_id_to_name = {}

    preferred_category_names = {
        all_categories_map_id_to_name.get(pref_id)
        for pref_id in preferred_category_ids_obj.keys()
        if all_categories_map_id_to_name.get(pref_id)
    }


    # 2. Get all books
    all_books_result = api_client.get_all_books(cookies)
    if not all_books_result.get("success") or not all_books_result.get("data"):
        await message_to_reply_to.reply_text("⚠️ Не удалось загрузить список книг для рекомендаций.")
        return ConversationHandler.END

    all_books = all_books_result.get("data")
    recommended_books = []

    if not all_books:
        await message_to_reply_to.reply_text("❗️ На данный момент нет доступных книг в каталоге.")
        return ConversationHandler.END

    for book in all_books:
        book_category_names = book.get("categories", [])
        if any(cat_name in preferred_category_names for cat_name in book_category_names):
            recommended_books.append(book)

    if not recommended_books:
        await message_to_reply_to.reply_text("😔 К сожалению, по вашим предпочтениям ничего не найдено.")
    else:
        await message_to_reply_to.reply_text(f"📚 Вот книги по вашим предпочтениям ({len(recommended_books)} шт.):")
        for book in recommended_books[:5]: # Limit display
            owner_name_display = "Неизвестен"
            owner_id = book.get("owner")
            if owner_id:
                owner_info_res = await api_client.get_user_by_id_async(owner_id, cookies=cookies)
                if owner_info_res.get("success") and owner_info_res.get("data"):
                    owner_data = owner_info_res.get("data")
                    owner_name_display = owner_data.get("fullName") or owner_data.get("telegramId", "Неизвестен")

            message_text = format_book_message(book, owner_name=owner_name_display)
            image_url = book.get("image")
            try:
                if image_url:
                    await message_to_reply_to.reply_photo(photo=image_url, caption=message_text, parse_mode="HTML")
                else:
                    await message_to_reply_to.reply_text(message_text, parse_mode="HTML")
            except Exception as e_send:
                await message_to_reply_to.reply_text(f"Не удалось отобразить книгу: {book.get('title', '')} (ошибка)")

    context.user_data.pop('all_categories_map', None)
    context.user_data.pop('selected_rec_category_ids', None)
    return ConversationHandler.END


async def recommendations_cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Получение рекомендаций отменено.")
    else:
        await update.message.reply_text("❌ Получение рекомендаций отменено.", reply_markup=ReplyKeyboardRemove())

    context.user_data.pop('all_categories_map', None)
    context.user_data.pop('selected_rec_category_ids', None)
    return ConversationHandler.END