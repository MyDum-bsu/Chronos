import asyncio
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from memory.db import (
    Task,
    get_tasks_today,
    update_task_status,
    get_task_by_id,
    get_incomplete_tasks,
    get_tasks_by_user,
    update_task_in_db,
    delete_task as db_delete_task,
    search_tasks as db_search_tasks,
    get_task_stats as db_get_task_stats,
)
from memory.vector import get_vector_memory


# ============== Input/Output Models ==============

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


class UpdateTaskInput(BaseModel):
    """Input model for updating a task."""
    task_id: int = Field(..., gt=0, description="ID of the task to update")
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="New task title")
    description: Optional[str] = Field(None, max_length=1000, description="New task description")
    deadline: Optional[str] = Field(None, description="New deadline in ISO format (YYYY-MM-DD HH:MM:SS)")


class UpdateTaskResponse(BaseModel):
    """Response model for updating a task."""
    success: bool = Field(..., description="Whether update succeeded")
    task: Optional[dict] = Field(None, description="Updated task data")
    error: Optional[str] = Field(None, description="Error message if failed")


class DeleteTaskInput(BaseModel):
    """Input model for deleting a task."""
    task_id: int = Field(..., gt=0, description="ID of the task to delete")


class DeleteTaskResponse(BaseModel):
    """Response model for deleting a task."""
    success: bool = Field(..., description="Whether deletion succeeded")
    error: Optional[str] = Field(None, description="Error message if failed")


class SearchTasksInput(BaseModel):
    """Input model for searching tasks."""
    user_id: int = Field(..., gt=0, description="Telegram user ID")
    query: str = Field(..., min_length=1, description="Search query")


class SearchTasksResponse(BaseModel):
    """Response model for searching tasks."""
    tasks: List[dict] = Field(default_factory=list, description="List of matching tasks")


class TaskStatsInput(BaseModel):
    """Input model for getting task statistics."""
    user_id: int = Field(..., gt=0, description="Telegram user ID")


class TaskStatsResponse(BaseModel):
    """Response model for task statistics."""
    total: int = Field(..., description="Total number of tasks")
    active: int = Field(..., description="Number of active (incomplete) tasks")
    completed: int = Field(..., description="Number of completed tasks")
    overdue: int = Field(..., description="Number of overdue tasks")
    today: int = Field(..., description="Number of tasks due today")


class CreateReminderInput(BaseModel):
    """Input model for creating a reminder."""
    user_id: int = Field(..., gt=0, description="Telegram user ID")
    text: str = Field(..., min_length=1, max_length=1000, description="Reminder text (exact message to send)")
    deadline: str = Field(..., description="Reminder time in ISO format (YYYY-MM-DD HH:MM:SS)")


class CreateReminderResponse(BaseModel):
    """Response model for creating a reminder."""
    success: bool = Field(..., description="Whether reminder creation succeeded")
    task_id: int = Field(..., description="ID of created reminder task")
    message: str = Field(..., description="Confirmation message")


class ToggleReminderInput(BaseModel):
    """Input model for toggling reminder on/off."""
    task_id: int = Field(..., gt=0, description="ID of the task to toggle")
    enable: bool = Field(..., description="True to enable reminders, False to disable")


class ToggleReminderResponse(BaseModel):
    """Response model for toggling reminder."""
    success: bool = Field(..., description="Whether toggle succeeded")
    task_id: int = Field(..., description="ID of the task")
    enabled: bool = Field(..., description="Current reminder status")
    message: str = Field(..., description="Confirmation message")


# ============== Core Tools ==============

async def get_time(timezone: str = "UTC") -> str:
    """Get the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def add_task(
    user_id: int,
    title: str,
    description: Optional[str] = None,
    deadline: Optional[datetime] = None,
) -> dict:
    """Create a new task for a user."""
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
    """Get all tasks due today for a specific user."""
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
    """Mark a task as completed."""
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


# ============== New Tools ==============

async def update_task(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    deadline: Optional[str] = None,
) -> UpdateTaskResponse:
    """
    Update an existing task's fields.
    
    Args:
        task_id: ID of the task to update
        title: New title (optional)
        description: New description (optional)
        deadline: New deadline in ISO format (optional)
    
    Returns:
        UpdateTaskResponse with success status and updated task if successful.
    """
    # Parse deadline if provided
    parsed_deadline = None
    if deadline:
        try:
            parsed_deadline = datetime.fromisoformat(deadline.replace(' ', 'T'))
        except ValueError:
            return UpdateTaskResponse(
                success=False,
                task=None,
                error=f"Invalid deadline format. Use YYYY-MM-DD HH:MM:SS"
            )
    
    # Check if at least one field is being updated
    if title is None and description is None and deadline is None:
        return UpdateTaskResponse(
            success=False,
            task=None,
            error="At least one field (title, description, or deadline) must be provided"
        )
    
    # Update in database
    task = await update_task_in_db(
        task_id=task_id,
        title=title,
        description=description,
        deadline=parsed_deadline,
    )
    
    if task:
        return UpdateTaskResponse(
            success=True,
            task={
                "task_id": task.id,
                "user_id": task.user_id,
                "title": task.title,
                "description": task.description,
                "deadline": task.deadline,
                "is_completed": task.is_completed,
            },
            error=None
        )
    else:
        return UpdateTaskResponse(
            success=False,
            task=None,
            error=f"Task with ID {task_id} not found"
        )


async def delete_task(task_id: int) -> DeleteTaskResponse:
    """
    Delete a task by ID.
    
    Args:
        task_id: ID of the task to delete
    
    Returns:
        DeleteTaskResponse with success status.
    """
    success = await db_delete_task(task_id)
    if success:
        return DeleteTaskResponse(success=True, error=None)
    else:
        return DeleteTaskResponse(
            success=False,
            error=f"Task with ID {task_id} not found or could not be deleted"
        )


async def search_tasks(user_id: int, query: str) -> SearchTasksResponse:
    """
    Search tasks by title or description text.
    
    Args:
        user_id: Telegram user ID
        query: Search query string (performs case-insensitive partial match)
    
    Returns:
        SearchTasksResponse with list of matching tasks.
    """
    if not query or not query.strip():
        return SearchTasksResponse(tasks=[])
    
    tasks = await db_search_tasks(user_id, query.strip())
    
    task_dicts = [
        {
            "task_id": t.id,
            "title": t.title,
            "description": t.description,
            "deadline": t.deadline,
            "is_completed": t.is_completed,
        }
        for t in tasks
    ]
    
    return SearchTasksResponse(tasks=task_dicts)


async def get_task_stats(user_id: int) -> dict:
    """
    Get detailed statistics about user's tasks.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        Dictionary with counts: total, active, completed, overdue, today.
    """
    stats = await db_get_task_stats(user_id)
    return {
        "total": stats["total"],
        "active": stats["active"],
        "completed": stats["completed"],
        "overdue": stats["overdue"],
        "today": stats["today"],
    }


async def create_reminder(
    user_id: int,
    text: str,
    deadline: str,
) -> dict:
    """
    Create a reminder that will be sent at the specified time.
    
    Args:
        user_id: Telegram user ID
        text: Exact reminder message to send (will be sent as-is)
        deadline: Reminder time in ISO format (YYYY-MM-DD HH:MM:SS)
    
    Returns:
        Dictionary with task_id and confirmation message.
    """
    # Parse deadline
    try:
        parsed_deadline = datetime.fromisoformat(deadline.replace(' ', 'T'))
    except ValueError:
        return {
            "success": False,
            "task_id": None,
            "message": f"Invalid deadline format. Use YYYY-MM-DD HH:MM:SS",
        }
    
    # Create task with special reminder settings
    # title = text (the reminder message)
    # description = "reminder" (marker for scheduler)
    task = await create_task(
        user_id=user_id,
        title=text,
        description="reminder",
        deadline=parsed_deadline,
    )
    
    # Ensure remind is set (create_task already sets it, but ensuring)
    # Note: We could explicitly set remind=True here if needed
    
    return {
        "success": True,
        "task_id": task.id,
        "message": f"Reminder set for {deadline}",
    }


async def toggle_reminder(task_id: int, enable: bool) -> dict:
    """
    Enable or disable reminders for a specific task.
    
    Args:
        task_id: ID of the task to toggle
        enable: True to enable reminders, False to disable
    
    Returns:
        Dictionary with success status and confirmation message.
    """
    # First, get the task to verify it exists
    task = await get_task_by_id(task_id)
    if not task:
        return {
            "success": False,
            "task_id": task_id,
            "enabled": enable,
            "message": f"Task with ID {task_id} not found"
        }
    
    # Update the remind field using update_task_in_db (we need a new function for just updating remind)
    # For now, use a direct session update
    from memory.db import get_session
    async with get_session() as session:
        task = await session.get(Task, task_id)
        if task:
            task.remind = enable
            session.add(task)
            await session.commit()
            return {
                "success": True,
                "task_id": task_id,
                "enabled": enable,
                "message": f"Reminder {'enabled' if enable else 'disabled'} for task '{task.title}'"
            }
        else:
            return {
                "success": False,
                "task_id": task_id,
                "enabled": enable,
                "message": f"Task with ID {task_id} not found"
            }


async def recall_user_preferences(user_id: int, query: Optional[str] = None) -> list[str]:
    """Recall relevant user preferences from vector memory."""
    try:
        vm = get_vector_memory()
        search_query = query if query else ""
        memories = await vm.recall(user_id=user_id, query=search_query, n_results=5)
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
