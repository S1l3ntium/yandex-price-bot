# Yandex Price Bot

Telegram-бот для отслеживания цен на Яндекс.Маркете.

## Возможности

- отслеживание цен товаров
- уведомления об изменении цены
- история цен
- индивидуальный порог для товара
- кнопочный интерфейс в Telegram

## Переменные окружения

Скопируйте шаблон и заполните значения:

```bash
cp .env.example .env
```

Обязательные переменные:

- `TOKEN` — токен Telegram-бота
- `YA_COOKIE` — cookie для доступа к данным Яндекс.Маркета
- `ADMIN_IDS` — список Telegram user id через запятую

Опциональные:

- `CHECK_INTERVAL` — интервал проверки в минутах, по умолчанию `30`
- `PRICE_THRESHOLD` — порог по умолчанию, `500`
- `DATABASE_PATH` — путь к SQLite БД, по умолчанию `data/prices.db`
- `BACKUP_DIR` — директория backup-файлов, по умолчанию `backups` локально и `/app/backups` в Docker
- `TIMEZONE` — часовой пояс для подписей времени на графиках, по умолчанию `Europe/Moscow`

Пример:

```env
TOKEN=your_telegram_bot_token
YA_COOKIE=your_yandex_cookie
ADMIN_IDS=123456789
CHECK_INTERVAL=10
PRICE_THRESHOLD=500
DATABASE_PATH=data/prices.db
BACKUP_DIR=backups
TIMEZONE=Europe/Moscow
```

## Локальный запуск

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Для разработки, тестов и lint:

```bash
pip install -r requirements-dev.txt
```

## Docker

База данных хранится в `/app/data/prices.db` в named volume `yandex_price_bot_db`.
Backup-файлы сохраняются в named volume `yandex_price_bot_backups` (`/app/backups`).
Контейнер запускается non-root, с read-only root filesystem, writable только volume и `/tmp`.

```bash
docker compose up --build -d
```

Остановка:

```bash
docker compose down
```

Создать консистентный backup SQLite через Online Backup API:

```bash
docker compose run --rm yandex-price-bot python scripts/backup_db.py
```

Локально backup пишется в `backups/`:

```bash
python scripts/backup_db.py
```

## Тесты и lint

Установка зависимостей:

```bash
pip install -r requirements-dev.txt
```

Запуск тестов:

```bash
pytest
```

Проверка линтером:

```bash
ruff check .
```

Или через `make`:

```bash
make install-dev
make test
make lint
make run
```

CI:
- GitHub Actions запускает `ruff check .` и `pytest` на push/pull request.

## Структура

- `main.py` — основная точка входа
- `bot.py` — совместимый entrypoint с запуском scheduler/runtime
- `app/runtime.py` — композиция приложения
- `app/handlers/` — Telegram handlers
- `app/services/` — market/pricing/graphs/scheduler services
- `app/keyboards.py` — клавиатуры
- `app/core/` — конфигурация и логирование
- `app/db/` — SQLite-слой
- `config.py`, `database.py` — compatibility shim-импорты
- `Dockerfile`, `docker-compose.yml` — контейнеризация

Подробности:
- `docs/architecture.md`
- `docs/operations.md`

## Ограничения

- бот зависит от актуального `YA_COOKIE`
- парсинг Яндекс.Маркета может ломаться при изменении верстки
- для runtime/smoke-проверок должны быть установлены зависимости из `requirements.txt`
