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
            KeyboardButton(text="❌ Отменить запись")
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

    cursor.execute(
        "SELECT title FROM services"
    )

    services = cursor.fetchall()

    if not services:
        await message.answer(
            "❌ Услуги пока не добавлены."
        )
        return

    keyboard = []

    for service in services:

        keyboard.append(
            [
                KeyboardButton(
                    text=f"💅 {service[0]}"
                )
            ]
        )

    services_kb = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

    await message.answer(
        "💅 Выберите услугу:",
        reply_markup=services_kb
    )

# ================= BOOKING STEP 2 =================

user_booking = {}

@dp.message(F.text.startswith("💅"))
async def choose_service(message: Message):

    service = message.text.replace("💅 ", "")

    user_booking[message.from_user.id] = {
        "service": service
    }

    cursor.execute(
        """
        SELECT name
        FROM masters
        WHERE specialty ILIKE %s
        """,
        (f"%{service.split()[0]}%",)
    )

    masters = cursor.fetchall()

    if not masters:

        await message.answer(
            "❌ Для этой услуги мастеров пока нет."
        )

        return

    keyboard = []

    for master in masters:

        keyboard.append(
            [
                KeyboardButton(
                    text=f"👩 {master[0]}"
                )
            ]
        )

    masters_kb = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

    await message.answer(
        f"💅 Услуга: {service}\n\n"
        f"👩 Выберите мастера:",
        reply_markup=masters_kb
    )

# ================= BOOKING STEP 3 =================

@dp.message(F.text.startswith("👩"))
async def choose_master(message: Message):

    master = message.text.replace("👩 ", "")

    if message.from_user.id not in user_booking:
        return

    user_booking[message.from_user.id]["master"] = master

    dates_kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📅 Сегодня")
            ],
            [
                KeyboardButton(text="📅 Завтра")
            ],
            [
                KeyboardButton(text="📅 17 мая")
            ],
            [
                KeyboardButton(text="📅 18 мая")
            ]
        ],
        resize_keyboard=True
    )

    await message.answer(
        f"👩 Мастер: {master}\n\n"
        f"📅 Выберите дату:",
        reply_markup=dates_kb
    )

# ================= BOOKING STEP 4 =================

@dp.message(F.text.startswith("📅"))
async def choose_date(message: Message):

    date = message.text.replace("📅 ", "")

    if message.from_user.id not in user_booking:
        return

    user_booking[message.from_user.id]["date"] = date

    master = user_booking[message.from_user.id]["master"]

    all_times = [
        "10:00",
        "11:00",
        "12:00",
        "13:00",
        "14:00",
        "15:00",
        "16:00",
        "17:00",
        "18:00"
    ]

    # занятые слоты
    cursor.execute(
        """
        SELECT time
        FROM appointments
        WHERE master = %s
        AND date = %s
        """,
        (master, date)
    )

    busy_times = cursor.fetchall()

    busy_list = [x[0] for x in busy_times]

    keyboard = []

    for time in all_times:

        if time not in busy_list:

            keyboard.append(
                [
                    KeyboardButton(
                        text=f"🕐 {time}"
                    )
                ]
            )

    times_kb = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

    await message.answer(
        f"📅 Дата: {date}\n\n"
        f"🕐 Выберите время:",
        reply_markup=times_kb
    )

# ================= FINAL BOOKING SAVE =================

@dp.message(F.text.startswith("🕐"))
async def save_booking(message: Message):

    try:

        time = message.text.replace("🕐 ", "")

        user_id = message.from_user.id

        if user_id not in user_booking:
            return

        booking_data = user_booking[user_id]

        service = booking_data["service"]
        master = booking_data["master"]
        date = booking_data["date"]

        # Получаем клиента
        cursor.execute(
            """
            SELECT id, visits
            FROM clients
            WHERE tg_id = %s
            """,
            (user_id,)
        )

        client = cursor.fetchone()

        if not client:

            cursor.execute(
                """
                INSERT INTO clients (tg_id, name, visits)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (
                    user_id,
                    message.from_user.full_name,
                    0
                )
            )

            client_id = cursor.fetchone()[0]
            current_visits = 0

        else:

            client_id = client[0]
            current_visits = client[1]

        # Проверка занятого времени
        cursor.execute(
            """
            SELECT id
            FROM appointments
            WHERE master = %s
            AND date = %s
            AND time = %s
            """,
            (
                master,
                date,
                time
            )
        )

        busy_slot = cursor.fetchone()

        if busy_slot:

            await message.answer(
                "❌ Это время уже занято."
            )

            return

        # Сохраняем запись
        cursor.execute(
            """
            INSERT INTO appointments
            (client_id, service, master, date, time)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                client_id,
                service,
                master,
                date,
                time
            )
        )

        # Обновляем визиты
        cursor.execute(
            """
            UPDATE clients
            SET visits = %s
            WHERE id = %s
            """,
            (
                current_visits + 1,
                client_id
            )
        )

        conn.commit()

        # Чистим временные данные
        del user_booking[user_id]

        # Сообщение клиенту
        await message.answer(
            f"✅ Запись подтверждена!\n\n"
            f"💅 Услуга: {service}\n"
            f"👩 Мастер: {master}\n"
            f"📅 Дата: {date}\n"
            f"🕐 Время: {time}",
            reply_markup=client_kb
        )

        # Сообщение админу
        await bot.send_message(
            ADMIN_ID,
            f"📥 Новая запись!\n\n"
            f"👤 Клиент: {message.from_user.full_name}\n"
            f"💅 Услуга: {service}\n"
            f"👩 Мастер: {master}\n"
            f"📅 Дата: {date}\n"
            f"🕐 Время: {time}"
        )

    except Exception as e:

        print("BOOKING ERROR:", e)

        await message.answer(
            f"❌ Ошибка:\n{e}"
        )
        
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

@dp.message(F.text == "❌ Отменить запись")
async def cancel_booking(message: Message):

    try:

        user_id = message.from_user.id

        # Ищем клиента
        cursor.execute(
            """
            SELECT id, visits
            FROM clients
            WHERE tg_id = %s
            """,
            (user_id,)
        )

        client = cursor.fetchone()

        if not client:
            await message.answer("❌ У вас нет записей.")
            return

        client_id = client[0]
        current_visits = client[1]

        # Ищем последнюю запись
        cursor.execute(
            """
            SELECT id, service, master, date, time
            FROM appointments
            WHERE client_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (client_id,)
        )

        appointment = cursor.fetchone()

        if not appointment:
            await message.answer("❌ Записей не найдено.")
            return

        appointment_id = appointment[0]
        service = appointment[1]
        master = appointment[2]
        date = appointment[3]
        time = appointment[4]

        # Удаляем запись
        cursor.execute(
            """
            DELETE FROM appointments
            WHERE id = %s
            """,
            (appointment_id,)
        )

        # Уменьшаем visits
        if current_visits > 0:

            cursor.execute(
                """
                UPDATE clients
                SET visits = %s
                WHERE id = %s
                """,
                (
                    current_visits - 1,
                    client_id
                )
            )

        conn.commit()

        # Сообщение клиенту
        await message.answer(
            f"✅ Запись отменена.\n\n"
            f"💅 Услуга: {service}\n"
            f"👩 Мастер: {master}\n"
            f"📅 Дата: {date}\n"
            f"🕒 Время: {time}"
        )

        # Сообщение админу
        await bot.send_message(
            ADMIN_ID,
            f"❌ Клиент отменил запись!\n\n"
            f"👤 Клиент: {message.from_user.full_name}\n"
            f"💅 Услуга: {service}\n"
            f"👩 Мастер: {master}\n"
            f"📅 Дата: {date}\n"
            f"🕒 Время: {time}"
        )

    except Exception as e:

        print("CANCEL ERROR:", e)

        await message.answer(
            f"❌ Ошибка:\n{e}"
        )
        
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

# ================= MAIN ================
async def main():

    print("CRM BOT STARTED")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
