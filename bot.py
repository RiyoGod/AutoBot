import os
import asyncio
import logging
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "auto_reply_bot"

# MongoDB setup
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
accounts_collection = db["accounts"]
settings_collection = db["settings"]

# Configure essential logging (Only errors and important events)
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Custom debug logger
debug_logger = logging.getLogger("debug")
debug_logger.setLevel(logging.INFO)
debug_handler = logging.FileHandler("debug.log")
debug_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
debug_logger.addHandler(debug_handler)

# Create bot client
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to track login states
user_sessions = {}
userbots = {}  # Stores active userbot clients


async def start_userbot(string_session):
    """Starts a userbot session and returns the client."""
    try:
        userbot = Client(name="userbot", session_string=string_session, api_id=API_ID, api_hash=API_HASH)
        await userbot.start()
        me = await userbot.get_me()
        debug_logger.info(f"Userbot started for {me.first_name} ({me.id})")
        return userbot
    except Exception as e:
        debug_logger.error(f"Userbot startup failed: {str(e)}")
        raise RuntimeError(f"Userbot startup failed: {str(e)}")


@bot.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handles /start command."""
    debug_logger.info(f"User {message.from_user.id} used /start")
    await message.reply_text("Welcome! Use /login to add an account.")


@bot.on_message(filters.command("login"))
async def login_handler(client: Client, message: Message):
    """Handles user login request."""
    user_id = message.from_user.id
    debug_logger.info(f"User {user_id} initiated login.")
    await message.reply_text("Send your Pyrogram string session now:")
    user_sessions[user_id] = True  # Track user state


@bot.on_message(filters.private & filters.text)
async def session_receiver(client: Client, message: Message):
    """Handles string session input."""
    user_id = message.from_user.id

    if user_id in user_sessions:
        string_session = message.text.strip()

        try:
            userbot = await start_userbot(string_session)
            me = await userbot.get_me()
            accounts_collection.insert_one({"user_id": me.id, "string_session": string_session})
            userbots[me.id] = userbot  # Store active session

            await message.reply_text(f"✅ Logged in as {me.first_name} ({me.id})")
            debug_logger.info(f"User {me.id} logged in successfully.")
        except Exception as e:
            await message.reply_text(f"❌ Login failed: {str(e)}")
            debug_logger.error(f"Login failed for user {user_id}: {str(e)}")

        del user_sessions[user_id]  # Remove user from tracking


@bot.on_message(filters.command("accounts"))
async def accounts_handler(client: Client, message: Message):
    """Lists all logged-in accounts."""
    debug_logger.info(f"User {message.from_user.id} used /accounts")
    
    accounts = accounts_collection.find({})
    account_list = [f"{acc['user_id']}" for acc in accounts]

    if account_list:
        await message.reply_text("📝 **Logged-in Accounts:**\n" + "\n".join(account_list))
    else:
        await message.reply_text("❌ No accounts logged in.")


@bot.on_message(filters.command("setgroup"))
async def set_group_handler(client: Client, message: Message):
    """Sets auto-reply message for group mentions."""
    text = message.text.split(maxsplit=1)

    if len(text) < 2:
        await message.reply_text("❌ Please provide a message. Usage: `/setgroup Your message`")
        return

    settings_collection.update_one({"type": "group"}, {"$set": {"message": text[1]}}, upsert=True)
    debug_logger.info(f"User {message.from_user.id} set group auto-reply.")
    await message.reply_text("✅ Auto-reply for groups set successfully!")


@bot.on_message(filters.command("setdm"))
async def set_dm_handler(client: Client, message: Message):
    """Sets auto-reply message for direct messages."""
    text = message.text.split(maxsplit=1)

    if len(text) < 2:
        await message.reply_text("❌ Please provide a message. Usage: `/setdm Your message`")
        return

    settings_collection.update_one({"type": "dm"}, {"$set": {"message": text[1]}}, upsert=True)
    debug_logger.info(f"User {message.from_user.id} set DM auto-reply.")
    await message.reply_text("✅ Auto-reply for DMs set successfully!")


@bot.on_message(filters.command("logout"))
async def logout_handler(client: Client, message: Message):
    """Logs out a user account."""
    text = message.text.split()

    if len(text) < 2:
        await message.reply_text("❌ Please provide a user ID. Usage: `/logout user_id`")
        return

    user_id = int(text[1])
    account = accounts_collection.find_one({"user_id": user_id})

    if account:
        accounts_collection.delete_one({"user_id": user_id})
        
        # Stop and remove userbot session
        if user_id in userbots:
            await userbots[user_id].stop()
            del userbots[user_id]
        
        debug_logger.info(f"User {user_id} logged out successfully.")
        await message.reply_text(f"✅ Logged out {user_id} successfully!")
    else:
        await message.reply_text("❌ No account found with this ID.")


# Run the bot
if __name__ == "__main__":
    bot.run()
