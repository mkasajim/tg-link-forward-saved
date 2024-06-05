# Telegram Link Forwarder and Saver

This Python script acts as a Telegram bot that listens for messages containing links in a specified chat. It then forwards those links to another specified chat, providing additional context like the sender's name and the chat it originated from. 

## Features

- **Link Forwarding:** Forwards links from a source chat to a destination chat.
- **Contextual Information:** Includes sender name, chat title, and source (group/channel/private) with each forwarded link.
- **Blacklisting:** Allows blocking links from specific domains.
- **Link Saving:** Saves forwarded links to a local database to prevent duplicates.
- **Administrative Commands:** Provides commands for managing the blacklist and checking the bot's status.

## Requirements

- Python 3.7 or higher
- `telethon` library
- `python-dotenv` library
- `sqlite3` library

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/tg-link-forward-saved.git
   cd tg-link-forward-saved
   ```
2. Install the required libraries:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory and add your Telegram API credentials and chat IDs:
   ```
   API_ID=your_api_id
   API_HASH=your_api_hash
   PHONE_NUMBER=your_phone_number
   BOT_TOKEN=your_bot_token
   CHAT_ID=your_destination_chat_id
   ADMIN_CHAT_ID=your_admin_chat_id
   ```

## Usage

1. Run the script:
   ```bash
   python bot_final.py
   ```
2. The bot will start listening for messages in your source chat.
3. Any links shared in the source chat will be forwarded to your destination chat with the added context.

## Commands

The following commands can be used to manage the bot:

- `/ping`: Checks if the bot is responsive.
- `/start`: Starts the bot.
- `/links`: Lists all the links that have been sent. (Admin only)
- `/block <domain>`: Adds a domain to the blacklist. (Admin only)
- `/unblock <domain>`: Removes a domain from the blacklist. (Admin only)
- `/blacklist`: Shows the current blacklist. (Admin only)
- `/status`: Checks the bot's status. (Admin only)

## Notes

- Replace the placeholders in the `.env` file with your actual Telegram API credentials and chat IDs.
- The bot requires access to both your user account and the bot account.
- Make sure to add the bot to both the source and destination chats.
- The blacklist is stored in a local SQLite database.

## Contributing

Contributions are welcome! If you find any bugs or have suggestions for improvements, please open an issue or submit a pull request.
