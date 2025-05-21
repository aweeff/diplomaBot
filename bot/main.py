from telegram.ext import (
    ApplicationBuilder, MessageHandler, CommandHandler, filters,
    ConversationHandler, CallbackQueryHandler
)
from bot.config import TELEGRAM_TOKEN
from bot.keyboards import reply_keyboards


from bot.handlers.book_handlers import (
    my_books_command, choose_action_handler, choose_book_index_handler,
    confirm_delete_handler,
    universal_edit_field_handler,
    skip_edit_field_handler,
    cancel_my_books_action
)
from bot.handlers import general_handlers, auth_handlers, book_handlers, profile_handlers
from bot.handlers.conversation_states import (
    LOGIN_EMAIL, LOGIN_PASSWORD,
    REGISTER_FULL_NAME, REGISTER_EMAIL, REGISTER_PASSWORD,
    CREATE_BOOK_TITLE, CREATE_BOOK_DESC, CREATE_BOOK_AUTHOR, CREATE_BOOK_DATE,
    CREATE_BOOK_LANG, CREATE_BOOK_CATEGORIES, CREATE_BOOK_TYPE, CREATE_BOOK_PRICE,
    CREATE_BOOK_IMAGE,
    PROFILE_WAITING_FOR_PIC,
    RECOMMENDATIONS_SELECTING_GENRES
)

from bot.handlers.conversation_states import (
    MY_BOOKS_CHOOSE_ACTION, MY_BOOKS_CHOOSE_BOOK_INDEX, MY_BOOKS_CONFIRM_DELETE,
    MY_BOOKS_EDIT_TITLE, MY_BOOKS_EDIT_DESCRIPTION, MY_BOOKS_EDIT_AUTHOR,
    MY_BOOKS_EDIT_DATE, MY_BOOKS_EDIT_LANGUAGE, MY_BOOKS_EDIT_CATEGORIES,
    MY_BOOKS_EDIT_IMAGE, MY_BOOKS_EDIT_TYPE, MY_BOOKS_EDIT_PRICE
)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    login_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{reply_keyboards.MAIN_MENU_KEYBOARD_LAYOUT[2][0]}$"), auth_handlers.start_login_command),
                      CommandHandler("login", auth_handlers.start_login_command)],
        states={
            LOGIN_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handlers.received_email_login)],
            LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handlers.received_password_login)],
        },
        fallbacks=[CommandHandler("cancel", auth_handlers.cancel_login)],
    )

    register_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{reply_keyboards.MAIN_MENU_KEYBOARD_LAYOUT[2][1]}$"), auth_handlers.start_register_command),
                      CommandHandler("register", auth_handlers.start_register_command)],
        states={
            REGISTER_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handlers.received_fullname_register)],
            REGISTER_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handlers.received_email_register)],
            REGISTER_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handlers.received_password_register)],
        },
        fallbacks=[CommandHandler("cancel", auth_handlers.cancel_register)],
    )

    create_book_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{reply_keyboards.MAIN_MENU_KEYBOARD_LAYOUT[1][0]}$"), book_handlers.start_create_book_command),
                      CommandHandler("createbook", book_handlers.start_create_book_command)],
        states={
            CREATE_BOOK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_handlers.title_received_handler)],
            CREATE_BOOK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_handlers.desc_received_handler)],
            CREATE_BOOK_AUTHOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_handlers.author_received_handler)],
            CREATE_BOOK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_handlers.date_received_handler)],
            CREATE_BOOK_LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_handlers.lang_received_handler)],
            CREATE_BOOK_CATEGORIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_handlers.categories_received_handler)],
            CREATE_BOOK_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_handlers.type_received_handler)],
            CREATE_BOOK_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_handlers.price_received_handler)],
            CREATE_BOOK_IMAGE: [MessageHandler(filters.PHOTO, book_handlers.image_received_handler)],
        },
        fallbacks=[CommandHandler("cancel", book_handlers.cancel_create_book_handler)],
    )

    my_books_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(f"^{reply_keyboards.MAIN_MENU_KEYBOARD_LAYOUT[0][0]}$"), my_books_command),
            CommandHandler("mybooks", my_books_command)],
        states={
            MY_BOOKS_CHOOSE_ACTION: [
                MessageHandler(filters.Regex("^(✏️ Редактировать|🗑 Удалить|❌ Отмена)$"), choose_action_handler)],
            MY_BOOKS_CHOOSE_BOOK_INDEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_book_index_handler)],
            MY_BOOKS_CONFIRM_DELETE: [
                MessageHandler(filters.Regex("^(да|нет|yes|no|Да|Нет)$"), confirm_delete_handler)],

            MY_BOOKS_EDIT_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                CommandHandler("skip", skip_edit_field_handler)
            ],
            MY_BOOKS_EDIT_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                CommandHandler("skip", skip_edit_field_handler)
            ],
            MY_BOOKS_EDIT_AUTHOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                CommandHandler("skip", skip_edit_field_handler)
            ],
            MY_BOOKS_EDIT_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                CommandHandler("skip", skip_edit_field_handler)
            ],
            MY_BOOKS_EDIT_LANGUAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                CommandHandler("skip", skip_edit_field_handler)
            ],
            MY_BOOKS_EDIT_CATEGORIES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                CommandHandler("skip", skip_edit_field_handler)
            ],
            MY_BOOKS_EDIT_IMAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                CommandHandler("skip", skip_edit_field_handler)
            ],
            MY_BOOKS_EDIT_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                CommandHandler("skip", skip_edit_field_handler)
            ],
            MY_BOOKS_EDIT_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                CommandHandler("skip", skip_edit_field_handler)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_my_books_action)],
    )

    profile_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{reply_keyboards.MAIN_MENU_KEYBOARD_LAYOUT[0][1]}$"), profile_handlers.profile_command),
                      CommandHandler("me", profile_handlers.profile_command)],
        states={
            PROFILE_WAITING_FOR_PIC: [
                MessageHandler(filters.Regex("^🖼 Изменить фото профиля$"), profile_handlers.request_new_profile_pic_action),
                MessageHandler(filters.PHOTO, profile_handlers.update_profile_picture_handler),
                MessageHandler(filters.Regex("^❌ Отмена$") | filters.COMMAND & filters.Regex("^/cancel$"), profile_handlers.cancel_profile_update_action),
            ],
        },
        fallbacks=[CommandHandler("cancel", profile_handlers.cancel_profile_update_action)],
    )

    recommendations_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{reply_keyboards.MAIN_MENU_KEYBOARD_LAYOUT[3][0]}$"), general_handlers.recommendations_start_command), # Assuming "My Recommendations" is added to menu
                      CommandHandler("myrecommendations", general_handlers.recommendations_start_command)],
        states={
            RECOMMENDATIONS_SELECTING_GENRES: [CallbackQueryHandler(general_handlers.handle_genre_selection_callback)],
        },
        fallbacks=[
            CommandHandler("cancel", general_handlers.recommendations_cancel_action),
            CallbackQueryHandler(general_handlers.handle_genre_selection_callback, pattern="^rec_genre_cancel$")
        ],
    )

    app.add_handler(login_conv)
    app.add_handler(register_conv)
    app.add_handler(create_book_conv)
    app.add_handler(my_books_conv)
    app.add_handler(profile_conv)
    app.add_handler(recommendations_conv)

    app.add_handler(MessageHandler(filters.Regex(f"^{reply_keyboards.MAIN_MENU_KEYBOARD_LAYOUT[1][1]}$"), general_handlers.list_all_books_command)) # Browse Books
    app.add_handler(CommandHandler("books", general_handlers.list_all_books_command))

    app.add_handler(MessageHandler(filters.Regex(f"^{reply_keyboards.MAIN_MENU_KEYBOARD_LAYOUT[2][2]}$"), auth_handlers.logout_command)) # Logout
    app.add_handler(CommandHandler("logout", auth_handlers.logout_command))

    app.add_handler(CommandHandler("start", general_handlers.show_menu_command))
    app.add_handler(MessageHandler(filters.Regex("^(📋 Главное меню|menu|меню)$"), general_handlers.show_menu_command))
    app.add_handler(CommandHandler("menu", general_handlers.show_menu_command))

    print("Bot is polling...")
    app.run_polling()

if __name__ == "__main__":
    main()