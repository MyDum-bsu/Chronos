import html
import re
from aiogram import types, F
from typing import TypeGuard
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
    MaybeInaccessibleMessageUnion,
)

from agent.core import process_message, vector_memory
from agent.tools import (
    get_today_tasks,
    complete_task,
    get_task_stats as get_stats_tool,
)
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


async def cmd_stats(message: types.Message) -> None:
    """Handle /stats command - show task statistics."""
    if not message.from_user:
        await message.answer("I apologize, but I couldn't identify you. Please start the bot with /start.")
        return

    user_id = message.from_user.id
    try:
        stats = await get_stats_tool(user_id)
        
        response = "📊 Ваша статистика:\n\n"
        response += f"📋 Всего задач: {stats.get('total', 0)}\n"
        response += f"✅ Завершено: {stats.get('completed', 0)}\n"
        response += f"⏳ Активных: {stats.get('active', 0)}\n"
        response += f"❗ Просрочено: {stats.get('overdue', 0)}\n"
        response += f"📅 На сегодня: {stats.get('today', 0)}\n"
        
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


async def cmd_help(message: types.Message) -> None:
    """Handle /help command."""
    help_text = (
        "🔧 Доступные команды:\n\n"
        "/start - Приветствие и представление\n"
        "/tasks - Показать задачи на сегодня\n"
        "/complete - Отметить задачу как выполненной\n"
        "/stats - Показать подробную статистику\n"
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
    
    # Check for name introduction patterns and save with type="user_name"
    name_pattern = re.compile(r'меня зовут\s+(\w+)|зовут\s+(\w+)|имя\s+(\w+)|обращайся\s+ко\s+мне\s+(\w+)|меня\s+(\w+)', re.IGNORECASE)
    name_match = name_pattern.search(user_text)
    if name_match:
        name = next((g for g in name_match.groups() if g), None)
        if name:
            try:
                await vector_memory.remember(
                    user_id=user_id,
                    text=f"Пользователь зовется {name}",
                    metadata={"role": "user", "type": "user_name"}
                )
            except Exception:
                pass
    
    # Save user message to vector memory before processing
    try:
        await vector_memory.remember(
            user_id=user_id,
            text=user_text,
            metadata={"role": "user"}
        )
    except Exception:
        pass  # Don't fail if memory save fails
    
    # Recall user_name memory if exists
    user_name_info = ""
    try:
        memories = await vector_memory.recall(user_id, "имя пользователь", n_results=3)
        for mem in memories:
            if isinstance(mem, dict):
                metadata = mem.get("metadata", {})
                if metadata.get("type") == "user_name":
                    user_name_info = f" (имя пользователя: {mem.get('text', '').replace('Пользователь зовется ', '')})"
                    break
    except Exception:
        pass  # Don't fail if recall fails
    
    # Prepend user name context to message if available
    enhanced_text = user_text
    if user_name_info:
        enhanced_text = f"[Контекст: {user_name_info}] {user_text}"
    
    # Show typing status while processing (only if bot is available)
    if message.bot:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        response = await process_message(user_id, enhanced_text)
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


async def callback_new_task(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle 'new_task' callback from main menu - start FSM."""
    if not callback.from_user:
        await callback.answer("Cannot identify user.")
        return
    
    await callback.answer()
    await state.set_state(CreateTaskState.waiting_for_title)
    
    text = "📝 Введи название задачи:\n\nДля отмены в любой момент отправь /cancel"
    
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
        stats = await get_stats_tool(user_id)
        
        response = "📊 Ваша статистика:\n\n"
        response += f"📋 Всего задач: {stats.get('total', 0)}\n"
        response += f"✅ Завершено: {stats.get('completed', 0)}\n"
        response += f"⏳ Активных: {stats.get('active', 0)}\n"
        response += f"❗ Просрочено: {stats.get('overdue', 0)}\n"
        response += f"📅 На сегодня: {stats.get('today', 0)}\n"
        
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




# FSM handlers for creating tasks step by step
from bot.fsm import CreateTaskState
from agent.tools import add_task as add_task_tool


async def cmd_new_task_start(message: types.Message, state: FSMContext) -> None:
    """Handle /newtask command or '➕ Новая задача' button - start FSM."""
    if not message.from_user:
        await message.answer("I apologize, but I couldn't identify you. Please start the bot with /start.")
        return
    
    await state.set_state(CreateTaskState.waiting_for_title)
    await message.answer(
        "📝 Введи название задачи:\n\nДля отмены в любой момент отправь /cancel",
        reply_markup=types.ReplyKeyboardRemove()
    )


async def process_title(message: types.Message, state: FSMContext) -> None:
    """Process task title and move to description input."""
    if not message.from_user:
        await message.answer("I apologize, but I couldn't identify you. Please start the bot with /start.")
        return
    
    if not message.text:
        await message.answer("Пожалуйста, введи название задачи.")
        return
    
    await state.update_data(title=message.text.strip())
    await state.set_state(CreateTaskState.waiting_for_description)
    await message.answer(
        "📝 Теперь введи описание задачи (или отправь '-' если нет описания):"
    )


async def process_description(message: types.Message, state: FSMContext) -> None:
    """Process task description and move to deadline input."""
    if not message.from_user:
        await message.answer("I apologize, but I couldn't identify you. Please start the bot with /start.")
        return
    
    if not message.text:
        await message.answer("Пожалуйста, введи описание задачи.")
        return
    
    description = message.text.strip()
    if description == '-':
        description = None
    await state.update_data(description=description)
    await state.set_state(CreateTaskState.waiting_for_deadline)
    await message.answer(
        "📅 Введи дедлайн в формате 'ГГГГ-ММ-ДД ЧЧ:ММ:СС' (например, 2026-05-01 18:00:00) "
        "или отправь '-' если дедлайн не нужен:"
    )


async def process_deadline(message: types.Message, state: FSMContext) -> None:
    """Process task deadline and create the task."""
    if not message.from_user:
        await message.answer("I apologize, but I couldn't identify you. Please start the bot with /start.")
        return
    
    user_id = message.from_user.id
    data = await state.get_data()
    title = data.get('title')
    description = data.get('description')
    
    if not message.text:
        await message.answer("Пожалуйста, введи дедлайн.")
        return
    
    if title is None:
        await message.answer("Ошибка: название задачи не найдено. Начните заново с /newtask")
        await state.clear()
        return
    
    # At this point, title is guaranteed to be a string from FSM state
    assert title is not None  # for type checker
    
    deadline_str = message.text.strip()
    
    # Parse deadline
    deadline = None
    if deadline_str != '-':
        try:
            from datetime import datetime
            deadline = datetime.fromisoformat(deadline_str.replace(' ', 'T'))
        except ValueError:
            await message.answer(
                "❌ Неверный формат даты. Использи 'ГГГГ-ММ-ДД ЧЧ:ММ:СС' (например, 2026-05-01 18:00:00)"
            )
            return
    
    # Create task using the tool
    try:
        result = await add_task_tool(
            user_id=user_id,
            title=title,
            description=description,
            deadline=deadline
        )
        
        if "task_id" in result:
            await message.answer(
                f"✅ Задача успешно создана!\n"
                f"ID: {result['task_id']}\n"
                f"Название: {result['title']}",
                reply_markup=get_main_menu()
            )
        else:
            await message.answer(
                f"❌ Ошибка при создании задачи: {result.get('error', 'Неизвестная ошибка')}",
                reply_markup=get_main_menu()
            )
    except Exception as e:
        await message.answer(
            f"❌ Произошла ошибка при создании задачи: {str(e)}",
            reply_markup=get_main_menu()
        )
    
    # Clear state
    await state.clear()


async def cmd_cancel(message: types.Message, state: FSMContext) -> None:
    """Handle /cancel command - exit FSM."""
    if not message.from_user:
        await message.answer("I apologize, but I couldn't identify you. Please start the bot with /start.")
        return
    
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активных операций для отмены.", reply_markup=get_main_menu())
        return
    
    await state.clear()
    await message.answer("❌ Операция отменена.", reply_markup=get_main_menu())


async def callback_priorities(callback: CallbackQuery) -> None:
    """Handle 'priorities' callback from main menu."""
    if not callback.from_user:
        await callback.answer("Cannot identify user.")
        return
    
    user_id = callback.from_user.id
    await callback.answer("Анализирую приоритеты задач...")
    
    try:
        from agent.tools import prioritize_tasks
        result = await prioritize_tasks(user_id)
        
        if result["count"] == 0:
            text = "📭 У вас пока нет задач для приоритизации."
        else:
            text = f"🎯 Приоритизация задач ({result['count']} задач):\n\n"
            text += result.get("prioritization", "Приоритизация недоступна")
            if result.get("reasoning"):
                text += f"\n\n💡 Обоснование: {result['reasoning']}"
        
        if _message_is_editable(callback.message):
            await callback.message.edit_text(text, reply_markup=get_main_menu())
        else:
            await callback.answer(text, show_alert=True)
            
    except Exception as e:
        error_text = "❌ Произошла ошибка при приоритизации задач."
        if _message_is_editable(callback.message):
            await callback.message.edit_text(error_text, reply_markup=get_main_menu())
        else:
            await callback.answer(error_text, show_alert=True)
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
    dp.message.register(cmd_stats, Command("stats"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_new_task_start, Command("newtask"))
    dp.message.register(cmd_new_task_start, F.text == "➕ Новая задача")
    dp.message.register(cmd_cancel, Command("cancel"))
    dp.message.register(handle_text_message, F.text)
    
    # FSM handlers for task creation
    dp.message.register(process_title, CreateTaskState.waiting_for_title)
    dp.message.register(process_description, CreateTaskState.waiting_for_description)
    dp.message.register(process_deadline, CreateTaskState.waiting_for_deadline)
    
    # Callback query handlers
    dp.callback_query.register(callback_show_today, F.data == "show_today")
    dp.callback_query.register(callback_new_task, F.data == "new_task")
    dp.callback_query.register(callback_complete_task, F.data == "complete_task")
    dp.callback_query.register(callback_stats, F.data == "stats")
    dp.callback_query.register(callback_priorities, F.data == "priorities")
    dp.callback_query.register(callback_complete_specific, F.data.startswith("comp_"))
