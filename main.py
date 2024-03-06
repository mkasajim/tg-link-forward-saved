import os
from dotenv import load_dotenv
import sqlite3
from telethon import TelegramClient, events

# Database setup
db_name = 'links.db'

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

# Handler for new messages with a URL pattern
@client.on(events.NewMessage(pattern=r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'))
async def handler(event):
    url = event.message.text
    if not link_exists(conn, url):
        insert_link(conn, url)
        # Forwarding the message containing a new link to Saved Messages
        await client.forward_messages(chat_id, event.message)

async def main():
    # Start the client
    await client.start()
    print("Bot is up and running!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    client.loop.run_until_complete(main())
