# Архитектура

## Точка входа

- `main.py` — основной entrypoint для локального запуска и Docker
- `bot.py` — совместимый runtime entrypoint; содержит запуск scheduler и `main()`
- `app/runtime.py` — композиция приложения: bot, dispatcher, middleware, DB, routers, wiring handlers

## Структура модулей

- `app/core/`
  - `config.py` — чтение env и базовые настройки
  - `logging.py` — настройка логирования
- `app/db/`
  - `database.py` — SQLite-слой
- `app/services/`
  - `market.py` — получение данных товара с Яндекс.Маркета
  - `pricing.py` — проверка цен и уведомления
  - `graphs.py` — генерация графиков
  - `scheduler.py` — обновление interval job и rollback логики
- `app/handlers/`
  - `common.py` — start/help/settings/check_now
  - `products.py` — товары, добавление, удаление, threshold
  - `graphs.py` — графики и связанные callbacks
- `app/keyboards.py` — reply/inline клавиатуры

## Направление зависимостей

`handlers -> services -> db`

Дополнительно:
- `runtime` связывает handlers и services
- `core` используется инфраструктурными и сервисными слоями

## Совместимость

Для обратной совместимости оставлены shim-модули:
- `config.py` -> `app.core.config`
- `database.py` -> `app.db.database`

Это позволяет продолжать использовать старые импорты во время миграции.
