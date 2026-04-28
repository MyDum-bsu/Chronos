import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from dotenv import load_dotenv

from bot.handlers import register_handlers
from memory.db import init_db

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main entry point for the bot."""
    # Initialize database first
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully")
    
    # Get bot token from environment
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN or BOT_TOKEN environment variable is not set")
        return
    
    # Initialize bot with default properties
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Register handlers
    register_handlers(dp)
    
    # Start polling
    logger.info("Starting Chronos bot...")
    try:
        await dp.start_polling(bot, skip_updates=True)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
