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

# File-based storage for user accounts & settings
ACCOUNTS_FILE = "accounts.json"
SETTINGS_FILE = "settings.json"

# Configure logging (Only errors, no unnecessary logs)
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Load JSON storage
def load_json(filename):
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save JSON storage
def save_json(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)

# Initialize storage
accounts = load_json(ACCOUNTS_FILE)
settings = load_json(SETTINGS_FILE)

# Store active clients
active_clients = {}

async def start_userbot(user_id, string_session):
    """Starts a userbot session."""
    try:
        userbot = Client(name=str(user_id), session_string=string_session, api_id=API_ID, api_hash=API_HASH)
        await userbot.start()
        active_clients[user_id] = userbot
        return userbot
    except Exception as e:
        logging.error(f"Userbot startup failed for {user_id}: {str(e)}")
        return None

# Create bot client
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@bot.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handles /start command."""
    await message.reply_text("Welcome! Use /login to add an account.")

@bot.on_message(filters.command("login"))
async def login_handler(client: Client, message: Message):
    """Handles user login request."""
    user_id = message.from_user.id
    await message.reply_text("Send your Pyrogram string session now:")

    @bot.on_message(filters.private & filters.text)
    async def session_receiver(client: Client, session_message: Message):
        """Receives the Pyrogram string session and logs in the user."""
        if session_message.from_user.id == user_id:
            string_session = session_message.text.strip()

            try:
                userbot = await start_userbot(user_id, string_session)
                if userbot:
                    accounts[str(user_id)] = string_session
                    save_json(ACCOUNTS_FILE, accounts)
                    await session_message.reply_text(f"✅ Logged in as {userbot.me.first_name} ({userbot.me.id})")
                else:
                    await session_message.reply_text("❌ Login failed. Please check your session string.")
            except Exception as e:
                await session_message.reply_text(f"❌ Error: {str(e)}")

@bot.on_message(filters.command("setdm"))
async def set_dm_handler(client: Client, message: Message):
    """Sets auto-reply message for DMs."""
    user_id = str(message.from_user.id)

    if user_id not in accounts:
        await message.reply_text("❌ You need to log in first using `/login`.")
        return

    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        await message.reply_text("❌ Please provide a message. Usage: `/setdm Your message`")
        return

    if user_id not in settings:
        settings[user_id] = {}  # ✅ Fix: Ensure user_id has a dictionary

    settings[user_id]["dm"] = text[1]
    save_json(SETTINGS_FILE, settings)
    await message.reply_text("✅ Auto-reply for DMs set successfully!")

@bot.on_message(filters.command("setgroup"))
async def set_group_handler(client: Client, message: Message):
    """Sets auto-reply message for group mentions."""
    user_id = str(message.from_user.id)

    if user_id not in accounts:
        await message.reply_text("❌ You need to log in first using `/login`.")
        return

    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        await message.reply_text("❌ Please provide a message. Usage: `/setgroup Your message`")
        return

    if user_id not in settings:
        settings[user_id] = {}  # ✅ Fix: Ensure user_id has a dictionary

    settings[user_id]["group"] = text[1]
    save_json(SETTINGS_FILE, settings)
    await message.reply_text("✅ Auto-reply for group mentions set successfully!")

async def auto_reply():
    """Handles auto-reply for logged-in users."""
    while True:
        for user_id, client in active_clients.items():
            try:
                async for message in client.get_chat_history(user_id, limit=1):
                    chat = await client.get_chat(message.chat.id)

                    # Skip if chat is invalid or user has not met the peer
                    if not chat or chat.is_deleted or chat.is_scam or chat.is_restricted:
                        continue

                    # DM auto-reply
                    if message.chat.type == "private" and "dm" in settings.get(str(user_id), {}):
                        await client.send_message(message.chat.id, settings[str(user_id)]["dm"])

                    # Group mention auto-reply
                    elif message.mentioned and "group" in settings.get(str(user_id), {}):
                        await client.send_message(message.chat.id, settings[str(user_id)]["group"])

            except Exception as e:
                if "PEER_ID_INVALID" not in str(e):  # Ignore known issue for unknown chats
                    logging.error(f"Error in auto-reply for {user_id}: {str(e)}")

        await asyncio.sleep(5)  # Check every 5 seconds

# Run the bot
if __name__ == "__main__":
    bot.start()
    loop = asyncio.get_event_loop()
    loop.create_task(auto_reply())
    loop.run_forever()
