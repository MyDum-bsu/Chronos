from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu() -> InlineKeyboardMarkup:
    """Create main menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(text="📋 Сегодня", callback_data="show_today"),
            InlineKeyboardButton(text="➕ Новая задача", callback_data="new_task"),
        ],
        [
            InlineKeyboardButton(text="✅ Завершить", callback_data="complete_task"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
