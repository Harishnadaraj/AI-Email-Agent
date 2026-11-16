import sqlite3
import json


def init_db():
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    # messages
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        role TEXT,
        content TEXT
    )
    """)

    # context
    c.execute("""
    CREATE TABLE IF NOT EXISTS context (
        user TEXT,
        key TEXT,
        value TEXT,
        PRIMARY KEY (user, key)
    )
    """)

    # 🔥 NEW: logs
    c.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        type TEXT,
        data TEXT
    )
    """)

    conn.commit()
    conn.close()


# ---------------------------
# 💬 CHAT
# ---------------------------
def save_message(user, role, content):
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute(
        "INSERT INTO messages (user, role, content) VALUES (?, ?, ?)",
        (user, role, content)
    )

    conn.commit()
    conn.close()


def get_history(user, limit=20):
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute(
        "SELECT role, content FROM messages WHERE user=? ORDER BY id DESC LIMIT ?",
        (user, limit)
    )

    rows = c.fetchall()
    conn.close()

    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


# ---------------------------
# 🧠 CONTEXT
# ---------------------------
def set_context(user, key, value):
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute(
        "INSERT OR REPLACE INTO context (user, key, value) VALUES (?, ?, ?)",
        (user, key, value)
    )

    conn.commit()
    conn.close()


def get_context(user, key):
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute(
        "SELECT value FROM context WHERE user=? AND key=?",
        (user, key)
    )

    row = c.fetchone()
    conn.close()

    return row[0] if row else None


# ---------------------------
# 🔥 PENDING ACTIONS
# ---------------------------
def set_pending_action(user, data):
    set_context(user, "pending_action", json.dumps(data))


def get_pending_action(user):
    data = get_context(user, "pending_action")
    return json.loads(data) if data else None


def clear_pending_action(user):
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute(
        "DELETE FROM context WHERE user=? AND key='pending_action'",
        (user,)
    )

    conn.commit()
    conn.close()


# ---------------------------
# 📊 LOGS (NEW)
# ---------------------------
def save_log(user, type, data):
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute(
        "INSERT INTO logs (user, type, data) VALUES (?, ?, ?)",
        (user, type, json.dumps(data))
    )

    conn.commit()
    conn.close()