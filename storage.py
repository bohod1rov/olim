"""SQLite orqali sozlamalar va statistika"""

import sqlite3
import logging
from config import Config

logger = logging.getLogger(__name__)

DB_PATH = "bot_data.db"


def init_db():
    """Ma'lumotlar bazasini ishga tushirish"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            language TEXT DEFAULT 'auto',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_settings (
            chat_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            chat_id INTEGER,
            duration INTEGER DEFAULT 0,
            char_count INTEGER DEFAULT 0,
            language TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Ma'lumotlar bazasi tayyor")


def get_user_language(user_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT language FROM user_settings WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else Config.DEFAULT_LANGUAGE


def set_user_language(user_id: int, language: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_settings (user_id, language)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET language = excluded.language
    """, (user_id, language))
    conn.commit()
    conn.close()


def is_chat_enabled(chat_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT enabled FROM chat_settings WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row[0]) if row else True


def set_chat_enabled(chat_id: int, enabled: bool):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_settings (chat_id, enabled)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET enabled = excluded.enabled
    """, (chat_id, int(enabled)))
    conn.commit()
    conn.close()


def save_stat(user_id: int, chat_id: int, duration: int, text: str, language: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO stats (user_id, chat_id, duration, char_count, language)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, chat_id, duration, len(text), language))
    conn.commit()
    conn.close()


def get_user_stats(user_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(char_count), 0), COALESCE(SUM(duration), 0)
        FROM stats WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()
    return {"total": row[0], "total_chars": row[1], "total_duration": row[2]}


def get_global_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*), COUNT(DISTINCT user_id), COALESCE(SUM(char_count), 0)
        FROM stats
    """)
    row = cursor.fetchone()
    conn.close()
    return {"total": row[0], "unique_users": row[1], "total_chars": row[2]}