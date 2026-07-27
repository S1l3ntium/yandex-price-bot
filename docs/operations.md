# Operations

## Локальный запуск

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
python main.py
```

## Docker

```bash
docker compose up --build -d
```

Остановка:

```bash
docker compose down
```

## Переменные окружения

Обязательные:
- `TOKEN`
- `YA_COOKIE`
- `ADMIN_IDS`

Опциональные:
- `CHECK_INTERVAL` — интервал проверки в минутах
- `PRICE_THRESHOLD` — дефолтный порог
- `DATABASE_PATH` — путь к SQLite БД
- `BACKUP_DIR` — путь для backup-файлов, по умолчанию `backups/` локально и `/app/backups` в Docker
- `TIMEZONE` — часовой пояс графиков, по умолчанию `Europe/Moscow`

## База данных и backup

По умолчанию используется:
- локально: `data/prices.db`
- в Docker: `/app/data/prices.db`
- Docker volume с БД: `yandex_price_bot_db`
- Docker volume с backup: `yandex_price_bot_backups`

Важно, чтобы `DATABASE_PATH` совпадал с mounted volume.

Создать backup локально:

```bash
python scripts/backup_db.py
```

Создать backup из Docker volume:

```bash
docker compose run --rm yandex-price-bot python scripts/backup_db.py
```

Скрипт использует SQLite Online Backup API, поэтому корректен для WAL-режима.

## Проверки качества

```bash
ruff check .
pytest
python3 -m py_compile bot.py main.py
```

## Известные ограничения

- Бот зависит от актуального `YA_COOKIE`
- Парсинг Маркета чувствителен к изменениям верстки
- В локальном окружении для smoke/runtime import нужны установленные зависимости из `requirements.txt`
