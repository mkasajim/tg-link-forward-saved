from telethon import TelegramClient, events

# Use your own values here
api_id = 'YOUR_API_ID'
api_hash = 'YOUR_API_HASH'
bot_token = 'YOUR_BOT_TOKEN'

# The client will be used to listen to messages. Using the bot token to forward messages.
client = TelegramClient('anon', api_id, api_hash)

# Handler for new messages with a URL pattern
@client.on(events.NewMessage(pattern=r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'))
async def handler(event):
    # Forwarding the message containing a link to Saved Messages
    await client.forward_messages('me', event.message)

async def main():
    # Start the client
    await client.start()
    print("Bot is up and running!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    client.loop.run_until_complete(main())
