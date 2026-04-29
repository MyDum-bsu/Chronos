import asyncio
from datetime import datetime, date, timedelta
from typing import Optional, List, Sequence, AsyncIterator
from contextlib import asynccontextmanager

from sqlmodel import SQLModel, Field, select, func
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession


class Task(SQLModel, table=True):
    """Task model for storing user tasks."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    title: str
    description: Optional[str] = Field(default=None)
    deadline: Optional[datetime] = Field(default=None)
    is_completed: bool = Field(default=False)
    # Reminder settings
    remind: bool = Field(default=True, description="Whether to send reminders for this task")
    reminded: bool = Field(default=False, description="Whether reminder has been sent")


# Database URL for SQLite async
DATABASE_URL = "sqlite+aiosqlite:///chronos.db"


# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True, future=True)


async def init_db() -> None:
    """Initialize database and create tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Async context manager for database sessions."""
    async with AsyncSession(engine) as session:
        yield session


# CRUD operations

async def create_task(
    user_id: int,
    title: str,
    description: Optional[str] = None,
    deadline: Optional[datetime] = None,
) -> Task:
    """Create a new task."""
    task = Task(
        user_id=user_id,
        title=title,
        description=description,
        deadline=deadline,
        is_completed=False,
        remind=True,
        reminded=False,
    )
    async with get_session() as session:
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task


async def get_tasks_by_user(user_id: int) -> List[Task]:
    """Get all tasks for a specific user."""
    async with get_session() as session:
        statement = select(Task).where(Task.user_id == user_id)
        result = await session.exec(statement)
        return list(result.all())


async def get_tasks_today(user_id: int) -> List[Task]:
    """Get tasks due today for a specific user."""
    today = date.today()
    async with get_session() as session:
        statement = select(Task).where(
            Task.user_id == user_id,
            Task.deadline != None,
            Task.is_completed == False,
        )
        result = await session.exec(statement)
        tasks = result.all()
        # Filter tasks due today
        return [
            task for task in tasks
            if task.deadline and task.deadline.date() == today
        ]


async def get_task_by_id(task_id: int) -> Optional[Task]:
    """Get a single task by ID."""
    async with get_session() as session:
        return await session.get(Task, task_id)


async def update_task_in_db(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    deadline: Optional[datetime] = None,
) -> Optional[Task]:
    """Update task fields."""
    async with get_session() as session:
        task = await session.get(Task, task_id)
        if not task:
            return None
        
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if deadline is not None:
            task.deadline = deadline
        
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task


async def update_task_status(task_id: int, is_completed: bool) -> Optional[Task]:
    """Update task completion status."""
    async with get_session() as session:
        task = await session.get(Task, task_id)
        if task:
            task.is_completed = is_completed
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return task
        return None


async def delete_task(task_id: int) -> bool:
    """Delete a task by ID."""
    async with get_session() as session:
        task = await session.get(Task, task_id)
        if task:
            await session.delete(task)
            await session.commit()
            return True
        return False


async def get_incomplete_tasks(user_id: int) -> List[Task]:
    """Get all incomplete tasks for a user."""
    async with get_session() as session:
        statement = select(Task).where(
            Task.user_id == user_id,
            Task.is_completed == False,
        )
        result = await session.exec(statement)
        return list(result.all())


async def get_all_incomplete_tasks() -> List[Task]:
    """Get all incomplete tasks across all users with deadline set."""
    async with get_session() as session:
        statement = select(Task).where(
            Task.is_completed == False,
            Task.deadline != None,
        )
        result = await session.exec(statement)
        return list(result.all())


async def search_tasks(user_id: int, query: str) -> List[Task]:
    """Search tasks by title/description text (case-insensitive partial match)."""
    async with get_session() as session:
        search_pattern = f"%{query}%"
        statement = select(Task).where(
            Task.user_id == user_id,
            func.lower(Task.title).like(func.lower(search_pattern)) |
            func.lower(Task.description).like(func.lower(search_pattern))
        )
        result = await session.exec(statement)
        return list(result.all())


async def get_due_reminders() -> List[Task]:
    """
    Get tasks due for reminder notification.
    
    Returns tasks where:
    - remind == True
    - reminded == False
    - deadline <= now() (due now or past)
    - deadline > now() - timedelta(minutes=2) (within the last 2 minutes)
    """
    now = datetime.now()
    window_start = now - timedelta(minutes=2)
    
    async with get_session() as session:
        statement = select(Task).where(
            Task.remind == True,
            Task.reminded == False,
            Task.is_completed == False,
            Task.deadline != None,
            Task.deadline <= now,
            Task.deadline > window_start,
        )
        result = await session.exec(statement)
        return list(result.all())


async def mark_reminded(task_id: int) -> bool:
    """Mark a task as having sent its reminder."""
    async with get_session() as session:
        task = await session.get(Task, task_id)
        if task:
            task.reminded = True
            session.add(task)
            await session.commit()
            return True
        return False


async def get_task_stats(user_id: int) -> dict:
    """Get detailed task statistics for a user including overdue count."""
    tasks = await get_tasks_by_user(user_id)
    incomplete = await get_incomplete_tasks(user_id)
    today_tasks = await get_tasks_today(user_id)
    
    # Count overdue tasks (incomplete with deadline in the past)
    now = datetime.now()
    overdue_count = sum(
        1 for task in incomplete
        if task.deadline and task.deadline < now
    )
    
    return {
        "total": len(tasks),
        "completed": len(tasks) - len(incomplete),
        "active": len(incomplete),
        "overdue": overdue_count,
        "today": len(today_tasks),
    }


if __name__ == "__main__":
    asyncio.run(init_db())
    print("Database initialized")
