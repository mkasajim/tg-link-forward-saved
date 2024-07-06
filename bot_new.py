from telethon import TelegramClient, events
import os
from dotenv import load_dotenv
import re
import sqlite3
from urllib.parse import urlparse, parse_qs, urlunparse
import socket
import time

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

if chat_id_str is not None:
    chat_id = int(chat_id_str)
else:
    raise ValueError("CHAT_ID environment variable not found. Please check your .env file.")

if admin_chat_id_str is not None:
    admin_chat_id = int(admin_chat_id_str)
else:
    raise ValueError("CHAT_ID environment variable not found. Please check your .env file.")

# Initialize the client for your user account
user_client = TelegramClient('anon', api_id, api_hash)

# Initialize the client for your bot
bot_client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)


# Handler for new messages to the user account
@user_client.on(events.NewMessage(incoming=True))
async def user_message_handler(event):
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', event.message.text)
    if urls:
        for url in urls:
            chat_title = ''
            sender_name = 'Unknown'  # Default sender name
            source = ''
            post_source = 'Unknown'
            chat_link_available = False
            chat_link = ''

            # Check if the event has a chat and username or use alternative methods
            if hasattr(event.chat, 'username') and event.chat.username:
                chat_link_available = True
                chat_link = f"https://t.me/{event.chat.username}/{event.message.id}"
            elif hasattr(event.message, 'id'):
                chat_link_available = False
                # Fallback to using message ID and chat ID for private groups/channels, if direct link construction is needed
                chat_link = f"Message ID: {event.message.id} in Chat ID: {event.chat_id} (Direct link not available for private chats)"
            else:
                chat_link_available = False
                chat_link = "Direct link not available."

            # Attempt to retrieve the sender; if None, handle accordingly
            sender = await event.get_sender()
            if sender:
                if hasattr(sender, 'first_name') and hasattr(sender, 'last_name'):
                    sender_name = f"{sender.first_name} {sender.last_name if sender.last_name else ''}"
                else:
                    sender_name = "Anonymous"
                post_source = sender_name

            # Adjust logic based on the type of the chat
            if event.is_private:
                # For private chats, the sender name is already set
                pass
            elif event.is_group or event.is_channel:
                chat = await event.get_chat()
                chat_title = chat.title  # Chat title for groups/channels
                if event.is_group:
                    # Append group title for group messages
                    sender_name += f" (Group: {chat_title})"
                    source = "Group"
                else:
                    # For channels, the sender might be None, so we use the channel title
                    sender_name = f"Channel: {chat_title}"
                    source = "Channel"

            print(f"New message from {sender_name}: \n{event.text}\n-------------------------------------------------------------")

            base_url, _ = normalize_url(url)
            domain = extract_domain(url)

            if is_new_bot(bots_conn, event.message.text):
                print("New bot detected!\n-------------------------------------------------------------\n")
                # bot_link_match = re.search(r't\.me/([^/]+)', event.message.text)
                bot_link_match = re.search(r'(?:https?://)?t\.me/([^/?]+)', event.message.text)
                if bot_link_match:
                    bot_username = bot_link_match.group(1)
                    insert_bot(bots_conn, bot_username)
                    # Send message about the new bot
                    message_text = (f"**Full Post:-**\n{event.text}\n\n"
                            f"**Event Link:-**\n{url}\n\n"
                            f"**Post Source:-** {post_source} ({chat_link})\n"
                            f"**{source}:-** {chat_title}"
                        )
                    print(f"Sending message by bot.............\n-------------------------------------------------------------\n")
                    await user_client.send_message(chat_id, message_text, parse_mode='md')
                    break

            if not is_domain_blacklisted(blacklist_conn, domain):
                print("Link is not in blacklist")
                if not link_exists(conn, domain):
                    print("Link does not exist\n-------------------------------------------------------------\n")
                    insert_link(conn, domain, url)
                    if chat_link_available:
                        message_text = (f"**Full Post:-**\n{event.text}\n\n"
                            f"**Event Link:-**\n{url}\n\n"
                            f"**Post Source:-** [{post_source}]({chat_link})\n"
                            f"**{source}:-** {chat_title}"
                        )
                    else:
                        message_text = (f"**Full Post:-**\n{event.text}\n\n"
                            f"**Event Link:-**\n{url}\n\n"
                            f"**Post Source:-** {post_source} ({chat_link})\n"
                            f"**{source}:-** {chat_title}"
                        )
                    print(f"Sending message by bot.............\n-------------------------------------------------------------\n")
                    await user_client.send_message(chat_id, message_text, parse_mode='md')
                    break
            


# Handler for commands sent to the bot
@bot_client.on(events.NewMessage(incoming=True, pattern='/ping'))
async def command_handler(event):
    # Respond to the "/ping" command
    await event.reply('Pong!')

@bot_client.on(events.NewMessage(incoming=True, pattern='/start'))
async def command_handler(event):
    # Respond to the "/start" command
    await event.reply('The bot has started!')


@bot_client.on(events.NewMessage(incoming=True, pattern='/links'))
async def show_blacklist(event):
    sender = await event.get_sender()
    sender_id = sender.id
    if sender_id == admin_chat_id:
        domains = list_links(conn)
        if domains:
            message = "All Links Sent:\n" + "\n".join([domain[0] for domain in domains])
            await event.reply(message)
        else:
            await event.reply("The list is currently empty")

@bot_client.on(events.NewMessage(incoming=True, pattern='/block (.+)'))
async def block_domain(event):
    sender = await event.get_sender()
    sender_id = sender.id
    if sender_id == admin_chat_id:
        domain_to_block = event.pattern_match.group(1)
        domain_to_block = extract_domain(domain_to_block)
        if not is_domain_blacklisted(blacklist_conn, domain_to_block):
            add_to_blacklist(blacklist_conn, domain_to_block)
            await event.reply(f"Domain {domain_to_block} has been added to the blacklist.")
        else:
            await event.reply(f"Domain {domain_to_block} is already in the blacklist.")

@bot_client.on(events.NewMessage(incoming=True, pattern='/unblock (.+)'))
async def unblock_domain(event):
    sender = await event.get_sender()
    sender_id = sender.id
    if sender_id == admin_chat_id:
        domain_to_unblock = event.pattern_match.group(1)
        domain_to_unblock = extract_domain(domain_to_unblock)
        if is_domain_blacklisted(blacklist_conn, domain_to_unblock):
            remove_from_blacklist(blacklist_conn, domain_to_unblock)
            await event.reply(f"Domain {domain_to_unblock} has been removed from the blacklist.")
        else:
            await event.reply(f"Domain {domain_to_unblock} is not in the blacklist.")

@bot_client.on(events.NewMessage(incoming=True, pattern='/blacklist'))
async def show_blacklist(event):
    sender = await event.get_sender()
    sender_id = sender.id
    if sender_id == admin_chat_id:
        blacklist_domains = list_blacklist(blacklist_conn)
        if blacklist_domains:
            message = "Blacklisted domains:\n" + "\n".join([domain[0] for domain in blacklist_domains])
            await event.reply(message)
        else:
            await event.reply("The blacklist is currently empty.")

@bot_client.on(events.NewMessage(incoming=True, pattern='/status'))
async def show_status(event):
    sender = await event.get_sender()
    sender_id = sender.id
    if sender_id == admin_chat_id:
        await event.reply("The Bot is up and running.")

db_name = 'links.db'

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except sqlite3.Error as e:
        print(e)

def normalize_url(url):
    url_parts = list(urlparse(url))
    query = dict(parse_qs(url_parts[4]))
    for param in ['Code', 'invite', 'refercode', 'referral_code', 'invite_code']:
        query.pop(param, None)
    url_parts[4] = ''
    return urlunparse(url_parts), query

def link_exists(conn, domain):
    """ Check if a domain exists in the database """
    sql = '''SELECT id FROM links WHERE url=?'''
    cur = conn.cursor()
    cur.execute(sql, (domain,))
    data = cur.fetchone()
    print (f"Does link exist: {domain}: {data is not None}\n-------------------------------------------------------------\n")
    return data is not None

# def insert_link(conn, domain, full_url):
#     if not link_exists(conn, domain):
#         sql = '''INSERT INTO links(url, full_url) VALUES(?, ?)'''
#         try:
#             c = conn.cursor()
#             c.execute(sql, (domain, full_url))
#             conn.commit()
#             return c.lastrowid
#         except sqlite3.IntegrityError:
#             return None
#     return None

def insert_link(conn, domain, full_url):
    if not link_exists(conn, domain):  # Use the return value to make a decision
        sql = '''INSERT INTO links(url, full_url) VALUES(?, ?)'''
        try:
            c = conn.cursor()
            c.execute(sql, (domain, full_url))
            conn.commit()
            return c.lastrowid
        except sqlite3.IntegrityError:
            print("Link insertion failed due to IntegrityError.")
            return None
    else:
        print(f"Link already exists: {domain}")
        return None


def list_links(conn):
    sql = '''SELECT url FROM links'''
    try:
        c = conn.cursor()
        c.execute(sql)
        return c.fetchall()
    except sqlite3.Error as e:
        return []

conn = create_connection(db_name)
if conn is not None:
    create_table_sql = """ CREATE TABLE IF NOT EXISTS links (
                            id integer PRIMARY KEY,
                            url text NOT NULL,
                            full_url text NOT NULL UNIQUE
                        ); """
    create_table(conn, create_table_sql)

blacklist_db_name = 'blacklist.db'

def create_blacklist_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        print(e)
    return conn

def add_to_blacklist(conn, domain):
    sql = '''INSERT INTO blacklist(domain) VALUES(?)'''
    try:
        c = conn.cursor()
        c.execute(sql, (domain,))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        return None

def remove_from_blacklist(conn, domain):
    sql = '''DELETE FROM blacklist WHERE domain=?'''
    try:
        c = conn.cursor()
        c.execute(sql, (domain,))
        conn.commit()
    except sqlite3.Error as e:
        print(e)

def list_blacklist(conn):
    sql = '''SELECT domain FROM blacklist'''
    try:
        c = conn.cursor()
        c.execute(sql)
        return c.fetchall()
    except sqlite3.Error as e:
        return []

def is_domain_blacklisted(conn, domain):
    sql = '''SELECT id FROM blacklist WHERE domain=?'''
    cur = conn.cursor()
    cur.execute(sql, (domain,))
    respond = cur.fetchone() is not None
    print (f"Is domain blacklisted: {domain}: {respond}\n-------------------------------------------------------------\n")
    return respond

blacklist_conn = create_blacklist_connection(blacklist_db_name)
if blacklist_conn is not None:
    create_blacklist_table_sql = """CREATE TABLE IF NOT EXISTS blacklist (
                                    id integer PRIMARY KEY,
                                    domain text NOT NULL UNIQUE
                                );"""
    create_table(blacklist_conn, create_blacklist_table_sql)

def extract_domain(url):
    parsed_uri = urlparse(url)
    domain = '{uri.netloc}'.format(uri=parsed_uri)
    if domain.startswith('www.'):
        domain = domain[4:]
    print(f"{domain}\n-------------------------------------------------------------\n")
    return domain

# Database for storing bot usernames
bots_db_name = 'bots.db'

def create_bots_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        print(e)
    return conn

def create_bots_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except sqlite3.Error as e:
        print(e)

def bot_exists(conn, bot_username):
    """ Check if a bot username exists in the database """
    sql = '''SELECT id FROM bots WHERE username=?'''
    cur = conn.cursor()
    cur.execute(sql, (bot_username,))
    data = cur.fetchone()
    print(f"Does bot exist: {bot_username}: {data is not None}\n-------------------------------------------------------------\n")
    return data is not None

def insert_bot(conn, bot_username):
    if not bot_exists(conn, bot_username):
        sql = '''INSERT INTO bots(username) VALUES(?)'''
        try:
            c = conn.cursor()
            c.execute(sql, (bot_username,))
            conn.commit()
            return c.lastrowid
        except sqlite3.IntegrityError:
            return None
    return None

# def is_new_bot(conn, text_msg):
#     """ Checks if the given text message contains a new bot link. """

#     # Check for Telegram bot links
#     bot_link_match = re.search(r't\.me/([^/]+)', text_msg)
#     if bot_link_match:
#         bot_username = bot_link_match.group(1)

#         # Check if the username matches the bot pattern
#         if re.search(r'_bot$|bot$|Bot$', bot_username):
#             print(f"Found potential bot link: {bot_username}")
#             return not bot_exists(conn, bot_username)  # Check if the bot is new

#     return False  # No new bot link found

def is_new_bot(conn, text_msg):
    """Checks if the given text message contains a new bot link."""

    # Match both "t.me/" and "https://t.me/" patterns
    bot_link_match = re.search(r'(?:https?://)?t\.me/([^/?]+)', text_msg)

    if bot_link_match:
        bot_username = bot_link_match.group(1)

        # Check if the username matches the bot pattern
        if re.search(r'_bot$|bot$|Bot$', bot_username):
            print(f"Found potential bot link: {bot_username}")
            return not bot_exists(conn, bot_username)  # Check if the bot is new

    return False  # No new bot link found


# Create connection and table for bots database
bots_conn = create_bots_connection(bots_db_name)
if bots_conn is not None:
    create_bots_table_sql = """ CREATE TABLE IF NOT EXISTS bots (
                                id integer PRIMARY KEY,
                                username text NOT NULL UNIQUE
                            ); """
    create_bots_table(bots_conn, create_bots_table_sql)

def is_connected(hostname):
    """ Checks internet connection by attempting to resolve a hostname. """
    try:
        # Try resolving a hostname (e.g., Google's DNS)
        host = socket.gethostbyname(hostname)
        # Try connecting to the host on port 80
        with socket.create_connection((host, 80), 2):
            return True
    except Exception:
        pass
    return False


def main():
    # Start both clients
    # print("Listening for incoming messages and bot commands...")
    # user_client.start(phone=phone_number)
    # bot_client.run_until_disconnected()

    while True:
        try:
            # Start both clients
            print("Listening for incoming messages and bot commands...")
            user_client.start(phone=phone_number)
            bot_client.run_until_disconnected()
        except Exception as e:
            print(f"Error occurred: {e}")
            print("Checking internet connection...")

            # Check internet connection every 5 seconds
            while not is_connected("one.one.one.one"):
                print("Internet connection lost. Waiting for connection...")
                time.sleep(5)

            print("Internet connection regained. Restarting bot...")

if __name__ == '__main__':
    main()