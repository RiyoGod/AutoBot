import os
import json
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

# File paths for storage
ACCOUNTS_FILE = "accounts.json"
SETTINGS_FILE = "settings.json"

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


# Helper functions to manage storage
def load_json(filename, default_data):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump(default_data, f)
    with open(filename, "r") as f:
        return json.load(f)


def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


# Load accounts and settings from storage
accounts = load_json(ACCOUNTS_FILE, [])
settings = load_json(SETTINGS_FILE, {"group": "", "dm": ""})


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
            accounts.append({"user_id": userbot.me.id, "string_session": string_session})
            save_json(ACCOUNTS_FILE, accounts)  # Save accounts to JSON

            await message.reply_text(f"✅ Logged in as {userbot.me.first_name} ({userbot.me.id})")
        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            await message.reply_text(f"❌ Login failed: {str(e)}")

        del user_sessions[user_id]  # Remove user from tracking


@bot.on_message(filters.command("accounts"))
async def accounts_handler(client: Client, message: Message):
    """Lists all logged-in accounts."""
    try:
        if accounts:
            account_list = [f"{acc['user_id']}" for acc in accounts]
            await message.reply_text("📝 **Logged-in Accounts:**\n" + "\n".join(account_list))
        else:
            await message.reply_text("❌ No accounts logged in.")
    except Exception as e:
        logging.error(f"Error in /accounts command: {str(e)}")


@bot.on_message(filters.command("setgroup"))
async def set_group_handler(client: Client, message: Message):
    """Sets auto-reply message for group mentions."""
    logging.error("Received /setgroup command")  # Debug log

    try:
        text = message.text.split(maxsplit=1)
        if len(text) < 2:
            await message.reply_text("❌ Please provide a message. Usage: `/setgroup Your message`")
            return

        settings["group"] = text[1]
        save_json(SETTINGS_FILE, settings)

        await message.reply_text("✅ Auto-reply for groups set successfully!")
    except Exception as e:
        logging.error(f"Error in /setgroup command: {str(e)}")


@bot.on_message(filters.command("setdm"))
async def set_dm_handler(client: Client, message: Message):
    """Sets auto-reply message for direct messages."""
    logging.error("Received /setdm command")  # Debug log

    try:
        text = message.text.split(maxsplit=1)
        if len(text) < 2:
            await message.reply_text("❌ Please provide a message. Usage: `/setdm Your message`")
            return

        settings["dm"] = text[1]
        save_json(SETTINGS_FILE, settings)

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
        global accounts
        accounts = [acc for acc in accounts if acc["user_id"] != user_id]
        save_json(ACCOUNTS_FILE, accounts)  # Save updated account list

        await message.reply_text(f"✅ Logged out {user_id} successfully!")
    except Exception as e:
        logging.error(f"Error in /logout command: {str(e)}")


# Run the bot
if __name__ == "__main__":
    bot.run()
