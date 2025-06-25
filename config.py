from dotenv import load_dotenv
import os
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Загрузка переменных окружения из файла .env
load_dotenv()

def get_env_var(name: str, default: str = None) -> str:
    """
    Получение переменной окружения с логированием ошибок.
    
    Args:
        name: Имя переменной окружения
        default: Значение по умолчанию
        
    Returns:
        Значение переменной окружения или значение по умолчанию
    """
    value = os.getenv(name, default)
    if value is None:
        logger.error(f"Переменная окружения {name} не установлена")
    return value

# Токен бота Telegram
TOKEN = get_env_var("TOKEN")
if not TOKEN:
    raise ValueError("Не установлен TOKEN бота Telegram")

# Cookie для доступа к Яндекс.Маркету
YA_COOKIE = get_env_var("YA_COOKIE")
if not YA_COOKIE:
    raise ValueError("Не установлен YA_COOKIE для доступа к Яндекс.Маркету")

# Интервал проверки цен (в минутах)
try:
    CHECK_INTERVAL = int(get_env_var("CHECK_INTERVAL", "30"))
    if CHECK_INTERVAL < 1:
        raise ValueError("CHECK_INTERVAL должен быть положительным числом")
except ValueError as e:
    logger.error(f"Некорректное значение CHECK_INTERVAL: {e}")
    CHECK_INTERVAL = 30  # Значение по умолчанию

PRICE_THRESHOLD = int(os.getenv("PRICE_THRESHOLD", 500))

# Список ID администраторов
ADMIN_IDS = [int(id) for id in get_env_var("ADMIN_IDS", "").split(",") if id.isdigit()]
