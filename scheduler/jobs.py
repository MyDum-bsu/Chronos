from datetime import datetime, timedelta
from typing import Callable, Awaitable

from aiogram import Bot

from memory.db import get_due_reminders, mark_reminded


def create_reminder_job(bot: Bot) -> Callable[[], Awaitable[None]]:
    """
    Create a reminder job function that checks deadlines and sends notifications.
    
    Args:
        bot: Aiogram Bot instance for sending messages
        
    Returns:
        Async callable that can be scheduled
    """
    async def check_deadlines() -> None:
        """Check due reminders and send notifications."""
        try:
            # Get all tasks due for reminders (within 2-minute window, not yet reminded)
            tasks = await get_due_reminders()
            
            for task in tasks:
                try:
                    # Send reminder - just the task title as requested
                    message = f"⏰ {task.title}"
                    await bot.send_message(chat_id=task.user_id, text=message)
                    
                    # Mark as reminded to avoid duplicate notifications
                    await mark_reminded(task.id)
                except Exception:
                    # Don't let one failed message stop the whole loop
                    continue
        except Exception:
            # Log error but don't raise - scheduler should keep running
            pass
    
    return check_deadlines
