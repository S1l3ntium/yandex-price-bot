from datetime import datetime
from typing import Any

from aiogram import Router, types
from aiogram.filters import Command

router = Router()

_db: Any = None
_admin_ids: set[int] = set()
_get_main_keyboard = None
_get_settings_keyboard = None
_apply_check_interval = None
_check_prices = None
_logger = None


def configure_common_handlers(
    *,
    db,
    admin_ids: set[int],
    get_main_keyboard,
    get_settings_keyboard,
    apply_check_interval,
    check_prices,
    logger,
):
    global _db, _admin_ids, _get_main_keyboard, _get_settings_keyboard
    global _apply_check_interval, _check_prices, _logger
    _db = db
    _admin_ids = admin_ids
    _get_main_keyboard = get_main_keyboard
    _get_settings_keyboard = get_settings_keyboard
    _apply_check_interval = apply_check_interval
    _check_prices = check_prices
    _logger = logger


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start."""
    welcome_text = (
        "👋 Привет! Я бот для отслеживания цен на Яндекс.Маркете.\n\n"
        "🔍 Что я умею:\n"
        "• Отслеживать цены на товары с Яндекс.Маркета\n"
        "• Уведомлять об изменении цены\n"
        "• Показывать графики изменения цен\n"
        "• Управлять списком отслеживаемых товаров\n\n"
        "📱 Используйте кнопки ниже для навигации:"
    )

    welcome_message = await message.answer(
        welcome_text,
        reply_markup=_get_main_keyboard(message.from_user.id),
    )

    try:
        await welcome_message.pin(disable_notification=True)
    except Exception as e:
        _logger.error(f"Не удалось закрепить сообщение: {e}")

    await message.answer(
        "ℹ️ Для начала работы нажмите кнопку '➕ Добавить товар' "
        "и отправьте ссылку на товар с Яндекс.Маркета."
    )


@router.message(lambda message: message.text == "⚙️ Настройки")
async def show_settings(message: types.Message):
    """Показать настройки."""
    if message.from_user.id not in _admin_ids:
        await message.reply("❌ У вас нет доступа к настройкам.")
        return

    products_count = len(_db.get_user_products(message.from_user.id))
    current_interval = _db.get_check_interval()
    text = (
        "⚙️ Настройки бота:\n\n"
        f"• Отслеживаемых товаров: {products_count}\n"
        f"• Интервал проверки цен: каждые {current_interval} минут\n"
        f"• Последняя проверка: {datetime.now().strftime('%H:%M:%S')}\n"
        f"• Статус: активен\n\n"
        "Выберите новый интервал проверки цен:"
    )
    await message.reply(text, reply_markup=_get_settings_keyboard())


@router.callback_query(lambda c: c.data.startswith("interval_"))
async def process_interval_selection(callback_query: types.CallbackQuery):
    """Обработка выбора интервала проверки."""
    if callback_query.from_user.id not in _admin_ids:
        await callback_query.answer("❌ У вас нет доступа к настройкам.", show_alert=True)
        return

    try:
        interval = int(callback_query.data.split("_")[1])
        if interval not in [5, 10, 15, 30]:
            raise ValueError("Недопустимый интервал")

        if _apply_check_interval(interval):
            await callback_query.message.edit_text(
                f"✅ Интервал проверки цен успешно изменен на {interval} минут.\n\n"
                "⚙️ Настройки бота:\n"
                f"• Отслеживаемых товаров: "
                f"{len(_db.get_user_products(callback_query.from_user.id))}\n"
                f"• Интервал проверки цен: каждые {interval} минут\n"
                f"• Последняя проверка: {datetime.now().strftime('%H:%M:%S')}\n"
                f"• Статус: активен\n\n"
                "Выберите новый интервал проверки цен:",
                reply_markup=_get_settings_keyboard(),
            )
            await callback_query.answer("✅ Интервал обновлен")
        else:
            await callback_query.answer("❌ Ошибка при обновлении интервала", show_alert=True)
    except Exception as e:
        _logger.error(f"Ошибка при установке интервала: {e}")
        await callback_query.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(lambda c: c.data == "back_to_main")
async def process_back_to_main(callback_query: types.CallbackQuery):
    """Обработка возврата в главное меню."""
    await callback_query.message.edit_text("Главное меню открыто ниже.")
    await callback_query.message.answer(
        "Выберите действие:",
        reply_markup=_get_main_keyboard(callback_query.from_user.id),
    )
    await callback_query.answer()


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help."""
    help_text = (
        "📚 Справка по использованию бота:\n\n"
        "🔍 Основные команды:\n"
        "• /start - Начать работу с ботом\n"
        "• /help - Показать эту справку\n"
        "• /settings - Настройки бота (только для администраторов)\n\n"
        "📱 Как использовать бота:\n"
        "1. Нажмите '➕ Добавить товар'\n"
        "2. Отправьте ссылку на товар с Яндекс.Маркета\n"
        "3. Выберите порог изменения цены\n"
        "4. Бот будет отслеживать изменения цены\n\n"
        "⚙️ Управление товарами:\n"
        "• '📋 Мои товары' - просмотр списка товаров\n"
        "• '📊 Графики цен' - просмотр графиков изменения цен\n"
        "• Для каждого товара доступны:\n"
        "  - Просмотр графика за 24 часа или 7 дней\n"
        "  - Изменение порога уведомлений\n"
        "  - Удаление товара из отслеживания\n\n"
        "ℹ️ Дополнительно:\n"
        "• Бот автоматически проверяет цены каждые 5-30 минут\n"
        "• При достижении порога изменения цены вы получите уведомление\n"
        "• Все изменения цен сохраняются в истории"
    )
    await message.answer(help_text, reply_markup=_get_main_keyboard(message.from_user.id))


@router.callback_query(lambda c: c.data == "check_now")
async def process_check_now(callback_query: types.CallbackQuery):
    """Обработка запроса на немедленную проверку цен."""
    if callback_query.from_user.id not in _admin_ids:
        await callback_query.answer("❌ У вас нет доступа к настройкам.", show_alert=True)
        return

    await callback_query.message.edit_text("🔄 Запускаю проверку цен...")
    await _check_prices()

    products_count = len(_db.get_user_products(callback_query.from_user.id))
    current_interval = _db.get_check_interval()
    text = (
        "✅ Проверка цен завершена!\n\n"
        "⚙️ Настройки бота:\n"
        f"• Отслеживаемых товаров: {products_count}\n"
        f"• Интервал проверки цен: каждые {current_interval} минут\n"
        f"• Последняя проверка: {datetime.now().strftime('%H:%M:%S')}\n"
        f"• Статус: активен\n\n"
        "Выберите действие:"
    )
    await callback_query.message.answer(text, reply_markup=_get_settings_keyboard())
    await callback_query.answer("✅ Проверка завершена")
