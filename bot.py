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
SETTINGS_FILE = "settings.json"

# Configure logging (Print errors directly in terminal)
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Load settings
def load_json(filename):
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save settings
def save_json(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)

# Initialize settings
settings = load_json(SETTINGS_FILE)

# Create bot client
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@bot.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handles /start command."""
    await message.reply_text("Welcome! Use /setdm to set an auto-reply for DMs.")

@bot.on_message(filters.command("setdm"))
async def set_dm_handler(client: Client, message: Message):
    """Sets auto-reply message for direct messages."""
    logging.error(f"Received /setdm command from {message.from_user.id}")

    try:
        text = message.text.split(maxsplit=1)
        if len(text) < 2:
            await message.reply_text("❌ Please provide a message. Usage: `/setdm Your message`")
            return

        settings["dm"] = text[1]
        save_json(SETTINGS_FILE, settings)
        logging.error(f"DM reply set to: {text[1]}")

        await message.reply_text("✅ Auto-reply for DMs set successfully!")
    except Exception as e:
        logging.error(f"Error in /setdm command: {str(e)}")

@bot.on_message(filters.command("setgroup"))
async def set_group_handler(client: Client, message: Message):
    """Sets auto-reply message for group mentions."""
    logging.error(f"Received /setgroup command from {message.from_user.id}")

    try:
        text = message.text.split(maxsplit=1)
        if len(text) < 2:
            await message.reply_text("❌ Please provide a message. Usage: `/setgroup Your message`")
            return

        settings["group"] = text[1]
        save_json(SETTINGS_FILE, settings)
        logging.error(f"Group reply set to: {text[1]}")

        await message.reply_text("✅ Auto-reply for group mentions set successfully!")
    except Exception as e:
        logging.error(f"Error in /setgroup command: {str(e)}")

@bot.on_message(filters.private & ~filters.me)
async def auto_reply_dm(client: Client, message: Message):
    """Auto-replies to private messages (DMs) if a message is set."""
    if "dm" in settings:
        await message.reply_text(f"{settings['dm']}")

@bot.on_message(filters.mentioned & ~filters.me)
async def auto_reply_group(client: Client, message: Message):
    """Auto-replies to group mentions if a message is set."""
    if "group" in settings:
        await message.reply_text(f"{settings['group']}")

# Run the bot
if __name__ == "__main__":
    bot.run()
