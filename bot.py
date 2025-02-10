import os
import logging
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# Simple in-memory storage (for demo purposes)
user_sessions = {}
settings = {}

# Set up logging to show errors
logging.basicConfig(level=logging.ERROR)

# Create bot client
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Handle /start command
@bot.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply_text("Welcome! Use /login to log in using your Pyrogram session.")

# Handle /login command to accept Pyrogram string session
@bot.on_message(filters.command("login"))
async def login_handler(client: Client, message: Message):
    """Logs in user using Pyrogram session"""
    user_id = message.from_user.id
    await message.reply_text("Send your Pyrogram string session:")

    @bot.on_message(filters.private & filters.text)
    async def session_receiver(client: Client, session_message: Message):
        """Receives and logs in the user."""
        if session_message.from_user.id == user_id:
            string_session = session_message.text.strip()

            # Save session string to user_sessions
            user_sessions[user_id] = string_session

            try:
                userbot = Client(f"userbot_{user_id}", session_string=string_session, api_id=API_ID, api_hash=API_HASH)
                await userbot.start()
                await session_message.reply_text(f"✅ Logged in as {userbot.me.first_name} ({userbot.me.id})")
            except Exception as e:
                await session_message.reply_text(f"❌ Error: {str(e)}")

# Handle /setdm to set auto-reply for DMs
@bot.on_message(filters.command("setdm"))
async def set_dm_handler(client: Client, message: Message):
    """Sets auto-reply message for DMs."""
    user_id = message.from_user.id
    if user_id not in user_sessions:
        await message.reply_text("❌ You need to log in first using `/login`.")
        return

    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        await message.reply_text("❌ Please provide a message. Usage: `/setdm Your message`")
        return

    settings[user_id] = settings.get(user_id, {})
    settings[user_id]["dm"] = text[1]
    await message.reply_text("✅ Auto-reply for DMs set successfully!")

# Handle /setgroup to set auto-reply for group mentions
@bot.on_message(filters.command("setgroup"))
async def set_group_handler(client: Client, message: Message):
    """Sets auto-reply message for group mentions."""
    user_id = message.from_user.id
    if user_id not in user_sessions:
        await message.reply_text("❌ You need to log in first using `/login`.")
        return

    text = message.text.split(maxsplit=1)
    if len(text) < 2:
        await message.reply_text("❌ Please provide a message. Usage: `/setgroup Your message`")
        return

    settings[user_id] = settings.get(user_id, {})
    settings[user_id]["group"] = text[1]
    await message.reply_text("✅ Auto-reply for group mentions set successfully!")

# Handle incoming DMs (private messages)
@bot.on_message(filters.private & filters.text)
async def dm_auto_reply(client: Client, message: Message):
    """Responds with the set DM auto-reply message."""
    user_id = message.from_user.id
    if user_id in settings and "dm" in settings[user_id]:
        await message.reply_text(settings[user_id]["dm"])

# Handle group mentions
@bot.on_message(filters.group & filters.text)
async def group_auto_reply(client: Client, message: Message):
    """Responds with the set group auto-reply message when mentioned."""
    user_id = message.from_user.id
    if user_id in settings and "group" in settings[user_id]:
        if message.mentioned:
            await message.reply_text(settings[user_id]["group"])

# Run the bot
bot.run()
