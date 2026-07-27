from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.market import InvalidMarketUrl, normalize_yandex_market_url

router = Router()

_db = None
_get_main_keyboard = None
_get_product_keyboard = None
_get_threshold_keyboard = None
_get_product_info = None
_logger = None


class ProductStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_threshold = State()


def configure_product_handlers(
    *,
    db,
    get_main_keyboard,
    get_product_keyboard,
    get_threshold_keyboard,
    get_product_info,
    logger,
):
    global _db, _get_main_keyboard, _get_product_keyboard
    global _get_threshold_keyboard, _get_product_info, _logger
    _db = db
    _get_main_keyboard = get_main_keyboard
    _get_product_keyboard = get_product_keyboard
    _get_threshold_keyboard = get_threshold_keyboard
    _get_product_info = get_product_info
    _logger = logger


@router.message(lambda message: message.text == "📋 Мои товары")
async def show_products(message: types.Message):
    """Показать список товаров пользователя."""
    products = _db.get_user_products(message.from_user.id)
    if not products:
        await message.reply("У вас пока нет отслеживаемых товаров.")
        return

    text = "📋 Ваши товары:\n\n"
    keyboard = []
    for product_id, _, name, price, threshold in products:
        text += f"📦 {name}\n💰 Цена: {price}₽\n⚡️ Порог: {threshold}₽\n\n"
        keyboard.append([
            InlineKeyboardButton(
                text=f"📦 {name} | {price}₽ | ⚡️ {threshold}₽",
                callback_data=f"select_product_{product_id}",
            )
        ])

    await message.reply(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@router.message(lambda message: message.text == "➕ Добавить товар")
async def start_add_product(message: types.Message, state: FSMContext):
    """Начало процесса добавления товара."""
    await message.reply("Отправьте ссылку на товар с Яндекс.Маркета:")
    await state.set_state(ProductStates.waiting_for_url)


@router.message(ProductStates.waiting_for_url)
async def process_url(message: types.Message, state: FSMContext):
    """Обработка URL товара."""
    if not message.text:
        await message.reply("❌ Отправьте текстовую https-ссылку на товар Яндекс.Маркета.")
        return

    try:
        url = normalize_yandex_market_url(message.text)
    except InvalidMarketUrl:
        await message.reply("❌ Отправьте https-ссылку на товар Яндекс.Маркета.")
        return

    product_info = await _get_product_info(url)
    if not product_info:
        await message.reply("❌ Не удалось получить информацию о товаре. Проверьте ссылку.")
        return

    await state.update_data(url=url, name=product_info["name"], price=product_info["price"])
    await message.reply(
        f"Выберите порог изменения цены:\nТекущая цена: {product_info['price']}₽",
        reply_markup=_get_threshold_keyboard(),
    )
    await state.set_state(ProductStates.waiting_for_threshold)


@router.message(ProductStates.waiting_for_threshold)
async def process_threshold(message: types.Message, state: FSMContext):
    """Обработка порога изменения цены."""
    if not message.text:
        await message.reply("❌ Пожалуйста, введите порог числом.")
        return

    try:
        threshold = int(message.text)
        if threshold <= 0:
            await message.reply("❌ Порог должен быть положительным числом.")
            return
    except ValueError:
        await message.reply("❌ Пожалуйста, введите число.")
        return

    data = await state.get_data()
    if _db.add_product(
        message.from_user.id,
        data["url"],
        data["name"],
        data["price"],
        threshold,
    ):
        await message.reply(
            f"✅ Товар добавлен!\n"
            f"📦 {data['name']}\n"
            f"💰 Цена: {data['price']}₽\n"
            f"⚡️ Порог: {threshold}₽",
            reply_markup=_get_main_keyboard(message.from_user.id),
        )
    else:
        await message.reply("❌ Произошла ошибка при добавлении товара.")

    await state.clear()


@router.callback_query(lambda c: c.data.startswith("delete_"))
async def process_delete_callback(callback_query: types.CallbackQuery):
    """Обработка запроса на удаление товара."""
    product_id = int(callback_query.data.split("_")[1])
    if _db.delete_product(product_id, callback_query.from_user.id):
        await callback_query.message.edit_text("✅ Товар удален.")
    else:
        await callback_query.message.reply("❌ Не удалось удалить товар.")


@router.callback_query(lambda c: c.data.startswith("change_threshold_"))
async def process_threshold_update(callback_query: types.CallbackQuery):
    """Обработка запроса на изменение порога."""
    product_id = int(callback_query.data.split("_")[2])
    product = _db.get_product(product_id, callback_query.from_user.id)
    if product:
        _, _, name, price, threshold = product
        await callback_query.message.edit_text(
            f"📦 {name}\n"
            f"💰 Текущая цена: {price}₽\n"
            f"⚡️ Текущий порог: {threshold}₽\n\n"
            "Выберите новый порог:",
            reply_markup=_get_threshold_keyboard(product_id),
        )
    else:
        await callback_query.message.edit_text("❌ Товар не найден.")


@router.callback_query(lambda c: c.data.startswith("threshold_"))
async def process_threshold_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора порога."""
    try:
        parts = callback_query.data.split("_")
        threshold = int(parts[1])
        data = await state.get_data()

        if "url" in data:
            if _db.add_product(
                callback_query.from_user.id,
                data["url"],
                data["name"],
                data["price"],
                threshold,
            ):
                await callback_query.message.edit_text(
                    f"✅ Товар добавлен!\n"
                    f"📦 {data['name']}\n"
                    f"💰 Цена: {data['price']}₽\n"
                    f"⚡️ Порог: {threshold}₽"
                )
                await callback_query.message.answer(
                    "Используйте кнопки ниже для навигации:",
                    reply_markup=_get_main_keyboard(callback_query.from_user.id),
                )
            else:
                await callback_query.message.edit_text(
                    "❌ Произошла ошибка при добавлении товара."
                )
        elif len(parts) > 2:
            product_id = int(parts[2])
            if _db.set_threshold(product_id, callback_query.from_user.id, threshold):
                product = _db.get_product(product_id, callback_query.from_user.id)
                if product:
                    _, _, name, price, _ = product
                    await callback_query.message.edit_text(
                        f"✅ Порог успешно обновлен!\n"
                        f"📦 {name}\n"
                        f"💰 Цена: {price}₽\n"
                        f"⚡️ Новый порог: {threshold}₽",
                        reply_markup=_get_product_keyboard(product_id),
                    )
                else:
                    await callback_query.message.edit_text("❌ Товар не найден.")
            else:
                await callback_query.message.edit_text("❌ Не удалось обновить порог.")
        else:
            await callback_query.message.edit_text("❌ Неверный формат данных.")

        await state.clear()
    except Exception as e:
        _logger.error(f"Ошибка при обработке порога: {e}")
        await callback_query.message.edit_text("❌ Произошла ошибка при обработке порога.")
        await state.clear()


@router.callback_query(lambda c: c.data.startswith("select_product_"))
async def process_product_selection(callback_query: types.CallbackQuery):
    """Обработка выбора товара."""
    product_id = int(callback_query.data.split("_")[2])
    product = _db.get_product(product_id, callback_query.from_user.id)
    if product:
        _, _, name, price, threshold = product
        text = f"📦 {name}\n💰 Цена: {price}₽\n⚡️ Порог: {threshold}₽"
        await callback_query.message.edit_text(
            text,
            reply_markup=_get_product_keyboard(product_id),
        )
    else:
        await callback_query.message.edit_text("❌ Товар не найден.")


@router.callback_query(lambda c: c.data == "back_to_list")
async def process_back_to_list(callback_query: types.CallbackQuery):
    """Обработка возврата к списку товаров."""
    products = _db.get_user_products(callback_query.from_user.id)
    if not products:
        await callback_query.message.edit_text("У вас пока нет отслеживаемых товаров.")
        return

    text = "Выберите товар для управления:"
    keyboard = []
    for product_id, _, name, price, threshold in products:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📦 {name} | {price}₽ | ⚡️ {threshold}₽",
                callback_data=f"select_product_{product_id}",
            )
        ])

    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )


@router.callback_query(lambda c: c.data == "back_to_add")
async def process_back_to_add(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка возврата к добавлению товара."""
    await callback_query.message.edit_text("Отправьте ссылку на товар с Яндекс.Маркета:")
    await state.set_state(ProductStates.waiting_for_url)
