from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from states.session_manager import sessions

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_logged_in = False
    user_name = "Guest"

    session = sessions.get(user_id)
    if session and "cookies" in session and "user" in session:
        is_logged_in = True
        user_name = session["user"].get("fullName", "User")

    menu_keyboard = []
    greeting_message = f"Hello, {user_name}!\n📋 Main Menu:"

    if is_logged_in:
        greeting_message = f"Welcome back, {user_name}!\n📋 What would you like to do?"
        menu_keyboard = [
            [KeyboardButton("📚 All Books"), KeyboardButton("💡 My Recommendations")],
            [KeyboardButton("📖 My Books"), KeyboardButton("➕ Add Book")],
            [KeyboardButton("👤 My Profile"), KeyboardButton("🚪 Logout")],
        ]
    else:
        greeting_message = "Welcome, Guest!\n📋 Please log in or register to access all features."
        menu_keyboard = [
            [KeyboardButton("📚 All Books")], # Browse books is available to guests
            # My Recommendations could also be here, and the handler would prompt for login
            [KeyboardButton("💡 Get Book Recommendations")], # Renamed to be clearer for guests
            [KeyboardButton("🔓 Login"), KeyboardButton("📝 Register")],
        ]

    menu_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(greeting_message, reply_markup=menu_markup, parse_mode="HTML")