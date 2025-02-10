import asyncio
from pyrogram import Client, filters
from pyrogram.errors import FloodWait

# ====== CONFIGURATION ======
API_ID = 26416419                # Replace with your API_ID (as an integer)
API_HASH = "c109c77f5823c847b1aeb7fbd4990cc4"      # Replace with your API_HASH
BOT_TOKEN = "8180105447:AAGgzlLeYPCotZRvBt5XP2SXQCsJaQP9CEE "    # Replace with your Bot Token

# ====== MAIN BOT CLIENT ======
bot = Client("bot", bot_token=BOT_TOKEN)

# ====== GLOBAL STATE ======
# When a user calls /login in private chat, we wait for their session string.
# Mapping: chat_id -> user id (for pending login)
pending_login = {}

# Logged-in user accounts:
# Key: Telegram user id (the one chatting with the bot)
# Value: list of Pyrogram Client instances (one per logged‑in account)
logged_in_accounts = {}

# For the /save command, we use a “pending” state to hold conversation data.
# Key: chat_id, Value: dictionary with keys:
#    "keyword"   : the keyword for which the message is saved
#    "account"   : the chosen Pyrogram client (once selected)
#    "accounts"  : list of available accounts (if more than one)
#    "step"      : "choose_account" or "await_message"
pending_save = {}

# Saved messages:
# Key: keyword (string)
# Value: dict with keys:
#    "account" : the Pyrogram client that will send the message
#    "message" : the text content to send
saved_messages = {}

# ====== HANDLERS ======

# /login command handler (private chat only)
@bot.on_message(filters.command("login") & filters.private)
async def login_command(client, message):
    chat_id = message.chat.id
    await message.reply("Please send me your string session for your account.\n\nIf you don't have one, run a script like:\n\n"
                        "from pyrogram import Client\n\n"
                        "app = Client(\"my_account\", api_id=API_ID, api_hash=API_HASH)\n"
                        "with app:\n"
                        "    print(app.export_session_string())")
    pending_login[chat_id] = message.from_user.id

# /save command handler (private chat only)
@bot.on_message(filters.command("save") & filters.private)
async def save_command(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /save <keyword>\nExample: /save HI")
        return
    keyword = args[1].strip()
    user_accounts = logged_in_accounts.get(user_id, [])
    if not user_accounts:
        await message.reply("You have no logged in accounts. Please use /login first.")
        return
    if len(user_accounts) == 1:
        # Only one account available: use it automatically.
        pending_save[chat_id] = {"keyword": keyword, "account": user_accounts[0]}
        await message.reply(f"Using your only logged in account. Now send me the message content to be saved for keyword '{keyword}'.")
    else:
        # Multiple accounts: ask user to choose.
        text = "Which account do you want to use? Send the number:\n"
        for i, acct in enumerate(user_accounts, start=1):
            try:
                me = await acct.get_me()
                text += f"{i}. {me.first_name} (@{me.username})\n"
            except Exception:
                text += f"{i}. Unknown Account\n"
        pending_save[chat_id] = {"keyword": keyword, "account": None, "accounts": user_accounts, "step": "choose_account"}
        await message.reply(text)

# Private message handler to process pending login or pending save steps.
@bot.on_message(filters.private & filters.text)
async def process_private_text(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # ----- Process pending login -----
    if chat_id in pending_login:
        session_string = message.text.strip()
        # Create a new Pyrogram client for this user account.
        new_client = Client(
            f"session_{user_id}_{len(logged_in_accounts.get(user_id, [])) + 1}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=session_string
        )
        try:
            await new_client.start()
        except Exception as e:
            await message.reply(f"Failed to log in with the provided session string. Error: {e}")
            del pending_login[chat_id]
            return
        # Store the new client under the user's id.
        logged_in_accounts.setdefault(user_id, []).append(new_client)
        await message.reply("Successfully logged in your account!")
        del pending_login[chat_id]
        return

    # ----- Process pending save conversation -----
    if chat_id in pending_save:
        data = pending_save[chat_id]
        # If we are expecting the account choice…
        if data.get("step") == "choose_account":
            try:
                choice = int(message.text.strip())
            except ValueError:
                await message.reply("Please send a valid number corresponding to the account.")
                return
            accounts_list = data.get("accounts", [])
            if choice < 1 or choice > len(accounts_list):
                await message.reply("Invalid choice. Please send a valid number corresponding to the account.")
                return
            chosen_account = accounts_list[choice - 1]
            data["account"] = chosen_account
            data["step"] = "await_message"
            await message.reply(f"Account selected. Now send me the message content to be saved for keyword '{data['keyword']}'.")
            return
        else:
            # We are expecting the message content.
            keyword = data["keyword"]
            chosen_account = data["account"]
            saved_messages[keyword] = {"account": chosen_account, "message": message.text}
            await message.reply(f"Saved message for keyword '{keyword}'.")
            del pending_save[chat_id]
            return

# Group message handler.
# If a group message exactly equals one of the saved keywords, send the saved message using the associated account.
@bot.on_message(filters.group & filters.text)
async def group_message_handler(client, message):
    keyword = message.text.strip()
    if keyword in saved_messages:
        entry = saved_messages[keyword]
        account_client = entry["account"]
        text_to_send = entry["message"]
        try:
            await account_client.send_message(message.chat.id, text_to_send)
        except FloodWait as e:
            await asyncio.sleep(e.x)
        except Exception as e:
            print(f"Error sending message for keyword '{keyword}': {e}")

# ====== RUN THE BOT ======
if __name__ == "__main__":
    print("Bot is starting...")
    bot.run()
