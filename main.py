import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Ma'lumotlaringiz biriktirildi
BOT_TOKEN = "8886067153:AAH2wXq4AihJ0NE_Q8u43Dq-aCPjbm0DvGw"
ADMIN_ID = 8551664514

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- DATABASE SOZLAMALARI ---
def init_db():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            btn_title TEXT,
            btn_url TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_post(text, btn_title=None, btn_url=None):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO posts (text, btn_title, btn_url) VALUES (?, ?, ?)", (text, btn_title, btn_url))
    post_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return post_id

def delete_post(post_id):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def get_all_posts():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, text FROM posts")
    rows = cursor.fetchall()
    conn.close()
    return rows

# --- FSM (HOLATLAR) ---
class PostState(StatesGroup):
    text = State()
    btn_title = State()
    btn_url = State()

# --- 1. USER XABARINI ADMINGA YUBORISH ---
@dp.message(F.chat.type == "private", F.from_user.id != ADMIN_ID)
async def handle_user_message(message: types.Message):
    user = message.from_user
    username_text = f"@{user.username}" if user.username else "Username yo'q"
    
    admin_msg = (
        f"📩 **Yangi xabar keldi!**\n\n"
        f"👤 **Kimdan:** {username_text}\n"
        f"🆔 **ID:** `{user.id}`\n\n"
        f"💬 **Xabar:**\n{message.text or '[Media yuborildi]'}"
    )
    
    await bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
    await message.answer("Xabaringiz adminga yetkazildi!")

# --- 2. ADMIN: E'LON QO'SHISH (/post) ---
@dp.message(Command("post"), F.from_user.id == ADMIN_ID)
async def start_post(message: types.Message, state: FSMContext):
    await message.answer("E'lon matnini kiriting:")
    await state.set_state(PostState.text)

@dp.message(PostState.text, F.from_user.id == ADMIN_ID)
async def get_post_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("Tugma nomini kiriting (Tugma kerak bo'lmasa 'yoq' deb yozing):")
    await state.set_state(PostState.btn_title)

@dp.message(PostState.btn_title, F.from_user.id == ADMIN_ID)
async def get_btn_title(message: types.Message, state: FSMContext):
    if message.text.lower() == 'yoq':
        data = await state.get_data()
        post_id = save_post(data['text'])
        await message.answer(f"✅ E'lon saqlandi! ID: `{post_id}`\n\n{data['text']}", parse_mode="Markdown")
        await state.clear()
        return

    await state.update_data(btn_title=message.text)
    await message.answer("Tugma havolasini (link) kiriting (masalan: https://t.me/...):")
    await state.set_state(PostState.btn_url)

@dp.message(PostState.btn_url, F.from_user.id == ADMIN_ID)
async def get_btn_url(message: types.Message, state: FSMContext):
    data = await state.get_data()
    btn_title = data['btn_title']
    btn_url = message.text
    
    post_id = save_post(data['text'], btn_title, btn_url)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_title, url=btn_url)]
    ])
    
    await message.answer(f"✅ E'lon saqlandi! ID: `{post_id}`", reply_markup=keyboard, parse_mode="Markdown")
    await state.clear()

# --- 3. ADMIN: E'LONLAR RO'YXATI VA O'CHIRISH ---
@dp.message(Command("posts"), F.from_user.id == ADMIN_ID)
async def list_posts(message: types.Message):
    posts = get_all_posts()
    if not posts:
        await message.answer("Hozircha hech qanday e'lon mavjud emas.")
        return
    
    res = "📋 **Mavjud e'lonlar:**\n\n"
    for p_id, p_text in posts:
        short_text = p_text[:30] + "..." if len(p_text) > 30 else p_text
        res += f"🔹 **ID {p_id}:** {short_text}\n"
    
    res += "\nE'lonni o'chirish uchun: `/del_ID` yuboring (masalan: `/del_1`)"
    await message.answer(res, parse_mode="Markdown")

@dp.message(F.text.startswith("/del_"), F.from_user.id == ADMIN_ID)
async def delete_post_handler(message: types.Message):
    try:
        post_id = int(message.text.split("_")[1])
        success = delete_post(post_id)
        if success:
            await message.answer(f"🗑 ID `{post_id}` bo'lgan e'lon o'chirildi.", parse_mode="Markdown")
        else:
            await message.answer("Bunday ID dagi e'lon topilmadi.")
    except Exception:
        await message.answer("Noto'g'ri buyruq kiritildi. Masalan: `/del_1`")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
