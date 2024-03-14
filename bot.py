import os
import re
import sqlite3
from telethon import TelegramClient, events
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load .env file for environment variables
dotenv_path = '.env'
load_dotenv(dotenv_path=dotenv_path)

# Retrieve values from environment
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('BOT_TOKEN')
chat_id_str = os.getenv('CHAT_ID')
admin_chat_id_str = os.getenv('ADMIN_CHAT_ID')

if chat_id_str is not None:
    chat_id = int(chat_id_str)
else:
    raise ValueError("CHAT_ID environment variable not found. Please check your .env file.")

if admin_chat_id_str is not None:
    admin_chat_id = int(admin_chat_id_str)
else:
    raise ValueError("CHAT_ID environment variable not found. Please check your .env file.")

# Database setup for links
db_name = 'links.db'

def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(sqlite3.version)
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement """
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

# Initialize and create the database and table for links
conn = create_connection(db_name)
if conn is not None:
    create_table_sql = """ CREATE TABLE IF NOT EXISTS links (
                                        id integer PRIMARY KEY,
                                        url text NOT NULL UNIQUE
                                    ); """
    create_table(conn, create_table_sql)
else:
    print("Error! cannot create the database connection.")

# Database setup for blacklist
blacklist_db_name = 'blacklist.db'

def create_blacklist_connection(db_file):
    """Create a database connection to the SQLite database for the blacklist"""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        print(e)
    return conn

def add_to_blacklist(conn, domain):
    """Add a domain to the blacklist"""
    sql = '''INSERT INTO blacklist(domain) VALUES(?)'''
    try:
        c = conn.cursor()
        c.execute(sql, (domain,))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        print("Domain already blacklisted.")
        return None

def remove_from_blacklist(conn, domain):
    """Remove a domain from the blacklist"""
    sql = '''DELETE FROM blacklist WHERE domain=?'''
    try:
        c = conn.cursor()
        c.execute(sql, (domain,))
        conn.commit()
    except sqlite3.Error as e:
        print(e)

def list_blacklist(conn):
    """List all domains in the blacklist"""
    sql = '''SELECT domain FROM blacklist'''
    try:
        c = conn.cursor()
        c.execute(sql)
        return c.fetchall()
    except sqlite3.Error as e:
        print(e)
        return []

# def is_domain_blacklisted(conn, domain):
#     """Check if a domain is in the blacklist"""
#     sql = '''SELECT id FROM blacklist WHERE domain=?'''
#     cur = conn.cursor()
#     cur.execute(sql, (domain,))
#     data = cur.fetchone()
#     return data is not None

def is_domain_blacklisted(conn, domain):
    """Check if a domain or any of its parent domains are in the blacklist"""
    domain_parts = domain.split('.')
    # Check each level of domain, from the most specific to the least
    for i in range(len(domain_parts)):
        check_domain = '.'.join(domain_parts[i:])
        sql = '''SELECT id FROM blacklist WHERE domain=?'''
        cur = conn.cursor()
        cur.execute(sql, (check_domain,))
        if cur.fetchone():
            return True
    return False


# Initialize blacklist database and table
blacklist_conn = create_blacklist_connection(blacklist_db_name)
if blacklist_conn is not None:
    create_blacklist_table_sql = """CREATE TABLE IF NOT EXISTS blacklist (
                                     id integer PRIMARY KEY,
                                     domain text NOT NULL UNIQUE
                                 );"""
    create_table(blacklist_conn, create_blacklist_table_sql)

# Helper function to extract domain
def extract_domain(url):
    parsed_uri = urlparse(url)
    domain = '{uri.netloc}'.format(uri=parsed_uri)
    return domain

client = TelegramClient('anon', api_id, api_hash)

@client.on(events.NewMessage)
async def handler(event):
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', event.message.text)
    if urls:
        for url in urls:
            domain = extract_domain(url)
            if not is_domain_blacklisted(blacklist_conn, domain) and not link_exists(conn, url):
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


@client.on(events.NewMessage(pattern='/block (.+)'))
async def block_domain(event):
    sender = await event.get_sender()
    sender_id = sender.id
    if sender_id == admin_chat_id:  # Replace with your condition to check for admin or authorized user
        domain_to_block = event.pattern_match.group(1)
        if not is_domain_blacklisted(blacklist_conn, domain_to_block):
            add_to_blacklist(blacklist_conn, domain_to_block)
            await event.reply(f"Domain {domain_to_block} has been added to the blacklist.")
        else:
            await event.reply(f"Domain {domain_to_block} is already in the blacklist.")


@client.on(events.NewMessage(pattern='/unblock (.+)'))
async def unblock_domain(event):
    sender = await event.get_sender()
    sender_id = sender.id
    if sender_id == admin_chat_id:  # Replace with your condition to check for admin or authorized user
        domain_to_unblock = event.pattern_match.group(1)
        if is_domain_blacklisted(blacklist_conn, domain_to_unblock):
            remove_from_blacklist(blacklist_conn, domain_to_unblock)
            await event.reply(f"Domain {domain_to_unblock} has been removed from the blacklist.")
        else:
            await event.reply(f"Domain {domain_to_unblock} is not in the blacklist.")


@client.on(events.NewMessage(pattern='/blacklist'))
async def show_blacklist(event):
    sender = await event.get_sender()
    sender_id = sender.id
    if sender_id == admin_chat_id:  # Replace with your condition to check for admin or authorized user
        blacklist_domains = list_blacklist(blacklist_conn)
        if blacklist_domains:
            message = "Blacklisted domains:\n" + "\n".join([domain[0] for domain in blacklist_domains])
            await event.reply(message)
        else:
            await event.reply("The blacklist is currently empty.")


async def main():
    await client.start(bot_token=bot_token)
    print("Bot is up and running!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    client.loop.run_until_complete(main())
