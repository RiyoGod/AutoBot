import os
import asyncio
from pyrogram import Client, filters
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "auto_reply_bot")

# Initialize MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
accounts_collection = db["accounts"]
responses_collection = db["responses"]

# Initialize Bot Client
bot = Client("auto_reply_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to store running userbots
userbots = {}

async def start_userbot(session_name, api_id, api_hash, phone_number):
    """Logs in a user account and starts handling messages."""
    userbot = Client(session_name, api_id=api_id, api_hash=api_hash, phone_number=phone_number)
    await userbot.start()
    userbots[session_name] = userbot
    print(f"✅ Userbot {session_name} is running...")

    @userbot.on_message(filters.mentioned & filters.group)
    async def reply_to_mentions(client, message):
        response = responses_collection.find_one({"type": "group"})
        if response:
            await message.reply_text(response["text"])
        else:
            await message.reply_text("Hello! How can I help?")

    @userbot.on_message(filters.private)
    async def auto_reply(client, message):
        response = responses_collection.find_one({"type": "dm"})
        if response:
            await message.reply_text(response["text"])
        else:
            await message.reply_text("Hey! I'm currently busy. I'll get back to you soon.")

    await userbot.idle()

@bot.on_message(filters.command("login"))
async def login_user(client, message):
    """Command to log in a new user account."""
    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("Usage: /login <phone_number>")
        return
    
    phone_number = args[1]
    session_name = f"user_{phone_number}"
    
    if session_name in userbots:
        await message.reply_text("This account is already logged in.")
        return
    
    accounts_collection.insert_one({"phone": phone_number, "session": session_name})
    asyncio.create_task(start_userbot(session_name, API_ID, API_HASH, phone_number))
    
    await message.reply_text(f"Login initiated for {phone_number}. Check your Telegram for login confirmation.")

@bot.on_message(filters.command("setgroup"))
async def set_group_reply(client, message):
    """Set the auto-reply for group mentions."""
    text = message.text.split("/setgroup ", 1)[-1]
    responses_collection.update_one({"type": "group"}, {"$set": {"text": text}}, upsert=True)
    await message.reply_text("✅ Group mention response updated.")

@bot.on_message(filters.command("setdm"))
async def set_dm_reply(client, message):
    """Set the auto-reply for DMs."""
    text = message.text.split("/setdm ", 1)[-1]
    responses_collection.update_one({"type": "dm"}, {"$set": {"text": text}}, upsert=True)
    await message.reply_text("✅ DM response updated.")

@bot.on_message(filters.command("accounts"))
async def list_accounts(client, message):
    """List all hosted user accounts."""
    accounts = accounts_collection.find()
    text = "**📌 Hosted Accounts:**\n"
    for acc in accounts:
        text += f"📌 {acc['phone']} (Session: {acc['session']})\n"
    await message.reply_text(text)

@bot.on_message(filters.command("logout"))
async def logout_user(client, message):
    """Logout a user account."""
    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("Usage: /logout <phone_number>")
        return
    
    phone_number = args[1]
    session_name = f"user_{phone_number}"
    
    if session_name in userbots:
        await userbots[session_name].stop()
        del userbots[session_name]
        accounts_collection.delete_one({"session": session_name})
        await message.reply_text(f"✅ Logged out {phone_number}.")
    else:
        await message.reply_text("❌ This account is not logged in.")

# Start the bot
print("🚀 Bot is running...")
bot.run()
