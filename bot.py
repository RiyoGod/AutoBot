import asyncio
from pyrogram import Client, filters
from pyrogram.errors import PeerIdInvalid, ChannelInvalid, FloodWait

# ====== CONFIGURATION ======
API_ID = 26416419
API_HASH = "c109c77f5823c847b1aeb7fbd4990cc4"
BOT_TOKEN = "8180105447:AAGgzlLeYPCotZRvBt5XP2SXQCsJaQP9CEE"
TARGET_USER = "@UncountableAura"  # Username of the target user

# ====== GLOBAL STATE ======
logged_in_accounts = {}  # This will store active accounts (string sessions)
saved_messages = {}      # This will store the keyword-message pairs

# ====== MAIN BOT CLIENT ======
bot = Client("bot", bot_token=BOT_TOKEN)

# ====== HANDLERS ======

# /login command handler (private chat only) to login via string session
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
        "Replace API_ID and API_HASH with your credentials."
    )

# /save command handler (private chat only) to save messages
@bot.on_message(filters.command("save") & filters.private)
async def save_command(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: `/save <keyword>`\nExample: `/save HII`")
        return
    keyword = args[1].strip().lower()
    if user_id not in logged_in_accounts:
        await message.reply("You must log in first using `/login`.")
        return

    # Wait for the actual message to save for the keyword
    await message.reply(f"Now send me the message to save for keyword `{keyword}`.")
    saved_messages[keyword] = None  # Initialize an empty entry

# Save the actual message after keyword is set
@bot.on_message(filters.private & filters.text)
async def save_message(client, message):
    user_id = message.from_user.id
    if user_id in logged_in_accounts:
        for keyword, _ in saved_messages.items():
            if saved_messages[keyword] is None:
                saved_messages[keyword] = message.text
                await message.reply(f"Saved message for `{keyword}`.")
                return

# ====== ACCOUNT CLIENT ======
# Function to monitor the group and send saved messages
async def account_worker(session_name):
    async with Client(session_name, api_id=API_ID, api_hash=API_HASH) as account:
        print(f"{session_name} logged in!")

        @account.on_message(filters.group & filters.text)
        async def group_message_handler(client, message):
            incoming_text = message.text.strip().lower()

            # Check if the incoming text matches any saved keyword
            if incoming_text in saved_messages and saved_messages[incoming_text]:
                text_to_send = saved_messages[incoming_text]
                try:
                    # Send the saved message in the group
                    await message.reply(text_to_send)
                    print(f"Sent saved message for '{incoming_text}'")  # Log the action
                except PeerIdInvalid:
                    print(f"Error: Invalid peer id. The account may not be a member of the group.")
                    await message.reply(f"Error: The account is not a member of the group or cannot access it.")
                except ChannelInvalid:
                    print(f"Error: Invalid channel/group. The account may not have permission to reply.")
                    await message.reply(f"Error: Invalid channel or group. The account cannot reply.")
                except FloodWait as e:
                    print(f"Error: Flood wait - the account is being rate-limited. Retry after {e.x} seconds.")
                    await message.reply(f"Error: The account is being rate-limited. Please try again after {e.x} seconds.")
                except Exception as e:
                    print(f"Unexpected error: {e}")
                    await message.reply(f"Failed to send saved message for '{incoming_text}'. Error: {e}")

# Function to login the account using string session and add to logged_in_accounts
async def login_account(session_string):
    try:
        session_name = f"session_{session_string}"  # Unique name for session
        async with Client(session_name, api_id=API_ID, api_hash=API_HASH, session_string=session_string) as account:
            logged_in_accounts[session_string] = session_name
            print(f"Successfully logged in as {session_name}")
            # After login, send a message
            try:
                target_user = await account.get_chat(TARGET_USER)
                await account.send_message(target_user.id, "HI")
            except Exception as e:
                print(f"Failed to send HI message: {e}")
    except Exception as e:
        print(f"Error logging in with session: {e}")

# ====== RUN THE BOT ======
if __name__ == "__main__":
    print("Bot is starting...")
    bot.run()
    
    # Start all the accounts
    for session_string in logged_in_accounts.values():
        asyncio.run(account_worker(session_string))
