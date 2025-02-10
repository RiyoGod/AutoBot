import os
import logging
import asyncio
from dotenv import load_dotenv
from pymongo import MongoClient
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

# Setup Logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Connect to MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    accounts_col = db["accounts"]
    settings_col = db["settings"]
    logging.info("✅ MongoDB connected successfully!")
except Exception as e:
    logging.error(f"❌ MongoDB Connection Error: {e}")
    exit()

# Telegram Bot
bot_app = Application.builder().token(BOT_TOKEN).build()

# Store Active User Sessions
user_clients = {}

# ➜ Command: Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Use /login to add a Telegram account.")

# ➜ Command: Login a Telegram Account
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args
    
    if len(args) != 1:
        await update.message.reply_text("Usage: `/login <string_session>`", parse_mode="Markdown")
        return
    
    string_session = args[0]
    
    if user_id in user_clients:
        await update.message.reply_text("⚠ You already have an active session.")
        return

    client = TelegramClient(StringSession(string_session), API_ID, API_HASH)

    try:
        await client.connect()
        if not await client.is_user_authorized():
            await update.message.reply_text("⚠ Session invalid. Login again.")
            return
        
        me = await client.get_me()
        user_clients[user_id] = client
        accounts_col.update_one({"user_id": user_id}, {"$set": {"session": string_session}}, upsert=True)

        await update.message.reply_text(f"✅ Logged in as {me.first_name} ({me.id})")
        logging.info(f"User {me.id} logged in successfully!")

    except Exception as e:
        logging.error(f"Login Error: {e}")
        await update.message.reply_text("❌ Login failed. Check logs.")

# ➜ Command: Set Group Auto-Reply
async def set_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args
    
    if len(args) < 2:
        await update.message.reply_text("Usage: `/setgroup <group_id> <message>`", parse_mode="Markdown")
        return
    
    group_id = int(args[0])
    message = " ".join(args[1:])
    
    settings_col.update_one({"user_id": user_id, "group_id": group_id}, {"$set": {"reply_message": message}}, upsert=True)
    await update.message.reply_text(f"✅ Auto-reply set for group `{group_id}`.", parse_mode="Markdown")
    logging.info(f"Set group auto-reply for {group_id} → {message}")

# ➜ Command: Set DM Auto-Reply
async def set_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args
    
    if len(args) < 1:
        await update.message.reply_text("Usage: `/setdm <message>`", parse_mode="Markdown")
        return
    
    message = " ".join(args)
    settings_col.update_one({"user_id": user_id, "type": "dm"}, {"$set": {"reply_message": message}}, upsert=True)
    await update.message.reply_text(f"✅ DM auto-reply set!", parse_mode="Markdown")
    logging.info(f"Set DM auto-reply → {message}")

# ➜ Command: Show Hosted Accounts
async def show_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    accounts = list(accounts_col.find({}))
    if not accounts:
        await update.message.reply_text("⚠ No active accounts.")
        return
    
    message = "👥 **Hosted Accounts:**\n"
    for acc in accounts:
        message += f"• `{acc['user_id']}` - **Session Active**\n"
    
    await update.message.reply_text(message, parse_mode="Markdown")

# ➜ Auto-Reply Handler for Messages
async def auto_reply(event):
    user_id = event.chat_id
    group_id = event.chat_id if event.is_group else None
    
    if group_id:
        setting = settings_col.find_one({"user_id": user_id, "group_id": group_id})
    else:
        setting = settings_col.find_one({"user_id": user_id, "type": "dm"})
    
    if setting and "reply_message" in setting:
        await event.reply(setting["reply_message"])
        logging.info(f"Replied in chat {user_id}: {setting['reply_message']}")

# ➜ Function to Start User Sessions
async def start_user_sessions():
    accounts = list(accounts_col.find({}))
    for acc in accounts:
        string_session = acc["session"]
        client = TelegramClient(StringSession(string_session), API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            logging.error(f"❌ Account {acc['user_id']} not authorized!")
            continue
        
        user_clients[acc["user_id"]] = client
        client.add_event_handler(auto_reply, events.NewMessage())
        
        logging.info(f"✅ User {acc['user_id']} session started.")

# ➜ Start Telegram Bot
async def main():
    await start_user_sessions()
    
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("login", login))
    bot_app.add_handler(CommandHandler("setgroup", set_group))
    bot_app.add_handler(CommandHandler("setdm", set_dm))
    bot_app.add_handler(CommandHandler("accounts", show_accounts))
    
    await bot_app.run_polling()

# ➜ Run the Bot
if __name__ == "__main__":
    asyncio.run(main())
