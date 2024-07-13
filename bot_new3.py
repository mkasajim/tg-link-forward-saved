from telethon import TelegramClient, events, types
from telethon.extensions import markdown
import os
from dotenv import load_dotenv
import re
import sqlite3
from urllib.parse import urlparse, parse_qs, urlunparse, urlunsplit
import socket
import time
from bs4 import BeautifulSoup
import requests
import hashlib
from playwright.async_api import async_playwright
import datetime

# Explicitly provide the path to your .env file
dotenv_path = '.env'
load_dotenv(dotenv_path=dotenv_path)

# Replace these with your own values
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
phone_number = os.getenv('PHONE_NUMBER')
bot_token = os.getenv('BOT_TOKEN')
# bot_token2 = os.getenv('NEW_BOT_TOKEN')
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

# bot_client2 = TelegramClient('bot2', api_id, api_hash).start(bot_token=bot_token2)


# Handler for new messages to the user account
# @user_client.on(events.NewMessage(incoming=True))
# async def user_message_handler(event):
#     # urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', event.message.text)
#     url_pattern = r'(?:(?:https?|ftp):\/\/)?(?:www\.)?(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,6}(?:\/[^\s]*)?'
#     urls = re.findall(url_pattern, event.message.text)

# url_pattern = r'\b(?:(?:https?://|www\.)\S+|(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+(?:[a-zA-Z]{2,6}))(?:/[^\s()]*[\w()]+)?'

# @user_client.on(events.NewMessage(incoming=True))
# async def user_message_handler(event):
#     urls = set()
    
#     # Entity approach
#     for entity in event.message.entities or []:
#         if isinstance(entity, (types.MessageEntityUrl, types.MessageEntityTextUrl)):
#             if isinstance(entity, types.MessageEntityTextUrl):
#                 urls.add(entity.url)
#             else:
#                 url = event.message.text[entity.offset:entity.offset+entity.length]
#                 urls.add(url)
    
#     # Regex approach
#     regex_urls = re.findall(url_pattern, event.message.text, re.IGNORECASE)
#     urls.update(regex_urls)

#    # Get the markdown of the message
#     markdown_msg = markdown.unparse(event.message.text, event.message.entities)
    
#     # print(f"Message markdown: {markdown_text}")

# Define the log file path
log_file_path = 'telegram_url_log.txt'
max_file_size = 1_000_000  # 1MB in bytes

def write_to_log(content):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{current_time}]\n{content}\n\n"

    # Check if the file exists and its size
    if os.path.exists(log_file_path):
        file_size = os.path.getsize(log_file_path)
        if file_size + len(log_entry.encode('utf-8')) > max_file_size:
            # If adding the new entry would exceed 1MB, remove old entries
            with open(log_file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            while len(''.join(lines).encode('utf-8')) + len(log_entry.encode('utf-8')) > max_file_size:
                lines.pop(0)  # Remove the oldest entry
            
            with open(log_file_path, 'w', encoding='utf-8') as file:
                file.writelines(lines)
    
    # Append the new log entry
    with open(log_file_path, 'a', encoding='utf-8') as file:
        file.write(log_entry)


@user_client.on(events.NewMessage(incoming=True))
async def user_message_handler(event):
    # Get the message text and the entities (which include links)
    message_text = event.message.message
    entities = event.message.entities
    msg = event.text

    urls = []
    emails = []

    if entities:
        for entity in entities:
            if isinstance(entity, types.MessageEntityTextUrl):
                # For custom URLs, we extract the URL directly
                urls.append(entity.url)
            elif isinstance(entity, types.MessageEntityEmail):
                # Collect emails separately
                offset = entity.offset
                length = entity.length
                email = message_text[offset:offset + length]
                emails.append(email)
            elif isinstance(entity, types.MessageEntityUrl):
                # For regular URLs, we extract the text that was recognized as a URL
                offset = entity.offset
                length = entity.length
                url = message_text[offset:offset + length]
                # Check and prepend the protocol if missing
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                # Remove trailing non-URL characters
                url = re.sub(r'[^\w/:.-]+$', '', url)
                urls.append(url)

    # Additional regex extraction to handle missed cases
    url_pattern = r'(https?:\/\/[^\s]+)'
    additional_urls = re.findall(url_pattern, message_text)

    # Filter out emails from additional URLs and ensure the correct protocol
    for url in additional_urls:
        # Remove trailing punctuation and newlines
        url = re.sub(r'[^\w/:.-]+$', '', url.strip().strip('.'))
        if '@' not in url and not any(email in url for email in emails):
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            if url not in urls:
                urls.append(url)

    # Ensure unique URLs while preserving order
    seen = set()
    unique_urls = []
    for url in urls:
        if url not in seen:
            unique_urls.append(url)
            seen.add(url)

    # # Print or process the extracted URLs
    # print(f"\n----------------------------------------------------\n{msg}\n----------------------------------------------------------")
    # print(f"Extracted URLs: {unique_urls}\n----------------------------------")
    # Prepare the log content
    log_content = f"Message:\n{msg}\n\nExtracted URLs: {unique_urls}"

    

    if unique_urls:
        print(f"Detected URLs: {unique_urls}")
        for url in unique_urls:
            # if not url.startswith(('http://', 'https://')):
            #     url = 'https://' + url

            # Write to log file
            write_to_log(log_content)
            
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
            print(f'\n---------------------------\nBase URL: {base_url}\n-----------------------------')
            domain = extract_domain(url)

            if is_new_bot(bots_conn, event.message.text):
                print("New bot detected!\n-------------------------------------------------------------\n")
                # bot_link_match = re.search(r't\.me/([^/]+)', event.message.text)
                bot_link_match = re.search(r'(?:https?://)?t\.me/([^/?]+)', event.message.text)
                if bot_link_match:
                    bot_username = bot_link_match.group(1)
                    insert_bot(bots_conn, bot_username)
                    # Send message about the new bot
                    message_text = (f"**Full Post:-**\n{msg}\n\n"
                            f"**Event Link:-**\n{url}\n\n"
                            f"**Post Source:-** {post_source} ({chat_link})\n"
                            f"**{source}:-** {chat_title}"
                        )
                    print(f"Sending message by bot.............\n-------------------------------------------------------------\n")
                    await user_client.send_message(chat_id, message_text, parse_mode='md')
                    break
            if is_domain_blacklisted(blacklist_conn, domain):
                print("Domain is blacklisted!\n-------------------------------------------------------------\n")
                break

            if not is_domain_blacklisted(blacklist_conn, domain):
                print("Link is not in blacklist")
                print("\n-------------------------------------------------------------\n")
                # if not insert_link(conn, domain, url):
                if not insert_link(conn, domain, base_url):
                    break
                # if not link_exists(conn, domain):
                # exist = await check_and_insert(url, cursor_webpages)
                exist = await check_and_insert(base_url, cursor_webpages)
                # if check_and_insert(url, cursor_webpages):
                if exist:
                    print("Link does not exist\n-------------------------------------------------------------\n")
                    # insert_link(conn, domain, url)

                    # if chat_link_available:
                    #     message_text = (f"**Full Post:-**\n{event.text}\n\n"
                    #         f"**Event Link:-**\n{url}\n\n"
                    #         f"**Post Source:-** [{post_source}]({chat_link})\n"
                    #         f"**{source}:-** {chat_title}"
                    #     )
                    # else:
                    #     message_text = (f"**Full Post:-**\n{event.text}\n\n"
                    #         f"**Event Link:-**\n{url}\n\n"
                    #         f"**Post Source:-** {post_source} ({chat_link})\n"
                    #         f"**{source}:-** {chat_title}"
                    #     )
                    # print("\033[92mSending message by bot.............\n-------------------------------------------------------------\n")
                    # print(message_text)
                    # print("\n-------------------------------------------------------------\n\033[0m")
                    # await user_client.send_message(chat_id, message_text, parse_mode='md')

                    if chat_link_available:
                        message_text = (f"**Full Post:-**\n{msg}\n\n"
                            f"**Event Link:-**\n{url}\n\n"
                            f"**Post Source:-** [{post_source}]({chat_link})\n"
                            f"**{source}:-** {chat_title}"
                        )
                    else:
                        message_text = (f"**Full Post:-**\n{msg}\n\n"
                            f"**Event Link:-**\n{url}\n\n"
                            f"**Post Source:-** {post_source} ({chat_link})\n"
                            f"**{source}:-** {chat_title}"
                        )

                    print("\033[92mSending message by bot.............\n-------------------------------------------------------------\n")
                    print(message_text)
                    print("\n-------------------------------------------------------------\n\033[0m")

                    # Check if the original message contains an image
                    if event.message.photo:
                        # Send the message with the image
                        await user_client.send_file(
                            chat_id,
                            event.message.photo,
                            caption=message_text,
                            parse_mode='md'
                        )
                    else:
                        # If there's no image, send the message as before
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

@bot_client.on(events.NewMessage(incoming=True, pattern='/refer'))
async def show_blacklist(event):
    sender = await event.get_sender()
    sender_id = sender.id
    if sender_id == admin_chat_id:
        refs = list_refer(refer_conn)
        if refs:
            message = "All refs:\n" + "\n".join([ref[0] for ref in refs])
            await event.reply(message)
        else:
            await event.reply("The referall list is currently empty")

@bot_client.on(events.NewMessage(incoming=True, pattern='/add_refer (.+)'))
async def add_refer_param(event):
    sender = await event.get_sender()
    sender_id = sender.id
    if sender_id == admin_chat_id:
        refer_to_add = event.pattern_match.group(1).strip()  # Remove any leading/trailing whitespace
        if not is_ref_exist(refer_conn, refer_to_add):
            insert_refer(refer_conn, refer_to_add)
            await event.reply(f"Referral parameter {refer_to_add} has been added to the list.")
        else:
            await event.reply(f"Referral parameter {refer_to_add} is already in the list.")

@bot_client.on(events.NewMessage(incoming=True, pattern='/remove_refer (.+)'))
async def remove_refer(event):
    sender = await event.get_sender()
    sender_id = sender.id
    if sender_id == admin_chat_id:
        refer_to_remove = event.pattern_match.group(1)
        if is_ref_exist(refer_conn, refer_to_remove):
            remove_from_refer(refer_conn, refer_to_remove)
            await event.reply(f"Referral parameter {refer_to_remove} has been removed from the list.")
        else:
            await event.reply(f"Referral {refer_to_remove} is not in the list.")

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
    params = list_refer(refer_conn)

    # print(f'\n-----------------------------------\nParams: {params} \n------------------------------')

    # for param in ['Code', 'invite', 'refercode', 'referral_code', 'invite_code', 'r']:
    for param in params:
        query.pop(param, None)
    url_parts[4] = ''
    return urlunparse(url_parts), query

# def link_exists(conn, domain):
#     """ Check if a domain exists in the database """
#     sql = '''SELECT id FROM links WHERE url=?'''
#     cur = conn.cursor()
#     cur.execute(sql, (domain,))
#     data = cur.fetchone()
#     print (f"Does link exist: {domain}: {data is not None}\n-------------------------------------------------------------\n")
#     return data is not None

def link_exists(conn, full_url):
    """ Check if a full_url exists in the database """
    sql = '''SELECT id FROM links WHERE full_url=?'''
    cur = conn.cursor()
    cur.execute(sql, (full_url,))
    data = cur.fetchone()
    print (f"Does link exist: {full_url}: {data is not None}\n-------------------------------------------------------------\n")
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
    # if not link_exists(conn, domain):  # Use the return value to make a decision
    if not link_exists(conn, full_url):
        sql = '''INSERT INTO links(url, full_url) VALUES(?, ?)'''
        try:
            c = conn.cursor()
            c.execute(sql, (domain, full_url))
            conn.commit()
            # return c.lastrowid
            return True
        except sqlite3.IntegrityError as e:
            print(f"Link insertion failed due to IntegrityError: {e}")
            # return False
            # return None
            return False
    else:
        print(f"Link already exists: {full_url}")
        print("\n-------------------------------------------------------------\n")
        # return None
        return False


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

refer_db = 'refer.db'

def create_refer_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        print(e)
    return conn

def insert_refer(conn, referrer):
    sql = '''INSERT INTO refer(referrer) VALUES(?)'''
    try:
        c = conn.cursor()
        c.execute(sql, (referrer,))  # Note the comma to make it a tuple
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        return None
    
def remove_from_refer(conn, referrer):
    sql = '''DELETE FROM refer WHERE referrer=?'''
    try:
        c = conn.cursor()
        c.execute(sql, (referrer,))
        conn.commit()
    except sqlite3.Error as e:
        print(e)

def list_refer(conn):
    sql = '''SELECT referrer FROM refer'''
    try:
        c = conn.cursor()
        c.execute(sql)
        return c.fetchall()
    except sqlite3.Error as e:
        return []
    
def is_ref_exist(conn, referral):
    sql = '''SELECT id FROM refer WHERE referrer=?'''
    cur = conn.cursor()
    cur.execute(sql, (referral,))
    respond = cur.fetchone() is not None
    print (f"Is referral exist: {referral}: {respond}\n-------------------------------------------------------------\n")
    return respond

refer_conn = create_refer_connection(refer_db)
if refer_conn is not None:
    create_refer_table_sql = """CREATE TABLE IF NOT EXISTS refer (
                                    id integer PRIMARY KEY,
                                    referrer text NOT NULL UNIQUE
                                );"""
    create_table(refer_conn, create_refer_table_sql)



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

# Connect to SQLite database
conn_webpages = sqlite3.connect('webpages.db')
cursor_webpages = conn_webpages.cursor()
# Create table if it doesn't exist
cursor_webpages.execute('''
CREATE TABLE IF NOT EXISTS web_content (
 url TEXT,
 content_hash TEXT UNIQUE
)
''')
conn.commit()

# def fetch_and_hash(url):
#     # Add https if the url does not contain http/https
#     if not url.startswith('http://') and not url.startswith('https://'):
#         url = 'https://' + url

#     # Visiting website
#     print(f"Visiting website: {url}")
#     print("-------------------------------------------------------------")
#     response = requests.get(url)
#     if response.status_code == 200:
#         # Optional: Use BeautifulSoup to parse and clean up the HTML
#         soup = BeautifulSoup(response.content, 'html.parser')
#         webpage_content = soup.get_text()

#         # Create a hash of the webpage content
#         hasher = hashlib.sha256()
#         hasher.update(webpage_content.encode('utf-8'))
#         return hasher.hexdigest()
#     else:
#         return None

# def fetch_and_hash(url):
#     # Add https if the url does not contain http/https
#     if not url.startswith('http://') and not url.startswith('https://'):
#         url = 'https://' + url

#     # Visiting website
#     print(f"Visiting website: {url}")
#     print("-------------------------------------------------------------")
#     try:
#         response = requests.get(url)
#     except requests.exceptions.RequestException as e:
#         print(f"Error occurred: {e}")
#         return None

#     if response.status_code == 200:
#         # Optional: Use BeautifulSoup to parse and clean up the HTML
#         soup = BeautifulSoup(response.content, 'html.parser')
#         webpage_content = soup.get_text()

#         # Create a hash of the webpage content
#         hasher = hashlib.sha256()
#         hasher.update(webpage_content.encode('utf-8'))
#         return hasher.hexdigest()
#     else:
#         return None

# async def fetch_and_hash(url):
#     # Add https if the url does not contain http/https
#     if not url.startswith('http://') and not url.startswith('https://'):
#         url = 'https://' + url

#     print(f"Visiting website: {url}")
#     print("-------------------------------------------------------------")

#     async with async_playwright() as p:
#         browser = await p.chromium.launch()
#         try:
#             page = await browser.new_page()
#             response = await page.goto(url)

#             if response is not None and response.ok:
#                 # Get the full page content
#                 webpage_content = await page.content()

#                 # Create a hash of the webpage content
#                 hasher = hashlib.sha256()
#                 hasher.update(webpage_content.encode('utf-8'))
#                 return hasher.hexdigest()
#             else:
#                 print(f"Failed to load the page. Status: {response.status if response else 'Unknown'}")
#                 return None
#         except Exception as e:
#             print(f"Error occurred: {e}")
#             return None
#         finally:
#             await browser.close()


# async def check_and_insert(url, cursor):
#     content_hash = await fetch_and_hash(url)
#     if content_hash:
#         try:
#             cursor.execute('INSERT INTO web_content (url, content_hash) VALUES (?, ?)', (url, content_hash))
#             conn.commit()
#             print(f"Inserted: {url}")
#             print("\n-------------------------------------------------------------\n")
#             return True
#         except sqlite3.IntegrityError:
#             print(f"Same website already exists: {url}")
#             print("\n-------------------------------------------------------------\n")
#             return False
#     else:
#         print(f"Failed to fetch or hash content for URL: {url}")
#         print("\n-------------------------------------------------------------\n")
#         return False

async def fetch_and_hash(url):
    # Add https if the url does not contain http/https
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url

    print(f"Visiting website: {url}")
    print("-------------------------------------------------------------")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            page = await browser.new_page()
            response = await page.goto(url)
            if response is not None and response.ok:
                # Get the full page content
                webpage_content = await page.content()
                # Create a hash of the webpage content
                hasher = hashlib.sha256()
                hasher.update(webpage_content.encode('utf-8'))
                return hasher.hexdigest()
            else:
                print(f"Failed to load the page. Status: {response.status if response else 'Unknown'}")
                return None
        except Exception as e:
            print(f"Error occurred: {e}")
            return None
        finally:
            await browser.close()

def hash_url(url):
    # Parse the URL
    parsed_url = urlparse(url)
    # Reconstruct the URL without query parameters
    clean_url = urlunsplit((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', ''))
    # Hash the clean URL
    hasher = hashlib.sha256()
    hasher.update(clean_url.encode('utf-8'))
    return hasher.hexdigest()

async def check_and_insert(url, cursor):
    content_hash = await fetch_and_hash(url)
    if content_hash is None:
        # If fetching fails, hash the URL instead
        content_hash = hash_url(url)
        print(f"Using URL hash instead for: {url}")

    try:
        cursor.execute('INSERT INTO web_content (url, content_hash) VALUES (?, ?)', (url, content_hash))
        conn.commit()
        print(f"Inserted: {url}")
        print("\n-------------------------------------------------------------\n")
        return True
    except sqlite3.IntegrityError:
        print(f"Same website already exists: {url}")
        print("\n-------------------------------------------------------------\n")
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
