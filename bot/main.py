from telegram.ext import (
    ApplicationBuilder, MessageHandler, CommandHandler, filters,
    ConversationHandler, CallbackQueryHandler
)
from bot.config import TELEGRAM_TOKEN

from bot.handlers.menu import show_menu as show_main_menu_command

from bot.handlers.book_handlers import (
    my_books_command, choose_action_handler, choose_book_index_handler,
    confirm_delete_handler,
    universal_edit_field_handler,
    skip_edit_field_handler,
    cancel_my_books_action,
    start_create_book_command, title_received_handler, desc_received_handler,
    author_received_handler, date_received_handler, lang_received_handler,
    categories_received_handler, type_received_handler, price_received_handler,
    image_received_handler, cancel_create_book_handler
)
from bot.handlers import general_handlers, auth_handlers, profile_handlers

from bot.handlers.general_handlers import book_paginator_callback

from bot.handlers.conversation_states import (
    LOGIN_EMAIL, LOGIN_PASSWORD,
    REGISTER_FULL_NAME, REGISTER_EMAIL, REGISTER_PASSWORD, REGISTER_COUNTRY, REGISTER_CITY,
    CREATE_BOOK_TITLE, CREATE_BOOK_DESC, CREATE_BOOK_AUTHOR, CREATE_BOOK_DATE,
    CREATE_BOOK_LANG, CREATE_BOOK_CATEGORIES, CREATE_BOOK_TYPE, CREATE_BOOK_PRICE,
    CREATE_BOOK_IMAGE,
    PROFILE_WAITING_FOR_PIC,
    RECOMMENDATIONS_SELECTING_GENRES,
    ALL_BOOKS_PAGINATING, RECOMMENDATIONS_PAGINATING
)

from bot.handlers.conversation_states import (
    MY_BOOKS_CHOOSE_ACTION, MY_BOOKS_CHOOSE_BOOK_INDEX, MY_BOOKS_CONFIRM_DELETE,
    MY_BOOKS_EDIT_TITLE, MY_BOOKS_EDIT_DESCRIPTION, MY_BOOKS_EDIT_AUTHOR,
    MY_BOOKS_EDIT_DATE, MY_BOOKS_EDIT_LANGUAGE, MY_BOOKS_EDIT_CATEGORIES,
    MY_BOOKS_EDIT_IMAGE, MY_BOOKS_EDIT_TYPE, MY_BOOKS_EDIT_PRICE
)


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    CANCEL_BOOK_CREATION_TEXT = "❌ Отменить создание книги"
    CANCEL_BOOK_CREATION_REGEX = f"^{CANCEL_BOOK_CREATION_TEXT}$"

    login_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^🔓 Войти$"), auth_handlers.start_login_command),
                      CommandHandler("login", auth_handlers.start_login_command)],
        states={
            LOGIN_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handlers.received_email_login)],
            LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handlers.received_password_login)],
        },
        fallbacks=[CommandHandler("cancel", auth_handlers.cancel_login)],
    )
    register_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^📝 Регистрация$"), auth_handlers.start_register_command),
                      CommandHandler("register", auth_handlers.start_register_command)],
        states={
            REGISTER_FULL_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handlers.received_fullname_register)],
            REGISTER_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handlers.received_email_register)],
            REGISTER_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handlers.received_password_register)],
            REGISTER_COUNTRY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handlers.received_country_register),
                CommandHandler("skip", auth_handlers.received_country_register)
            ],
            REGISTER_CITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handlers.received_city_register),
                CommandHandler("skip", auth_handlers.received_city_register)
            ],
        },
        fallbacks=[CommandHandler("cancel", auth_handlers.cancel_register)],
    )
    create_book_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^➕ Добавить новую книгу$"), start_create_book_command),
                      CommandHandler("createbook", start_create_book_command)],
        states={
            CREATE_BOOK_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(CANCEL_BOOK_CREATION_REGEX),
                               title_received_handler)],
            CREATE_BOOK_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(CANCEL_BOOK_CREATION_REGEX),
                               desc_received_handler)],
            CREATE_BOOK_AUTHOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(CANCEL_BOOK_CREATION_REGEX),
                               author_received_handler)],
            CREATE_BOOK_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(CANCEL_BOOK_CREATION_REGEX),
                               date_received_handler)],
            CREATE_BOOK_LANG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(CANCEL_BOOK_CREATION_REGEX),
                               lang_received_handler)],
            CREATE_BOOK_CATEGORIES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(CANCEL_BOOK_CREATION_REGEX),
                               categories_received_handler)],
            CREATE_BOOK_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(CANCEL_BOOK_CREATION_REGEX),
                               type_received_handler)],
            CREATE_BOOK_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(CANCEL_BOOK_CREATION_REGEX),
                               price_received_handler)],
            CREATE_BOOK_IMAGE: [MessageHandler(filters.PHOTO, image_received_handler)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_create_book_handler),
            MessageHandler(filters.Regex(CANCEL_BOOK_CREATION_REGEX), cancel_create_book_handler)
        ],
    )
    my_books_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(f"^📖 Мои книги$"), my_books_command),
            CommandHandler("mybooks", my_books_command)],
        states={
            MY_BOOKS_CHOOSE_ACTION: [
                MessageHandler(filters.Regex("^(✏️ Редактировать|🗑 Удалить|❌ Отмена)$"), choose_action_handler)],
            MY_BOOKS_CHOOSE_BOOK_INDEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_book_index_handler)],
            MY_BOOKS_CONFIRM_DELETE: [MessageHandler(filters.Regex("^(да|нет|yes|no)$"), confirm_delete_handler)],
            MY_BOOKS_EDIT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                                  CommandHandler("skip", skip_edit_field_handler)],
            MY_BOOKS_EDIT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                                        CommandHandler("skip", skip_edit_field_handler)],
            MY_BOOKS_EDIT_AUTHOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                                   CommandHandler("skip", skip_edit_field_handler)],
            MY_BOOKS_EDIT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                                 CommandHandler("skip", skip_edit_field_handler)],
            MY_BOOKS_EDIT_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                                     CommandHandler("skip", skip_edit_field_handler)],
            MY_BOOKS_EDIT_CATEGORIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                                       CommandHandler("skip", skip_edit_field_handler)],
            MY_BOOKS_EDIT_IMAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                                  CommandHandler("skip", skip_edit_field_handler)],
            MY_BOOKS_EDIT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                                 CommandHandler("skip", skip_edit_field_handler)],
            MY_BOOKS_EDIT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_edit_field_handler),
                                  CommandHandler("skip", skip_edit_field_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel_my_books_action),
                   MessageHandler(filters.Regex("^❌ Отмена$"), cancel_my_books_action)],
    )
    profile_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^👤 Мой профиль$"), profile_handlers.profile_command),
                      CommandHandler("me", profile_handlers.profile_command)],
        states={
            PROFILE_WAITING_FOR_PIC: [
                MessageHandler(filters.Regex("^🖼 Изменить фото профиля$"),
                               profile_handlers.request_new_profile_pic_action),
                MessageHandler(filters.PHOTO, profile_handlers.update_profile_picture_handler),
            ],
        },
        fallbacks=[CommandHandler("cancel", profile_handlers.cancel_profile_update_action),
                   MessageHandler(filters.Regex("^❌ Отмена$"), profile_handlers.cancel_profile_update_action)],
    )

    recommendations_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(f"^💡 (Рекомендации книг|Мои рекомендации)$"),
                           general_handlers.recommendations_start_command),
            CommandHandler("myrecommendations", general_handlers.recommendations_start_command)
        ],
        states={
            RECOMMENDATIONS_SELECTING_GENRES: [
                CallbackQueryHandler(general_handlers.handle_genre_selection_callback, pattern="^rec_genre_")
            ],
            RECOMMENDATIONS_PAGINATING: [
                CallbackQueryHandler(book_paginator_callback, pattern=r"^paginate_rec_books_list_(next|prev|ignore)")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", general_handlers.recommendations_cancel_action),
            CallbackQueryHandler(general_handlers.recommendations_cancel_action, pattern="^rec_genre_cancel$"),
            CallbackQueryHandler(general_handlers.recommendations_cancel_action,
                                 pattern=r"^paginate_rec_books_list_close")
        ]
    )

    all_books_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(f"^📚 Все книги$"), general_handlers.list_all_books_command),
            CommandHandler("books", general_handlers.list_all_books_command)
        ],
        states={
            ALL_BOOKS_PAGINATING: [
                CallbackQueryHandler(book_paginator_callback, pattern=r"^paginate_all_books_list_(next|prev|ignore)")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", general_handlers.recommendations_cancel_action),
            CallbackQueryHandler(general_handlers.recommendations_cancel_action,
                                 pattern=r"^paginate_all_books_list_close")
        ]
    )

    app.add_handler(login_conv)
    app.add_handler(register_conv)
    app.add_handler(create_book_conv)
    app.add_handler(my_books_conv)
    app.add_handler(profile_conv)
    app.add_handler(recommendations_conv)
    app.add_handler(all_books_conv)

    app.add_handler(MessageHandler(filters.Regex(f"^🚪 Выйти$"), auth_handlers.logout_command))
    app.add_handler(CommandHandler("logout", auth_handlers.logout_command))
    app.add_handler(CommandHandler("start", show_main_menu_command))
    app.add_handler(CommandHandler("menu", show_main_menu_command))

    print("Бот запущен и принимает сообщения...")
    app.run_polling()


if __name__ == "__main__":
    main()