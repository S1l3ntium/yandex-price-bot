import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.runtime import bot, check_prices, configure_handlers, db, dp, logger
from app.services.scheduler import (
    CHECK_PRICES_JOB_ID,
)
from app.services.scheduler import (
    apply_check_interval as apply_interval_change,
)
from app.services.scheduler import (
    update_check_prices_schedule as reschedule_check_prices,
)

scheduler: AsyncIOScheduler | None = None


def update_check_prices_schedule(interval: int) -> bool:
    return reschedule_check_prices(scheduler, interval, check_prices)


def apply_check_interval(interval: int) -> bool:
    return apply_interval_change(db, scheduler, interval, check_prices)


configure_handlers(apply_check_interval)


async def main():
    """Основная функция запуска бота."""
    global scheduler

    try:
        await check_prices()

        scheduler = AsyncIOScheduler()
        check_interval = db.get_check_interval()
        scheduler.add_job(check_prices, "interval", minutes=check_interval, id=CHECK_PRICES_JOB_ID)
        scheduler.start()
        job = scheduler.get_job(CHECK_PRICES_JOB_ID)
        next_run = job.next_run_time.isoformat() if job and job.next_run_time else "unknown"
        logger.info(
            f"Scheduler запущен с интервалом {check_interval} минут, next_run={next_run}"
        )

        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"Ошибка при запуске бота: {e}")
        raise
    finally:
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
        db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
