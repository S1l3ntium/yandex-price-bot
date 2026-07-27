import asyncio
import logging

from bot import main as run_bot

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logging.getLogger("bot").info("Бот остановлен пользователем")
    except Exception as e:
        logging.getLogger("bot").error(f"Критическая ошибка: {e}")
