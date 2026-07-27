import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


def get_env_var(name: str, default: str | None = None) -> str | None:
    """Получение переменной окружения с логированием ошибок."""
    value = os.getenv(name, default)
    if value is None:
        logger.error(f"Переменная окружения {name} не установлена")
    return value


TOKEN = get_env_var("TOKEN")
if not TOKEN:
    raise ValueError("Не установлен TOKEN бота Telegram")

YA_COOKIE = get_env_var("YA_COOKIE")
if not YA_COOKIE:
    raise ValueError("Не установлен YA_COOKIE для доступа к Яндекс.Маркету")

try:
    CHECK_INTERVAL = int(get_env_var("CHECK_INTERVAL", "30"))
    if CHECK_INTERVAL < 1:
        raise ValueError("CHECK_INTERVAL должен быть положительным числом")
except ValueError as e:
    logger.error(f"Некорректное значение CHECK_INTERVAL: {e}")
    CHECK_INTERVAL = 30

try:
    PRICE_THRESHOLD = int(get_env_var("PRICE_THRESHOLD", "500"))
except ValueError:
    logger.error("Некорректное значение PRICE_THRESHOLD, используется 500")
    PRICE_THRESHOLD = 500

DATABASE_PATH = get_env_var("DATABASE_PATH", "data/prices.db")
if not DATABASE_PATH:
    DATABASE_PATH = "data/prices.db"

DATABASE_DIR = Path(DATABASE_PATH).expanduser().resolve().parent
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

_raw_admin_ids = [user_id.strip() for user_id in get_env_var("ADMIN_IDS", "").split(",")]
_invalid_admin_ids = [user_id for user_id in _raw_admin_ids if user_id and not user_id.isdigit()]
if _invalid_admin_ids:
    raise ValueError("ADMIN_IDS содержит нечисловые значения")

ADMIN_IDS = [int(user_id) for user_id in _raw_admin_ids if user_id]

if not ADMIN_IDS:
    logger.warning("ADMIN_IDS пустой: бот не будет доступен ни одному пользователю")
