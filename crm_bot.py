import os
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.filters import Command

from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

import psycopg2

# ================= CONFIG =================

TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

ADMIN_ID = 8398266271

# ================= BOT =================

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================= DATABASE =================

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True

cursor = conn.cursor()

# ================= TABLES =================

cursor.execute("""
CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    tg_id BIGINT UNIQUE,
    name TEXT,
    visits INTEGER DEFAULT 0,
    total_paid INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    title TEXT,
    price INTEGER,
    duration INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS masters (
    id SERIAL PRIMARY KEY,
    name TEXT,
    specialty TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS appointments (
    id SERIAL PRIMARY KEY,
    client_id BIGINT,
    service TEXT,
    master TEXT,
    date TEXT,
    time TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
)
""")

# ================= FSM =================

class BookingState(StatesGroup):
    service = State()
    master = State()
    date = State()
    time = State()

# ================= KEYBOARDS =================

client_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Записаться")],

        [
            KeyboardButton(text="💅 Услуги"),
            KeyboardButton(text="👩‍🔬 Мастера")
        ],

        [
            KeyboardButton(text="🕒 Мои записи"),
            KeyboardButton(text="💰 Прайс")
        ],

        [
            KeyboardButton(text="📍 Адрес"),
            KeyboardButton(text="📞 Контакты")
        ]
    ],
    resize_keyboard=True
)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Все записи")],

        [
            KeyboardButton(text="👥 Клиенты"),
            KeyboardButton(text="📊 Статистика")
        ],

        [
            KeyboardButton(text="➕ Добавить услугу"),
            KeyboardButton(text="➕ Добавить мастера")
        ]
    ],
    resize_keyboard=True
)

# ================= START =================

@dp.message(Command("start"))
async def start_cmd(message: Message):

    user_id = message.from_user.id
    full_name = message.from_user.full_name

    cursor.execute(
        "SELECT * FROM clients WHERE tg_id = %s",
        (user_id,)
    )

    client = cursor.fetchone()

    if not client:
        cursor.execute(
            """
            INSERT INTO clients (tg_id, name)
            VALUES (%s, %s)
            """,
            (user_id, full_name)
        )

    await message.answer(
        "Добро пожаловать в CRM бот ✅",
        reply_markup=client_kb
    )

# ================= ADMIN =================

@dp.message(Command("admin"))
async def admin_panel(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM clients")
    users_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments")
    appointments_count = cursor.fetchone()[0]

    await message.answer(
        f"👨‍💼 Админ панель\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"📅 Записей: {appointments_count}",
        reply_markup=admin_kb
    )

# ================= BOOKING =================

@dp.message(F.text == "📅 Записаться")
async def booking_start(message: Message, state: FSMContext):

    cursor.execute("SELECT title FROM services")
    services = cursor.fetchall()

    if not services:
        await message.answer("Услуги пока не добавлены.")
        return

    buttons = []

    for service in services:
        buttons.append([KeyboardButton(text=service[0])])

    kb = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

    await state.set_state(BookingState.service)

    await message.answer(
        "💅 Выберите услугу:",
        reply_markup=kb
    )

# ================= SERVICE =================

@dp.message(BookingState.service)
async def booking_service(message: Message, state: FSMContext):

    await state.update_data(service=message.text)

    cursor.execute("SELECT name FROM masters")
    masters = cursor.fetchall()

    buttons = []

    for master in masters:
        buttons.append([KeyboardButton(text=master[0])])

    kb = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

    await state.set_state(BookingState.master)

    await message.answer(
        "👩 Выберите мастера:",
        reply_markup=kb
    )

# ================= MASTER =================

@dp.message(BookingState.master)
async def booking_master(message: Message, state: FSMContext):

    await state.update_data(master=message.text)

    await state.set_state(BookingState.date)

    await message.answer(
        "📅 Введите дату:\n\nНапример: 15.05"
    )

# ================= DATE =================

@dp.message(BookingState.date)
async def booking_date(message: Message, state: FSMContext):

    await state.update_data(date=message.text)

    buttons = [
        [KeyboardButton(text="10:00")],
        [KeyboardButton(text="12:00")],
        [KeyboardButton(text="14:00")],
        [KeyboardButton(text="16:00")],
        [KeyboardButton(text="18:00")]
    ]

    kb = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

    await state.set_state(BookingState.time)

    await message.answer(
        "🕒 Выберите время:",
        reply_markup=kb
    )

# ================= TIME =================

@dp.message(BookingState.time)
async def booking_time(message: Message, state: FSMContext):

    await state.update_data(time=message.text)

    data = await state.get_data()

    service = data["service"]
    master = data["master"]
    date = data["date"]
    time = data["time"]

    cursor.execute(
        """
        INSERT INTO appointments
        (client_id, service, master, date, time)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            message.from_user.id,
            service,
            master,
            date,
            time
        )
    )

    conn.commit()

    await message.answer(
        "✅ Вы успешно записаны!\n\n"
        f"💅 Услуга: {service}\n"
        f"👩 Мастер: {master}\n"
        f"📅 Дата: {date}\n"
        f"🕒 Время: {time}",
        reply_markup=client_kb
    )

    await state.clear()

# ================= SERVICES =================

@dp.message(F.text == "💅 Услуги")
async def services(message: Message):

    cursor.execute("SELECT title, price FROM services")

    services_list = cursor.fetchall()

    if not services_list:
        await message.answer("Услуги пока не добавлены.")
        return

    text = "💅 Наши услуги:\n\n"

    for service in services_list:
        text += f"• {service[0]} — {service[1]}₸\n"

    await message.answer(text)

# ================= MASTERS =================

@dp.message(F.text == "👩‍🔬 Мастера")
async def masters(message: Message):

    cursor.execute("SELECT name, specialty FROM masters")

    masters_list = cursor.fetchall()

    if not masters_list:
        await message.answer("Мастера пока не добавлены.")
        return

    text = "👩‍🔬 Наши мастера:\n\n"

    for master in masters_list:
        text += f"• {master[0]} — {master[1]}\n"

    await message.answer(text)

# ================= MY APPOINTMENTS =================

@dp.message(F.text == "🕒 Мои записи")
async def my_appointments(message: Message):

    cursor.execute(
        """
        SELECT service, master, date, time
        FROM appointments
        WHERE client_id = %s
        ORDER BY id DESC
        """,
        (message.from_user.id,)
    )

    appointments = cursor.fetchall()

    if not appointments:
        await message.answer("У вас пока нет записей.")
        return

    text = "🕒 Ваши записи:\n\n"

    for item in appointments:

        text += (
            f"💅 Услуга: {item[0]}\n"
            f"👩 Мастер: {item[1]}\n"
            f"📅 Дата: {item[2]}\n"
            f"🕒 Время: {item[3]}\n\n"
        )

    await message.answer(text)

# ================= PRICE =================

@dp.message(F.text == "💰 Прайс")
async def price(message: Message):

    cursor.execute("SELECT title, price FROM services")

    services_list = cursor.fetchall()

    if not services_list:
        await message.answer("Прайс пока пуст.")
        return

    text = "💰 Прайс:\n\n"

    for service in services_list:
        text += f"{service[0]} — {service[1]}₸\n"

    await message.answer(text)

# ================= ADDRESS =================

@dp.message(F.text == "📍 Адрес")
async def address(message: Message):

    await message.answer(
        "📍 Алматы\nул. Примерная 25"
    )

# ================= CONTACTS =================

@dp.message(F.text == "📞 Контакты")
async def contacts(message: Message):

    await message.answer(
        "📞 +7 777 777 77 77"
    )

# ================= ALL APPOINTMENTS =================

@dp.message(F.text == "📋 Все записи")
async def all_appointments(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("""
        SELECT service, master, date, time
        FROM appointments
        ORDER BY id DESC
    """)

    appointments = cursor.fetchall()

    if not appointments:
        await message.answer("Записей пока нет.")
        return

    text = "📋 Все записи:\n\n"

    for app in appointments:

        text += (
            f"💅 {app[0]}\n"
            f"👩 {app[1]}\n"
            f"📅 {app[2]}\n"
            f"🕒 {app[3]}\n\n"
        )

    await message.answer(text)

# ================= CLIENTS =================

@dp.message(F.text == "👥 Клиенты")
async def clients_list(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("""
        SELECT name, visits, total_paid
        FROM clients
        ORDER BY id DESC
    """)

    clients = cursor.fetchall()

    if not clients:
        await message.answer("Клиентов пока нет.")
        return

    text = "👥 Клиенты:\n\n"

    for client in clients:

        text += (
            f"👤 {client[0]}\n"
            f"📅 Визитов: {client[1]}\n"
            f"💰 Потратил: {client[2]}₸\n\n"
        )

    await message.answer(text)

# ================= STATS =================

@dp.message(F.text == "📊 Статистика")
async def stats(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM clients")
    clients_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments")
    appointments_count = cursor.fetchone()[0]

    await message.answer(
        f"📊 Статистика\n\n"
        f"👥 Клиентов: {clients_count}\n"
        f"📅 Записей: {appointments_count}"
    )

# ================= ADD SERVICE =================

@dp.message(F.text == "➕ Добавить услугу")
async def add_service(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        "Отправьте:\n\n"
        "Маникюр,15000,90"
    )

# ================= ADD MASTER =================

@dp.message(F.text == "➕ Добавить мастера")
async def add_master(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        "Отправьте:\n\n"
        "Алина,Маникюр"
    )

# ================= AUTO ADD =================

@dp.message(F.text.contains(","))
async def auto_add(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split(",")

    # SERVICE
    if len(parts) == 3:

        title = parts[0]
        price = int(parts[1])
        duration = int(parts[2])

        cursor.execute(
            """
            INSERT INTO services (title, price, duration)
            VALUES (%s, %s, %s)
            """,
            (title, price, duration)
        )

        await message.answer("✅ Услуга добавлена")

    # MASTER
    elif len(parts) == 2:

        name = parts[0]
        specialty = parts[1]

        cursor.execute(
            """
            INSERT INTO masters (name, specialty)
            VALUES (%s, %s)
            """,
            (name, specialty)
        )

        await message.answer("✅ Мастер добавлен")

# ================= MAIN =================

async def main():

    print("CRM BOT STARTED")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
