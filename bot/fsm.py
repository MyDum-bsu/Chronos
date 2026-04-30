from aiogram.fsm.state import State, StatesGroup


class CreateTaskState(StatesGroup):
    """FSM states for creating a task step by step."""
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_deadline = State()
