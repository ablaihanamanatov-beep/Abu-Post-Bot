import os
import asyncio
import logging
import sqlite3
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatMemberStatus, ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InputMediaPhoto,
)


# =========================
# НАСТРОЙКИ
# =========================

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

CHANNEL_USERNAME = "@shop_abu1"
REVIEWS = "@otzyvabu"
GUARANT = "@abu_ejje"
ABU_POST = "@Post_FreeFireBot"
ADMIN_ID = 7954321223


# =========================
# ЛОГИ
# =========================

logging.basicConfig(level=logging.INFO)


# =========================
# БД
# =========================

db = sqlite3.connect("abu_post.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    reg_date TEXT,
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
    bank TEXT,
    description TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS favorites(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    ad_id INTEGER
)
""")

db.commit()


# =========================
# FSM
# =========================

class CreateAd(StatesGroup):
    game = State()
    photos = State()
    access = State()
    price = State()
    description = State()
    currency = State()
    bank = State()
    preview = State()

class ComplaintState(StatesGroup):
    waiting = State()

class SignalState(StatesGroup):
    waiting = State()


# =========================
# БОТ
# =========================

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())


# =========================
# КЛАВИАТУРЫ
# =========================

subscribe_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться", url="https://t.me/shop_abu1")],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")]
    ]
)

main_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать объявление", callback_data="create_ad")],
        [
            InlineKeyboardButton(text="🔍 Поиск", callback_data="search"),
            InlineKeyboardButton(text="❤️ Избранное", callback_data="favorites")
        ],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            InlineKeyboardButton(text="⭐ Отзывы", callback_data="reviews")
        ],
        [
            InlineKeyboardButton(text="🔔 Сигнал", callback_data="signal"),
            InlineKeyboardButton(text="🚨 Жалоба", callback_data="complaint")
        ],
        [
            InlineKeyboardButton(text="📜 Правила", callback_data="rules"),
            InlineKeyboardButton(text="ℹ️ Инфо", callback_data="info")
        ]
    ]
)

games_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Free Fire", callback_data="game_Free Fire")],
        [InlineKeyboardButton(text="🔫 PUBG", callback_data="game_PUBG")],
        [InlineKeyboardButton(text="🎵 TikTok", callback_data="game_TikTok")],
        [InlineKeyboardButton(text="⭐ Brawl Stars", callback_data="game_Brawl Stars")],
        [InlineKeyboardButton(text="⚽ FIFA", callback_data="game_FIFA")],
        [InlineKeyboardButton(text="🧱 Roblox", callback_data="game_Roblox")],
        [InlineKeyboardButton(text="🎮 Другое", callback_data="game_Другое")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_menu")]
    ]
)

access_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Google", callback_data="access_Google"),
         InlineKeyboardButton(text="VK", callback_data="access_VK")],
        [InlineKeyboardButton(text="Facebook", callback_data="access_Facebook"),
         InlineKeyboardButton(text="X (Twitter)", callback_data="access_X")],
        [InlineKeyboardButton(text="Apple ID", callback_data="access_Apple ID"),
         InlineKeyboardButton(text="Другое", callback_data="access_Другое")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_ad")]
    ]
)

currency_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🇰🇬 Сом", callback_data="currency_Сом")],
        [InlineKeyboardButton(text="🇷🇺 Рубли", callback_data="currency_Рубли")],
        [InlineKeyboardButton(text="🇹🇯 Сомони", callback_data="currency_Сомони")],
        [InlineKeyboardButton(text="💵 Доллары", callback_data="currency_Доллары")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_ad")]
    ]
)

bank_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🏦 Мбанк", callback_data="bank_Мбанк"),
         InlineKeyboardButton(text="🏦 Т-Банк", callback_data="bank_Т-Банк")],
        [InlineKeyboardButton(text="🏦 Сбер", callback_data="bank_Сбер"),
         InlineKeyboardButton(text="💰 ЮMoney", callback_data="bank_ЮMoney")],
        [InlineKeyboardButton(text="💳 Другое", callback_data="bank_Другое")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_ad")]
    ]
)

photo_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="✅ Готово"), KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True
)

cancel_reply = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True
)

remove_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="‌")]],
    resize_keyboard=True,
    one_time_keyboard=True
)


# =========================
# ВСПОМОГАТЕЛЬНЫЕ
# =========================

async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        )
    except Exception:
        return False


async def send_main_menu(target, text="👋 Выберите действие:"):
    """Отправляет главное меню (Message или CallbackQuery)."""
    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=main_menu)
        except Exception:
            await target.message.answer(text, reply_markup=main_menu)
    else:
        await target.answer(text, reply_markup=main_menu)


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (message.from_user.id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users(user_id, username, reg_date) VALUES(?,?,?)",
            (
                message.from_user.id,
                message.from_user.username,
                datetime.now().strftime("%d.%m.%Y %H:%M")
            )
        )
        db.commit()

    if not await is_subscribed(message.from_user.id):
        await message.answer(
            "👋 Добро пожаловать!\n\n"
            "Для использования бота необходимо подписаться на канал.\n\n"
            "После подписки нажмите кнопку ниже.",
            reply_markup=subscribe_keyboard
        )
        return

    await message.answer(
        "👋 Добро пожаловать в <b>Abu Post</b>\n\n"
        "Выберите действие:",
        reply_markup=main_menu
    )


@dp.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery):
    if await is_subscribed(callback.from_user.id):
        await callback.message.edit_text(
            "✅ Подписка подтверждена!\n\n"
            "👋 Добро пожаловать в <b>Abu Post</b>\n\n"
            "Выберите действие:",
            reply_markup=main_menu
        )
    else:
        await callback.answer("❌ Вы не подписались.", show_alert=True)


@dp.callback_query(F.data == "back_menu")
async def back_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await send_main_menu(callback)


# =========================
# СОЗДАНИЕ ОБЪЯВЛЕНИЯ
# =========================

@dp.callback_query(F.data == "create_ad")
async def create_ad(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🎮 Выберите игру:", reply_markup=games_keyboard)
    await state.set_state(CreateAd.game)


@dp.callback_query(F.data.startswith("game_"))
async def select_game(callback: CallbackQuery, state: FSMContext):
    game = callback.data.replace("game_", "")
    await state.update_data(game=game, photos=[])
    await callback.message.answer(
        "📷 Отправьте от 1 до 12 фотографий.\n\n"
        "После загрузки нажмите «✅ Готово».",
        reply_markup=photo_keyboard
    )
    await callback.message.delete()
    await state.set_state(CreateAd.photos)


@dp.message(CreateAd.photos, F.photo)
async def get_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    if len(photos) < 12:
        photos.append(message.photo[-1].file_id)
        await state.update_data(photos=photos)
        await message.answer(f"📷 Фото добавлено ({len(photos)}/12). Ещё или «✅ Готово».")
    else:
        await message.answer("❗ Максимум 12 фотографий. Нажмите «✅ Готово».")


@dp.message(CreateAd.photos, F.text == "✅ Готово")
async def photos_done(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    if not photos:
        await message.answer("❌ Добавьте хотя бы 1 фото.")
        return
    await message.answer("🔑 Выберите тип доступа:", reply_markup=access_keyboard)
    await state.set_state(CreateAd.access)


@dp.message(CreateAd.photos, F.text == "❌ Отмена")
async def cancel_from_photos(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Создание отменено.", reply_markup=remove_keyboard)
    await message.answer("👋 Выберите действие:", reply_markup=main_menu)


@dp.callback_query(F.data.startswith("access_"))
async def select_access(callback: CallbackQuery, state: FSMContext):
    access = callback.data.replace("access_", "")
    await state.update_data(access=access)
    await callback.message.edit_text(
        "💰 Введите цену аккаунта:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_ad")]]
        )
    )
    await state.set_state(CreateAd.price)


@dp.message(CreateAd.price)
async def get_price(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_ad_handler(message, state)
        return
    await state.update_data(price=message.text)
    await message.answer("📝 Напишите описание аккаунта:", reply_markup=cancel_reply)
    await state.set_state(CreateAd.description)


@dp.message(CreateAd.description)
async def get_description(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await cancel_ad_handler(message, state)
        return
    await state.update_data(description=message.text)
    await message.answer("💵 Выберите валюту:", reply_markup=currency_keyboard)
    await state.set_state(CreateAd.currency)


@dp.callback_query(F.data.startswith("currency_"))
async def select_currency(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.replace("currency_", "")
    await state.update_data(currency=currency)
    await callback.message.edit_text("🏦 Выберите способ оплаты:", reply_markup=bank_keyboard)
    await state.set_state(CreateAd.bank)


@dp.callback_query(F.data.startswith("bank_"))
async def select_bank(callback: CallbackQuery, state: FSMContext):
    bank = callback.data.replace("bank_", "")
    await state.update_data(bank=bank)

    data = await state.get_data()

    preview_text = (
        f"📋 <b>Предпросмотр объявления:</b>\n\n"
        f"🎮 Игра: <b>{data.get('game')}</b>\n"
        f"🔑 Доступ: <b>{data.get('access')}</b>\n"
        f"📝 Описание: {data.get('description')}\n"
        f"💰 Цена: <b>{data.get('price')} {data.get('currency')}</b>\n"
        f"🏦 Оплата: <b>{data.get('bank')}</b>\n\n"
        f"Нажмите «✅ Опубликовать» для публикации."
    )

    publish_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Опубликовать", callback_data="publish_ad")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_ad")]
        ]
    )

    await callback.message.edit_text(preview_text, reply_markup=publish_keyboard)
    await state.set_state(CreateAd.preview)


@dp.callback_query(F.data == "publish_ad")
async def publish_ad(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = callback.from_user
    username = f"@{user.username}" if user.username else f"ID: {user.id}"

    caption = (
        f"🎮 <b>{data['game'].upper()}</b>\n\n"
        f"➡️ Доступ: {data['access']}\n"
        f"💰 Цена: {data['price']} {data['currency']}\n"
        f"🏦 Оплата: {data['bank']}\n\n"
        f"📝 {data['description']}\n\n"
        f"✍️ Писать — {username}\n\n"
        f"💬 Отзывы: {REVIEWS}\n"
        f"✅ Гарант: {GUARANT}\n"
        f"📢 Abu Post: {ABU_POST}\n\n"
        f"🧑‍💻 𝙎𝙚𝙡𝙡𝙚𝙧𝙨 𝘼𝙗𝙪 🧑‍💻"
    )

    photos = data.get("photos", [])

    try:
        if len(photos) == 1:
            await bot.send_photo(
                chat_id=CHANNEL_USERNAME,
                photo=photos[0],
                caption=caption
            )
        else:
            media = [InputMediaPhoto(media=photos[0], caption=caption)]
            for photo in photos[1:]:
                media.append(InputMediaPhoto(media=photo))
            await bot.send_media_group(chat_id=CHANNEL_USERNAME, media=media)

        cursor.execute(
            "INSERT INTO ads(user_id, game, access, price, currency, bank, description) VALUES(?,?,?,?,?,?,?)",
            (user.id, data["game"], data["access"], data["price"], data["currency"], data["bank"], data["description"])
        )
        cursor.execute("UPDATE users SET posts = posts + 1 WHERE user_id = ?", (user.id,))
        db.commit()

        await callback.message.edit_text(
            "✅ Объявление опубликовано!\n\nВыберите действие:",
            reply_markup=main_menu
        )
    except Exception as e:
        logging.error(f"Ошибка публикации: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка при публикации: {e}\n\nПопробуйте позже.",
            reply_markup=main_menu
        )

    await state.clear()


@dp.callback_query(F.data == "cancel_ad")
async def cancel_ad_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Создание отменено.\n\nВыберите действие:", reply_markup=main_menu)


async def cancel_ad_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Создание отменено.", reply_markup=remove_keyboard)
    await message.answer("👋 Выберите действие:", reply_markup=main_menu)


# =========================
# ПРОФИЛЬ
# =========================

@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    user = callback.from_user
    cursor.execute("SELECT posts, reg_date FROM users WHERE user_id=?", (user.id,))
    result = cursor.fetchone()
    posts = result[0] if result else 0
    reg_date = result[1] if result else "—"

    await callback.message.edit_text(
        f"👤 <b>Мой профиль</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"👤 Username: @{user.username or '—'}\n"
        f"📅 Регистрация: {reg_date}\n"
        f"📢 Объявлений: {posts}\n"
        f"⭐ Репутация: новая",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_menu")]]
        )
    )


# =========================
# ОТЗЫВЫ
# =========================

@dp.callback_query(F.data == "reviews")
async def reviews(callback: CallbackQuery):
    await callback.message.edit_text(
        f"⭐ <b>Отзывы</b>\n\n"
        f"Все отзывы о продавцах и покупателях:\n{REVIEWS}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_menu")]]
        )
    )


# =========================
# ПРАВИЛА
# =========================

@dp.callback_query(F.data == "rules")
async def rules(callback: CallbackQuery):
    await callback.message.edit_text(
        "📜 <b>Правила Abu Post</b>\n\n"
        "1. Запрещено продавать ворованные аккаунты.\n"
        "2. Используйте гаранта при крупных сделках.\n"
        "3. Сохраняйте доказательства сделок.\n"
        "4. Мошенничество → бан навсегда.\n"
        "5. Администрация не несёт ответственности за сделки без гаранта.\n\n"
        f"✅ Гарант: {GUARANT}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_menu")]]
        )
    )


# =========================
# ИНФО
# =========================

@dp.callback_query(F.data == "info")
async def info(callback: CallbackQuery):
    await callback.message.edit_text(
        f"ℹ️ <b>О Abu Post</b>\n\n"
        f"Маркетплейс игровых аккаунтов.\n\n"
        f"📢 Канал: {CHANNEL_USERNAME}\n"
        f"⭐ Отзывы: {REVIEWS}\n"
        f"✅ Гарант: {GUARANT}\n"
        f"🤖 Бот: {ABU_POST}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_menu")]]
        )
    )


# =========================
# ПОИСК
# =========================

@dp.callback_query(F.data == "search")
async def search(callback: CallbackQuery):
    cursor.execute(
        "SELECT game, price, currency, bank FROM ads ORDER BY id DESC LIMIT 10"
    )
    ads = cursor.fetchall()

    if not ads:
        await callback.message.edit_text(
            "🔍 Пока нет доступных объявлений.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_menu")]]
            )
        )
        return

    text = "🔍 <b>Последние объявления:</b>\n\n"
    for ad in ads:
        text += f"🎮 {ad[0]} | 💰 {ad[1]} {ad[2]} | 🏦 {ad[3]}\n"

    text += f"\n📢 Все объявления: {CHANNEL_USERNAME}"

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_menu")]]
        )
    )


# =========================
# ИЗБРАННОЕ
# =========================

@dp.callback_query(F.data == "favorites")
async def favorites(callback: CallbackQuery):
    await callback.message.edit_text(
        "❤️ <b>Избранное</b>\n\n"
        "Функция в разработке. Скоро появится возможность сохранять понравившиеся аккаунты.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_menu")]]
        )
    )


# =========================
# ЖАЛОБА
# =========================

@dp.callback_query(F.data == "complaint")
async def complaint(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🚨 <b>Жалоба</b>\n\n"
        "Напишите причину жалобы. Администратор рассмотрит её.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="back_menu")]]
        )
    )
    await state.set_state(ComplaintState.waiting)


@dp.message(ComplaintState.waiting)
async def save_complaint(message: Message, state: FSMContext):
    user = message.from_user
    username = f"@{user.username}" if user.username else f"ID: {user.id}"

    await bot.send_message(
        ADMIN_ID,
        f"🚨 <b>Новая жалоба</b>\n\n"
        f"👤 Пользователь: {username}\n"
        f"🆔 ID: {user.id}\n\n"
        f"📝 Причина:\n{message.text}"
    )

    await state.clear()
    await message.answer("✅ Жалоба отправлена администратору.", reply_markup=remove_keyboard)
    await message.answer("👋 Выберите действие:", reply_markup=main_menu)


# =========================
# СИГНАЛ
# =========================

@dp.callback_query(F.data == "signal")
async def signal(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔔 <b>Сигнал</b>\n\n"
        "Напишите какой аккаунт вы ищете.\n\n"
        "Например:\n"
        "🎮 Free Fire, бюджет 500 сом, нужен Google-доступ",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="back_menu")]]
        )
    )
    await state.set_state(SignalState.waiting)


@dp.message(SignalState.waiting)
async def save_signal(message: Message, state: FSMContext):
    user = message.from_user
    username = f"@{user.username}" if user.username else f"ID: {user.id}"

    await bot.send_message(
        ADMIN_ID,
        f"🔔 <b>Новый сигнал (запрос)</b>\n\n"
        f"👤 Пользователь: {username}\n"
        f"🆔 ID: {user.id}\n\n"
        f"🔍 Ищет:\n{message.text}"
    )

    await state.clear()
    await message.answer(
        "✅ Сигнал отправлен! Если подходящий аккаунт появится — мы уведомим.",
        reply_markup=remove_keyboard
    )
    await message.answer("👋 Выберите действие:", reply_markup=main_menu)


# =========================
# АДМИН
# =========================

@dp.message(Command("admin"))
async def admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещён.")
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ads")
    ads_count = cursor.fetchone()[0]

    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Последние объявления", callback_data="admin_ads")],
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")]
        ]
    )

    await message.answer(
        f"👮 <b>Abu Post Admin</b>\n\n"
        f"👤 Пользователей: {users_count}\n"
        f"📢 Объявлений: {ads_count}",
        reply_markup=admin_keyboard
    )


@dp.callback_query(F.data == "admin_ads")
async def admin_ads(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT id, game, price, currency FROM ads ORDER BY id DESC LIMIT 5")
    ads = cursor.fetchall()
    text = "📋 <b>Последние 5 объявлений:</b>\n\n"
    for ad in ads:
        text += f"#{ad[0]} | 🎮 {ad[1]} | 💰 {ad[2]} {ad[3]}\n"
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]]
        )
    )


@dp.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT user_id, username, posts FROM users ORDER BY posts DESC LIMIT 10")
    users = cursor.fetchall()
    text = "👥 <b>Топ пользователей:</b>\n\n"
    for u in users:
        uname = f"@{u[1]}" if u[1] else f"ID:{u[0]}"
        text += f"{uname} — {u[2]} объявл.\n"
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]]
        )
    )


@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM ads")
    ads_count = cursor.fetchone()[0]
    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Последние объявления", callback_data="admin_ads")],
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")]
        ]
    )
    await callback.message.edit_text(
        f"👮 <b>Abu Post Admin</b>\n\n"
        f"👤 Пользователей: {users_count}\n"
        f"📢 Объявлений: {ads_count}",
        reply_markup=admin_keyboard
    )


# =========================
# ЗАПУСК
# =========================

def start_health_server():
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Abu Post Bot is running")
        def log_message(self, format, *args):
            pass

    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"✅ Health server started on port {port}")


async def main():
    start_health_server()
    print("🤖 Abu Post Bot запущен!")
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
