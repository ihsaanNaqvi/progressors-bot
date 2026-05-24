"""SQLite operations — users, conversations, route completion tracking, language."""
import os
import json
from datetime import datetime
import aiosqlite
from config import DB_PATH


async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id           INTEGER PRIMARY KEY,
                username          TEXT,
                profile           TEXT,
                route             TEXT,
                current_step      INTEGER DEFAULT 0,
                route_created_at  TEXT,
                routes_count      INTEGER DEFAULT 0,
                language          TEXT DEFAULT 'ru',
                created_at        TEXT DEFAULT (datetime('now')),
                updated_at        TEXT DEFAULT (datetime('now'))
            )
        """)
        # Migration — add columns if upgrading
        for ddl in [
            "ALTER TABLE users ADD COLUMN route_created_at TEXT",
            "ALTER TABLE users ADD COLUMN routes_count INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'ru'",
        ]:
            try:
                await db.execute(ddl)
            except Exception:
                pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS step_feedback (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                step_number   INTEGER NOT NULL,
                feedback_type TEXT NOT NULL,
                created_at    TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.commit()


# ── Users ──────────────────────────────────────────────────────────────────

async def create_user(user_id: int, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username or str(user_id))
        )
        await db.commit()


async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_language(user_id: int) -> str:
    """Get user's language preference (defaults to 'ru')."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT language FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return (row["language"] if row and row["language"] else "ru")


async def set_language(user_id: int, language: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET language = ?, updated_at = ? WHERE user_id = ?",
            (language, datetime.now().isoformat(), user_id)
        )
        await db.commit()


async def update_user_profile(user_id: int, profile: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET profile = ?, updated_at = ? WHERE user_id = ?",
            (json.dumps(profile, ensure_ascii=False), datetime.now().isoformat(), user_id)
        )
        await db.commit()


async def update_user_route(user_id: int, route: dict):
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE users SET
               route = ?, current_step = 0,
               route_created_at = ?, updated_at = ?,
               routes_count = COALESCE(routes_count, 0) + 1
               WHERE user_id = ?""",
            (json.dumps(route, ensure_ascii=False), now, now, user_id)
        )
        await db.commit()


async def update_route_only(user_id: int, route: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET route = ?, updated_at = ? WHERE user_id = ?",
            (json.dumps(route, ensure_ascii=False), datetime.now().isoformat(), user_id)
        )
        await db.commit()


async def update_current_step(user_id: int, step: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET current_step = ?, updated_at = ? WHERE user_id = ?",
            (step, datetime.now().isoformat(), user_id)
        )
        await db.commit()


async def reset_user(user_id: int):
    """Clear profile, route and feedback — keep language preference."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE users SET
               profile = NULL, route = NULL, current_step = 0,
               route_created_at = NULL, updated_at = ?
               WHERE user_id = ?""",
            (datetime.now().isoformat(), user_id)
        )
        await db.execute("DELETE FROM step_feedback WHERE user_id = ?", (user_id,))
        await db.commit()


# ── Conversation history ───────────────────────────────────────────────────

async def add_message(user_id: int, role: str, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content)
        )
        await db.commit()


async def get_conversation(user_id: int, limit: int = 30) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT role, content FROM conversations WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


async def clear_conversation(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
        await db.commit()


# ── Step feedback / progress ───────────────────────────────────────────────

async def add_step_feedback(user_id: int, step_number: int, feedback_type: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO step_feedback (user_id, step_number, feedback_type) VALUES (?, ?, ?)",
            (user_id, step_number, feedback_type)
        )
        await db.commit()


async def mark_step_complete(user_id: int, step_number: int):
    await add_step_feedback(user_id, step_number, "completed")
    await update_current_step(user_id, step_number)


async def get_completed_steps(user_id: int) -> list[int]:
    """Steps completed for CURRENT route only."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT route_created_at FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row or not row["route_created_at"]:
                return []
            route_started = row["route_created_at"]

        async with db.execute(
            """SELECT DISTINCT step_number FROM step_feedback
               WHERE user_id = ? AND feedback_type = 'completed'
               AND created_at >= ?
               ORDER BY step_number""",
            (user_id, route_started)
        ) as cursor:
            rows = await cursor.fetchall()
            return [r["step_number"] for r in rows]


async def get_user_stats(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT created_at, routes_count FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            user = await cursor.fetchone()

        async with db.execute(
            "SELECT COUNT(DISTINCT step_number) AS c FROM step_feedback WHERE user_id = ? AND feedback_type = 'completed'",
            (user_id,)
        ) as cursor:
            total_completed = (await cursor.fetchone())["c"] or 0

        async with db.execute(
            "SELECT COUNT(*) AS c FROM step_feedback WHERE user_id = ?", (user_id,)
        ) as cursor:
            total_feedback = (await cursor.fetchone())["c"] or 0

        completed_now = await get_completed_steps(user_id)

        return {
            "joined": user["created_at"] if user else None,
            "routes_count": (user["routes_count"] if user else 0) or 0,
            "lifetime_completed": total_completed,
            "current_completed": len(completed_now),
            "feedback_given": total_feedback,
        }
