from telegram import ReplyKeyboardMarkup

MAIN_MENU_KEYBOARD_LAYOUT = [
    ["📚 My Books", "🧑‍💼 My Profile"],
    ["➕ Add Book", "🔍 Browse Books"],
    ["🔓 Login", "🔐 Register", "🚪 Logout"],
    ["🌟 My Recommendations"]
]
main_menu_markup = ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD_LAYOUT, resize_keyboard=True)

MY_BOOKS_ACTION_KEYBOARD_LAYOUT = [
    ["✏️ Редактировать", "🗑 Удалить"],
    ["❌ Отмена"]
]
my_books_action_markup = ReplyKeyboardMarkup(MY_BOOKS_ACTION_KEYBOARD_LAYOUT, one_time_keyboard=True, resize_keyboard=True)

PROFILE_ACTION_KEYBOARD_LAYOUT = [
    ["🖼 Изменить фото профиля"],
    ["❌ Отмена"]
]
profile_action_markup = ReplyKeyboardMarkup(PROFILE_ACTION_KEYBOARD_LAYOUT, one_time_keyboard=True, resize_keyboard=True)
