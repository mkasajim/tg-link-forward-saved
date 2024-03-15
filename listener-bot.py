from telethon import TelegramClient, events
import os
from dotenv import load_dotenv

# Explicitly provide the path to your .env file
dotenv_path = '.env'
load_dotenv(dotenv_path=dotenv_path)

# Replace these with your own values
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
phone_number = os.getenv('PHONE_NUMBER')
bot_token = os.getenv('BOT_TOKEN')

# Initialize the client for your user account
user_client = TelegramClient('anon', api_id, api_hash)

# Initialize the client for your bot
bot_client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

# Handler for new messages to the user account
@user_client.on(events.NewMessage(incoming=True))
async def user_message_handler(event):
    sender = await event.get_sender()
    sender_name = getattr(sender, 'first_name', 'Unknown')
    print(f"New message from {sender_name}: {event.text}")

# Handler for commands sent to the bot
@bot_client.on(events.NewMessage(incoming=True, pattern='/ping'))
async def command_handler(event):
    # Respond to the "/ping" command
    await event.reply('Pong!')


def main():
    # Start both clients
    print("Listening for incoming messages and bot commands...")
    user_client.start(phone=phone_number)
    bot_client.run_until_disconnected()

if __name__ == '__main__':
    main()
