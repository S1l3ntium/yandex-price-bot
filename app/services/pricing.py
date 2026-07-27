import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter

from app.services.market import get_product_info

logger = logging.getLogger("bot")
db_logger = logging.getLogger("database")
aiogram_logger = logging.getLogger("aiogram")
_check_prices_lock = asyncio.Lock()
_SEND_LOCK = asyncio.Lock()
_LAST_SEND_BY_CHAT: dict[int, float] = {}


async def send_message_with_retry(bot: Bot, user_id: int, message: str) -> None:
    """Отправка уведомления с простым per-chat throttle и поддержкой flood control."""
    async with _SEND_LOCK:
        loop = asyncio.get_running_loop()
        elapsed = loop.time() - _LAST_SEND_BY_CHAT.get(user_id, 0)
        if elapsed < 1:
            await asyncio.sleep(1 - elapsed)

        for attempt in range(2):
            try:
                await bot.send_message(user_id, message)
                _LAST_SEND_BY_CHAT[user_id] = loop.time()
                return
            except TelegramRetryAfter as e:
                if attempt == 1:
                    raise
                retry_after = max(float(e.retry_after), 1.0)
                aiogram_logger.warning(
                    "Flood control для пользователя %s, повтор через %.1fs",
                    user_id,
                    retry_after,
                )
                await asyncio.sleep(retry_after)


async def check_single_product(
    bot: Bot,
    db,
    product_id: int,
    user_id: int,
    url: str,
    last_price: int,
    threshold: int,
):
    """Проверка цены одного товара."""
    try:
        product_info = await get_product_info(url)
        if not product_info:
            logger.error(f"Не удалось получить информацию о товаре {product_id}")
            return

        current_price = product_info["price"]
        price_diff = current_price - last_price
        abs_price_diff = abs(price_diff)

        logger.info(f"Проверка товара {product_id}:")
        logger.info(f"  • Название: {product_info['name']}")
        logger.info(f"  • Последняя цена: {last_price}₽")
        logger.info(f"  • Текущая цена: {current_price}₽")
        logger.info(f"  • Разница: {price_diff}₽")
        logger.info(f"  • Модуль разницы: {abs_price_diff}₽")
        logger.info(f"  • Порог: {threshold}₽")

        if abs_price_diff >= threshold:
            try:
                if price_diff > 0:
                    message = (
                        f"📈 Цена выросла!\n"
                        f"📦 {product_info['name']}\n"
                        f"Была: {last_price}₽, стала: {current_price}₽\n"
                        f"Разница: +{price_diff}₽"
                    )
                    logger.info(
                        f"  • Статус: Цена выросла на {price_diff}₽ "
                        f"(превышен порог {threshold}₽)"
                    )
                else:
                    message = (
                        f"📉 Цена упала!\n"
                        f"📦 {product_info['name']}\n"
                        f"Была: {last_price}₽, стала: {current_price}₽\n"
                        f"Разница: {price_diff}₽"
                    )
                    logger.info(
                        f"  • Статус: Цена упала на {abs_price_diff}₽ "
                        f"(превышен порог {threshold}₽)"
                    )

                logger.info(f"  • Отправка уведомления пользователю {user_id}")
                await send_message_with_retry(bot, user_id, message)
                aiogram_logger.info(f"  • Уведомление отправлено пользователю {user_id}")

                if db.update_price(product_id, current_price):
                    db_logger.info("  • Цена успешно обновлена в базе данных")
                else:
                    db_logger.error("  • Ошибка обновления цены в базе данных")
            except TelegramAPIError as e:
                aiogram_logger.error(f"  • Ошибка отправки уведомления: {e}")
        elif price_diff != 0:
            db.update_price(product_id, current_price)
            logger.info(
                f"  • Статус: Цена изменилась на {price_diff}₽ "
                f"(не достигнут порог {threshold}₽)"
            )
        else:
            logger.info("  • Статус: Цена не изменилась")
    except Exception as e:
        logger.error(f"Ошибка при проверке товара {product_id}: {e}")


async def check_prices(bot: Bot, db):
    """Проверка цен всех товаров."""
    if _check_prices_lock.locked():
        logger.warning("Проверка цен уже выполняется, повторный запуск пропущен")
        return

    async with _check_prices_lock:
        logger.info("=== Начало проверки цен ===")
        try:
            products = db.get_all_products()
            logger.info(f"Найдено товаров для проверки: {len(products)}")

            for product_id, user_id, url, last_price, threshold in products:
                logger.info(f"Подготовка проверки товара {product_id} для пользователя {user_id}")
                await check_single_product(bot, db, product_id, user_id, url, last_price, threshold)

            logger.info("=== Проверка цен завершена ===")
        except Exception as e:
            logger.error(f"Ошибка при проверке цен: {e}")
