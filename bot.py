import os
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
import json
import time

# Your bot details
bot_token = '8180105447:AAGgzlLeYPCotZRvBt5XP2SXQCsJaQP9CEE'  # Replace with your bot token

bot = Client("bot", bot_token=bot_token)
accounts = {}  # Dictionary to store the saved accounts
saved_messages = {}  # Dictionary to store saved messages

# Function to login with session string
@bot.on_message(filters.command('login'))
async def login(client, message):
    chat_id = message.chat.id
    username = message.from_user.username
    if username not in accounts:
        # Ask for the string session
        await bot.send_message(chat_id, "Please provide the string session for your account.")
        
        @bot.on_message(filters.text)
        async def handle_session_string(client, session_message):
            if session_message.from_user.username == username:
                session_string = session_message.text
                session_name = f'{username}_session'
                # Save the session string to use later
                pyrogram_client = Client(session_name, bot_token=None, session_string=session_string)
                await pyrogram_client.start()
                accounts[username] = pyrogram_client
                await bot.send_message(chat_id, f"Successfully logged in as {username}.")
                
                # Unsubscribe the session listener
                bot.remove_handler(handle_session_string)

# Command to save a message
@bot.on_message(filters.command('save'))
async def save_message(client, message):
    chat_id = message.chat.id
    username = message.from_user.username
    if username not in accounts:
        await bot.send_message(chat_id, "You need to login first using /login.")
        return

    content = message.text.split(maxsplit=1)
    if len(content) > 1:
        message_name = content[1]  # Unique name for the message
        saved_messages[message_name] = message.text
        await bot.send_message(chat_id, f"Message saved as {message_name}.")
    else:
        await bot.send_message(chat_id, "Please provide a unique message name like /save HI")

# Command to select which account to use for sending the saved message
@bot.on_message(filters.command('send'))
async def send_saved_message(client, message):
    chat_id = message.chat.id
    username = message.from_user.username
    if username not in accounts:
        await bot.send_message(chat_id, "You need to login first using /login.")
        return
    
    content = message.text.split(maxsplit=1)
    if len(content) > 1 and content[1] in saved_messages:
        message_name = content[1]
        saved_msg = saved_messages[message_name]
        
        # Asking which account to use
        await bot.send_message(chat_id, "Which account would you like to use to send this message?")
        accounts_list = list(accounts.keys())
        for idx, account in enumerate(accounts_list, 1):
            await bot.send_message(chat_id, f"{idx}. {account}")
        
        # Wait for the response from the user
        await bot.listen(chat_id, filters.text)
        
        @bot.on_message(filters.text)
        async def account_selector(client, message):
            if message.text in accounts_list:
                selected_account = message.text
                pyrogram_client = accounts[selected_account]
                
                # Send message from the selected account in the group
                try:
                    await pyrogram_client.send_message(chat_id, saved_msg)
                    await bot.send_message(chat_id, "Message sent successfully!")
                except FloodWait as e:
                    time.sleep(e.x)
            else:
                await bot.send_message(chat_id, "Invalid account selection.")

# Monitor messages in groups and send saved message if match
@bot.on_message(filters.text)
async def group_monitor(client, message):
    if message.text in saved_messages:
        saved_msg = saved_messages[message.text]
        try:
            await message.reply(saved_msg)
        except FloodWait as e:
            time.sleep(e.x)

if __name__ == "__main__":
    bot.run()
