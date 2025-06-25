# Yandex Price Bot

Telegram бот для отслеживания цен товаров на Яндекс.Маркете.

## Возможности

- Отслеживание цен товаров на Яндекс.Маркете
- Уведомления при изменении цены
- История изменения цен
- Индивидуальные пороги изменения цены для каждого товара
- Управление списком отслеживаемых товаров

## Установка

1. Клонируйте репозиторий:

```bash
git clone https://github.com/S1l3ntium/yandex-price-bot.git
cd yandex-price-bot
```

2. Создайте виртуальное окружение и активируйте его:

```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
# или
venv\Scripts\activate  # для Windows
```

3. Установите зависимости:

```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` в корневой директории проекта со следующим содержимым:

```
TOKEN=your_telegram_bot_token
YA_COOKIE=your_yandex_cookie
CHECK_INTERVAL=10
PRICE_THRESHOLD=500
ADMIN_IDS=your_id,your_id
```

## Запуск в Docker

1. Соберите и запустите контейнер с помощью docker-compose:

```bash
docker-compose up --build -d
```

2. Остановить контейнер:

```bash
docker-compose down
```

3. Для хранения базы данных используется volume `prices_data`. Если у вас уже есть файл `prices.db`, он будет скопирован в volume при первом запуске.

4. Не забудьте создать и заполнить файл `.env` в корне проекта (см. раздел "Установка").

## Использование

1. Запустите бота:

```bash
python bot.py
```

2. В Telegram отправьте боту ссылку на товар с Яндекс.Маркета

### Команды

- `/start` - Начать работу с ботом
- `/list` - Показать список отслеживаемых товаров
- `/delete <id>` - Удалить товар из отслеживания
- `/threshold <id> <value>` - Установить индивидуальный порог изменения цены
- `/help` - Показать справку по командам

## Структура проекта

- `bot.py` - Основной файл бота
- `config.py` - Конфигурация проекта
- `database.py` - Работа с базой данных
- `requirements.txt` - Зависимости проекта
- `.env` - Файл с переменными окружения
- `prices.db` - База данных SQLite

## Лицензия

MIT
