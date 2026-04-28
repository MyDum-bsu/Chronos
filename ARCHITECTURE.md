# Chronos - AI Agentic Planner

## Tech Stack
- Python 3.11+
- Agent Framework: `pydantic-ai`
- LLM: `groq` (model: `llama-3.3-70b-versatile`)
- Telegram UI: `aiogram` (v3.x, async)
- Database: `sqlmodel` + `aiosqlite`
- Vector Memory: `chromadb` + `sentence-transformers` (model: `all-MiniLM-L6-v2`)
- Scheduling: `apscheduler`
- Environment variables: `python-dotenv`

## Project Structure
/bot
  handlers.py
  keyboards.py
/agent
  core.py (PydanticAI agent setup)
  tools.py (Functions for LLM)
/memory
  db.py (SQLModel setup and CRUD)
  vector.py (ChromaDB logic)
/scheduler
  jobs.py
main.py
