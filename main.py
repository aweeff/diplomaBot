from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters
import db
from handlers.login import login_conv_handler
from handlers.books import books_handler
from handlers.logout import logout_handler
from handlers.recommendation import recommendations_conv_handler
from handlers.register import register_conv_handler
from handlers.my_books import my_books_conv_handler
from handlers.profile import profile_handler
from handlers.menu import show_menu
from handlers.logout import logout
from handlers.login import start_login
from handlers.books import get_books
from handlers.register import start_register
from handlers.my_books import my_books
from handlers.profile import profile
from handlers.createBooks import start_create_book, get_create_book_handler

"""
from handlers.update_profile import update_profile_conv_handler
"""
def main():
    app = ApplicationBuilder().token(db.TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.Regex(r"^🔐 Login\s*$"), start_login))
    app.add_handler(MessageHandler(filters.Regex(r"^📚 All Books\s*$"), get_books))
    app.add_handler(MessageHandler(filters.Regex(r"^📝 Register\s*$"), start_register))
    app.add_handler(MessageHandler(filters.Regex(r"^📖 My Books\s*$"), my_books))
    app.add_handler(MessageHandler(filters.Regex(r"^🙋 My Profile\s*$"), profile))

    app.add_handler(MessageHandler(filters.Regex(r"^🚪 Logout\s*$"), logout))

    # Conversation and command handlers AFTER
    app.add_handler(logout_handler)
    app.add_handler(login_conv_handler)
    app.add_handler(register_conv_handler)
    app.add_handler(books_handler)
    app.add_handler(my_books_conv_handler)
    app.add_handler(profile_handler)
    app.add_handler(get_create_book_handler())
    app.add_handler(recommendations_conv_handler)

    app.add_handler(CommandHandler("start", show_menu))
    app.add_handler(MessageHandler(filters.Regex("^(📋 Главное меню|menu|меню)$"), show_menu))
    app.add_handler(CommandHandler("menu", show_menu))

    app.run_polling()

if __name__ == "__main__":
    main()
