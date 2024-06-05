import time
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest, JoinChannelRequest
from dotenv import load_dotenv
import os

# Explicitly provide the path to your .env file
dotenv_path = '.env'
load_dotenv(dotenv_path=dotenv_path)

# Replace these with your own values
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
phone_number = os.getenv('PHONE_NUMBER')
bot_token = os.getenv('BOT_TOKEN')
chat_id_str = os.getenv('CHAT_ID')
admin_chat_id_str = os.getenv('ADMIN_CHAT_ID')

client = TelegramClient('anon2', api_id, api_hash)

async def get_channels_with_linked_groups_and_bio_and_join():
    await client.start()
    # Get all dialogs
    dialogs = await client.get_dialogs()

    # Filter dialogs to only include channels
    for dialog in dialogs:
        if dialog.is_channel:
            # Fetch full channel details including bio
            full_channel = await client(GetFullChannelRequest(dialog.entity))
            channel = await client.get_entity(dialog.entity)
            linked_group_id = full_channel.full_chat.linked_chat_id if hasattr(full_channel.full_chat, 'linked_chat_id') else None
            linked_group = None
            join_status = "No linked group"

            if linked_group_id:
                try:
                    # Attempt to join the linked group
                    linked_group = await client.get_entity(linked_group_id)
                    await client(JoinChannelRequest(linked_group))
                    join_status = "Joined"
                except Exception as e:
                    join_status = f"Failed to join: {str(e)}"

                # Print channel name, linked group name, and join status immediately
                print({
                    'channel': {
                        'title': channel.title,
                        'id': channel.id,
                    },
                    'linked_group': {
                        'title': linked_group.title if linked_group else None,
                        'id': linked_group.id if linked_group else None
                    } if linked_group else None,
                    'join_status': join_status
                })

                # Sleep to avoid rate limits
                time.sleep(60)

# Schedule the function every 60 minutes
while True:
    with client:
        client.loop.run_until_complete(get_channels_with_linked_groups_and_bio_and_join())
    # Wait for 60 minutes before running again
    time.sleep(60 * 60)
