from pyrogram import Client, filters
import html
import asyncio

# Escape HTML to avoid any issues with invalid tags
def escape_html(text):
    return html.escape(text)

# Save messages and sessions
saved_messages = {}
logged_in_accounts = {}

# Initialize the bot
bot = Client("bot", bot_token="8180105447:AAGgzlLeYPCotZRvBt5XP2SXQCsJaQP9CEE")

# Step 1: /login command to log in account using session string
@bot.on_message(filters.command("login") & filters.private)
async def login_command(client, message):
    if len(message.text.split()) < 2:
        await message.reply("Please provide the session string after /login command. Example: `/login <session_string>`")
        return

    session_string = message.text.split(maxsplit=1)[1]  # Get session string after /login
    try:
        session_name = f"session_{session_string}"
        async with Client(session_name, api_id=26416419, api_hash="c109c77f5823c847b1aeb7fbd4990cc4", session_string=session_string) as account:
            logged_in_accounts[session_string] = session_name
            await message.reply(f"Successfully logged in with session `{session_string}`!")
            # Send a message after login to the target user (just as a test)
            try:
                target_user = await account.get_chat("@UncountableAura")
                await account.send_message(target_user.id, "HI")
            except Exception as e:
                print(f"Error sending 'HI' message: {e}")
    except Exception as e:
        print(f"Failed to login with session string: {e}")
        await message.reply(f"Failed to login. Error: {e}")

# Step 2: /save command to save a message under a keyword
@bot.on_message(filters.command("save") & filters.private)
async def save_command(client, message):
    if len(message.text.split()) < 2:
        await message.reply("Usage: /save <keyword>")
        return
    keyword = message.text.split(maxsplit=1)[1]
    saved_messages[keyword] = None  # Initialize an empty message for the keyword
    await message.reply(f"Now, send me the message you want to save for keyword `{keyword}`.")

# Step 3: Store the message after saving it for the keyword
@bot.on_message(filters.private & filters.text)
async def save_message(client, message):
    if not message.text.startswith("/save"):
        keyword = message.text.strip().lower()
        if keyword in saved_messages and saved_messages[keyword] is None:
            escaped_message = escape_html(message.text)  # Escape HTML for safe message
            saved_messages[keyword] = escaped_message
            await message.reply(f"Saved message for keyword `{keyword}`: {escaped_message}")
        return

# Step 4: Account Worker to listen for keyword in group chats and send saved messages
async def account_worker(session_name):
    async with Client(session_name, api_id=26416419, api_hash="c109c77f5823c847b1aeb7fbd4990cc4") as account:
        print(f"Account {session_name} is now listening for keywords...")
        @account.on_message(filters.group & filters.text)
        async def group_message_handler(client, message):
            incoming_text = message.text.strip().lower()
            if incoming_text in saved_messages and saved_messages[incoming_text]:
                text_to_send = saved_messages[incoming_text]
                
                # Debug: Print the message to be sent
                print(f"Attempting to send saved message for keyword '{incoming_text}': {text_to_send}")

                # Check message length
                if len(text_to_send) > 4096:
                    print("Message exceeds the length limit of 4096 characters.")
                    return

                # Send the saved message in the group
                try:
                    await message.reply(text_to_send)
                    print(f"Sent saved message for '{incoming_text}' in group.")
                except Exception as e:
                    print(f"Error sending saved message in group: {e}")

# Start listening for groups and checking for keywords
async def start_account_listeners():
    for session_string in logged_in_accounts.values():
        await account_worker(session_string)

# Run the bot
if __name__ == "__main__":
    bot.run()
    # Start the account listeners after the bot is running
    asyncio.run(start_account_listeners())
