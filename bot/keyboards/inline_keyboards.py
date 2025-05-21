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