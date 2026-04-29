import os
import httpx
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider

from .tools import (
    get_time as _get_time,
    add_task as _add_task,
    get_today_tasks as _get_today_tasks,
    complete_task as _complete_task,
    get_task_stats as _get_task_stats,
    recall_user_preferences as _recall_user_preferences,
)
from memory.vector import get_vector_memory

# Initialize global vector memory
vector_memory = get_vector_memory()

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

**Memory and Context:**
- Before generating a response, if the user's message relates to their preferences, habits, or past discussions, use the recall_user_preferences tool to retrieve relevant context from their memory.
- Use this recalled information to personalize your response without explicitly mentioning the memory lookup.
- Save important user preferences and facts automatically when they are revealed in conversation."""


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
    
    # Use GroqProvider with optional custom http_client (for proxy)
    provider = GroqProvider(
        api_key=os.getenv('GROQ_API_KEY'),
        http_client=http_client,
    )
    
    model = GroqModel(
        model_name='openai/gpt-oss-20b',
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
    
    @agent.tool
    async def get_task_stats(ctx: RunContext[AgentDeps]) -> dict:
        """
        Get statistics about user's tasks.
        
        Returns:
            Dictionary with total, completed, incomplete, and today's task counts.
        """
        return await _get_task_stats(ctx.deps.user_id)
    
    @agent.tool
    async def recall_user_preferences(
        ctx: RunContext[AgentDeps],
        query: str | None = None
    ) -> list[str]:
        """
        Recall relevant user preferences and past context from memory.
        
        Args:
            query: Optional search query. If not provided, uses an empty query to retrieve recent memories.
        
        Returns:
            List of relevant memory strings sorted by relevance. Returns empty list if no memories found.
        """
        user_id = ctx.deps.user_id
        
        # If query not provided, use empty string to get recent/contextual memories
        search_query = query if query else ""
        
        try:
            memories = await _recall_user_preferences(user_id=user_id, query=search_query)
            return memories if memories else []
        except Exception:
            return []
    
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
    # Save user message to vector memory
    try:
        await vector_memory.remember(
            user_id=user_id,
            text=text,
            metadata={"role": "user", "message": text[:200]}  # Truncate for metadata
        )
    except Exception:
        pass  # Don't fail the whole process if memory save fails
    
    agent = get_agent_instance()
    
    # Run agent with user_id in deps
    result = await agent.run(
        text,
        deps=AgentDeps(user_id=user_id)
    )
    
    response = result.output
    
    # Optionally save assistant response to memory (commented for now)
    # try:
    #     await vector_memory.remember(
    #         user_id=user_id,
    #         text=response,
    #         metadata={"role": "assistant", "message": response[:200]}
    #     )
    # except Exception:
    #     pass
    
    return response
