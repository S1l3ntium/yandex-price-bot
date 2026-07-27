from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def get_main_keyboard(user_id: int, products, admin_ids: set[int]) -> ReplyKeyboardMarkup:
    """Создание основной клавиатуры."""
    keyboard = []

    if products:
        keyboard.extend([
            [KeyboardButton(text="📋 Мои товары"), KeyboardButton(text="➕ Добавить товар")],
            [KeyboardButton(text="📊 Графики цен")],
        ])
    else:
        keyboard.append([KeyboardButton(text="➕ Добавить товар")])

    if user_id in admin_ids:
        keyboard[-1].append(KeyboardButton(text="⚙️ Настройки"))

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Создание клавиатуры для управления товаром."""
    keyboard = [
        [
            InlineKeyboardButton(text="📊 График (24ч)", callback_data=f"graph_{product_id}_24"),
            InlineKeyboardButton(text="📊 График (7д)", callback_data=f"graph_{product_id}_168"),
        ],
        [
            InlineKeyboardButton(
                text="⚙️ Изменить порог",
                callback_data=f"change_threshold_{product_id}",
            ),
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_{product_id}"),
        ],
        [InlineKeyboardButton(text="◀️ Назад к списку", callback_data="back_to_list")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_time_range_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Создание клавиатуры для выбора временного диапазона."""
    keyboard = [
        [
            InlineKeyboardButton(text="📊 24 часа", callback_data=f"graph_{product_id}_24"),
            InlineKeyboardButton(text="📊 7 дней", callback_data=f"graph_{product_id}_168"),
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_graphs")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_threshold_keyboard(product_id: int | None = None) -> InlineKeyboardMarkup:
    """Создание клавиатуры для выбора порога."""
    keyboard = [
        [
            InlineKeyboardButton(
                text="⚡️ 500₽",
                callback_data=f"threshold_500_{product_id}" if product_id else "threshold_500",
            ),
            InlineKeyboardButton(
                text="⚡️ 1000₽",
                callback_data=f"threshold_1000_{product_id}" if product_id else "threshold_1000",
            ),
        ],
        [
            InlineKeyboardButton(
                text="⚡️ 3000₽",
                callback_data=f"threshold_3000_{product_id}" if product_id else "threshold_3000",
            ),
            InlineKeyboardButton(
                text="⚡️ 5000₽",
                callback_data=f"threshold_5000_{product_id}" if product_id else "threshold_5000",
            ),
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_add")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для настроек."""
    keyboard = [
        [
            InlineKeyboardButton(text="⏱ 5 минут", callback_data="interval_5"),
            InlineKeyboardButton(text="⏱ 10 минут", callback_data="interval_10"),
        ],
        [
            InlineKeyboardButton(text="⏱ 15 минут", callback_data="interval_15"),
            InlineKeyboardButton(text="⏱ 30 минут", callback_data="interval_30"),
        ],
        [InlineKeyboardButton(text="🔄 Проверить сейчас", callback_data="check_now")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
