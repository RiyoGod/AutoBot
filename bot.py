import os
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

# Configure logging (Only errors)
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("errors.log"), logging.StreamHandler()]
)

# Create bot client
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Dictionary to track login states
user_sessions = {}


async def start_userbot(string_session):
    """Starts a userbot session and returns the client."""
    try:
        userbot = Client(name="userbot", session_string=string_session, api_id=API_ID, api_hash=API_HASH)
        await userbot.start()
        return userbot
    except Exception as e:
        logging.error(f"Userbot startup failed: {str(e)}")
        raise RuntimeError(f"Userbot startup failed: {str(e)}")


@bot.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handles /start command."""
    await message.reply_text("Welcome! Use /login to add an account.")


@bot.on_message(filters.command("login"))
async def login_handler(client: Client, message: Message):
    """Handles user login request."""
    user_id = message.from_user.id
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
            accounts_collection.insert_one({"user_id": userbot.me.id, "string_session": string_session})
            await message.reply_text(f"✅ Logged in as {userbot.me.first_name} ({userbot.me.id})")
        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            await message.reply_text(f"❌ Login failed: {str(e)}")

        del user_sessions[user_id]  # Remove user from tracking


@bot.on_message(filters.command("accounts"))
async def accounts_handler(client: Client, message: Message):
    """Lists all logged-in accounts."""
    try:
        accounts = accounts_collection.find({})
        account_list = [f"{acc['user_id']}" for acc in accounts]

        if account_list:
            await message.reply_text("📝 **Logged-in Accounts:**\n" + "\n".join(account_list))
        else:
            await message.reply_text("❌ No accounts logged in.")
    except Exception as e:
        logging.error(f"Error in /accounts command: {str(e)}")


@bot.on_message(filters.command("setgroup", prefixes="/"))
async def set_group_handler(client: Client, message: Message):
    """Sets auto-reply message for group mentions."""
    logging.error("Received /setgroup command")  # Debug log
    
    try:
        text = message.text.split(maxsplit=1)
        if len(text) < 2:
            await message.reply_text("❌ Please provide a message. Usage: `/setgroup Your message`")
            return

        settings_collection.update_one({"type": "group"}, {"$set": {"message": text[1]}}, upsert=True)
        await message.reply_text("✅ Auto-reply for groups set successfully!")
    except Exception as e:
        logging.error(f"Error in /setgroup command: {str(e)}")


@bot.on_message(filters.command("setdm", prefixes="/"))
async def set_dm_handler(client: Client, message: Message):
    """Sets auto-reply message for direct messages."""
    logging.error("Received /setdm command")  # Debug log
    
    try:
        text = message.text.split(maxsplit=1)
        if len(text) < 2:
            await message.reply_text("❌ Please provide a message. Usage: `/setdm Your message`")
            return

        settings_collection.update_one({"type": "dm"}, {"$set": {"message": text[1]}}, upsert=True)
        await message.reply_text("✅ Auto-reply for DMs set successfully!")
    except Exception as e:
        logging.error(f"Error in /setdm command: {str(e)}")



@bot.on_message(filters.command("logout"))
async def logout_handler(client: Client, message: Message):
    """Logs out a user account."""
    try:
        text = message.text.split()

        if len(text) < 2:
            await message.reply_text("❌ Please provide a user ID. Usage: `/logout user_id`")
            return

        user_id = int(text[1])
        account = accounts_collection.find_one({"user_id": user_id})

        if account:
            accounts_collection.delete_one({"user_id": user_id})
            await message.reply_text(f"✅ Logged out {user_id} successfully!")
        else:
            await message.reply_text("❌ No account found with this ID.")
    except Exception as e:
        logging.error(f"Error in /logout command: {str(e)}")


# Run the bot
if __name__ == "__main__":
    bot.run()
