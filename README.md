# AI Agent Orchestrator

**AI Agent Orchestrator** — это микросервис оркестрации (Control Plane) в рамках мультиагентной системы. Его главная задача — принимать запросы, строить граф зависимостей (DAG) для AI-агентов на основе их манифестов, планировать волны выполнения и управлять всем процессом через отказоустойчивые Temporal-рабочие процессы.

## 🏗 Архитектура

Сервис построен с использованием современных инструментов и фреймворков для обеспечения надежности, асинхронности и возможности масштабирования.

### Стек технологий:
- **FastAPI**: API-шлюз для приема запросов инициации оркестрации и проверки их статуса.
- **Temporal**: Платформа для оркестрации микросервисов и рабочих процессов. Обеспечивает отказоустойчивое выполнение агентов (координация `Workflows` и `Activities`).
- **OpenSearch**: База данных и семантический поисковик (Registry) для хранения манифестов агентов и векторного поиска по их возможностям.
- **LangGraph**: Используется для симуляции выполнения агента (микро-граф состояний) внутри системы.
- **Pydantic**: Строгая валидация и описание контрактов ввода-вывода (схем).
- **uv**: Менеджер зависимостей, проектов и скриптов в Python.

## 🗂 Структура проекта

Весь исходный код находится в директории `src/app/`.

```
src/app/
├── api/          # Эндпоинты FastAPI (/dispatch, /jobs/{id}/status)
├── clients/      # Внешние клиенты (AgentDiscoveryClient для OpenSearch)
├── models/       # Pydantic модели (Контракты, Манифесты, Инструменты)
├── orchestration/# Ядро логики: Backward Tracing, Cycle Detection, Topological Sort
├── temporal/     # Определение Workflows и Activities для Temporal
└── main.py       # Точка входа в приложение FastAPI
```

## 🧠 Ключевые концепции и Сущности

### 1. Агент (Agent)
В основе системы лежит декларативная JSON-структура агента, описанная в `AgentManifest` (`src/app/models/manifest.py`). Это строгий контракт без кода. Он включает:
- Контракты данных (`input_schema`, `output_schema`).
- Системные промпты и ролевые модели.
- Доступные инструменты (REST API, MCP Server, Kafka, Built-in).
- Внутренний граф переходов (Micro-Graph), определяющий изолированные шаги и условные переходы.

Агенты хранятся в **OpenSearch** в виде индексов с плотными векторами (`capabilities_embedding`) для семантического поиска.

### 2. Оркестрация (Macro-Orchestration)
Процесс оркестрации проходит следующие этапы (реализованы в `src/app/orchestration/` и `src/app/temporal/`):
- **Семантический поиск**: нахождение "корневого" агента на основе пользовательского запроса (`AgentDiscoveryClient`).
- **Backward Tracing**: рекурсивный поиск зависимостей агентов для построения направленного ациклического графа (DAG).
- **Cycle Detection**: выявление и предотвращение зацикливаний.
- **Topological Sort**: разбиение DAG на "волны" (Waves) выполнения, где агенты в одной волне независимы и могут выполняться параллельно.
- **Temporal Workflow**: последовательно запускает волны, передает `input_context` следующим агентам на основе `output` предыдущих и сохраняет промежуточные состояния (`state_store`).

## 🚀 Как запустить локально

### Требования
- [Docker](https://docs.docker.com/get-docker/) и [Docker Compose V2](https://docs.docker.com/compose/)
- [uv](https://github.com/astral-sh/uv) (современный пакетный менеджер для Python)
- Python >= 3.12 (если планируете локальную разработку вне Docker)

### Шаг 1. Поднятие инфраструктуры
Запустите Temporal, OpenSearch и другие сервисы с помощью Docker Compose:
```bash
docker compose up -d
```
*Temporal UI будет доступен по адресу: http://localhost:8080*
*OpenSearch Dashboards: http://localhost:5601*

### Шаг 2. Установка зависимостей проекта
```bash
uv sync
```

### Шаг 3. Запуск сервиса
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 🧪 Запуск тестов и проверок

Проект жестко следует стандартам типизации (Mypy strict) и форматирования (Ruff, Black).

**Запуск тестов:**
```bash
uv run pytest
```
*Для E2E тестов и мокирования Temporal используются `temporalio.testing` и `respx`.*

**Проверка типов:**
```bash
PYTHONPATH=src uv run mypy .
```

**Форматирование и Линтинг:**
```bash
uv run black .
uv run ruff check .
```

## 🔌 API Reference

### 1. Инициация оркестрации
`POST /api/v1/orchestrator/dispatch`
- **Body**: `{"query": "Текстовый запрос пользователя"}`
- **Response**: `{"orchestration_job_id": "orchestration-uuid..."}`
- Запускает асинхронный Temporal Workflow (`start_workflow`) и сразу возвращает ID задачи.

### 2. Статус оркестрации
`GET /api/v1/orchestrator/jobs/{job_id}/status`
- **Response**: `{"job_id": "orchestration-uuid...", "status": "RUNNING | COMPLETED | FAILED"}`
- Опрашивает Temporal на предмет статуса выполнения `Workflow`.

## 📌 План развития (TODO)
Для ознакомления с текущим прогрессом проекта и будущими задачами обратитесь к файлу `TODO.md`.
