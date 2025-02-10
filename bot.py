import asyncio
from pyrogram import Client, filters

# ====== CONFIGURATION ======
API_ID = 26416419  # Replace with your API_ID (as an integer)
API_HASH = "c109c77f5823c847b1aeb7fbd4990cc4"  # Replace with your API_HASH
BOT_TOKEN = "8180105447:AAGgzlLeYPCotZRvBt5XP2SXQCsJaQP9CEE"  # Your bot token

saved_messages = {}  # Store saved messages by keyword

# Step 1: Bot command to save messages
async def save_command(client, message):
    try:
        keyword = message.text.split(maxsplit=1)[1].strip().lower()  # Extract the keyword from the message
        saved_messages[keyword] = "Message saved for keyword: " + keyword  # Save the message (can replace with any desired message)

        # Debug message to confirm saving
        print(f"Saved message for keyword '{keyword}': {saved_messages[keyword]}")

        # Reply with confirmation
        await message.reply(f"Message saved for keyword: `{keyword}`", parse_mode=None)  # No formatting used
    except Exception as e:
        print(f"Error in save_command: {e}")
        await message.reply("Error saving the message.", parse_mode=None)

# Step 2: Account Worker to listen for keyword in group chats and send saved messages
async def account_worker(session_name):
    try:
        async with Client(session_name, api_id=API_ID, api_hash=API_HASH) as account:
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

                    # Send the saved message in the group as plain text (no formatting)
                    try:
                        await message.reply(text_to_send, parse_mode=None)  # Remove parse_mode for plain text
                        print(f"Sent saved message for '{incoming_text}' in group.")
                    except Exception as e:
                        print(f"Error sending saved message in group: {e}")
    except Exception as e:
        print(f"Error in account_worker: {e}")

# Step 3: Bot command to login and start listening
async def login_command(client, message):
    try:
        # Get session string after the /login command
        session_string = message.text.split(maxsplit=1)[1]  # Extract the session string from the message
        if not session_string:
            await message.reply("Please provide the session string after /login command. Example: `/login <session_string>`", parse_mode=None)
            return

        session_name = f"{session_string}_session"
        await account_worker(session_name)  # Start the account worker with the session string
        await message.reply(f"Successfully logged in to {session_string}'s account and started listening.", parse_mode=None)

    except IndexError:
        await message.reply("Please provide the session string after /login command. Example: `/login <session_string>`", parse_mode=None)
    except Exception as e:
        print(f"Error in login_command: {e}")
        await message.reply("Error logging in. Please check the session string and try again.", parse_mode=None)

# Step 4: Main bot setup
async def main():
    bot = Client("bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

    @bot.on_message(filters.command("save") & filters.private)
    async def handle_save(client, message):
        # Command to save messages
        if len(message.text.split()) < 2:
            await message.reply("Usage: `/save <keyword>`\nExample: `/save HI`", parse_mode=None)
            return
        await save_command(client, message)

    @bot.on_message(filters.command("login") & filters.private)
    async def handle_login(client, message):
        # Command to login using session string
        await login_command(client, message)

    print("Bot is starting...")
    await bot.start()  # Start the bot

# Run the bot
asyncio.run(main())
