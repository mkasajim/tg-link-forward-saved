from telethon import TelegramClient, events
import os
from dotenv import load_dotenv
import re
import sqlite3
from urllib.parse import urlparse, parse_qs, urlunparse

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

def link_exists(conn, link):
    """ Check if a link exists in the database """
    sql = ''' SELECT id FROM links WHERE url=? '''
    cur = conn.cursor()
    cur.execute(sql, (link,))
    data = cur.fetchone()
    return data is not None

# Handler for new messages to the user account
@user_client.on(events.NewMessage(incoming=True))
async def user_message_handler(event):
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', event.message.text)
    if urls:
        for url in urls:
            # sender = await event.get_sender()
            # sender_name = getattr(sender, 'first_name', 'Unknown')
            # print(f"New message from {sender_name}: {event.text}")
            chat_title = ''
            sender_name = 'Unknown'  # Default sender name
            source = ''
            post_source= 'Unknown'

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
            if not is_domain_blacklisted(blacklist_conn, domain) and not link_exists(conn, base_url):
                insert_link(conn, base_url, url)
                message_text = (
                        f"**Full Post:-**\n{event.text}\n\n"
                        f"**Event Link:-**\n{url}\n\n"
                        f"**Post Source:-** {post_source}\n"
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
    # Respond to the "/ping" command
    await event.reply('The bot has started!')

@bot_client.on(events.NewMessage(incoming=True,pattern='/block (.+)'))
async def block_domain(event):
    sender = await event.get_sender()
    sender_id = sender.id
    if sender_id == admin_chat_id:
        domain_to_block = event.pattern_match.group(1)
        if not is_domain_blacklisted(blacklist_conn, domain_to_block):
            add_to_blacklist(blacklist_conn, domain_to_block)
            await event.reply(f"Domain {domain_to_block} has been added to the blacklist.")
        else:
            await event.reply(f"Domain {domain_to_block} is already in the blacklist.")

@bot_client.on(events.NewMessage(incoming=True,pattern='/unblock (.+)'))
async def unblock_domain(event):
    sender = await event.get_sender()
    sender_id = sender.id
    if sender_id == admin_chat_id:
        domain_to_unblock = event.pattern_match.group(1)
        if is_domain_blacklisted(blacklist_conn, domain_to_unblock):
            remove_from_blacklist(blacklist_conn, domain_to_unblock)
            await event.reply(f"Domain {domain_to_unblock} has been removed from the blacklist.")
        else:
            await event.reply(f"Domain {domain_to_unblock} is not in the blacklist.")

@bot_client.on(events.NewMessage(incoming=True,pattern='/blacklist'))
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

@bot_client.on(events.NewMessage(incoming=True,pattern='/status'))
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

def link_exists(conn, base_url):
    sql = '''SELECT id FROM links WHERE url LIKE ?'''
    cur = conn.cursor()
    cur.execute(sql, (base_url + '%',))
    data = cur.fetchone()
    return data is not None

def insert_link(conn, base_url, full_url):
    if not link_exists(conn, base_url):
        sql = '''INSERT INTO links(url, full_url) VALUES(?, ?)'''
        try:
            c = conn.cursor()
            c.execute(sql, (base_url, full_url))
            conn.commit()
            return c.lastrowid
        except sqlite3.IntegrityError:
            return None
    return None

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
    domain_parts = domain.split('.')
    for i in range(len(domain_parts)):
        check_domain = '.'.join(domain_parts[i:])
        sql = '''SELECT id FROM blacklist WHERE domain=?'''
        cur = conn.cursor()
        cur.execute(sql, (check_domain,))
        if cur.fetchone():
            return True
    return False

blacklist_conn = create_blacklist_connection(blacklist_db_name)
if blacklist_conn is not None:
    create_blacklist_table_sql = """CREATE TABLE IF NOT EXISTS blacklist (
                                     id integer PRIMARY KEY,
                                     domain text NOT NULL UNIQUE
                                 );"""
    create_table(blacklist_conn, create_blacklist_table_sql)

def extract_domain(url):
    parsed_uri = urlparse(url)
    return '{uri.netloc}'.format(uri=parsed_uri)

def main():
    # Start both clients
    print("Listening for incoming messages and bot commands...")
    user_client.start(phone=phone_number)
    bot_client.run_until_disconnected()

if __name__ == '__main__':
    main()
