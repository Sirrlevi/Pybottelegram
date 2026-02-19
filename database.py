import aiosqlite
import time

DB_NAME = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            chat_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 1
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS message_log (
            user_id INTEGER,
            timestamp INTEGER
        )
        """)
        await db.commit()

async def is_enabled(chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT enabled FROM settings WHERE chat_id=?",
            (chat_id,))
        row = await cursor.fetchone()
        return row[0] == 1 if row else True

async def set_enabled(chat_id, value):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (chat_id, enabled) VALUES (?, ?)",
            (chat_id, value))
        await db.commit()

async def check_spam(user_id):
    now = int(time.time())
    one_hour = now - 3600
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM message_log WHERE timestamp < ?",
            (one_hour,))
        cursor = await db.execute(
            "SELECT COUNT(*) FROM message_log WHERE user_id=?",
            (user_id,))
        count = (await cursor.fetchone())[0]

        if count >= 15:
            return True

        await db.execute(
            "INSERT INTO message_log VALUES (?, ?)",
            (user_id, now))
        await db.commit()
        return False
