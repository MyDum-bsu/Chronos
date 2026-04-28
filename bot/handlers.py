import asyncio
from aiogram import types
from aiogram.filters import Command
from aiogram.enums import ContentType

from agent.core import process_message


async def cmd_start(message: types.Message) -> None:
    """Handle /start command."""
    await message.answer(
        "Bonjour. I am Chronos, your personal butler-planner.\n"
        "I help manage tasks, schedule appointments, and organize your time.\n"
        "How may I assist you today?"
    )


async def handle_text_message(message: types.Message) -> None:
    """Handle any text message from user."""
    # Ensure message has from_user
    if not message.from_user:
        await message.answer("I apologize, but I couldn't identify you. Please start the bot with /start.")
        return
    
    user_id = message.from_user.id
    user_text = message.text
    
    if not user_text:
        return
    
    # Show typing status while processing
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        response = await process_message(user_id, user_text)
        await message.answer(response)
    except Exception as e:
        # Log error and send friendly message
        await message.answer(
            "I apologize, but I encountered an issue processing your request. "
            "Please try again later."
        )
        # Re-raise for logging
        raise


def register_handlers(dp) -> None:
    """
    Register all handlers to the dispatcher.
    
    Args:
        dp: Aiogram Dispatcher instance
    """
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(handle_text_message, content_type=ContentType.TEXT)
