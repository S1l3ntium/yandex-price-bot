import io
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter

logger = logging.getLogger("bot")
DEFAULT_GRAPH_TIMEZONE = "Europe/Moscow"


def get_graph_timezone() -> ZoneInfo:
    timezone_name = os.getenv("TIMEZONE", DEFAULT_GRAPH_TIMEZONE)
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        logger.warning("Некорректный TIMEZONE=%s, используется UTC", timezone_name)
        return ZoneInfo("UTC")


def parse_db_timestamp(timestamp: str, timezone: ZoneInfo) -> datetime:
    """SQLite CURRENT_TIMESTAMP хранится в UTC; для графика показываем локальное время."""
    utc_timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    return utc_timestamp.astimezone(timezone)


async def generate_price_graph(db, product_id: int, hours: int, user_id: int) -> Optional[bytes]:
    """Генерация графика изменения цен."""
    try:
        product = db.get_product(product_id, user_id)
        if not product:
            return None

        history = db.get_price_history(product_id, hours)
        if not history:
            return None

        timezone = get_graph_timezone()
        now_utc = datetime.now(UTC)
        range_start = (now_utc - timedelta(hours=hours)).astimezone(timezone)
        range_end = now_utc.astimezone(timezone)
        prices = [price for price, _ in history]
        timestamps = [parse_db_timestamp(ts, timezone) for _, ts in history]
        product_name = product[2] if product else "Товар"

        plt.figure(figsize=(10, 6))
        plt.plot(timestamps, prices, marker="o")
        plt.title(f"Изменение цены: {product_name}")
        plt.xlabel("Время")
        plt.ylabel("Цена (₽)")
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.gca().yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f} ₽"))

        plt.xlim(range_start, range_end)

        formatter = plt.matplotlib.dates.DateFormatter("%d.%m %H:%M", tz=timezone)
        plt.gca().xaxis.set_major_formatter(formatter)
        plt.gca().xaxis.set_major_locator(plt.matplotlib.dates.AutoDateLocator())

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        plt.close()
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        logger.error(f"Ошибка при генерации графика: {e}")
        return None
