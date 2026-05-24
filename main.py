"""
Progressors Bot — entry point.
Run: python main.py
"""
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import feedback_handler, profile_handler, route_handler, start
from bot.services.database import init_db
from config import BOT_TOKEN, GROQ_API_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in environment (.env or Railway/Render variables)")
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set in environment")

    os.makedirs("data", exist_ok=True)
    await init_db()
    logger.info("Database initialized")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(profile_handler.router)
    dp.include_router(route_handler.router)
    dp.include_router(feedback_handler.router)

    logger.info("Starting polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
