from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

main_menu_keyboard = [
    ["📚 My Books", "🧑‍💼 My Profile"],
    ["➕ Add Book", "🔍 Browse Books"],
    ["🔓 Login", "🔐 Register", "🚪 Logout"]
]
main_menu_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True)

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📋 Главное меню:", reply_markup=main_menu_markup)


