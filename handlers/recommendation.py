from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
    CallbackQueryHandler
)

from handlers.categories import get_all_categories, update_user_preferences_api, get_user_current_preferences, \
    get_all_books_api
from handlers.getUserById import get_user_by_id
from state.session_store import sessions

# --- "My Recommendations" Conversation ---

SELECTING_GENRES, SHOWING_RECOMMENDATIONS = range(2)
RECOMMENDATIONS_MENU_TEXT = "📚 Мои Рекомендации"  # Assuming this is a button in your main menu


async def recommendations_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the recommendation process by fetching and showing genres."""
    user_id = update.effective_user.id
    session = sessions.get(user_id)

    if not session or "cookies" not in session:
        await update.message.reply_text("❌ Вы не вошли в систему. Используйте /login.")
        return ConversationHandler.END

    await update.message.reply_text("⏳ Загружаю список жанров...")

    categories = await get_all_categories(cookies=session["cookies"])
    if not categories:
        await update.message.reply_text("⚠️ Не удалось загрузить жанры. Попробуйте позже.")
        return ConversationHandler.END

    context.user_data['all_categories'] = {cat['_id']: cat['name'] for cat in categories}
    context.user_data['selected_category_ids_for_recommendation'] = set()  # Store selected IDs

    keyboard_buttons = []
    for cat_id, cat_name in context.user_data['all_categories'].items():
        keyboard_buttons.append([InlineKeyboardButton(f"◻️ {cat_name}", callback_data=f"rec_genre_{cat_id}")])

    keyboard_buttons.append([InlineKeyboardButton("✅ Готово", callback_data="rec_genre_done")])
    keyboard_buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="rec_genre_cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    await update.message.reply_text(
        "👇 Выберите интересующие вас жанры для рекомендации и нажмите 'Готово':",
        reply_markup=reply_markup
    )
    return SELECTING_GENRES


async def handle_genre_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles inline keyboard button presses for genre selection."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    session = sessions.get(user_id)

    callback_data = query.data

    if callback_data == "rec_genre_done":
        selected_ids = list(context.user_data.get('selected_category_ids_for_recommendation', []))
        if not selected_ids:
            await query.edit_message_text(
                "⚠️ Вы не выбрали ни одного жанра. Пожалуйста, выберите хотя бы один или нажмите 'Отмена'.")
            # Re-show keyboard if needed or just let user press cancel
            return SELECTING_GENRES

        await query.edit_message_text("💾 Сохраняю ваши предпочтения...")
        success = await update_user_preferences_api(selected_ids, cookies=session["cookies"])

        if success:
            await query.message.reply_text("✅ Ваши предпочтения по жанрам сохранены!")
            # Proceed to show recommendations
            return await show_recommendations(update, context, query.message)  # Pass query.message
        else:
            await query.message.reply_text("⚠️ Не удалось сохранить предпочтения. Попробуйте позже.")
            return ConversationHandler.END

    elif callback_data == "rec_genre_cancel":
        await query.edit_message_text("❌ Выбор жанров отменен.")
        context.user_data.pop('all_categories', None)
        context.user_data.pop('selected_category_ids_for_recommendation', None)
        return ConversationHandler.END

    elif callback_data.startswith("rec_genre_"):
        cat_id = callback_data.split("_")[-1]
        selected_ids: set = context.user_data.get('selected_category_ids_for_recommendation', set())

        if cat_id in selected_ids:
            selected_ids.remove(cat_id)
        else:
            selected_ids.add(cat_id)
        context.user_data['selected_category_ids_for_recommendation'] = selected_ids

        # Update keyboard
        keyboard_buttons = []
        all_categories_map = context.user_data.get('all_categories', {})
        for c_id, c_name in all_categories_map.items():
            prefix = "✅" if c_id in selected_ids else "◻️"
            keyboard_buttons.append([InlineKeyboardButton(f"{prefix} {c_name}", callback_data=f"rec_genre_{c_id}")])

        keyboard_buttons.append([InlineKeyboardButton("✅ Готово", callback_data="rec_genre_done")])
        keyboard_buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="rec_genre_cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard_buttons)

        try:
            await query.edit_message_reply_markup(reply_markup=reply_markup)
        except Exception as e:
            print(f"Error updating keyboard: {e}")  # Can happen if message is too old or not changed

        return SELECTING_GENRES

    return ConversationHandler.END  # Should not reach here ideally


async def show_recommendations(update: Update, context: ContextTypes.DEFAULT_TYPE, message_to_reply_to) -> int:
    """Fetches and displays books based on saved preferences."""
    user_id = update.effective_user.id
    session = sessions.get(user_id)

    if not session or "cookies" not in session:
        await message_to_reply_to.reply_text("❌ Сессия не найдена. Пожалуйста, войдите снова с /login.")
        return ConversationHandler.END

    await message_to_reply_to.reply_text("🔍 Ищу книги по вашим предпочтениям...")

    user_prefs_obj = await get_user_current_preferences(cookies=session["cookies"])
    if not user_prefs_obj:
        await message_to_reply_to.reply_text("⚠️ Не удалось загрузить ваши предпочтения. Попробуйте установить их снова.")
        return ConversationHandler.END

    preferred_category_ids = set(user_prefs_obj.keys())
    if not preferred_category_ids:
        await message_to_reply_to.reply_text("Вы еще не выбрали предпочтительные жанры. Используйте команду /myrecommendations, чтобы задать их.")
        return ConversationHandler.END

    all_books = await get_all_books_api(cookies=session["cookies"])
    if all_books is None:
        await message_to_reply_to.reply_text("⚠️ Не удалось загрузить список книг. Попробуйте позже.")
        return ConversationHandler.END

    recommended_books = []
    if not all_books:
        await message_to_reply_to.reply_text("❗️ На данный момент нет доступных книг в каталоге.")
        return ConversationHandler.END

    all_categories_map_id_to_name = context.user_data.get('all_categories')
    if not all_categories_map_id_to_name:
        all_cats_from_api = await get_all_categories(cookies=session["cookies"])
        if all_cats_from_api:
            all_categories_map_id_to_name = {cat['_id']: cat['name'] for cat in all_cats_from_api}
        else:
            all_categories_map_id_to_name = {}

    preferred_category_names = {
        all_categories_map_id_to_name.get(pref_id)
        for pref_id in preferred_category_ids
        if all_categories_map_id_to_name.get(pref_id)
    }

    for book in all_books:
        book_category_names = book.get("categories", [])
        if any(cat_name in preferred_category_names for cat_name in book_category_names):
            recommended_books.append(book)

    if not recommended_books:
        await message_to_reply_to.reply_text("😔 К сожалению, по вашим предпочтениям ничего не найдено.")
    else:
        await message_to_reply_to.reply_text(f"📚 Вот книги по вашим предпочтениям ({len(recommended_books)} шт.):")
        for book in recommended_books[:5]:
            title = book.get("title", "Без названия")
            author = book.get("author", "Автор неизвестен")
            categories_str = ", ".join(book.get("categories", []))
            price = book.get("price", "N/A")
            image_url = book.get("image")

            # 🔍 Get owner information
            owner_id = book.get("owner")
            owner_info = None
            if owner_id:
                try: # Assuming this exists
                    owner_info = await get_user_by_id(owner_id, cookies=session["cookies"])
                except Exception as e:
                    print(f"Error fetching owner: {e}")

            owner_name = owner_info.get("fullName") or owner_info.get("telegramId") if owner_info else "Неизвестен"

            message_text = (
                f"📖 <b>{title}</b>\n"
                f"✍️ Автор: {author}\n"
                f"🏷 Жанры: {categories_str}\n"
                f"💰 Цена: {price} у.е.\n"
                f"👤 Владелец: {owner_name}"
            )
            try:
                if image_url:
                    await message_to_reply_to.reply_photo(photo=image_url, caption=message_text, parse_mode="HTML")
                else:
                    await message_to_reply_to.reply_text(message_text, parse_mode="HTML")
            except Exception as e_send:
                print(f"Error sending book message: {e_send}")
                await message_to_reply_to.reply_text(f"Не удалось отобразить книгу: {title} (ошибка)")

    context.user_data.pop('all_categories', None)
    context.user_data.pop('selected_category_ids_for_recommendation', None)
    return ConversationHandler.END

async def recommendations_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the recommendation conversation."""
    await update.message.reply_text("❌ Получение рекомендаций отменено.", reply_markup=ReplyKeyboardRemove())
    context.user_data.pop('all_categories', None)
    context.user_data.pop('selected_category_ids_for_recommendation', None)
    return ConversationHandler.END


recommendations_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("myrecommendations", recommendations_start)],
    states={
         SELECTING_GENRES: [CallbackQueryHandler(handle_genre_selection)],
         # SHOWING_RECOMMENDATIONS is handled directly after "Done" or can be a separate state if needed
     },
     fallbacks=[
         CommandHandler("cancel", recommendations_cancel),
         CallbackQueryHandler(handle_genre_selection, pattern="^rec_genre_cancel$") # handles cancel from inline
     ],
 )
