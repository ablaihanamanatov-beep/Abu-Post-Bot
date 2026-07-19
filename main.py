# =========================================================
# main.py
# Telegram Account Marketplace Bot
# aiogram 3.22.0
# =========================================================

import asyncio
import logging
import os
import sqlite3

from datetime import datetime
from threading import Thread

from flask import Flask

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InputMediaPhoto
)

from aiogram.utils.keyboard import InlineKeyboardBuilder


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")

SUBSCRIBE_CHANNEL = "@shop_abu1"

POST_CHANNEL = "@shop_abu1"  # замените на ID или username вашего канала публикаций

REVIEWS_CHANNEL = "@otzyvabu"

SUPPORT_USERNAME = "@abu_ejje"

RULES_USERNAME = "@abupravila"

ABU_POST = "@Post_FreeFireBot"

SELLERS = "Sellers Abu"


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(level=logging.INFO)


# =========================================================
# BOT
# =========================================================

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher(
    storage=MemoryStorage()
)


# =========================================================
# FLASK KEEP ALIVE
# =========================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is alive"


def flask_run():
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080))
    )


def keep_alive():
    Thread(
        target=flask_run,
        daemon=True
    ).start()


# =========================================================
# DATABASE
# =========================================================

db = sqlite3.connect(
    "bot.db",
    check_same_thread=False
)

cursor = db.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    username TEXT,
    first_name TEXT,
    register_date TEXT,
    ads_count INTEGER DEFAULT 0,
    moderation INTEGER DEFAULT 0,
    approved INTEGER DEFAULT 0,
    removed INTEGER DEFAULT 0,
    reviews INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    dislikes INTEGER DEFAULT 0,
    active_boosts INTEGER DEFAULT 0,
    total_boosts INTEGER DEFAULT 0
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS ads(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    game TEXT,
    access TEXT,
    description TEXT,
    price INTEGER,
    currency TEXT,
    bank TEXT,
    created TEXT,
    status TEXT
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS photos(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad_id INTEGER,
    file_id TEXT
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS reviews(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    text TEXT,
    created TEXT
)
""")


db.commit()

# Миграция: добавляем колонки если их нет (для старых баз данных)
migrations = [
    "ALTER TABLE ads ADD COLUMN bank TEXT",
    "ALTER TABLE ads ADD COLUMN created TEXT",
    "ALTER TABLE ads ADD COLUMN status TEXT",
    "ALTER TABLE users ADD COLUMN moderation INTEGER DEFAULT 0",
    "ALTER TABLE users ADD COLUMN approved INTEGER DEFAULT 0",
    "ALTER TABLE users ADD COLUMN removed INTEGER DEFAULT 0",
    "ALTER TABLE users ADD COLUMN reviews INTEGER DEFAULT 0",
    "ALTER TABLE users ADD COLUMN likes INTEGER DEFAULT 0",
    "ALTER TABLE users ADD COLUMN dislikes INTEGER DEFAULT 0",
    "ALTER TABLE users ADD COLUMN active_boosts INTEGER DEFAULT 0",
    "ALTER TABLE users ADD COLUMN total_boosts INTEGER DEFAULT 0",
]
for migration in migrations:
    try:
        cursor.execute(migration)
        db.commit()
    except Exception:
        pass  # колонка уже существует


# =========================================================
# FSM
# =========================================================

class CreateAdvertisement(StatesGroup):
    game = State()
    photos = State()
    access = State()
    price = State()
    description = State()
    currency = State()
    bank = State()
    preview = State()


# =========================================================
# CONSTANTS
# =========================================================

GAMES = {
    "freefire": "🔥 Free Fire",
    "pubg": "🔫 PUBG",
    "tiktok": "🎵 TikTok",
    "brawlstars": "⭐ Brawl Stars",
    "fifa": "⚽ FIFA",
    "roblox": "🧱 Roblox"
}

ACCESS_TYPES = {
    "google": "Google",
    "vk": "VK",
    "x": "X",
    "facebook": "Facebook",
    "mail": "Почта"
}

CURRENCIES = {
    "kgs": "🇰🇬 Сом",
    "kzt": "🇰🇿 Тенге",
    "tjs": "🇹🇯 Сомони",
    "rub": "🇷🇺 Рубль"
}

BANKS = {
    "mbank": "🏦 MBANK",
    "tbank": "🏦 T-Bank",
    "yumoney": "🏦 ЮMoney",
    "obank": "🏦 О!Банк",
    "sber": "🏦 Сбер",
    "kaspi": "🏦 Kaspi"
}


# =========================================================
# DATABASE FUNCTIONS
# =========================================================

def create_user(user):
    cursor.execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (user.id,)
    )

    if cursor.fetchone():
        return

    cursor.execute(
        """
        INSERT INTO users
        (user_id, username, first_name, register_date)
        VALUES (?, ?, ?, ?)
        """,
        (
            user.id,
            user.username,
            user.first_name,
            datetime.now().strftime("%d.%m.%Y %H:%M")
        )
    )

    db.commit()


def get_user(user_id):
    cursor.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    )
    return cursor.fetchone()


def update_publication_stat(user_id):
    cursor.execute(
        """
        UPDATE users
        SET ads_count = ads_count + 1
        WHERE user_id=?
        """,
        (user_id,)
    )
    db.commit()


def create_advertisement(user_id, game, access, description, price, currency, bank):
    cursor.execute(
        """
        INSERT INTO ads
        (user_id, game, access, description, price, currency, bank, created, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            game,
            access,
            description,
            price,
            currency,
            bank,
            datetime.now().strftime("%d.%m.%Y %H:%M"),
            "published"
        )
    )
    db.commit()
    return cursor.lastrowid


def save_photo(ad_id, file_id):
    cursor.execute(
        "INSERT INTO photos (ad_id, file_id) VALUES (?, ?)",
        (ad_id, file_id)
    )
    db.commit()


def profile_text(user_id):
    # Колонки: 0=id, 1=user_id, 2=username, 3=first_name, 4=register_date,
    #          5=ads_count, 6=moderation, 7=approved, 8=removed, 9=reviews,
    #          10=likes, 11=dislikes, 12=active_boosts, 13=total_boosts
    user = get_user(user_id)

    if not user:
        return "❌ Пользователь не найден."

    ads_count = user[5]
    level = "Новый"
    if ads_count >= 10:
        level = "Продавец"
    if ads_count >= 50:
        level = "Опытный"
    if ads_count >= 100:
        level = "Профессионал"

    return (
        "📊 <b>Ваша статистика</b>\n\n"
        "⚙️ <b>Профиль:</b>\n"
        f"▸ Всего объявлений: {user[5]}\n"
        f"▸ На модерации: {user[6]}\n"
        f"▸ Регистрация: {user[4]}\n"
        f"▸ Уровень: {level}\n\n"
        "👤 <b>Репутация продавца:</b>\n"
        f"▸ Одобрено: {user[7]}\n"
        f"▸ Снято: {user[8]}\n"
        f"▸ Отзывы: {user[9]}\n"
        f"▸ Лайки: {user[10]}\n"
        f"▸ Дизлайки: {user[11]}\n"
        f"▸ Активные бусты: {user[12]}\n"
        f"▸ Всего бустов: {user[13]}"
    )


# =========================================================
# KEYBOARDS
# =========================================================

def subscribe_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📢 Подписаться",
            url="https://t.me/shop_abu1"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="✅ Проверить подписку",
            callback_data="check_subscription"
        )
    )
    return builder.as_markup()


def main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📝 Создать объявление", callback_data="create_ad"))
    builder.row(InlineKeyboardButton(text="📜 Правила", callback_data="rules"))
    builder.row(InlineKeyboardButton(text="⭐ Отзывы", callback_data="reviews"))
    builder.row(InlineKeyboardButton(text="ℹ️ Инфо", callback_data="info"))
    builder.row(InlineKeyboardButton(text="👤 Профиль", callback_data="profile"))
    return builder.as_markup()


def games_keyboard():
    builder = InlineKeyboardBuilder()
    for key, value in GAMES.items():
        builder.button(text=value, callback_data=f"game_{key}")
    builder.adjust(2)
    return builder.as_markup()


def access_keyboard():
    builder = InlineKeyboardBuilder()
    for key, value in ACCESS_TYPES.items():
        builder.button(text=value, callback_data=f"access_{key}")
    builder.adjust(2)
    return builder.as_markup()


def currency_keyboard():
    builder = InlineKeyboardBuilder()
    for key, value in CURRENCIES.items():
        builder.button(text=value, callback_data=f"currency_{key}")
    builder.adjust(2)
    return builder.as_markup()


def bank_keyboard():
    builder = InlineKeyboardBuilder()
    for key, value in BANKS.items():
        builder.button(text=value, callback_data=f"bank_{key}")
    builder.adjust(2)
    return builder.as_markup()


def preview_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Опубликовать", callback_data="publish"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


def back_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back"))
    return builder.as_markup()


photo_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Готово")],
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True
)


# =========================================================
# SUBSCRIPTION CHECK
# =========================================================

async def check_subscription(user_id: int):
    try:
        member = await bot.get_chat_member(
            chat_id=SUBSCRIBE_CHANNEL,
            user_id=user_id
        )
        return member.status in [
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR
        ]
    except Exception:
        return False


# =========================================================
# START COMMAND
# =========================================================

@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    create_user(message.from_user)

    if not await check_subscription(message.from_user.id):
        await message.answer(
            "👋 <b>Добро пожаловать!</b>\n\n"
            "Для использования бота необходимо "
            "подписаться на наш канал.\n\n"
            "После подписки нажмите кнопку "
            "«✅ Проверить подписку».",
            reply_markup=subscribe_keyboard()
        )
        return

    await message.answer(
        "🏠 <b>Главное меню</b>",
        reply_markup=main_menu_keyboard()
    )


# =========================================================
# CHECK SUBSCRIPTION BUTTON
# =========================================================

@dp.callback_query(F.data == "check_subscription")
async def check_subscription_button(callback: CallbackQuery):
    result = await check_subscription(callback.from_user.id)

    if not result:
        await callback.answer(
            "❌ Вы еще не подписались на канал.",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        "✅ <b>Подписка успешно подтверждена!</b>"
    )
    await callback.message.answer(
        "🏠 <b>Главное меню</b>",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()


# =========================================================
# BACK MENU
# =========================================================

@dp.callback_query(F.data == "back")
async def back_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()


# =========================================================
# PROFILE
# =========================================================

@dp.callback_query(F.data == "profile")
async def profile_handler(callback: CallbackQuery):
    text = profile_text(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=back_keyboard())
    await callback.answer()


# =========================================================
# RULES
# =========================================================

@dp.callback_query(F.data == "rules")
async def rules_handler(callback: CallbackQuery):
    text = (
        "📜 <b>Правила публикации</b>\n\n"
        "1. Запрещено публиковать ложную информацию "
        "об аккаунте.\n\n"
        "2. Используйте только реальные фотографии "
        "аккаунта.\n\n"
        "3. Цена должна соответствовать стоимости "
        "аккаунта.\n\n"
        "4. Запрещено размещать одинаковые объявления "
        "несколько раз.\n\n"
        "5. Не используйте нецензурную лексику.\n\n"
        "6. После продажи аккаунта удалите или "
        "обновите объявление.\n\n"
        "7. Администрация вправе удалить объявление, "
        "нарушающее правила.\n\n"
        "⚠️ Публикуя объявление, вы соглашаетесь "
        "соблюдать правила.\n\n"
        f"📖 Полная версия правил:\n{RULES_USERNAME}"
    )
    await callback.message.edit_text(text, reply_markup=back_keyboard())
    await callback.answer()


# =========================================================
# REVIEWS
# =========================================================

@dp.callback_query(F.data == "reviews")
async def reviews_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        f"⭐ <b>Отзывы</b>\n\n{REVIEWS_CHANNEL}",
        reply_markup=back_keyboard()
    )
    await callback.answer()


# =========================================================
# INFO
# =========================================================

@dp.callback_query(F.data == "info")
async def info_handler(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📢 Канал", url="https://t.me/shop_abu1"))
    builder.row(InlineKeyboardButton(text="👨‍💻 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back"))

    await callback.message.edit_text(
        "ℹ️ <b>Информация</b>\n\n"
        "Выберите раздел.",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


# =========================================================
# CREATE AD START
# =========================================================

@dp.callback_query(F.data == "create_ad")
async def create_ad_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(CreateAdvertisement.game)
    await callback.message.edit_text(
        "🎮 <b>Выберите игру:</b>",
        reply_markup=games_keyboard()
    )
    await callback.answer()


# =========================================================
# GAME SELECT
# =========================================================

@dp.callback_query(CreateAdvertisement.game, F.data.startswith("game_"))
async def game_selected(callback: CallbackQuery, state: FSMContext):
    game_key = callback.data.replace("game_", "")
    game_name = GAMES.get(game_key, "Неизвестная игра")

    await state.update_data(game=game_name, photos=[])
    await state.set_state(CreateAdvertisement.photos)

    await callback.message.delete()
    await callback.message.answer(
        "📷 <b>Отправьте от 1 до 12 фотографий.</b>\n\n"
        "После загрузки нажмите кнопку «✅ Готово».",
        reply_markup=photo_keyboard
    )
    await callback.answer()


# =========================================================
# RECEIVE PHOTOS
# =========================================================

@dp.message(CreateAdvertisement.photos, F.photo)
async def receive_ad_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])

    if len(photos) >= 12:
        await message.answer("❌ Максимум можно отправить 12 фотографий.")
        return

    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await message.answer(f"✅ Фото добавлено: {len(photos)}/12")


# =========================================================
# PHOTO CANCEL
# =========================================================

@dp.message(CreateAdvertisement.photos, F.text == "❌ Отмена")
async def cancel_photo_upload(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Создание объявления отменено.",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer(
        "🏠 Главное меню",
        reply_markup=main_menu_keyboard()
    )


# =========================================================
# PHOTO COMPLETE
# =========================================================

@dp.message(CreateAdvertisement.photos, F.text == "✅ Готово")
async def photos_complete(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])

    if len(photos) == 0:
        await message.answer("❌ Сначала отправьте хотя бы одну фотографию.")
        return

    await state.set_state(CreateAdvertisement.access)
    await message.answer(
        "🔑 <b>Выберите привязку:</b>",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer(
        "Выберите вариант:",
        reply_markup=access_keyboard()
    )


# =========================================================
# ACCESS SELECT
# =========================================================

@dp.callback_query(CreateAdvertisement.access, F.data.startswith("access_"))
async def access_selected(callback: CallbackQuery, state: FSMContext):
    access_key = callback.data.replace("access_", "")
    access_name = ACCESS_TYPES.get(access_key, "Не указано")

    await state.update_data(access=access_name)
    await state.set_state(CreateAdvertisement.price)

    await callback.message.edit_text(
        "💰 <b>Введите цену аккаунта.</b>\n\n"
        "Цена должна быть указана цифрами."
    )
    await callback.answer()


# =========================================================
# PRICE INPUT
# =========================================================

@dp.message(CreateAdvertisement.price)
async def price_input(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Введите цену только цифрами.")
        return

    await state.update_data(price=int(message.text))
    await state.set_state(CreateAdvertisement.description)
    await message.answer("📝 <b>Напишите описание аккаунта.</b>")


# =========================================================
# DESCRIPTION INPUT
# =========================================================

@dp.message(CreateAdvertisement.description)
async def description_input(message: Message, state: FSMContext):
    description = message.text.strip()

    if len(description) < 3:
        await message.answer("❌ Описание слишком короткое.")
        return

    await state.update_data(description=description)
    await state.set_state(CreateAdvertisement.currency)
    await message.answer(
        "💱 <b>Выберите валюту:</b>",
        reply_markup=currency_keyboard()
    )


# =========================================================
# CURRENCY SELECT
# =========================================================

@dp.callback_query(CreateAdvertisement.currency, F.data.startswith("currency_"))
async def currency_selected(callback: CallbackQuery, state: FSMContext):
    currency_key = callback.data.replace("currency_", "")
    currency_name = CURRENCIES.get(currency_key, "Сом")

    await state.update_data(currency=currency_name)
    await state.set_state(CreateAdvertisement.bank)

    await callback.message.edit_text(
        "🏦 <b>Выберите банк оплаты:</b>",
        reply_markup=bank_keyboard()
    )
    await callback.answer()


# =========================================================
# BANK SELECT
# =========================================================

@dp.callback_query(CreateAdvertisement.bank, F.data.startswith("bank_"))
async def bank_selected(callback: CallbackQuery, state: FSMContext):
    bank_key = callback.data.replace("bank_", "")
    bank_name = BANKS.get(bank_key, "Не указан")

    await state.update_data(bank=bank_name)
    data = await state.get_data()

    preview_text = (
        "📋 <b>Предпросмотр объявления</b>\n\n"
        f"🎮 Игра: {data['game']}\n"
        f"🔑 Доступ: {data['access']}\n\n"
        f"📝 Описание:\n"
        f"{data['description']}\n\n"
        f"💰 Цена: {data['price']} {data['currency']}\n"
        f"💳 Оплата: {bank_name}"
    )

    await state.set_state(CreateAdvertisement.preview)
    await callback.message.delete()

    await bot.send_photo(
        chat_id=callback.from_user.id,
        photo=data["photos"][0],
        caption=preview_text,
        reply_markup=preview_keyboard()
    )
    await callback.answer()


# =========================================================
# PREVIEW CANCEL
# =========================================================

@dp.callback_query(CreateAdvertisement.preview, F.data == "cancel")
async def preview_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await bot.send_message(callback.from_user.id, "❌ Создание объявления отменено.")
    await bot.send_message(
        callback.from_user.id,
        "🏠 Главное меню",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()


# =========================================================
# PUBLISH ADVERTISEMENT
# =========================================================

@dp.callback_query(CreateAdvertisement.preview, F.data == "publish")
async def publish_advertisement(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id

    ad_id = create_advertisement(
        user_id=user_id,
        game=data["game"],
        access=data["access"],
        description=data["description"],
        price=data["price"],
        currency=data["currency"],
        bank=data["bank"]
    )

    for photo in data["photos"]:
        save_photo(ad_id, photo)

    update_publication_stat(user_id)

    username = (
        f"@{callback.from_user.username}"
        if callback.from_user.username
        else callback.from_user.full_name
    )

    caption = (
        f"🎮🔥 <b>{data['game'].upper()}</b> 🎮🔥\n\n"
        f"➡️ Доступ: {data['access']}\n"
        f"➡️ Цена: {data['price']} {data['currency']}\n"
        f"➡️ Оплата: {data['bank']}\n\n"
        f"📝 <b>Описание:</b>\n"
        f"{data['description']}\n\n"
        f"✍️ Писать — {username}\n\n"
        f"💬 Отзывы\n"
        f"{REVIEWS_CHANNEL}\n\n"
        f"✅ Гарант сделки\n"
        f"{SUPPORT_USERNAME}\n\n"
        f"📢 Abu Post\n"
        f"{ABU_POST}\n\n"
        f"🧑‍💼 {SELLERS}"
    )

    media = []
    for index, photo in enumerate(data["photos"]):
        if index == 0:
            media.append(InputMediaPhoto(media=photo, caption=caption))
        else:
            media.append(InputMediaPhoto(media=photo))

    await bot.send_media_group(chat_id=POST_CHANNEL, media=media)

    await state.clear()
    await callback.message.delete()

    await bot.send_message(user_id, "✅ <b>Ваше объявление успешно опубликовано.</b>")
    await bot.send_message(
        user_id,
        "🏠 <b>Главное меню</b>",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()


# =========================================================
# ERROR HANDLER
# =========================================================

@dp.error()
async def global_error_handler(event, exception):
    logging.exception(exception)
    return True


# =========================================================
# START BOT
# =========================================================

async def main():
    keep_alive()
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Bot started")
    await dp.start_polling(bot)


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    asyncio.run(main())
