# Chronos — AI Agentic Planner

Телеграм-бот с AI-агентом для планирования задач и управления временем. Chronos выступает в роли цифрового дворецкого, который помогает создавать задачи, отслеживать дедлайны и организовывать расписание.

## Технологический стек

- **Python 3.12+**
- **Agent Framework**: [pydantic-ai](https://docs.pydantic.dev/ai/) (v1.x)
- **LLM Provider**: [Groq](https://groq.com) — модель `llama3-groq-70b-8192-tool-use-preview` (специализирована на tool calling)
  - Поддержка прокси для доступа из ограниченных регионов
  - Возможность переключения на OpenRouter/OpenAI через переменные окружения
- **Telegram Bot**: [aiogram](https://docs.aiogram.dev/) 3.7+ (async)
- **Database**: [SQLModel](https://sqlmodel.tiangolo.com/) + [aiosqlite](https://aiosqlite.omnilib.dev/) (асинхронный SQLite)
- **Vector Memory (планируется)**: ChromaDB + sentence-transformers
- **Task Scheduling (планируется)**: APScheduler
- **Environment**: `python-dotenv` для управления переменными окружения
- **Package Manager**: `uv` (ultra-fast Python package installer)

## Структура проекта

```
Chronos/
├── agent/
│   ├── core.py       # PydanticAI Agent: инициализация модели, system prompt, регистрация инструментов
│   └── tools.py      # Инструменты для LLM: get_time, add_task, get_today_tasks, complete_task
├── bot/
│   ├── handlers.py   # Aiogram хендлеры: /start, текстовые сообщения
│   └── keyboards.py  # (планируется) клавиатуры Telegram
├── memory/
│   ├── db.py         # SQLModel: модель Task, асинхронные CRUD-функции, инициализация БД
│   └── vector.py     # (планируется) ChromaDB для векторной памяти
├── scheduler/
│   └── jobs.py       # (планируется) APScheduler jobs
├── .env              # Переменные окружения (не коммитится)
├── .env.example      # Шаблон переменных окружения
├── .gitignore
├── main.py           # Точка входа: инициализация БД, запуск бота
├── pyproject.toml    # UV-проект с зависимостями
├── requirements.txt  # Pip-зависимости
└── README.md
```

## Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/MyDum-bsu/Chronos.git
cd Chronos
```

### 2. Установка зависимостей

```bash
# Создание и активация виртуального окружения через UV
uv sync

# Активация окружения (zsh/fish)
source .venv/bin/activate
```

### 3. Настройка переменных окружения

Скопируйте `.env.example` в `.env` и заполните необходимые ключи:

```bash
cp .env.example .env
```

Редактируйте `.env`:

```env
# Токен бота от @BotFather
TELEGRAM_BOT_TOKEN=ваш_токен_бота

# Ключ API от Groq (https://console.groq.com)
GROQ_API_KEY=gsk_...

# Прокси (опционально, для доступа из регионов с ограничениями)
# Формат: http://user:password@host:port
PROXY_URL=http://login:pass@proxy.example.com:8080

# Резервные ключи (необязательно)
OPENROUTER_API_KEY=...
OPENAI_API_KEY=...
```

### 4. Инициализация базы данных

База создаётся автоматически при первом запуске бота (таблица `task`).

```bash
python3 main.py
```

Бот запустится и начнёт polling. Отправьте `/start` в Telegram.

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие, краткая инструкция |
| Любой текст | Спросите бота что-нибудь — он поможет с планированием, создаст задачу, покажет задачи на сегодня и т.д. |

## Доступные инструменты (tools)

Агент может вызывать следующие функции:

1. **`get_time(timezone="UTC")`** — получить текущее время
2. **`add_task(title, description=None, deadline=None)`** — создать задачу
   - `title` — название (обязательно)
   - `description` — подробное описание (опционально)
   - `deadline` — дедлайн в формате `YYYY-MM-DD HH:MM:SS` (опционально)
3. **`get_today_tasks(timezone="UTC")`** — показать задачи на сегодня
4. **`complete_task(task_id, timezone="UTC")`** — отметить задачу как выполненную

## Системный промт агента

Chronos — вежливый дворецкий-планировщик. Он:
- Всегда проверяет текущее время перед установкой дедлайна
- Отказывается от запросов, не связанных с планированием/временем
- Обращается к пользователю уважительно (sir/madam)
- Предлагает стратегии управления задачами

## База данных

Используется SQLite с асинхронным драйвером `aiosqlite` через SQLModel.

**Таблица `task`:**
- `id` (INTEGER, PRIMARY KEY)
- `user_id` (INTEGER, indexed) — ID пользователя Telegram
- `title` (VARCHAR) — название задачи
- `description` (VARCHAR, nullable) — описание
- `deadline` (DATETIME, nullable) — срок сдачи
- `is_completed` (BOOLEAN) — статус выполнения

База создаётся автоматически в файле `chronos.db` при запуске (вызов `init_db()` в `main.py`). Файл БД добавлен в `.gitignore`.

## Настройка LLM провайдера

По умолчанию используется **Groq** с моделью `llama3-groq-70b-8192-tool-use-preview` (бесплатно, нужен API-ключ).

### Переключение на OpenRouter

1. Получите API ключ на [openrouter.ai](https://openrouter.ai)
2. Добавьте в `.env`:
   ```env
   OPENROUTER_API_KEY=sk-or-v1-...
   ```
3. Измените `agent/core.py` — используйте `OpenAIProvider` с `base_url='https://openrouter.ai/api/v1'` и моделью `'meta-llama/llama-3.3-70b-instruct:free'` (или платной)

### Переключение на OpenAI

```env
OPENAI_API_KEY=sk-...
```
Используйте `OpenAIProvider()` без `base_url` и модель `'gpt-4o-mini'`.

## Прокси

Если Groq/OpenRouter заблокирован в вашем регионе, настройте HTTP-прокси:

```env
PROXY_URL=http://user:password@proxy.host:port
```

Прокси передаётся в `httpx.AsyncClient` и используется `GroqProvider`.

## Разработка

### Запуск тестов инструментов

```bash
python -c "from agent.tools import get_time, add_task, get_today_tasks, complete_task; import asyncio; asyncio.run(get_time())"
```

### Добавление новых инструментов

1. Добавьте функцию в `agent/tools.py` (с типизацией и docstring)
2. Импортируйте в `agent/core.py` (с алиасом `_`)
3. Зарегистрируйте через `@agent.tool` внутри `get_agent()`
4. Учтите параметр `timezone` для совместимости с tool-use моделью

### Линтинг и форматирование

(Пока не настроено)

## Возможные ошибки

### 403 от Groq
- Проверьте аккаунт на console.groq.com (возможно, нужен платёжный метод)
- Убедитесь, что VPN/прокси работает для `api.groq.com`
- Создайте новый API ключ

### 429 Too Many Requests
- Бесплатные модели имеют rate limits. Перейдите на платную или используйте резервный провайдер (OpenRouter/OpenAI)

### no such table: task
- База не инициализирована. Убедитесь, что `await init_db()` вызывается в `main.py` перед запуском polling

### TelegramUnauthorizedError
- Неверный `TELEGRAM_BOT_TOKEN`. Получите токен у @BotFather
- Убедитесь, что бот не заблокирован

## Лицензия

MIT

## Автор

MyDum-bsu (mydum.bsu@gmail.com)
