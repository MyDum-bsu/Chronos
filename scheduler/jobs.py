from datetime import datetime, timedelta
from typing import Callable, Awaitable

from aiogram import Bot

from memory.db import get_all_incomplete_tasks


def create_reminder_job(bot: Bot) -> Callable[[], Awaitable[None]]:
    """
    Create a reminder job function that checks deadlines and sends notifications.
    
    Args:
        bot: Aiogram Bot instance for sending messages
        
    Returns:
        Async callable that can be scheduled
    """
    async def check_deadlines() -> None:
        """Check upcoming deadlines and send reminders to users."""
        try:
            now = datetime.now()
            # Get all incomplete tasks with deadline set
            tasks = await get_all_incomplete_tasks()
            
            for task in tasks:
                try:
                    # Skip if no deadline
                    if not task.deadline:
                        continue
                    
                    # Calculate time difference
                    time_diff = task.deadline - now
                    
                    # Send reminder if deadline is within 15 minutes from now
                    # and not in the past (avoid re-sending for past minutes)
                    if timedelta(0) < time_diff <= timedelta(minutes=15):
                        deadline_str = task.deadline.strftime('%H:%M')
                        message = (
                            f"⏰ Напоминание: задача «{task.title}» "
                            f"начинается в {deadline_str}"
                        )
                        await bot.send_message(chat_id=task.user_id, text=message)
                except Exception:
                    # Don't let one failed message stop the whole loop
                    continue
        except Exception:
            # Log error but don't raise - scheduler should keep running
            pass
    
    return check_deadlines
