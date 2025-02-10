import os
import asyncio
import logging
import json
import sys
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# File-based storage (VPS-based)
ACCOUNTS_FILE = "accounts.json"
SETTINGS_FILE = "settings.json"

# Configure logging (Print errors directly in terminal)
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Load accounts from file
def load_json(filename):
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save accounts to file
def save_json(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)

# Load settings
settings = load_json(SETTINGS_FILE)
accounts = load_json(ACCOUNTS_FILE)

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
        if "SESSION_REVOKED" in str(e):
            logging.error("Session revoked, removing from storage...")
            global accounts
            accounts = [acc for acc in accounts if acc["string_session"] != string_session]
            save_json(ACCOUNTS_FILE, accounts)  # Remove session from storage
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
            accounts.append({"user_id": userbot.me.id, "string_session": string_session})
            save_json(ACCOUNTS_FILE, accounts)
            await message.reply_text(f"✅ Logged in as {userbot.me.first_name} ({userbot.me.id})")
        except Exception as e:
            await message.reply_text(f"❌ Login failed: {str(e)}")

        del user_sessions[user_id]  # Remove user from tracking

@bot.on_message(filters.command("accounts"))
async def accounts_handler(client: Client, message: Message):
    """Lists all logged-in accounts."""
    if accounts:
        account_list = [f"{acc['user_id']}" for acc in accounts]
        await message.reply_text("📝 **Logged-in Accounts:**\n" + "\n".join(account_list))
    else:
        await message.reply_text("❌ No accounts logged in.")

@bot.on_message(filters.command("setgroup"))
async def set_group_handler(client: Client, message: Message):
    """Sets auto-reply message for group mentions."""
    logging.error(f"Received /setgroup command from {message.from_user.id}")  # Debug Log

    try:
        text = message.text.split(maxsplit=1)
        if len(text) < 2:
            await message.reply_text("❌ Please provide a message. Usage: `/setgroup Your message`")
            return

        settings["group"] = text[1]
        save_json(SETTINGS_FILE, settings)
        logging.error(f"Group reply set to: {text[1]}")  # Debug Log

        await message.reply_text("✅ Auto-reply for groups set successfully!")
    except Exception as e:
        logging.error(f"Error in /setgroup command: {str(e)}")

@bot.on_message(filters.command("setdm"))
async def set_dm_handler(client: Client, message: Message):
    """Sets auto-reply message for direct messages."""
    logging.error(f"Received /setdm command from {message.from_user.id}")  # Debug Log

    try:
        text = message.text.split(maxsplit=1)
        if len(text) < 2:
            await message.reply_text("❌ Please provide a message. Usage: `/setdm Your message`")
            return

        settings["dm"] = text[1]
        save_json(SETTINGS_FILE, settings)
        logging.error(f"DM reply set to: {text[1]}")  # Debug Log

        await message.reply_text("✅ Auto-reply for DMs set successfully!")
    except Exception as e:
        logging.error(f"Error in /setdm command: {str(e)}")

@bot.on_message(filters.command("logout"))
async def logout_handler(client: Client, message: Message):
    """Logs out a user account."""
    text = message.text.split()

    if len(text) < 2:
        await message.reply_text("❌ Please provide a user ID. Usage: `/logout user_id`")
        return

    user_id = int(text[1])
    global accounts
    accounts = [acc for acc in accounts if acc["user_id"] != user_id]
    save_json(ACCOUNTS_FILE, accounts)

    await message.reply_text(f"✅ Logged out {user_id} successfully!")

# Run the bot
if __name__ == "__main__":
    bot.run()
