import os
import sqlite3
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from dotenv import load_dotenv

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)


# =========================
# НАСТРОЙКИ
# =========================

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

CHANNEL = "@shop_abu1"

REVIEWS = "@otzyvabu"

GUARANT = "@abu_ejje"

ABU_POST = "@Post_FreeFireBot"

ADMIN_ID = 7954321223


# =========================
# ЛОГИ
# =========================

logging.basicConfig(
    level=logging.INFO
)


# =========================
# БАЗА ДАННЫХ
# =========================

db = sqlite3.connect(
    "abu_post.db",
    check_same_thread=False
)

cursor = db.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE,
    username TEXT,
    posts INTEGER DEFAULT 0
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS ads(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    game TEXT,
    access TEXT,
    price TEXT,
    currency TEXT,
    payment TEXT,
    description TEXT
)
""")


db.commit()


# =========================
# СОСТОЯНИЯ ОБЪЯВЛЕНИЯ
# =========================

(
    GAME,
    PHOTOS,
    ACCESS,
    DESCRIPTION,
    PRICE,
    CURRENCY,
    PAYMENT
) = range(7)


# =========================
# МЕНЮ
# =========================

main_menu = ReplyKeyboardMarkup(
    [
        ["📢 Объявление"],
        ["🔍 Поиск аккаунтов"],
        ["🔔 Сигнал"],
        ["🚨 Жалоба"],
        ["❤️ Избранное"],
        ["👤 Профиль"],
        ["⭐ Отзывы"]
    ],
    resize_keyboard=True
)


games_menu = ReplyKeyboardMarkup(
    [
        ["🔥 Free Fire", "⭐ Brawl Stars"],
        ["🔫 PUBG", "🧱 Roblox"],
        ["⚽ FIFA", "🎮 Другое"]
    ],
    resize_keyboard=True
)


cancel_menu = ReplyKeyboardMarkup(
    [
        ["❌ Отменить"]
    ],
    resize_keyboard=True
)


# =========================
# ПРОВЕРКА ПОДПИСКИ
# =========================

subscribe_keyboard = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "📢 Подписаться",
                url="https://t.me/shop_abu1"
            )
        ],
        [
            InlineKeyboardButton(
                "✅ Проверить подписку",
                callback_data="check_sub"
            )
        ]
    ]
)


async def check_subscription(user_id, context):

    try:
        member = await context.bot.get_chat_member(
            CHANNEL,
            user_id
        )

        return member.status in [
            "member",
            "administrator",
            "creator"
        ]

    except Exception as e:

        print("Ошибка проверки подписки:", e)

        return False


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    cursor.execute(
        """
        INSERT OR IGNORE INTO users
        (
            user_id,
            username
        )
        VALUES
        (?,?)
        """,
        (
            user.id,
            user.username
        )
    )

    db.commit()

    if not await check_subscription(user.id, context):

        await update.message.reply_text(
            "❗ Для использования Abu Post подпишитесь на канал:",
            reply_markup=subscribe_keyboard
        )

        return

    await update.message.reply_text(
        """
🎮 Abu Post

Добро пожаловать!

Здесь можно покупать и продавать игровые аккаунты.
""",
        reply_markup=main_menu
    )


# =========================
# КНОПКА ПРОВЕРКИ
# =========================

async def check_sub_button(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    if await check_subscription(user_id, context):

        await query.message.delete()

        await query.message.reply_text(
            """
✅ Подписка подтверждена!

Добро пожаловать в Abu Post 🎮
""",
            reply_markup=main_menu
        )

    else:

        await query.answer(
            "❌ Вы ещё не подписались!",
            show_alert=True
        )


# =========================
# СОЗДАНИЕ ОБЪЯВЛЕНИЯ
# =========================

photo_done_menu = ReplyKeyboardMarkup(
    [
        ["✅ Готово"],
        ["❌ Отменить"]
    ],
    resize_keyboard=True
)


access_menu = ReplyKeyboardMarkup(
    [
        ["Google", "VK"],
        ["Facebook", "X"],
        ["Apple ID", "Другое"]
    ],
    resize_keyboard=True
)


async def create_ad(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🎮 Выберите игру:",
        reply_markup=games_menu
    )

    return GAME


async def choose_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data["game"] = update.message.text
    context.user_data["photos"] = []

    await update.message.reply_text(
        """
📸 Отправьте от 2 до 10 фотографий аккаунта.

После загрузки нажмите:
✅ Готово

""",
        reply_markup=photo_done_menu
    )

    return PHOTOS


async def get_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    photos = context.user_data.get("photos", [])

    if len(photos) >= 10:
        return PHOTOS

    photos.append(update.message.photo[-1].file_id)

    context.user_data["photos"] = photos

    return PHOTOS


async def photos_done(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    photos = context.user_data.get("photos", [])

    if len(photos) < 2:

        await update.message.reply_text(
            "❌ Нужно минимум 2 фотографии."
        )

        return PHOTOS

    await update.message.reply_text(
        "🔑 Выберите доступ:",
        reply_markup=access_menu
    )

    return ACCESS


async def cancel_ad(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()

    await update.message.reply_text(
        "❌ Создание объявления отменено.",
        reply_markup=main_menu
    )

    return ConversationHandler.END


# =========================
# ДАННЫЕ ОБЪЯВЛЕНИЯ
# =========================

currency_menu = ReplyKeyboardMarkup(
    [
        ["🇰🇬 Сом"],
        ["🇷🇺 Рубли"],
        ["🇹🇯 Сомони"],
        ["💵 Доллары"]
    ],
    resize_keyboard=True
)


payment_menu = ReplyKeyboardMarkup(
    [
        ["🏦 Мбанк", "🏦 Т-Банк"],
        ["🏦 Сбер", "💰 ЮMoney"],
        ["💳 Другое"]
    ],
    resize_keyboard=True
)


async def choose_access(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data["access"] = update.message.text

    await update.message.reply_text(
        "📝 Напишите описание аккаунта:",
        reply_markup=ReplyKeyboardMarkup(
            [["❌ Отменить"]],
            resize_keyboard=True
        )
    )

    return DESCRIPTION


async def get_description(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data["description"] = update.message.text

    await update.message.reply_text(
        "💰 Напишите цену:",
        reply_markup=ReplyKeyboardMarkup(
            [["❌ Отменить"]],
            resize_keyboard=True
        )
    )

    return PRICE


async def get_price(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data["price"] = update.message.text

    await update.message.reply_text(
        "💵 Выберите валюту:",
        reply_markup=currency_menu
    )

    return CURRENCY


async def get_currency(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data["currency"] = update.message.text

    await update.message.reply_text(
        "💳 Выберите способ оплаты:",
        reply_markup=payment_menu
    )

    return PAYMENT


async def get_payment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data["payment"] = update.message.text

    data = context.user_data

    publish_menu = ReplyKeyboardMarkup(
        [["✅ Опубликовать"], ["❌ Отменить"]],
        resize_keyboard=True
    )

    await update.message.reply_text(
        f"""
📋 Предпросмотр объявления:

🎮 Игра: {data.get('game', '')}
🔑 Доступ: {data.get('access', '')}
📝 Описание: {data.get('description', '')}
💰 Цена: {data.get('price', '')} {data.get('currency', '')}
💳 Оплата: {data.get('payment', '')}

Нажмите «✅ Опубликовать» для публикации.
""",
        reply_markup=publish_menu
    )

    return ConversationHandler.END


# =========================
# ПУБЛИКАЦИЯ ОБЪЯВЛЕНИЯ
# =========================

async def publish_ad(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    data = context.user_data

    if not data.get("game"):
        await update.message.reply_text(
            "❌ Нет данных объявления. Создайте новое.",
            reply_markup=main_menu
        )
        return

    user = update.effective_user

    username = (
        f"@{user.username}"
        if user.username
        else "Без username"
    )

    caption = f"""
🎮 {data['game'].upper()} 🎮

➡️ Доступ: {data['access']}
➡️ Цена: {data['price']} {data['currency']}
➡️ Оплата: {data['payment']}

✍️ Писать — {username}

💬 Отзывы
{REVIEWS}

✅ Гарант сделки
{GUARANT}

📢 Abu Post
{ABU_POST}

🧑‍💻 𝙎𝙚𝙡𝙡𝙚𝙧𝙨 𝘼𝙗𝙪 🧑‍💻
"""

    photos = data.get("photos", [])

    if len(photos) < 2:

        await update.message.reply_text(
            "❌ Нужно минимум 2 фотографии. Создайте объявление заново.",
            reply_markup=main_menu
        )
        context.user_data.clear()
        return

    media = []

    for i, photo in enumerate(photos):

        if i == 0:
            media.append(
                InputMediaPhoto(media=photo, caption=caption)
            )
        else:
            media.append(InputMediaPhoto(media=photo))

    await context.bot.send_media_group(
        chat_id=CHANNEL,
        media=media
    )

    cursor.execute(
        """
        INSERT INTO ads
        (user_id, game, access, price, currency, payment, description)
        VALUES(?,?,?,?,?,?,?)
        """,
        (
            user.id,
            data["game"],
            data["access"],
            data["price"],
            data["currency"],
            data["payment"],
            data["description"]
        )
    )

    cursor.execute(
        """
        UPDATE users
        SET posts = posts + 1
        WHERE user_id = ?
        """,
        (user.id,)
    )

    db.commit()

    await update.message.reply_text(
        "✅ Объявление успешно опубликовано!",
        reply_markup=main_menu
    )

    context.user_data.clear()


# =========================
# ПРОФИЛЬ
# =========================

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    cursor.execute(
        """
        SELECT posts
        FROM users
        WHERE user_id = ?
        """,
        (user.id,)
    )

    result = cursor.fetchone()

    posts = result[0] if result else 0

    await update.message.reply_text(
        f"""
👤 Мой профиль

🆔 ID: {user.id}
📢 Объявлений: {posts}

⭐ Репутация: новая
"""
    )


# =========================
# ОТЗЫВЫ
# =========================

async def reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        f"""
⭐ Отзывы

{REVIEWS}
"""
    )


# =========================
# ПОИСК АККАУНТОВ
# =========================

async def search_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cursor.execute(
        """
        SELECT game, price, currency, payment
        FROM ads
        ORDER BY id DESC
        LIMIT 10
        """
    )

    ads = cursor.fetchall()

    if not ads:

        await update.message.reply_text(
            "🔍 Пока нет доступных объявлений."
        )

        return

    text = "🔍 Последние аккаунты:\n\n"

    for ad in ads:

        text += f"""
🎮 {ad[0]}
💰 Цена: {ad[1]} {ad[2]}
💳 Оплата: {ad[3]}

"""

    await update.message.reply_text(text)


# =========================
# ИЗБРАННОЕ
# =========================

async def favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        """
❤️ Избранное

У вас пока нет сохранённых аккаунтов.
"""
    )


# =========================
# ЖАЛОБА
# =========================

async def complaint(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["waiting_complaint"] = True

    await update.message.reply_text(
        """
🚨 Жалоба

Напишите причину жалобы.
Администратор рассмотрит её.
"""
    )


async def save_complaint(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("waiting_complaint"):
        return

    user = update.effective_user

    username = (
        f"@{user.username}"
        if user.username
        else "Без username"
    )

    await context.bot.send_message(
        ADMIN_ID,
        f"""
🚨 Новая жалоба

👤 Пользователь:
{username}

📝 Причина:
{update.message.text}
"""
    )

    await update.message.reply_text(
        "✅ Жалоба отправлена.",
        reply_markup=main_menu
    )

    context.user_data.clear()


# =========================
# СИГНАЛ
# =========================

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        """
🔔 Сигнал

Напишите, какой аккаунт вы ищете.

Например:
🎮 Free Fire
💰 Бюджет
🔑 Доступ
"""
    )


# =========================
# АДМИН ПАНЕЛЬ
# =========================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "❌ Доступ запрещён."
        )

        return

    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ads")
    ads = cursor.fetchone()[0]

    await update.message.reply_text(
        f"""
👮 Abu Post Admin

👤 Пользователи: {users}

📢 Объявления: {ads}
"""
    )


# =========================
# ЗАПУСК
# =========================

def main():

    app = Application.builder().token(TOKEN).build()

    # Диалог создания объявления
    ad_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📢 Объявление$"), create_ad)
        ],
        states={
            GAME: [
                MessageHandler(filters.Regex("^❌ Отменить$"), cancel_ad),
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_game),
            ],
            PHOTOS: [
                MessageHandler(filters.PHOTO, get_photo),
                MessageHandler(filters.Regex("^✅ Готово$"), photos_done),
                MessageHandler(filters.Regex("^❌ Отменить$"), cancel_ad),
            ],
            ACCESS: [
                MessageHandler(filters.Regex("^❌ Отменить$"), cancel_ad),
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_access),
            ],
            DESCRIPTION: [
                MessageHandler(filters.Regex("^❌ Отменить$"), cancel_ad),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_description),
            ],
            PRICE: [
                MessageHandler(filters.Regex("^❌ Отменить$"), cancel_ad),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_price),
            ],
            CURRENCY: [
                MessageHandler(filters.Regex("^❌ Отменить$"), cancel_ad),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_currency),
            ],
            PAYMENT: [
                MessageHandler(filters.Regex("^❌ Отменить$"), cancel_ad),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_payment),
            ],
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Отменить$"), cancel_ad),
            CommandHandler("start", start),
        ],
    )

    # Основные хэндлеры
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(check_sub_button, pattern="^check_sub$"))

    # Диалог объявления
    app.add_handler(ad_conv)

    # Публикация (после диалога)
    app.add_handler(MessageHandler(filters.Regex("^✅ Опубликовать$"), publish_ad))

    # Меню-кнопки
    app.add_handler(MessageHandler(filters.Regex("^👤 Профиль$"), profile))
    app.add_handler(MessageHandler(filters.Regex("^⭐ Отзывы$"), reviews))
    app.add_handler(MessageHandler(filters.Regex("^🔍 Поиск аккаунтов$"), search_ads))
    app.add_handler(MessageHandler(filters.Regex("^❤️ Избранное$"), favorites))
    app.add_handler(MessageHandler(filters.Regex("^🔔 Сигнал$"), signal))
    app.add_handler(MessageHandler(filters.Regex("^🚨 Жалоба$"), complaint))

    # Жалоба — ловим текст (должен быть последним)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_complaint))

    # Запускаем HTTP-сервер для Render (health check)
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Abu Post Bot is running")
        def log_message(self, format, *args):
            pass

    port = int(os.getenv("PORT", 8080))
    health_server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=health_server.serve_forever, daemon=True)
    thread.start()

    print("🤖 Abu Post Bot запущен!")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
