import os
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import Message
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
    tg_id BIGINT,
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
    client_id INTEGER
)
""")

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

    await message.answer(text)

# ================= ADMIN =================

@dp.message(Command("admin"))
async def admin_panel(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM clients")
    users_count = cursor.fetchone()[0]

    text = (
        f"👨‍💼 Админ панель\n\n"
        f"Пользователей: {users_count}"
    )

    await message.answer(text)

# ================= MAIN =================

async def main():

    print("CRM BOT STARTED")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
