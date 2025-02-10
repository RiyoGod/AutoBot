import os
import asyncio
import logging
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackContext

# Load Environment Variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")

# MongoDB Setup
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["auto_reply_bot"]
accounts_collection = db["accounts"]
auto_replies_collection = db["auto_replies"]

# Bot Setup
bot = Bot(BOT_TOKEN)
app = Application.builder().token(BOT_TOKEN).build()

# Store active userbot sessions
userbots = {}

# Logging
logging.basicConfig(level=logging.DEBUG)


async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("🤖 **Auto-Reply Bot** is running!\nUse /login to add accounts.")


async def login(update: Update, context: CallbackContext):
    """Login a new userbot"""
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Usage: `/login <STRING_SESSION>`")
        return

    string_session = args[0]
    userbot_client = TelegramClient(StringSession(string_session), API_ID, API_HASH)

    try:
        await userbot_client.start()
        me = await userbot_client.get_me()
        userbots[me.id] = userbot_client

        # Save to MongoDB
        await accounts_collection.insert_one({"user_id": me.id, "string_session": string_session})
        await update.message.reply_text(f"✅ **Logged in as {me.first_name}** (ID: `{me.id}`)")

    except Exception as e:
        await update.message.reply_text(f"❌ **Login Failed:** {str(e)}")


async def accounts(update: Update, context: CallbackContext):
    """Show logged-in accounts"""
    accounts = await accounts_collection.find().to_list(None)
    if not accounts:
        await update.message.reply_text("🚫 No accounts are hosted.")
        return

    message = "📝 **Hosted Accounts:**\n"
    for acc in accounts:
        message += f"- `{acc['user_id']}`\n"

    await update.message.reply_text(message)


async def setgroup(update: Update, context: CallbackContext):
    """Set auto-reply for group mentions"""
    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/setgroup <GROUP_ID> <MESSAGE>`")
        return

    group_id = context.args[0]
    reply_text = " ".join(context.args[1:])

    await auto_replies_collection.update_one(
        {"type": "group", "group_id": group_id},
        {"$set": {"reply_text": reply_text}},
        upsert=True,
    )
    await update.message.reply_text(f"✅ **Group auto-reply set for {group_id}**")


async def setdm(update: Update, context: CallbackContext):
    """Set auto-reply for DMs"""
    if len(context.args) < 1:
        await update.message.reply_text("Usage: `/setdm <MESSAGE>`")
        return

    reply_text = " ".join(context.args)
    await auto_replies_collection.update_one(
        {"type": "dm"},
        {"$set": {"reply_text": reply_text}},
        upsert=True,
    )
    await update.message.reply_text(f"✅ **DM auto-reply set!**")


async def handle_messages(event):
    """Handles userbot messages"""
    sender = await event.get_sender()
    user_id = sender.id

    if event.is_private:
        reply_data = await auto_replies_collection.find_one({"type": "dm"})
        if reply_data:
            await event.reply(reply_data["reply_text"])
    
    elif event.is_group:
        if event.message.mentioned:
            reply_data = await auto_replies_collection.find_one({"type": "group", "group_id": event.chat_id})
            if reply_data:
                await event.reply(reply_data["reply_text"])


async def start_userbots():
    """Start listening for messages on userbot accounts"""
    accounts = await accounts_collection.find().to_list(None)

    for acc in accounts:
        session = acc["string_session"]
        client = TelegramClient(StringSession(session), API_ID, API_HASH)
        
        await client.start()
        userbots[acc["user_id"]] = client
        client.add_event_handler(handle_messages, events.NewMessage())

    if userbots:
        print(f"✅ {len(userbots)} userbot(s) started!")


# Add Bot Commands
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("login", login))
app.add_handler(CommandHandler("accounts", accounts))
app.add_handler(CommandHandler("setgroup", setgroup))
app.add_handler(CommandHandler("setdm", setdm))

# Start everything
async def main():
    await start_userbots()
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
