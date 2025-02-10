import os
import asyncio
import logging
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "auto_reply_bot")

# Initialize MongoDB
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[DB_NAME]
accounts_col = db["accounts"]
replies_col = db["replies"]

# Initialize Bot
bot = Client("AutoReplyBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Dictionary to store running user sessions
user_sessions = {}

### ✅ Command: /start
@bot.on_message(filters.command("start"))
async def start_handler(_, message: Message):
    await message.reply_text("Welcome! Use /login to add an account.")

### ✅ Command: /login (Add User Account)
@bot.on_message(filters.command("login"))
async def login_handler(_, message: Message):
    await message.reply_text(
        "To log in, send your **PHONE NUMBER** (with country code). Example: `+123456789`",
        parse_mode="markdown"
    )

    def check(m: Message):
        return m.chat.id == message.chat.id and m.text.startswith("+")

    phone_message = await bot.listen(message.chat.id, check=check)
    phone_number = phone_message.text.strip()

    # Create a new Pyrogram Client for the user
    session_name = f"user_{message.chat.id}"
    user_client = Client(session_name, api_id=API_ID, api_hash=API_HASH)

    await user_client.connect()
    code = await user_client.send_code(phone_number)

    await message.reply_text("Enter the **login code** sent to your Telegram.")

    code_message = await bot.listen(message.chat.id)
    login_code = code_message.text.strip()

    try:
        await user_client.sign_in(phone_number, login_code)
        user_sessions[message.chat.id] = user_client

        # Save to MongoDB
        await accounts_col.update_one(
            {"user_id": message.chat.id},
            {"$set": {"phone_number": phone_number}},
            upsert=True
        )

        await message.reply_text("✅ Login successful!")
    except Exception as e:
        await message.reply_text(f"❌ Login failed: {e}")

### ✅ Command: /accounts (List Logged-in Accounts)
@bot.on_message(filters.command("accounts"))
async def list_accounts(_, message: Message):
    accounts = await accounts_col.find().to_list(length=100)
    if not accounts:
        await message.reply_text("❌ No accounts logged in.")
        return
    
    msg = "🔹 **Logged-in Accounts:**\n"
    for acc in accounts:
        msg += f"- `{acc['phone_number']}`\n"
    
    await message.reply_text(msg)

### ✅ Command: /setgroup (Set Auto-reply for Group Mentions)
@bot.on_message(filters.command("setgroup"))
async def set_group_reply(_, message: Message):
    reply_text = message.text.replace("/setgroup", "").strip()
    if not reply_text:
        await message.reply_text("❌ Please provide a reply message.")
        return

    await replies_col.update_one(
        {"user_id": message.chat.id, "type": "group"},
        {"$set": {"reply_text": reply_text}},
        upsert=True
    )

    await message.reply_text("✅ Group auto-reply set!")

### ✅ Command: /setdm (Set Auto-reply for Direct Messages)
@bot.on_message(filters.command("setdm"))
async def set_dm_reply(_, message: Message):
    reply_text = message.text.replace("/setdm", "").strip()
    if not reply_text:
        await message.reply_text("❌ Please provide a reply message.")
        return

    await replies_col.update_one(
        {"user_id": message.chat.id, "type": "dm"},
        {"$set": {"reply_text": reply_text}},
        upsert=True
    )

    await message.reply_text("✅ DM auto-reply set!")

### ✅ Auto-reply in Groups
@bot.on_message(filters.mentioned & filters.group)
async def group_reply_handler(_, message: Message):
    user_id = message.from_user.id
    reply_data = await replies_col.find_one({"user_id": user_id, "type": "group"})
    
    if reply_data:
        await message.reply_text(reply_data["reply_text"])

### ✅ Auto-reply in Direct Messages
@bot.on_message(filters.private)
async def dm_reply_handler(_, message: Message):
    user_id = message.from_user.id
    reply_data = await replies_col.find_one({"user_id": user_id, "type": "dm"})
    
    if reply_data:
        await message.reply_text(reply_data["reply_text"])

### ✅ Command: /logout (Remove an Account)
@bot.on_message(filters.command("logout"))
async def logout_handler(_, message: Message):
    if message.chat.id not in user_sessions:
        await message.reply_text("❌ No active session found.")
        return
    
    user_client = user_sessions.pop(message.chat.id)
    await user_client.disconnect()

    await accounts_col.delete_one({"user_id": message.chat.id})

    await message.reply_text("✅ Logged out successfully!")

# Run the bot
print("✅ Bot is running...")
bot.run()
