import html
from typing import TypeGuard
from aiogram import types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
    MaybeInaccessibleMessageUnion,
)

from agent.core import process_message, vector_memory
from agent.tools import get_today_tasks, complete_task, get_task_stats
from memory.db import get_incomplete_tasks, get_task_by_id
from bot.keyboards import get_main_menu


async def cmd_start(message: types.Message) -> None:
    """Handle /start command."""
    if not message.from_user:
        await message.answer("I apologize, but I couldn't identify you. Please start the bot with /start.")
        return

    await message.answer(
        "👋 Привет! Я твой умный планировщик.",
        reply_markup=get_main_menu()
    )


async def cmd_tasks(message: types.Message) -> None:
    """Handle /tasks command - show today's tasks."""
    if not message.from_user:
        await message.answer("I apologize, but I couldn't identify you. Please start the bot with /start.")
        return

    user_id = message.from_user.id
    try:
        result = await get_today_tasks(user_id)
        tasks = result.get("tasks", [])
        count = result.get("count", 0)

        if count == 0:
            await message.answer(
                "У вас нет задач на сегодня.",
                reply_markup=get_main_menu()
            )
            return

        response = f"📋 Ваши задачи на сегодня ({count}):\n\n"
        for task in tasks:
            status = "✅" if task.get("is_completed") else "⏳"
            response += f"{status} {task['title']}\n"
            if task.get("description"):
                response += f"   {task['description']}\n"
            if task.get("deadline"):
                response += f"   ⏰ {task['deadline']}\n"
            response += "\n"

        await message.answer(
            response,
            reply_markup=get_main_menu()
        )
    except Exception:
        await message.answer(
            "I apologize, but I encountered an issue processing your request. "
            "Please try again later.",
            reply_markup=get_main_menu()
        )
        raise


async def cmd_complete(message: types.Message) -> None:
    """Handle /complete command - show incomplete tasks with completion buttons."""
    if not message.from_user:
        await message.answer("I apologize, but I couldn't identify you. Please start the bot with /start.")
        return

    user_id = message.from_user.id
    try:
        tasks = await get_incomplete_tasks(user_id)
        if not tasks:
            await message.answer(
                "Все задачи выполнены! 🎉",
                reply_markup=get_main_menu()
            )
            return

        # Build keyboard with inline buttons for each task
        keyboard = []
        for task in tasks:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"✅ {task.title}",
                    callback_data=f"comp_{task.id}"
                )
            ])

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer(
            "Выберите задачу для отметки как выполненной:",
            reply_markup=reply_markup
        )
    except Exception:
        await message.answer(
            "I apologize, but I encountered an issue processing your request. "
            "Please try again later.",
            reply_markup=get_main_menu()
        )
        raise


async def cmd_help(message: types.Message) -> None:
    """Handle /help command."""
    help_text = (
        "🔧 Доступные команды:\n\n"
        "/start - Приветствие и представление\n"
        "/tasks - Показать задачи на сегодня\n"
        "/complete - Отметить задачу как выполненную\n"
        "/help - Показать эту справку\n\n"
        "Вы также можете просто писать мне сообщения, и я помогу вам управлять задачами и временем."
    )
    await message.answer(
        help_text,
        reply_markup=get_main_menu()
    )


async def handle_text_message(message: types.Message) -> None:
    """Handle any text message from user (non-command)."""
    if not message.from_user:
        await message.answer("I apologize, but I couldn't identify you. Please start the bot with /start.")
        return
    
    user_id = message.from_user.id
    user_text = message.text
    
    if not user_text:
        return
    
    # Save user message to vector memory before processing
    try:
        await vector_memory.remember(
            user_id=user_id,
            text=user_text,
            metadata={"role": "user"}
        )
    except Exception:
        pass  # Don't fail if memory save fails
    
    # Show typing status while processing (only if bot is available)
    if message.bot:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        response = await process_message(user_id, user_text)
        # Escape HTML to prevent Telegram parsing errors if model outputs raw tags
        safe_response = html.escape(response)
        await message.answer(
            safe_response,
            reply_markup=get_main_menu()
        )
    except Exception:
        # Log error and send friendly message
        await message.answer(
            "I apologize, but I encountered an issue processing your request. "
            "Please try again later.",
            reply_markup=get_main_menu()
        )
        # Re-raise for logging
        raise


def _message_is_editable(message: MaybeInaccessibleMessageUnion | None) -> TypeGuard[Message]:
    """Type guard to check if message is a real Message (not InaccessibleMessage or None)."""
    return isinstance(message, Message)


# Callback query handlers

async def callback_show_today(callback: CallbackQuery) -> None:
    """Handle 'show_today' callback from main menu."""
    if not callback.from_user:
        await callback.answer("Cannot identify user.")
        return
    
    user_id = callback.from_user.id
    await callback.answer()
    
    try:
        result = await get_today_tasks(user_id)
        tasks = result.get("tasks", [])
        count = result.get("count", 0)

        if count == 0:
            text = "Сегодня задач нет"
            if _message_is_editable(callback.message):
                await callback.message.edit_text(text, reply_markup=get_main_menu())
            else:
                await callback.answer(text, show_alert=True)
            return

        response = f"📋 Ваши задачи на сегодня ({count}):\n\n"
        for task in tasks:
            status = "✅" if task.get("is_completed") else "⏳"
            response += f"{status} {task['title']}\n"
            if task.get("description"):
                response += f"   {task['description']}\n"
            if task.get("deadline"):
                response += f"   ⏰ {task['deadline']}\n"
            response += "\n"

        if _message_is_editable(callback.message):
            await callback.message.edit_text(response, reply_markup=get_main_menu())
        else:
            await callback.answer(response, show_alert=True)
    except Exception:
        try:
            error_text = "I apologize, but I encountered an issue processing your request. Please try again later."
            if _message_is_editable(callback.message):
                await callback.message.edit_text(error_text, reply_markup=get_main_menu())
            else:
                await callback.answer(error_text, show_alert=True)
        except Exception:
            await callback.answer("Error occurred. Please try again.")
        raise


async def callback_new_task(callback: CallbackQuery) -> None:
    """Handle 'new_task' callback from main menu."""
    if not callback.from_user:
        await callback.answer("Cannot identify user.")
        return
    
    await callback.answer()
    text = "📝 Введи название задачи и время в свободной форме, например:\nКупить молоко завтра в 18:00\n\nИли просто напиши, что нужно сделать — я сам распределю время."
    
    if _message_is_editable(callback.message):
        await callback.message.edit_text(text, reply_markup=get_main_menu())
    else:
        await callback.answer(text, show_alert=True)


async def callback_complete_task(callback: CallbackQuery) -> None:
    """Handle 'complete_task' callback from main menu."""
    if not callback.from_user:
        await callback.answer("Cannot identify user.")
        return
    
    user_id = callback.from_user.id
    await callback.answer()
    
    try:
        tasks = await get_incomplete_tasks(user_id)
        if not tasks:
            text = "Нет активных задач. Все задачи выполнены! 🎉"
            if _message_is_editable(callback.message):
                await callback.message.edit_text(text, reply_markup=get_main_menu())
            else:
                await callback.answer(text, show_alert=True)
            return

        # Build keyboard with inline buttons for each task
        keyboard = []
        for task in tasks:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"✅ {task.title}",
                    callback_data=f"comp_{task.id}"
                )
            ])

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        response_text = "Выберите задачу для отметки как выполненной:"
        
        if _message_is_editable(callback.message):
            await callback.message.edit_text(response_text, reply_markup=reply_markup)
        else:
            await callback.answer(response_text, show_alert=True)
    except Exception:
        try:
            error_text = "I apologize, but I encountered an issue processing your request. Please try again later."
            if _message_is_editable(callback.message):
                await callback.message.edit_text(error_text, reply_markup=get_main_menu())
            else:
                await callback.answer(error_text, show_alert=True)
        except Exception:
            await callback.answer("Error occurred. Please try again.")
        raise


async def callback_stats(callback: CallbackQuery) -> None:
    """Handle 'stats' callback from main menu."""
    if not callback.from_user:
        await callback.answer("Cannot identify user.")
        return
    
    user_id = callback.from_user.id
    await callback.answer()
    
    try:
        stats = await get_task_stats(user_id)
        
        response = "📊 Ваша статистика:\n\n"
        response += f"📋 Всего задач: {stats['total']}\n"
        response += f"✅ Завершено: {stats['completed']}\n"
        response += f"⏳ Активных: {stats['incomplete']}\n"
        response += f"📅 На сегодня: {stats['today']}\n"
        
        if _message_is_editable(callback.message):
            await callback.message.edit_text(response, reply_markup=get_main_menu())
        else:
            await callback.answer(response, show_alert=True)
    except Exception:
        try:
            error_text = "I apologize, but I encountered an issue processing your request. Please try again later."
            if _message_is_editable(callback.message):
                await callback.message.edit_text(error_text, reply_markup=get_main_menu())
            else:
                await callback.answer(error_text, show_alert=True)
        except Exception:
            await callback.answer("Error occurred. Please try again.")
        raise


async def callback_complete_specific(callback: CallbackQuery) -> None:
    """Handle completion of a specific task (callback_data starts with 'comp_')."""
    if not callback.from_user:
        await callback.answer("Cannot identify user.")
        return
    
    # Extract task_id from callback_data (format: "comp_<task_id>")
    data = callback.data
    if not data or not data.startswith("comp_"):
        await callback.answer("Invalid callback data.")
        return
    
    try:
        task_id = int(data.split("_", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Invalid task ID.")
        return
    
    await callback.answer()
    
    try:
        result = await complete_task(task_id)
        if result.get("success"):
            text = "✅ Задача отмечена выполненной!"
            if _message_is_editable(callback.message):
                await callback.message.edit_text(text, reply_markup=get_main_menu())
            else:
                await callback.answer(text, show_alert=True)
        else:
            text = "❌ Не удалось отметить задачу. Возможно, она уже выполнена или не существует."
            if _message_is_editable(callback.message):
                await callback.message.edit_text(text, reply_markup=get_main_menu())
            else:
                await callback.answer(text, show_alert=True)
    except Exception:
        try:
            error_text = "I apologize, but I encountered an issue processing your request. Please try again later."
            if _message_is_editable(callback.message):
                await callback.message.edit_text(error_text, reply_markup=get_main_menu())
            else:
                await callback.answer(error_text, show_alert=True)
        except Exception:
            await callback.answer("Error occurred. Please try again.")
        raise


def register_handlers(dp) -> None:
    """
    Register all handlers to the dispatcher.
    
    Args:
        dp: Aiogram Dispatcher instance
    """
    # Message handlers
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_tasks, Command("tasks"))
    dp.message.register(cmd_complete, Command("complete"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(handle_text_message, F.text)
    
    # Callback query handlers
    dp.callback_query.register(callback_show_today, F.data == "show_today")
    dp.callback_query.register(callback_new_task, F.data == "new_task")
    dp.callback_query.register(callback_complete_task, F.data == "complete_task")
    dp.callback_query.register(callback_stats, F.data == "stats")
    dp.callback_query.register(callback_complete_specific, F.data.startswith("comp_"))
