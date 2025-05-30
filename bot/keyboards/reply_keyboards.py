from telegram import ReplyKeyboardMarkup, KeyboardButton

GUEST_MENU_LAYOUT = [
    [KeyboardButton("📚 Все книги"), KeyboardButton("💡 Рекомендации книг")],
    [KeyboardButton("🔓 Войти"), KeyboardButton("📝 Регистрация")],
]
guest_menu_markup = ReplyKeyboardMarkup(GUEST_MENU_LAYOUT, resize_keyboard=True, one_time_keyboard=False)

LOGGED_IN_MENU_LAYOUT = [
    [KeyboardButton("📖 Мои книги"), KeyboardButton("➕ Добавить новую книгу")],
    [KeyboardButton("📚 Все книги"), KeyboardButton("💡 Мои рекомендации")],
    [KeyboardButton("👤 Мой профиль"), KeyboardButton("🚪 Выйти")],
]
logged_in_menu_markup = ReplyKeyboardMarkup(LOGGED_IN_MENU_LAYOUT, resize_keyboard=True, one_time_keyboard=False)

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

CREATE_BOOK_CANCEL_LAYOUT = [
    [KeyboardButton("❌ Отменить создание книги")]
]
create_book_cancel_markup = ReplyKeyboardMarkup(CREATE_BOOK_CANCEL_LAYOUT, resize_keyboard=True, one_time_keyboard=True)

POSSIBLE_MAIN_MENU_COMMANDS = {
    "📚 Все книги", "💡 Рекомендации книг", "🔓 Войти", "📝 Регистрация",
    "📖 Мои книги", "➕ Добавить новую книгу", "💡 Мои рекомендации", "👤 Мой профиль", "🚪 Выйти"
}

