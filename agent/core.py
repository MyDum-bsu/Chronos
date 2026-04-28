import os
from pydantic_ai import Agent, RunContext, ModelSettings
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider

from .tools import (
    get_current_time,
    add_task,
    get_tasks_for_today,
    complete_task,
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
- Address the user respectfully (e.g., "sir", "madam", or by name if known)"""


# Dependencies container for agent
class AgentDependencies:
    """User context for agent dependencies."""
    user_id: int


# Initialize the PydanticAI Agent
def get_agent() -> Agent:
    """Get configured PydanticAI Agent instance."""
    # Create Groq provider with API key from environment
    provider = GroqProvider(api_key=os.getenv('GROQ_API_KEY'))
    
    model = GroqModel(
        model_name='llama-3.3-70b-versatile',
        provider=provider,
    )
    
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
    )
    
    # Register tools
    @agent.tool
    async def get_current_time_tool(ctx: RunContext[AgentDependencies]) -> str:
        """Get the current date and time."""
        return await get_current_time()
    
    @agent.tool
    async def add_task_tool(
        ctx: RunContext[AgentDependencies],
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
        
        task = await add_task(
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
    async def get_tasks_for_today_tool(ctx: RunContext[AgentDependencies]) -> dict:
        """Get all tasks due today for the current user."""
        return await get_tasks_for_today(ctx.deps.user_id)
    
    @agent.tool
    async def complete_task_tool(
        ctx: RunContext[AgentDependencies],
        task_id: int,
    ) -> dict:
        """
        Mark a task as completed.
        
        Args:
            task_id: ID of the task to mark as completed
        
        Returns:
            Confirmation message.
        """
        result = await complete_task(task_id)
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
_agent: Agent | None = None


def get_agent_instance() -> Agent:
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
    deps = AgentDependencies()
    deps.user_id = user_id
    
    result = await agent.run(text, deps=deps)
    return result.output
