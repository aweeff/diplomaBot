from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, ContextTypes, filters
from state.session_store import sessions
import requests
import db

ASK_LANGUAGE, ASK_CATEGORY = range(2)

# Step 1: Start
async def start_recommendations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = sessions.get(user_id)

    if not session or "cookies" not in session:
        await update.message.reply_text("❌ Вы не вошли в систему. Используйте /login.")
        return

    reply_keyboard = [["Русский", "English"]]
    await update.message.reply_text(
        "🌐 Выберите язык:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return ASK_LANGUAGE

# Step 2: Get language
async def ask_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["language"] = update.message.text

    reply_keyboard = [
        ["Художественная литература", "Фантастика"],
        ["История", "Наука"],
        ["Военная проза", "Детектив"]
    ]
    print("nashelsya")

    await update.message.reply_text(
        "🏷 Выберите категорию:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return ASK_CATEGORY

# Step 3: Fetch and display recommendations
async def show_recommendations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["category"] = update.message.text
    session = context.user_data.get("session")

    print("nashelsya")

    try:
        response = requests.get(
            f"{db.BACKEND_URL}/api/books",
            params={
                "language": context.user_data["language"],
                "category": context.user_data["category"]
            },
            cookies=session["cookies"]
        )

        if response.status_code == 200:
            books = response.json()
            if not books:
                await update.message.reply_text("📭 Нет рекомендаций по выбранным параметрам.", reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END

            for book in books:
                title = book.get("title", "Без названия")
                author = book.get("author", "Автор неизвестен")
                categories = ", ".join(book.get("categories", []))
                price = book.get("price", "N/A")
                image_url = book.get("image")

                message = (
                    f"\U0001F4D6 <b>{title}</b>\n"
                    f"✍️ Автор: {author}\n"
                    f"🏷 Категории: {categories}\n"
                    f"💰 Цена: {price} у.е."
                )

                if image_url:
                    await update.message.reply_photo(photo=image_url, caption=message, parse_mode="HTML")
                else:
                    await update.message.reply_text(message, parse_mode="HTML")

            await update.message.reply_text("🔚 Конец рекомендаций.", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

        else:
            await update.message.reply_text("⚠️ Ошибка при получении рекомендаций.")
            return ConversationHandler.END

    except Exception as e:
        await update.message.reply_text(f"🚫 Ошибка: {str(e)}")
        return ConversationHandler.END

# Cancel handler
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Операция отменена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Conversation handler
recommendations_handler = ConversationHandler(
    entry_points=[
        CommandHandler("recommend", start_recommendations),
        MessageHandler(filters.Regex("^🎯 Мои рекомендации$"), start_recommendations)
    ],
    states={
        ASK_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_category)],
        ASK_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_recommendations)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
