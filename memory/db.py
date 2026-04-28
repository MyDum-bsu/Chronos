import asyncio
from datetime import datetime
from typing import Optional, List, Sequence, AsyncIterator
from contextlib import asynccontextmanager

from sqlmodel import SQLModel, Field, select
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
    )
    async with get_session() as session:
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task


async def get_tasks_by_user(user_id: int) -> Sequence[Task]:
    """Get all tasks for a specific user."""
    async with get_session() as session:
        statement = select(Task).where(Task.user_id == user_id)
        result = await session.exec(statement)
        return result.all()


async def get_tasks_today(user_id: int) -> List[Task]:
    """Get tasks due today for a specific user."""
    from datetime import date
    today = date.today()
    async with get_session() as session:
        statement = select(Task).where(
            Task.user_id == user_id,
            Task.deadline != None,
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


async def get_incomplete_tasks(user_id: int) -> Sequence[Task]:
    """Get all incomplete tasks for a user."""
    async with get_session() as session:
        statement = select(Task).where(
            Task.user_id == user_id,
            Task.is_completed == False,
        )
        result = await session.exec(statement)
        return result.all()


if __name__ == "__main__":
    asyncio.run(init_db())
    print("Database initialized")
