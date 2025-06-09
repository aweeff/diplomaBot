from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Dict, Set


def create_genre_selection_keyboard(all_categories: Dict[str, str], selected_ids: Set[str]) -> InlineKeyboardMarkup:
    keyboard_buttons = []
    for cat_id, cat_name in all_categories.items():
        prefix = "✅" if cat_id in selected_ids else "◻️"
        keyboard_buttons.append([InlineKeyboardButton(f"{prefix} {cat_name}", callback_data=f"rec_genre_{cat_id}")])
    keyboard_buttons.append([InlineKeyboardButton("✅ Готово", callback_data="rec_genre_done")])
    keyboard_buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="rec_genre_cancel")])
    return InlineKeyboardMarkup(keyboard_buttons)


def create_pagination_keyboard(page: int, total_pages: int, view_key: str) -> InlineKeyboardMarkup:
    buttons = []
    row = []

    if page > 0:
        row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"paginate_{view_key}_prev_{page - 1}"))

    row.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="paginate_ignore"))

    if page < total_pages - 1:
        row.append(InlineKeyboardButton("Вперёд ➡️", callback_data=f"paginate_{view_key}_next_{page + 1}"))

    buttons.append(row)
    buttons.append([InlineKeyboardButton("❌ Закрыть", callback_data=f"paginate_{view_key}_close_0")])

    return InlineKeyboardMarkup(buttons)