import os
import asyncio
import logging
from pyrogram import Client, filters
from pymongo import MongoClient

# Enable Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Configuration (Read from Environment Variables)
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "auto_reply_bot"

# Connect to MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
accounts_collection = db["accounts"]
replies_collection = db["replies"]

# Initialize the Bot
bot = Client("AutoReplyBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Store logged-in userbots
userbots = {}

# Function to create a new Userbot Client
def create_userbot(phone_number, session_name):
    return Client(session_name, api_id=API_ID, api_hash=API_HASH, phone_number=phone_number)

# Start Command
@bot.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text("Welcome! Use `/login` to add an account.")

# Login Command
@bot.on_message(filters.command("login"))
async def login_handler(client, message):
    await message.reply_text("Send your **phone number** (with country code) to log in.", parse_mode="markdown2")

    phone_msg = await bot.listen(message.chat.id)
    phone_number = phone_msg.text.strip()

    session_name = f"userbot_{phone_number}"
    
    # Check if the account is already logged in
    if phone_number in userbots:
        await message.reply_text("This account is already logged in!")
        return

    # Create and start the Userbot
    userbot = create_userbot(phone_number, session_name)
    await userbot.start()

    # Store userbot details
    userbots[phone_number] = userbot
    accounts_collection.insert_one({"phone_number": phone_number, "session_name": session_name})
    
    await message.reply_text("Login successful! Now use `/setgroup` or `/setdm` to configure auto-replies.")

# Set Auto-Reply for Group
@bot.on_message(filters.command("setgroup"))
async def set_group_reply(client, message):
    await message.reply_text("Send the group name where you want to set auto-reply.")

    group_msg = await bot.listen(message.chat.id)
    group_name = group_msg.text.strip()

    await message.reply_text("Now send the auto-reply message for this group.")

    reply_msg = await bot.listen(message.chat.id)
    reply_text = reply_msg.text.strip()

    replies_collection.update_one(
        {"group_name": group_name},
        {"$set": {"reply_text": reply_text}},
        upsert=True
    )

    await message.reply_text(f"Auto-reply set for `{group_name}`.")

# Set Auto-Reply for DM
@bot.on_message(filters.command("setdm"))
async def set_dm_reply(client, message):
    await message.reply_text("Send the auto-reply message for DMs.")

    reply_msg = await bot.listen(message.chat.id)
    reply_text = reply_msg.text.strip()

    replies_collection.update_one(
        {"dm": True},
        {"$set": {"reply_text": reply_text}},
        upsert=True
    )

    await message.reply_text("Auto-reply set for DMs.")

# List Logged-in Accounts
@bot.on_message(filters.command("accounts"))
async def list_accounts(client, message):
    accounts = accounts_collection.find()
    account_list = [f"📱 {acc['phone_number']}" for acc in accounts]

    if account_list:
        await message.reply_text("**Logged-in Accounts:**\n" + "\n".join(account_list), parse_mode="markdown2")
    else:
        await message.reply_text("No accounts are logged in.")

# Auto-reply in Group (Handled by Userbot)
@bot.on_message(filters.mentioned & filters.group)
async def auto_reply_group(client, message):
    group_name = message.chat.title
    reply_data = replies_collection.find_one({"group_name": group_name})

    if reply_data:
        await message.reply_text(reply_data["reply_text"])

# Auto-reply in DM (Handled by Userbot)
@bot.on_message(filters.private & ~filters.bot)
async def auto_reply_dm(client, message):
    reply_data = replies_collection.find_one({"dm": True})

    if reply_data:
        await message.reply_text(reply_data["reply_text"])

# Run the Bot
bot.run()
