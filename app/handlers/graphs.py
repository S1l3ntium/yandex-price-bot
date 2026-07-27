from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()

_db = None
_get_time_range_keyboard = None
_get_product_keyboard = None
_generate_price_graph = None


def configure_graph_handlers(
    *,
    db,
    get_time_range_keyboard,
    get_product_keyboard,
    generate_price_graph,
):
    global _db, _get_time_range_keyboard, _get_product_keyboard, _generate_price_graph
    _db = db
    _get_time_range_keyboard = get_time_range_keyboard
    _get_product_keyboard = get_product_keyboard
    _generate_price_graph = generate_price_graph


@router.message(lambda message: message.text == "📊 Графики цен")
async def show_graphs_menu(message: types.Message):
    """Показать меню графиков."""
    products = _db.get_user_products(message.from_user.id)
    if not products:
        await message.reply(
            "У вас пока нет отслеживаемых товаров.\n"
            "Добавьте товар, чтобы просматривать графики изменения цен."
        )
        return

    text = "Выберите товар для просмотра графика:"
    keyboard = []
    for product_id, _, name, _, _ in products:
        keyboard.append([
            InlineKeyboardButton(text=f"📊 {name}", callback_data=f"select_graph_{product_id}")
        ])

    await message.reply(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@router.callback_query(lambda c: c.data.startswith("graph_"))
async def process_graph_callback(callback_query: types.CallbackQuery):
    """Обработка запроса на показ графика."""
    _, product_id, hours = callback_query.data.split("_")
    product_id = int(product_id)
    hours = int(hours)

    graph_data = await _generate_price_graph(product_id, hours, callback_query.from_user.id)
    if graph_data:
        await callback_query.message.answer_photo(
            types.BufferedInputFile(graph_data, filename="graph.png"),
            caption=f"График изменения цены за последние {hours} часов",
        )
        await callback_query.message.answer(
            "Выберите действие:",
            reply_markup=_get_product_keyboard(product_id),
        )
    else:
        await callback_query.message.reply("❌ Не удалось сгенерировать график.")


@router.callback_query(lambda c: c.data.startswith("select_graph_"))
async def process_graph_selection(callback_query: types.CallbackQuery):
    """Обработка выбора товара для графика."""
    product_id = int(callback_query.data.split("_")[2])
    await callback_query.message.reply(
        "Выберите период для графика:",
        reply_markup=_get_time_range_keyboard(product_id),
    )


@router.callback_query(lambda c: c.data == "back_to_graphs")
async def process_back_to_graphs(callback_query: types.CallbackQuery):
    """Обработка возврата к списку товаров для графиков."""
    products = _db.get_user_products(callback_query.from_user.id)
    if not products:
        await callback_query.message.edit_text(
            "У вас пока нет отслеживаемых товаров.\n"
            "Добавьте товар, чтобы просматривать графики изменения цен."
        )
        return

    text = "Выберите товар для просмотра графика:"
    keyboard = []
    for product_id, _, name, _, _ in products:
        keyboard.append([
            InlineKeyboardButton(text=f"📊 {name}", callback_data=f"select_graph_{product_id}")
        ])

    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
