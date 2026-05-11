import os
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.filters import Command

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
    phone TEXT,
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
    client_id INTEGER,
    service TEXT,
    master TEXT,
    date TEXT,
    time TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
)
""")

# ================= KEYBOARDS =================

client_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📅 Записаться")
        ],
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
        [
            KeyboardButton(text="📋 Все записи")
        ],
        [
            KeyboardButton(text="👥 Клиенты"),
            KeyboardButton(text="📊 Статистика")
        ],
        [
            KeyboardButton(text="➕ Добавить услугу"),
            KeyboardButton(text="➕ Добавить мастера")
        ],
        [
            KeyboardButton(text="📢 Рассылка")
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

    text = (
        "Добро пожаловать в CRM бот ✅\n\n"
        "Ваш аккаунт сохранен."
    )

    await message.answer(
        text,
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

    text = (
        f"👨‍💼 Админ панель\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"📅 Записей: {appointments_count}"
    )

    await message.answer(
        text,
        reply_markup=admin_kb
    )

# ================= CLIENT MENU =================

@dp.message(F.text == "📅 Записаться")
async def booking(message: Message):

    text = (
    "📅 Онлайн запись\n\n"
    "Отправьте:\n\n"
    "1. Услугу\n"
    "2. Мастера\n"
    "3. Дату\n"
    "4. Время\n\n"
    "Пример:\n\n"
    "Стрижка\n"
    "Мадина\n"
    "12.05\n"
    "13:00"
)

    await message.answer(text)

@dp.message(F.text.regexp(r".+\n.+\n.+\n.+"))
async def save_booking(message: Message):

    try:

        text = message.text.strip()

        lines = text.split("\n")

        if len(lines) != 4:
            return

        service = lines[0].strip()
        master = lines[1].strip()
        date = lines[2].strip()
        time = lines[3].strip().replace(".", ":")

        print(service, master, date, time)

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

        await message.answer(
            f"✅ Вы успешно записаны!\n\n"
            f"💅 Услуга: {service}\n"
            f"👩 Мастер: {master}\n"
            f"📅 Дата: {date}\n"
            f"🕒 Время: {time}"
        )

    except Exception as e:
        print("ERROR:", e)
        
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

@dp.message(F.text == "🕒 Мои записи")
async def my_appointments(message: Message):

    user_id = message.from_user.id

    cursor.execute(
        "SELECT id FROM clients WHERE tg_id = %s",
        (user_id,)
    )

    client = cursor.fetchone()

    if not client:
        await message.answer("Вы не зарегистрированы.")
        return

    client_id = client[0]

    cursor.execute(
        """
        SELECT service, master, date, time, status
        FROM appointments
        WHERE client_id = %s
        ORDER BY id DESC
        """,
        (client_id,)
    )

    appointments = cursor.fetchall()

    if not appointments:
        await message.answer("У вас пока нет записей.")
        return

    text = "🕒 Ваши записи:\n\n"

    for item in appointments:
        text += (
            f"💅 Услуга: {item[0]}\n"
            f"👩‍🔬 Мастер: {item[1]}\n"
            f"📅 Дата: {item[2]}\n"
            f"⏰ Время: {item[3]}\n"
            f"📌 Статус: {item[4]}\n\n"
        )

    await message.answer(text)

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

@dp.message(F.text == "📍 Адрес")
async def address(message: Message):

    text = (
        "📍 Наш адрес:\n\n"
        "г. Алматы\n"
        "ул. Примерная 25"
    )

    await message.answer(text)

@dp.message(F.text == "📞 Контакты")
async def contacts(message: Message):

    text = (
        "📞 Контакты:\n\n"
        "+7 777 777 77 77\n"
        "@your_instagram"
    )

    await message.answer(text)

# ================= ADMIN FUNCTIONS =================
@dp.message(F.text == "📋 Все записи")
async def all_appointments(message: Message):

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

        service = app[0]
        master = app[1]
        date = app[2]
        time = app[3]

        text += (
            f"💅 Услуга: {service}\n"
            f"👩 Мастер: {master}\n"
            f"📅 Дата: {date}\n"
            f"🕒 Время: {time}\n\n"
        )

    await message.answer(text)
    
@dp.message(F.text == "👥 Клиенты")
async def clients_list(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("""
    SELECT name, visits, total_paid
    FROM clients
    WHERE name != 'AI Учитель Поддержка'
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

@dp.message(F.text == "📊 Статистика")
async def stats(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM clients")
    clients_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments")
    appointments_count = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(total_paid),0) FROM clients")
    total_money = cursor.fetchone()[0]

    text = (
        "📊 Статистика\n\n"
        f"👥 Клиентов: {clients_count}\n"
        f"📅 Записей: {appointments_count}\n"
        f"💰 Общая выручка: {total_money}₸"
    )

    await message.answer(text)

@dp.message(F.text == "➕ Добавить услугу")
async def add_service(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    text = (
        "Чтобы добавить услугу,\n"
        "отправьте так:\n\n"
        "Маникюр,15000,90"
    )

    await message.answer(text)

@dp.message(F.text == "➕ Добавить мастера")
async def add_master(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    text = (
        "Чтобы добавить мастера,\n"
        "отправьте так:\n\n"
        "Алина,Маникюр"
    )

    await message.answer(text)

@dp.message(F.text == "📢 Рассылка")
async def mailing(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        "Отправьте текст для рассылки."
    )

# ================= AUTO ADD SERVICE =================

@dp.message(F.text.contains(","))
async def text_handler(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    text = message.text

    # Добавление услуги
    if "," in text:

        parts = text.split(",")

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
