import logging
import os
from logging.handlers import RotatingFileHandler


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _configure_logger(
    logger_name: str,
    file_name: str,
    formatter: logging.Formatter,
) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    if _env_flag("LOG_TO_FILES"):
        log_dir = os.getenv("LOG_DIR", "/tmp")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, file_name)
        has_file_handler = any(
            isinstance(handler, RotatingFileHandler)
            and handler.baseFilename == os.path.abspath(log_path)
            for handler in logger.handlers
        )
        if not has_file_handler:
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger


def setup_logging() -> tuple[logging.Logger, logging.Logger, logging.Logger]:
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    aiogram_logger = _configure_logger("aiogram", "aiogram.log", formatter)
    db_logger = _configure_logger("database", "database.log", formatter)
    bot_logger = _configure_logger("bot", "bot.log", formatter)

    for logger in (aiogram_logger, db_logger, bot_logger):
        has_stream_handler = any(
            isinstance(handler, logging.StreamHandler)
            and not isinstance(handler, logging.FileHandler)
            for handler in logger.handlers
        )
        if not has_stream_handler:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

    return bot_logger, db_logger, aiogram_logger
