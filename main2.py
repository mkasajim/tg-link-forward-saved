import os
import re
from dotenv import load_dotenv
import sqlite3
from telethon import TelegramClient, events

# Database setup
db_name = 'links.db'

# Explicitly provide the path to your .env file
dotenv_path = '.env'
load_dotenv(dotenv_path=dotenv_path)

# Retrieve values from environment
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('BOT_TOKEN')
chat_id_str = os.getenv('CHAT_ID')  # Get CHAT_ID as string

# Ensure CHAT_ID is provided and convert it to an integer
if chat_id_str is not None:
    chat_id = int(chat_id_str)
else:
    raise ValueError("CHAT_ID environment variable not found. Please check your .env file.")

def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(sqlite3.version)
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(conn):
    """ create a table for storing links """
    create_table_sql = """ CREATE TABLE IF NOT EXISTS links (
                                        id integer PRIMARY KEY,
                                        url text NOT NULL UNIQUE
                                    ); """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except sqlite3.Error as e:
        print(e)

def insert_link(conn, link):
    """ Insert a new link into the links table """
    sql = ''' INSERT INTO links(url) VALUES(?) '''
    try:
        c = conn.cursor()
        c.execute(sql, (link,))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        print("Link already exists.")
        return None

def link_exists(conn, link):
    """ Check if a link exists in the database """
    sql = ''' SELECT id FROM links WHERE url=? '''
    cur = conn.cursor()
    cur.execute(sql, (link,))
    data = cur.fetchone()
    return data is not None

# Initialize and create the database and table
conn = create_connection(db_name)
if conn is not None:
    create_table(conn)
else:
    print("Error! cannot create the database connection.")

client = TelegramClient('anon', api_id, api_hash)

@client.on(events.NewMessage)
async def handler(event):
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', event.message.text)
    if urls:
        for url in urls:
            if not link_exists(conn, url):
                insert_link(conn, url)
                
                # Check if the event has a chat and username or use alternative methods
                if hasattr(event.chat, 'username') and event.chat.username:
                    chat_link = f"https://t.me/{event.chat.username}/{event.message.id}"
                elif hasattr(event.message, 'id'):
                    # Fallback to using message ID and chat ID for private groups/channels, if direct link construction is needed
                    chat_link = f"Message ID: {event.message.id} in Chat ID: {event.chat_id} (Direct link not available for private chats)"
                else:
                    chat_link = "Direct link not available."
                
                # Get the title of the group/channel
                source_title = getattr(event.chat, 'title', 'Unknown source')
                
                # Prepare the new message text format with Markdown for bold
                message_text = (
                    f"**Full Post:-**\n{event.message.text}\n\n"
                    f"**Event Link:-**\n{url}\n\n"
                    f"**Post Source:-** {chat_link}\n"
                    f"**Channel/Group:-** {source_title}"
                )
                
                # Send the new message with the formatted text to the specified chat ID
                await client.send_message(chat_id, message_text, parse_mode='md')
                break  # Stop after the first new link is processed


async def main():
    # Start the client
    await client.start(bot_token=bot_token)
    print("Bot is up and running!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    client.loop.run_until_complete(main())
