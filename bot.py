import asyncio
from pyrogram import Client, filters
from pyrogram.errors import FloodWait

# ====== CONFIGURATION ======
API_ID = 26416419
API_HASH = "c109c77f5823c847b1aeb7fbd4990cc4"
BOT_TOKEN = "8180105447:AAGgzlLeYPCotZRvBt5XP2SXQCsJaQP9CEE"  # Remove any trailing spaces

# ====== MAIN BOT CLIENT ======
bot = Client("bot", bot_token=BOT_TOKEN)

# ====== GLOBAL STATE ======
# Pending login state (chat_id -> user id)
pending_login = {}

# Logged-in user accounts (user id -> list of Client instances)
logged_in_accounts = {}

# Pending save state for /save (chat_id -> dict with conversation state)
pending_save = {}

# Saved messages (lowercase keyword -> dict with keys "account" and "message")
saved_messages = {}

# ====== HANDLERS ======

# /login command handler (private chat only)
@bot.on_message(filters.command("login") & filters.private)
async def login_command(client, message):
    chat_id = message.chat.id
    await message.reply(
        "Please send me your string session for your account.\n\n"
        "If you don't have one, generate it using a script like this:\n\n"
        "```python\n"
        "from pyrogram import Client\n\n"
        "app = Client(\"my_account\", api_id=API_ID, api_hash=API_HASH)\n"
        "with app:\n"
        "    print(app.export_session_string())\n"
        "```\n"
        "Replace API_ID and API_HASH with your credentials.",
        parse_mode="markdown"
    )
    pending_login[chat_id] = message.from_user.id

# /save command handler (private chat only)
@bot.on_message(filters.command("save") & filters.private)
async def save_command(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: `/save <keyword>`\nExample: `/save HI`", parse_mode="markdown")
        return
    keyword = args[1].strip()
    user_accounts = logged_in_accounts.get(user_id, [])
    if not user_accounts:
        await message.reply("You have no logged in accounts. Please use `/login` first.", parse_mode="markdown")
        return
    if len(user_accounts) == 1:
        # Use the only logged in account.
        pending_save[chat_id] = {"keyword": keyword, "account": user_accounts[0]}
        await message.reply(
            f"Using your only logged in account. Now send me the message content to be saved for keyword **{keyword}**.",
            parse_mode="markdown"
        )
    else:
        # Multiple accounts: ask the user to choose one.
        text = "Which account do you want to use? Send the number:\n"
        for i, acct in enumerate(user_accounts, start=1):
            try:
                me = await acct.get_me()
                text += f"{i}. {me.first_name} (@{me.username})\n"
            except Exception:
                text += f"{i}. Unknown Account\n"
        pending_save[chat_id] = {"keyword": keyword, "account": None, "accounts": user_accounts, "step": "choose_account"}
        await message.reply(text)

# Process private text messages (for pending login or pending save)
@bot.on_message(filters.private & filters.text)
async def process_private_text(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Process pending login
    if chat_id in pending_login:
        session_string = message.text.strip()
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
        logged_in_accounts.setdefault(user_id, []).append(new_client)
        await message.reply("Successfully logged in your account!")
        del pending_login[chat_id]
        return

    # Process pending save conversation
    if chat_id in pending_save:
        data = pending_save[chat_id]
        # If expecting account choice:
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
            await message.reply(
                f"Account selected. Now send me the message content to be saved for keyword **{data['keyword']}**.",
                parse_mode="markdown"
            )
            return
        else:
            # Save the message content.
            keyword = data["keyword"]
            chosen_account = data["account"]
            saved_messages[keyword.lower()] = {"account": chosen_account, "message": message.text}
            await message.reply(f"Saved message for keyword **{keyword}**.", parse_mode="markdown")
            del pending_save[chat_id]
            return

# Group message handler
# When a group message (exactly) equals a saved keyword (case-insensitive), send the saved message.
@bot.on_message(filters.group & filters.text)
async def group_message_handler(client, message):
    incoming = message.text.strip().lower()
    if incoming in saved_messages:
        entry = saved_messages[incoming]
        account_client = entry["account"]
        text_to_send = entry["message"]
        try:
            await account_client.send_message(message.chat.id, text_to_send)
        except FloodWait as e:
            await asyncio.sleep(e.x)
        except Exception as e:
            print(f"Error sending message for keyword '{incoming}': {e}")

# ====== RUN THE BOT ======
if __name__ == "__main__":
    print("Bot is starting...")
    bot.run()
