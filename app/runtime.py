from aiogram import Bot, Dispatcher
from aiogram.fsm.middleware import BaseMiddleware
from aiogram.types import CallbackQuery, ErrorEvent, Message

from app.core.config import ADMIN_IDS, TOKEN
from app.core.logging import setup_logging
from app.db.database import Database
from app.handlers.common import configure_common_handlers
from app.handlers.common import router as common_router
from app.handlers.graphs import configure_graph_handlers
from app.handlers.graphs import router as graph_router
from app.handlers.products import (
    configure_product_handlers,
)
from app.handlers.products import (
    router as product_router,
)
from app.keyboards import (
    get_main_keyboard as build_main_keyboard,
)
from app.keyboards import (
    get_product_keyboard,
    get_settings_keyboard,
    get_threshold_keyboard,
    get_time_range_keyboard,
)
from app.services.graphs import generate_price_graph as build_price_graph
from app.services.market import get_product_info
from app.services.pricing import check_prices as run_price_checks

logger, _, _ = setup_logging()


class AccessMiddleware(BaseMiddleware):
    """Middleware для проверки доступа к боту."""

    async def __call__(self, handler, event: Message | CallbackQuery, data):
        if event.from_user is None:
            logger.warning("Получено событие без from_user")
            return

        user_id = event.from_user.id
        if user_id not in ADMIN_IDS:
            if isinstance(event, Message):
                await event.answer(
                    "❌ Бот закрыт для общего пользования.\n"
                    "Для получения доступа обратитесь к администратору."
                )
            else:
                await event.answer(
                    "❌ Бот закрыт для общего пользования.\n"
                    "Для получения доступа обратитесь к администратору.",
                    show_alert=True,
                )
            return
        return await handler(event, data)


bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.error()
async def handle_error(event: ErrorEvent) -> bool:
    exception = event.exception
    logger.error(
        "Необработанная ошибка aiogram",
        exc_info=(type(exception), exception, exception.__traceback__),
    )
    return True


dp.message.middleware(AccessMiddleware())
dp.callback_query.middleware(AccessMiddleware())
dp.include_router(common_router)
dp.include_router(product_router)
dp.include_router(graph_router)
db = Database()


def get_main_keyboard(user_id: int):
    return build_main_keyboard(user_id, db.get_user_products(user_id), ADMIN_IDS)


async def generate_price_graph(product_id: int, hours: int, user_id: int):
    return await build_price_graph(db, product_id, hours, user_id)


async def check_prices():
    await run_price_checks(bot, db)


def configure_handlers(apply_check_interval):
    configure_common_handlers(
        db=db,
        admin_ids=ADMIN_IDS,
        get_main_keyboard=get_main_keyboard,
        get_settings_keyboard=get_settings_keyboard,
        apply_check_interval=apply_check_interval,
        check_prices=check_prices,
        logger=logger,
    )

    configure_product_handlers(
        db=db,
        get_main_keyboard=get_main_keyboard,
        get_product_keyboard=get_product_keyboard,
        get_threshold_keyboard=get_threshold_keyboard,
        get_product_info=get_product_info,
        logger=logger,
    )

    configure_graph_handlers(
        db=db,
        get_time_range_keyboard=get_time_range_keyboard,
        get_product_keyboard=get_product_keyboard,
        generate_price_graph=generate_price_graph,
    )
