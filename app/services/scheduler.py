import logging
from collections.abc import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger("bot")
CHECK_PRICES_JOB_ID = "check_prices_job"


def update_check_prices_schedule(
    scheduler: AsyncIOScheduler | None,
    interval: int,
    check_prices_func: Callable[[], Awaitable[None]],
) -> bool:
    """Обновление расписания проверки цен без перезапуска бота."""
    if scheduler is None:
        logger.warning("Scheduler еще не инициализирован")
        return False

    try:
        if scheduler.get_job(CHECK_PRICES_JOB_ID):
            scheduler.reschedule_job(CHECK_PRICES_JOB_ID, trigger="interval", minutes=interval)
        else:
            scheduler.add_job(
                check_prices_func,
                "interval",
                minutes=interval,
                id=CHECK_PRICES_JOB_ID,
            )

        job = scheduler.get_job(CHECK_PRICES_JOB_ID)
        next_run = job.next_run_time.isoformat() if job and job.next_run_time else "unknown"
        logger.info(
            f"Расписание проверки цен обновлено: каждые {interval} минут, next_run={next_run}"
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении расписания проверки цен: {e}")
        return False


def apply_check_interval(
    db,
    scheduler: AsyncIOScheduler | None,
    interval: int,
    check_prices_func,
) -> bool:
    """Атомарное применение нового интервала в БД и scheduler."""
    previous_interval = db.get_check_interval()

    if not db.set_check_interval(interval):
        return False

    if update_check_prices_schedule(scheduler, interval, check_prices_func):
        return True

    logger.warning(
        "Не удалось обновить scheduler, откатываю интервал в БД к предыдущему значению: %s",
        previous_interval,
    )
    db.set_check_interval(previous_interval)
    return False
