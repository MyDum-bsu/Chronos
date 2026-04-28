import os
import httpx
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from .tools import (
    get_time as _get_time,
    add_task as _add_task,
    get_today_tasks as _get_today_tasks,
    complete_task as _complete_task,
)

# System prompt for the butler agent
SYSTEM_PROMPT = """You are Chronos, a polite and professional AI butler-planner. Your specialty is time management, scheduling, and task planning.

**Core principles:**
1. Always be polite, respectful, and helpful
2. ALWAYS check the current time before setting any deadlines
3. Only assist with tasks related to:
   - Time management and scheduling
   - Task creation and management
   - Planning and organization
   - Answering questions about time/date

**If a user asks about anything unrelated to planning or time:**
- Politely decline
- Explain that you are a specialized planning assistant
- Redirect the conversation back to scheduling and organization

**Guidelines:**
- Use the provided tools to help manage tasks
- When setting deadlines, always consider the current time
- Present information in a clear, organized manner
- Be proactive in suggesting task management strategies
- Address the user respectfully (e.g., "sir", "madam", or by name if known)

CRITICAL INSTRUCTION: When calling tools, you MUST output valid JSON for the arguments. Never merge the function name with the arguments. Format your internal calls flawlessly."""


# Dependencies container for agent
class AgentDeps(BaseModel):
    """User context for agent dependencies."""
    user_id: int


# Initialize the PydanticAI Agent
def get_agent() -> Agent[AgentDeps]:
    """Get configured PydanticAI Agent instance."""
    # Read proxy URL from environment
    proxy_url = os.getenv('PROXY_URL')
    
    # Create httpx client with proxy if configured
    http_client: httpx.AsyncClient | None = None
    if proxy_url:
        http_client = httpx.AsyncClient(proxy=proxy_url)
    
    # Use OpenAI-compatible provider for Groq API with optional proxy
    provider = OpenAIProvider(
        base_url='https://api.groq.com/openai/v1',
        api_key=os.getenv('GROQ_API_KEY'),
        http_client=http_client,
    )
    
    model = OpenAIChatModel(
        model_name='llama-3.3-70b-versatile',
        provider=provider,
    )
    
    agent: Agent[AgentDeps] = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        deps_type=AgentDeps,
    )
    
    # Register tools with ctx parameter for deps access
    @agent.tool
    async def get_time(ctx: RunContext[AgentDeps], timezone: str = "UTC") -> str:
        """
        Get the current date and time.
        
        Args:
            timezone: Timezone identifier (e.g., 'UTC', 'Europe/Moscow').
        
        Returns:
            Current date and time as ISO format string.
        """
        return await _get_time(timezone=timezone)
    
    @agent.tool
    async def add_task(
        ctx: RunContext[AgentDeps],
        title: str,
        description: str | None = None,
        deadline: str | None = None,
    ) -> dict:
        """
        Create a new task for the user.
        
        Args:
            title: Task title
            description: Detailed task description (optional)
            deadline: Task deadline as ISO datetime string, e.g. "2026-04-30 15:00:00" (optional)
        
        Returns:
            Dictionary with task_id, title, and confirmation message.
        """
        from datetime import datetime
        parsed_deadline = None
        if deadline:
            try:
                parsed_deadline = datetime.fromisoformat(deadline.replace(' ', 'T'))
            except ValueError:
                return {
                    "error": f"Invalid deadline format. Use YYYY-MM-DD HH:MM:SS",
                    "task_id": None,
                }
        
        task = await _add_task(
            user_id=ctx.deps.user_id,
            title=title,
            description=description,
            deadline=parsed_deadline,
        )
        return {
            "task_id": task["task_id"],
            "title": task["title"],
            "message": f"Task '{title}' has been added successfully."
        }
    
    @agent.tool
    async def get_today_tasks(ctx: RunContext[AgentDeps], timezone: str = "UTC") -> dict:
        """
        Get all tasks due today for the current user.
        
        Args:
            timezone: Timezone identifier for date calculation.
        
        Returns:
            Dictionary with tasks list and count.
        """
        return await _get_today_tasks(ctx.deps.user_id, timezone=timezone)
    
    @agent.tool
    async def complete_task(
        ctx: RunContext[AgentDeps],
        task_id: int,
        timezone: str = "UTC",
    ) -> dict:
        """
        Mark a task as completed.
        
        Args:
            task_id: ID of the task to mark as completed
            timezone: Timezone identifier (unused, for tool signature compatibility)
        
        Returns:
            Confirmation message with success status.
        """
        result = await _complete_task(task_id, timezone=timezone)
        if result["success"]:
            return {
                "success": True,
                "message": f"Task {task_id} has been marked as completed."
            }
        else:
            return {
                "success": False,
                "message": f"Task {task_id} not found or already completed."
            }
    
    return agent


# Global agent instance (lazy-loaded)
_agent: Agent[AgentDeps] | None = None


def get_agent_instance() -> Agent[AgentDeps]:
    """Get or create the global agent instance."""
    global _agent
    if _agent is None:
        _agent = get_agent()
    return _agent


async def process_message(user_id: int, text: str) -> str:
    """
    Process a user message through the AI agent.
    
    Args:
        user_id: Telegram user ID
        text: User's message text
    
    Returns:
        Agent's response as a string.
    
    Example:
        >>> response = await process_message(123, "Add task: buy groceries")
        "I've added the task for you, sir."
    """
    agent = get_agent_instance()
    
    # Run agent with user_id in deps
    result = await agent.run(
        text,
        deps=AgentDeps(user_id=user_id)
    )
    
    return result.output
