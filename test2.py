import sqlite3
from urllib.parse import urlparse, parse_qs, urlunparse

db_name = 'links.db'

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        print(e)
    return conn

def list_links(conn):
    sql = '''SELECT url FROM links'''
    try:
        c = conn.cursor()
        c.execute(sql)
        return c.fetchall()
    except sqlite3.Error as e:
        return []

def link_exists(conn, domain):
    sql = '''SELECT id FROM links WHERE url=?'''
    cur = conn.cursor()
    cur.execute(sql, (domain,))
    data = cur.fetchone()
    respond = data is not None
    print (f"Is link exist: {domain}: {respond}")
    return respond

conn = create_connection(db_name)

links = list_links(conn)

print (links)

domain= "https://check-cc.com/__**"

respond = link_exists(conn, domain)

print(respond)
