import os
import logging
import asyncio
from dotenv import load_dotenv
from pyrogram import Client, filters
from pymongo import MongoClient

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")

# Database Setup
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["auto_reply_bot"]
accounts_collection = db["accounts"]
auto_replies = db["auto_replies"]

# Logging Configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize the bot
bot = Client("bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Dictionary to store active userbots
userbots = {}

async def start_userbot(string_session):
    """Start a userbot using a given string session."""
    client = Client(name="userbot", session_string=string_session, api_id=API_ID, api_hash=API_HASH)
    await client.start()
    userbots[client.me.id] = client
    logging.info(f"Userbot started for {client.me.first_name} ({client.me.id})")
    return client

@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.reply_text("Welcome! Use /login to add an account.")

@bot.on_message(filters.command("login"))
async def login_handler(client, message):
    await message.reply_text("Send your Pyrogram string session:")

    # Wait for user response in private chat
    user_response = await bot.listen(message.chat.id, filters=filters.text)

    string_session = user_response.text.strip()
    
    try:
        userbot = await start_userbot(string_session)
        accounts_collection.insert_one({"user_id": userbot.me.id, "string_session": string_session})
        await message.reply_text(f"✅ Logged in as {userbot.me.first_name} ({userbot.me.id})")
    except Exception as e:
        await message.reply_text(f"❌ Login failed: {str(e)}")


@bot.on_message(filters.command("accounts"))
async def accounts_handler(client, message):
    accounts = list(accounts_collection.find({}))
    if not accounts:
        await message.reply_text("No accounts are logged in.")
        return

    account_list = "\n".join([f"- {acc['user_id']}" for acc in accounts])
    await message.reply_text(f"Logged-in Accounts:\n{account_list}")

@bot.on_message(filters.command("logout"))
async def logout_handler(client, message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("Usage: /logout <user_id>")
        return
    
    user_id = int(args[1])
    
    if user_id in userbots:
        await userbots[user_id].stop()
        del userbots[user_id]
        accounts_collection.delete_one({"user_id": user_id})
        await message.reply_text(f"✅ Logged out {user_id}")
    else:
        await message.reply_text("❌ User ID not found or already logged out.")

@bot.on_message(filters.command("setgroup"))
async def set_group_handler(client, message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply_text("Usage: /setgroup <reply_message>")
        return

    reply_text = args[1]
    auto_replies.update_one({"type": "group"}, {"$set": {"message": reply_text}}, upsert=True)
    await message.reply_text("✅ Auto-reply for groups set!")

@bot.on_message(filters.command("setdm"))
async def set_dm_handler(client, message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply_text("Usage: /setdm <reply_message>")
        return

    reply_text = args[1]
    auto_replies.update_one({"type": "dm"}, {"$set": {"message": reply_text}}, upsert=True)
    await message.reply_text("✅ Auto-reply for DMs set!")

async def group_reply_handler(client, message):
    """Handles group mentions."""
    reply_data = auto_replies.find_one({"type": "group"})
    if reply_data:
        await message.reply_text(reply_data["message"])

async def dm_reply_handler(client, message):
    """Handles direct messages."""
    reply_data = auto_replies.find_one({"type": "dm"})
    if reply_data:
        await message.reply_text(reply_data["message"])

async def userbot_listen(client):
    """Listens for mentions and direct messages."""
    @client.on_message(filters.mentioned & filters.group)
    async def mentioned_handler(_, message):
        await group_reply_handler(client, message)

    @client.on_message(filters.private)
    async def dm_handler(_, message):
        await dm_reply_handler(client, message)

    await client.run()

# Start the bot
if __name__ == "__main__":
    bot.run()
