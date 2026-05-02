# Chronos — AI Agentic Planner

Телеграм-бот с AI-агентом для планирования задач и управления временем. Chronos выступает в роли цифрового дворецкого, который помогает создавать задачи, отслеживать дедлайны, организовывать расписание и запоминает ваши предпочтения.

## Технологический стек

- **Python 3.12+**
- **Agent Framework**: [pydantic-ai](https://docs.pydantic.dev/ai/) (v1.x)
- **LLM Provider**: [Groq](https://groq.com) — модель `llama-3.1-8b-instant`
  - Поддержка прокси для доступа из ограниченных регионов
  - Возможность переключения на OpenRouter/OpenAI через переменные окружения
- **Telegram Bot**: [aiogram](https://docs.aiogram.dev/) 3.7+ (async)
- **Database**: [SQLModel](https://sqlmodel.tiangolo.com/) + [aiosqlite](https://aiosqlite.omnilib.dev/) (асинхронный SQLite)
- **Vector Memory**: [ChromaDB](https://chromadb.ai/) + [sentence-transformers](https://www.sbert.net/) (all-MiniLM-L6-v2) для семантического хранения предпочтений
- **Task Scheduling**: [APScheduler](https://apscheduler.readthedocs.io/) для напоминаний о дедлайнах
- **Environment**: `python-dotenv` для управления переменными окружения
- **Package Manager**: `uv` (ultra-fast Python package installer)

## Структура проекта

```
Chronos/
├── agent/
│   ├── core.py       # PydanticAI Agent: инициализация модели, system prompt, регистрация инструментов
│   └── tools.py      # Инструменты для LLM: get_time, add_task, get_today_tasks, complete_task, update_task, delete_task, search_tasks, get_task_stats, create_reminder, toggle_reminder, recall_user_preferences
├── bot/
│   ├── handlers.py   # Aiogram хендлеры: команды, текстовые сообщения, FSM, callback-запросы
│   ├── keyboards.py  # Inline-клавиатуры главного меню
│   └── fsm.py        # FSM состояния для создания задачи
├── memory/
│   ├── db.py         # SQLModel: модель Task, асинхронные CRUD-функции, инициализация БД
│   └── vector.py     # ChromaDB для векторной памяти пользователей
├── scheduler/
│   └── jobs.py       # APScheduler задачи (напоминания о дедлайнах)
├── evaluation/
│   ├── judge.py      # LLM-судья для оценки ответов
│   ├── run_evaluation.py  # Запуск оценки
│   └── test_cases.py     # Тестовые случаи
├── .env              # Переменные окружения (не коммитится)
├── .env.example      # Шаблон переменных окружения
├── .gitignore
├── main.py           # Точка входа: инициализация БД, запуск бота и планировщика
├── pyproject.toml    # UV-проект с зависимостями
├── requirements.txt  # Pip-зависимости
├── ARCHITECTURE.md   # Архитектурная документация
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

Или через pip:
```bash
pip install -r requirements.txt
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
| `/start` | Приветствие и показ главного меню |
| `/tasks` | Показать задачи на сегодня |
| `/complete` | Отметить задачу как выполненной (инлайн-кнопки) |
| `/stats` | Подробная статистика: всего, завершено, активных, просрочено, на сегодня |
| `/help` | Справка по командам |
| `/newtask` | Начать FSM создания задачи (пошаговый ввод) |
| `/cancel` | Отменить текущую операцию FSM |

## Главное меню (inline-кнопки)

Бот отображает постоянное inline-меню с действиями:

- **📋 Сегодня** — показать задачи на сегодня
- **➕ Новая задача** — начать пошаговое создание задачи (FSM)
- **✅ Завершить** — выбрать из активных задач для отметки как выполненной
- **📊 Статистика** — общая статистика: всего, завершено, активных, просрочено, на сегодня

## Создание задачи через FSM

При нажатии "➕ Новая задача" или команде `/newtask` бот последовательно запрашивает:

1. **Название задачи** — введите текст названия
2. **Дедлайн** — введите дату/время (например, "завтра в 18:00", "2026-05-15 14:30")
3. **Описание** — введите детали задачи или `/skip` чтобы пропустить

После сбора всех полей агент автоматически создаст задачу.

## Доступные инструменты (tools)

Агент может вызывать следующие функции:

1. **`get_time(timezone="UTC")`** — получить текущее время
2. **`add_task(title, description=None, deadline=None)`** — создать задачу
   - `title` — название (обязательно)
   - `description` — подробное описание (опционально)
   - `deadline` — дедлайн в формате `YYYY-MM-DD HH:MM:SS` (опционально)
3. **`get_today_tasks(timezone="UTC")`** — показать задачи на сегодня
4. **`complete_task(task_id, timezone="UTC")`** — отметить задачу как выполненную
5. **`update_task(task_id, title=None, description=None, deadline=None)`** — обновить задачу (любое поле)
6. **`delete_task(task_id)`** — удалить задачу
7. **`search_tasks(query)`** — поиск задач по названию/описанию
8. **`get_task_stats()`** — статистика (total, active, completed, overdue, today)
9. **`recall_user_preferences(query=None)`** — поиск в семантической памяти (предпочтения, привычки, прошлые обсуждения)
10. **`create_reminder(text, deadline)`** — создать напоминание
11. **`toggle_reminder(task_id, enable)`** — включить/выключить напоминания для задачи

## Семантическая память

Chronos автоматически запоминает ваши сообщения и использует их для контекста:

- **Автосохранение**: Каждое ваше сообщение сохраняется в векторную память (ChromaDB) при вводе
- **Recall**: Агент может вызвать `recall_user_preferences`, чтобы найти релевантные факты из прошлых диалогов
- **Персонализация**: Ответы строятся с учётом ваших предпочтений (например, "Вы обычно планируете утренние тренировки в 7:00")
- **Изоляция**: Память разделена по `user_id`, данные одного пользователя недоступны другому
- **Модель эмбеддингов**: `all-MiniLM-L6-v2` (легковесная, быстрая, 384-мерный вектор)
- **Хранение**: Постоянное хранение в директории `chroma_data/` (добавлена в `.gitignore`)

## Напоминания о дедлайнах

Бот автоматически проверяет предстоящие дедлайны и отправляет напоминания:

- **Периодичность**: Проверка каждые 60 секунд
- **Окно напоминания**: За 15 минут до начала задачи
- **Формат**: `⏰ Напоминание: задача «{title}» начинается в {HH:MM}`
- **Условия**: Только незавершённые задачи с установленным дедлайном
- **Изоляция**: Напоминания отправляются каждому пользователю персонально

## Системный промт агента

Chronos — вежливый дворецкий-планировщик. Он:
- Всегда проверяет текущее время перед установкой дедлайна
- Отказывается от запросов, не связанных с планированием/временем
- Обращается к пользователю уважительно (sir/madam)
- Предлагает стратегии управления задачами
- **Использует recall_user_preferences** при обсуждении предпочтений, привычек или прошлых обсуждений
- Автоматически сохраняет важные факты о пользователе (через автосохранение сообщений)

## База данных

Используется SQLite с асинхронным драйвером `aiosqlite` через SQLModel.

**Таблица `task`:**
- `id` (INTEGER, PRIMARY KEY)
- `user_id` (INTEGER, indexed) — ID пользователя Telegram
- `title` (VARCHAR) — название задачи
- `description` (VARCHAR, nullable) — описание
- `deadline` (DATETIME, nullable) — срок сдачи
- `is_completed` (BOOLEAN) — статус выполнения
- `reminder_enabled` (BOOLEAN) — включены ли напоминания

База создаётся автоматически в файле `chronos.db` при запуске (вызов `init_db()` в `main.py`). Файл БД добавлен в `.gitignore`.

## Настройка LLM провайдера

По умолчанию используется **Groq** с моделью `llama-3.1-8b-instant` (бесплатно, нужен API-ключ).

### Переключение на OpenRouter

1. Получите API ключ на [openrouter.ai](https://openrouter.ai)
2. Добавьте в `.env`:
   ```env
   OPENROUTER_API_KEY=sk-or-v1-...
   ```
3. Измените `agent/core.py` — используйте `OpenAIProvider` с `base_url='https://openrouter.ai/api/v1'`

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

## Оценка качества (Evaluation)

В директории `evaluation/` находятся инструменты для оценки качества ответов агента:

```bash
cd evaluation
python run_evaluation.py
```

## Разработка

### Запуск тестов инструментов

```bash
python -c "from agent.tools import get_time, add_task, get_today_tasks, complete_task; import asyncio; asyncio.run(get_time())"
```

### Тестирование VectorMemory

```bash
python test_vector_memory.py
```

### Добавление новых инструментов

1. Добавьте Pydantic модели (Input/Response) в `agent/tools.py`
2. Реализуйте функцию с типизацией и docstring
3. Импортируйте в `agent/core.py` (с алиасом `_`)
4. Зарегистрируйте через `@agent.tool` внутри `get_agent()`
5. Обновите `SYSTEM_PROMPT` с описанием нового инструмента

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

### chroma_data/ not creating
- Убедитесь, что установлены `chromadb` и `sentence-transformers`
- Проверьте права на запись в текущую директорию

## Лицензия

MIT

## Автор

MyDum-bsu (mydum.bsu@gmail.com)
