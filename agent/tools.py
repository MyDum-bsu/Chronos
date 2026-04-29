import asyncio
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from memory.db import (
    create_task,
    get_tasks_today,
    update_task_status,
    get_task_by_id,
    get_incomplete_tasks,
    get_tasks_by_user,
)
from memory.vector import get_vector_memory


class CurrentTimeResponse(BaseModel):
    """Response model for current time."""
    current_time: str = Field(..., description="Current date and time in ISO format")


class AddTaskInput(BaseModel):
    """Input model for adding a task."""
    user_id: int = Field(..., gt=0, description="Telegram user ID")
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, max_length=1000, description="Task description")
    deadline: Optional[datetime] = Field(None, description="Task deadline (optional)")


class AddTaskResponse(BaseModel):
    """Response model for adding a task."""
    task_id: int = Field(..., description="ID of created task")
    title: str = Field(..., description="Task title")
    user_id: int = Field(..., description="User ID")
    deadline: Optional[datetime] = Field(None, description="Task deadline")


class GetTasksTodayResponse(BaseModel):
    """Response model for getting today's tasks."""
    tasks: list[AddTaskResponse] = Field(default_factory=list, description="List of tasks due today")
    count: int = Field(..., description="Number of tasks due today")


class CompleteTaskInput(BaseModel):
    """Input model for completing a task."""
    task_id: int = Field(..., gt=0, description="ID of the task to mark as completed")


class CompleteTaskResponse(BaseModel):
    """Response model for completing a task."""
    task_id: int = Field(..., description="ID of the completed task")
    is_completed: bool = Field(..., description="Whether task is marked as completed")
    success: bool = Field(..., description="Whether operation succeeded")


async def get_time(timezone: str = "UTC") -> str:
    """
    Get the current date and time.
    
    Args:
        timezone: Timezone identifier (e.g., 'UTC', 'Europe/Moscow', 'America/New_York').
    
    Returns:
        Current date and time in ISO format (YYYY-MM-DD HH:MM:SS).
        
    Example:
        >>> await get_time()
        '2026-04-28 12:30:05'
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def add_task(
    user_id: int,
    title: str,
    description: Optional[str] = None,
    deadline: Optional[datetime] = None,
) -> dict:
    """
    Create a new task for a user.
    
    Args:
        user_id: Telegram user ID
        title: Task title (required)
        description: Detailed task description (optional)
        deadline: Task deadline as datetime object (optional)
    
    Returns:
        Dictionary with task_id, title, user_id, and deadline.
    
    Example:
        >>> await add_task(123, "Buy groceries", "Milk, eggs, bread")
        {"task_id": 1, "title": "Buy groceries", "user_id": 123, "deadline": null}
    """
    task = await create_task(
        user_id=user_id,
        title=title,
        description=description,
        deadline=deadline,
    )
    return {
        "task_id": task.id,
        "title": task.title,
        "user_id": task.user_id,
        "deadline": task.deadline,
    }


async def get_today_tasks(user_id: int, timezone: str = "UTC") -> dict:
    """
    Get all tasks due today for a specific user.
    
    Args:
        user_id: Telegram user ID
        timezone: Timezone identifier for date calculation (default: UTC)
    
    Returns:
        Dictionary with list of tasks and count.
    
    Example:
        >>> await get_today_tasks(123)
        {"tasks": [{"task_id": 1, "title": "Meeting", ...}], "count": 1}
    """
    tasks = await get_tasks_today(user_id)
    return {
        "tasks": [
            {
                "task_id": t.id,
                "title": t.title,
                "description": t.description,
                "deadline": t.deadline,
                "is_completed": t.is_completed,
            }
            for t in tasks
        ],
        "count": len(tasks),
    }


async def complete_task(task_id: int, timezone: str = "UTC") -> dict:
    """
    Mark a task as completed.
    
    Args:
        task_id: ID of the task to mark as completed
        timezone: Timezone identifier (unused, for tool signature compatibility)
    
    Returns:
        Dictionary with task_id, is_completed status, and success flag.
    
    Example:
        >>> await complete_task(1)
        {"task_id": 1, "is_completed": true, "success": true}
    """
    task = await update_task_status(task_id, is_completed=True)
    if task:
        return {
            "task_id": task.id,
            "is_completed": task.is_completed,
            "success": True,
        }
    return {
        "task_id": task_id,
        "is_completed": False,
        "success": False,
    }


async def get_task_stats(user_id: int) -> dict:
    """
    Get task statistics for a user.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        Dictionary with total, completed, incomplete, and today's task counts.
    
    Example:
        >>> await get_task_stats(123)
        {"total": 5, "completed": 2, "incomplete": 3, "today": 1}
    """
    all_tasks = await get_tasks_by_user(user_id)
    incomplete = await get_incomplete_tasks(user_id)
    today_tasks = await get_tasks_today(user_id)
    
    return {
        "total": len(all_tasks),
        "completed": len(all_tasks) - len(incomplete),
        "incomplete": len(incomplete),
        "today": len(today_tasks),
    }


async def recall_user_preferences(user_id: int, query: Optional[str] = None) -> list[str]:
    """
    Recall relevant user preferences and past context from memory.
    
    Args:
        user_id: Telegram user ID
        query: Optional search query. If None, returns recent memories using empty query.
    
    Returns:
        List of relevant memory strings sorted by relevance. Empty list if no memories found.
    """
    try:
        vm = get_vector_memory()
        # If query is None, use empty string to get recent memories
        search_query = query if query else ""
        memories = vm.recall(user_id=user_id, query=search_query, n_results=5)
        return memories if memories else []
    except Exception:
        return []


if __name__ == "__main__":
    async def test():
        from memory.db import init_db
        
        await init_db()
        print("DB initialized")
        
        time = await get_time()
        print(f"Current time: {time}")
        
        task = await add_task(1, "Test task", "Test desc")
        print(f"Added task: {task}")
        
        tasks = await get_today_tasks(1)
        print(f"Today's tasks: {tasks}")
        
        completed = await complete_task(task["task_id"])
        print(f"Completed: {completed}")
        
        stats = await get_task_stats(1)
        print(f"Stats: {stats}")
    
    asyncio.run(test())
