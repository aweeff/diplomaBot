from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from bot.keyboards import reply_keyboards, inline_keyboards
from bot.services import api_client
from bot.states import session_manager
from bot.utils.helpers import handle_api_error
from .conversation_states import (
    RECOMMENDATIONS_SELECTING_GENRES,
    ALL_BOOKS_PAGINATING,
    RECOMMENDATIONS_PAGINATING
)
from bot.handlers.menu import show_menu
from .pagination_helpers import send_or_edit_paginated_books


async def book_paginator_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    parts = query.data.split('_')
    view_key = "_".join(parts[1:-2])
    action = parts[-2]
    page = int(parts[-1])

    if action == "ignore":
        await query.answer()
        return

    await send_or_edit_paginated_books(update, context, view_key, page)

    if view_key == 'all_books_list':
        return ALL_BOOKS_PAGINATING
    elif view_key == 'rec_books_list':
        return RECOMMENDATIONS_PAGINATING


async def recommendations_cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    if query:
        await query.message.delete()

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="❌ Просмотр закрыт."
    )

    await show_menu(update, context)

    for key in ['all_categories_map', 'selected_rec_category_ids', 'rec_books_list', 'all_books_list']:
        context.user_data.pop(key, None)

    return ConversationHandler.END

async def list_all_books_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    cookies = session_manager.get_cookies(user_id)

    await update.message.reply_text("⏳ Загружаю список книг...", reply_markup=ReplyKeyboardRemove())
    result = api_client.get_all_books(cookies=cookies)

    if result.get("success"):
        books_data = result.get("data")
        if not books_data:
            await update.message.reply_text("❗️Нет доступных книг в каталоге.")
            return ConversationHandler.END

        context.user_data['all_books_list'] = books_data
        await send_or_edit_paginated_books(update, context, view_key='all_books_list', page=0)
        return ALL_BOOKS_PAGINATING
    else:
        await handle_api_error(update, result, "⚠️ Ошибка при получении списка книг.")
        return ConversationHandler.END


async def recommendations_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if not session_manager.get_cookies(user_id):
        await update.message.reply_text("❌ Вы не вошли в систему. Используйте /login или команду из меню.")
        return ConversationHandler.END

    cookies = session_manager.get_cookies(user_id)
    await update.message.reply_text("⏳ Загружаю список жанров...", reply_markup=ReplyKeyboardRemove())
    categories_result = api_client.get_all_categories(cookies)

    if not categories_result.get("success") or not categories_result.get("data"):
        await handle_api_error(update, categories_result, "⚠️ Не удалось загрузить жанры.")
        return ConversationHandler.END

    all_categories_list = categories_result.get("data")
    context.user_data['all_categories_map'] = {cat['_id']: cat['name'] for cat in all_categories_list}
    context.user_data.setdefault('selected_rec_category_ids', set())

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

    if 'all_categories_map' not in context.user_data:
        await query.edit_message_text("Произошла ошибка, пожалуйста, начните заново с /myrecommendations.")
        return ConversationHandler.END

    selected_ids = context.user_data.setdefault('selected_rec_category_ids', set())
    all_categories_map = context.user_data['all_categories_map']
    callback_data = query.data

    if callback_data == "rec_genre_done":
        if not selected_ids:
            await query.answer("⚠️ Пожалуйста, выберите хотя бы один жанр.", show_alert=True)
            return RECOMMENDATIONS_SELECTING_GENRES

        await query.edit_message_text("💾 Сохраняю ваши предпочтения и ищу книги...")
        api_client.update_user_preferences(cookies, list(selected_ids))

        return await show_recommendations_after_selection(update, context, cookies)

    elif callback_data == "rec_genre_cancel":
        return await recommendations_cancel_action(update, context)

    elif callback_data.startswith("rec_genre_"):
        cat_id = callback_data.split("_")[-1]
        if cat_id in selected_ids:
            selected_ids.remove(cat_id)
        else:
            selected_ids.add(cat_id)

        new_keyboard = inline_keyboards.create_genre_selection_keyboard(all_categories_map, selected_ids)
        await query.edit_message_reply_markup(reply_markup=new_keyboard)
        return RECOMMENDATIONS_SELECTING_GENRES


async def show_recommendations_after_selection(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                               cookies: dict) -> int:
    all_books_result = api_client.get_all_books(cookies)
    user_prefs_result = api_client.get_user_current_preferences(cookies)

    if not all_books_result.get("success") or not user_prefs_result.get("success"):
        await handle_api_error(update, all_books_result, "Не удалось получить книги или предпочтения.")
        return ConversationHandler.END

    all_books = all_books_result.get("data", [])
    preferred_category_ids = user_prefs_result.get("data", [])
    all_categories_map = context.user_data.get('all_categories_map', {})

    preferred_category_names = {all_categories_map.get(cat_id) for cat_id in preferred_category_ids if
                                cat_id in all_categories_map}

    recommended_books = []
    if all_books:
        for book in all_books:
            book_categories_list = book.get("categories", [])
            book_category_names = {
                cat.get("name") for cat in book_categories_list if isinstance(cat, dict) and "name" in cat
            }
            if not book_category_names.isdisjoint(preferred_category_names):
                recommended_books.append(book)

    message_object = update.message or update.callback_query.message

    if not recommended_books:
        pref_names_str = ", ".join(sorted(list(preferred_category_names))) or "выбранным"
        await message_object.reply_text(f"😔 К сожалению, по вашим {pref_names_str} предпочтениям ничего не найдено.")
        return ConversationHandler.END

    context.user_data['rec_books_list'] = recommended_books
    await send_or_edit_paginated_books(update, context, view_key='rec_books_list', page=0)
    return RECOMMENDATIONS_PAGINATING


async def recommendations_cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    if query:
        await query.message.delete()

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="❌ Действие отменено."
    )

    await show_menu(update, context)

    for key in ['all_categories_map', 'selected_rec_category_ids', 'rec_books_list', 'all_books_list']:
        context.user_data.pop(key, None)

    return ConversationHandler.END