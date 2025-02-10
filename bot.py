import os
import asyncio
import logging
from dotenv import load_dotenv
from pyrogram import Client, filters
from pymongo import MongoClient

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")

# Connect to MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["auto_reply_bot"]
accounts_collection = db["accounts"]
auto_replies_collection = db["auto_replies"]

# Initialize bot
bot = Client("bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Store active user sessions
active_sessions = {}

# Helper function to start user session
async def start_user_session(user_id, session_string):
    user_client = Client(name=str(user_id), session_string=session_string, api_id=API_ID, api_hash=API_HASH)

    @user_client.on_message(filters.mentioned & filters.group)
    async def group_mention_handler(_, message):
        user_data = auto_replies_collection.find_one({"user_id": user_id})
        if user_data and "group_reply" in user_data:
            await message.reply_text(user_data["group_reply"])

    @user_client.on_message(filters.private & ~filters.bot)
    async def dm_handler(_, message):
        user_data = auto_replies_collection.find_one({"user_id": user_id})
        if user_data and "dm_reply" in user_data:
            await message.reply_text(user_data["dm_reply"])

    await user_client.start()
    active_sessions[user_id] = user_client

# Start Command
@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.reply_text("Welcome! Use `/login` to add an account.")

# Login Command
@bot.on_message(filters.command("login"))
async def login_handler(client, message):
    user_id = message.from_user.id
    await message.reply_text(
        "Send your **Pyrogram String Session** to log in.\n"
        "Use [String Session Generator](https://t.me/SessionGeneratorBot) to create one."
    )

    def check_session(msg):
        return msg.from_user.id == user_id and msg.text

    session_msg = await client.listen(message.chat.id, filters=check_session)
    session_string = session_msg.text

    # Save session in MongoDB
    accounts_collection.update_one(
        {"user_id": user_id},
        {"$set": {"session_string": session_string}},
        upsert=True
    )

    # Start user session
    await start_user_session(user_id, session_string)
    await message.reply_text("✅ Account logged in successfully!")

# Set Group Auto-Reply Command
@bot.on_message(filters.command("setgroup"))
async def set_group_reply(client, message):
    user_id = message.from_user.id
    reply_text = message.text.replace("/setgroup ", "")

    auto_replies_collection.update_one(
        {"user_id": user_id},
        {"$set": {"group_reply": reply_text}},
        upsert=True
    )

    await message.reply_text(f"✅ Group auto-reply set: `{reply_text}`")

# Set DM Auto-Reply Command
@bot.on_message(filters.command("setdm"))
async def set_dm_reply(client, message):
    user_id = message.from_user.id
    reply_text = message.text.replace("/setdm ", "")

    auto_replies_collection.update_one(
        {"user_id": user_id},
        {"$set": {"dm_reply": reply_text}},
        upsert=True
    )

    await message.reply_text(f"✅ DM auto-reply set: `{reply_text}`")

# List Hosted Accounts Command
@bot.on_message(filters.command("accounts"))
async def accounts_handler(client, message):
    accounts = accounts_collection.find()
    account_list = [f"• `{acc['user_id']}`" for acc in accounts]

    reply_text = "👤 **Hosted Accounts:**\n" + "\n".join(account_list) if account_list else "No accounts hosted."
    await message.reply_text(reply_text)

# Logout Command
@bot.on_message(filters.command("logout"))
async def logout_handler(client, message):
    user_id = message.from_user.id
    if user_id in active_sessions:
        await active_sessions[user_id].stop()
        del active_sessions[user_id]
        accounts_collection.delete_one({"user_id": user_id})
        await message.reply_text("✅ Logged out successfully!")
    else:
        await message.reply_text("❌ No active session found.")

# Run bot
if __name__ == "__main__":
    bot.run()
