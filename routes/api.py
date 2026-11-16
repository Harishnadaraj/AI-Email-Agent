from fastapi import APIRouter
import sqlite3
import json

router = APIRouter()


@router.get("/api/history")
def get_history():
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute("SELECT user, role, content FROM messages ORDER BY id DESC LIMIT 100")
    rows = c.fetchall()
    conn.close()

    return [{"user": r[0], "role": r[1], "content": r[2]} for r in rows]


@router.get("/api/logs")
def get_logs():
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute("SELECT type, data FROM logs ORDER BY id DESC LIMIT 100")
    rows = c.fetchall()
    conn.close()

    return [{"type": r[0], "data": json.loads(r[1])} for r in rows]