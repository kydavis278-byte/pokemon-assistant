import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE_DIR, "pokedex.db")


def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_one(query, params=()):
    with connect() as conn:
        cur = conn.execute(query, params)
        return cur.fetchone()


def fetch_all(query, params=()):
    with connect() as conn:
        cur = conn.execute(query, params)
        return cur.fetchall()
