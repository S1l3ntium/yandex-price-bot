import asyncio
import logging
import aiohttp
from typing import Optional, Dict, List, Tuple
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InputFile, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.middleware import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import validators
import matplotlib.pyplot as plt
import io
from config import TOKEN, YA_COOKIE, CHECK_INTERVAL, ADMIN_IDS
from database import Database
from functools import lru_cache
from aiohttp import ClientTimeout
from aiogram.exceptions import TelegramAPIError

# Настройка логирования
def setup_logging():
    # Создаем форматтер для логов
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Настройка логгера для aiogram
    aiogram_logger = logging.getLogger('aiogram')
    aiogram_logger.setLevel(logging.INFO)
    aiogram_handler = logging.FileHandler('aiogram.log', encoding='utf-8')
    aiogram_handler.setFormatter(formatter)
    aiogram_logger.addHandler(aiogram_handler)
    
    # Настройка логгера для базы данных
    db_logger = logging.getLogger('database')
    db_logger.setLevel(logging.INFO)
    db_handler = logging.FileHandler('database.log', encoding='utf-8')
    db_handler.setFormatter(formatter)
    db_logger.addHandler(db_handler)
    
    # Настройка основного логгера бота
    bot_logger = logging.getLogger('bot')
    bot_logger.setLevel(logging.INFO)
    bot_handler = logging.FileHandler('bot.log', encoding='utf-8')
    bot_handler.setFormatter(formatter)
    bot_logger.addHandler(bot_handler)
    
    # Добавляем вывод в консоль для всех логгеров
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    aiogram_logger.addHandler(console_handler)
    db_logger.addHandler(console_handler)
    bot_logger.addHandler(console_handler)
    
    return bot_logger, db_logger, aiogram_logger

# Инициализация логгеров
logger, db_logger, aiogram_logger = setup_logging()

class AccessMiddleware(BaseMiddleware):
    """Middleware для проверки доступа к боту."""
    async def __call__(self, handler, event: Message | CallbackQuery, data):
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
                    show_alert=True
                )
            return
        return await handler(event, data)

# Инициализация бота и базы данных
bot = Bot(token=TOKEN)
dp = Dispatcher()
dp.message.middleware(AccessMiddleware())
dp.callback_query.middleware(AccessMiddleware())
db = Database()

class ProductStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_threshold = State()

# Получение информации о товаре
async def get_product_info(url: str) -> Optional[Dict]:
    """Получение информации о товаре с Яндекс.Маркета."""
    try:
        headers = {
            "Cookie": YA_COOKIE,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://market.yandex.ru/"
        }
        
        timeout = ClientTimeout(total=30)
        logger.info(f"Начало запроса к {url}")
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    logger.info(f"Получен ответ от {url}, размер: {len(html)} байт")
                    
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Получаем название товара
                    name_elem = soup.find('h1', {'data-auto': 'productCardTitle'})
                    if not name_elem:
                        logger.error(f"Не удалось найти название товара на странице {url}")
                        logger.debug(f"HTML страницы: {html[:500]}...")  # Логируем начало HTML для отладки
                        return None
                    name = name_elem.text.strip()
                    logger.info(f"Найдено название товара: {name}")
                    
                    # Получаем цену
                    price_elem = soup.find('span', {'data-auto': 'snippet-price-current'})
                    if not price_elem:
                        logger.error(f"Не удалось найти цену товара на странице {url}")
                        return None
                    
                    try:
                        # Очищаем цену от всех невидимых символов и пробелов
                        price_text = price_elem.text.strip()
                        # Удаляем все невидимые символы Unicode
                        price_text = ''.join(char for char in price_text if char.isprintable())
                        # Удаляем все пробелы и символ рубля
                        price_text = price_text.replace(' ', '').replace('₽', '')
                        # Преобразуем в число
                        price = int(price_text)
                        logger.info(f"Найдена цена товара: {price}₽")
                    except ValueError as e:
                        logger.error(f"Ошибка при преобразовании цены '{price_elem.text}': {e}")
                        logger.error(f"Очищенная цена: '{price_text}'")
                        return None
                    
                    return {
                        'name': name,
                        'price': price
                    }
                else:
                    logger.error(f"Ошибка при получении страницы {url}: {response.status}")
                    logger.error(f"Заголовки ответа: {response.headers}")
                    return None
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка сети при запросе к {url}: {e}")
        return None
    except asyncio.TimeoutError as e:
        logger.error(f"Таймаут при запросе к {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении информации о товаре {url}: {e}")
        return None

def get_main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    """Создание основной клавиатуры."""
    products = db.get_user_products(user_id)
    keyboard = []
    
    if products:
        keyboard.extend([
            [KeyboardButton(text="📋 Мои товары"), KeyboardButton(text="➕ Добавить товар")],
            [KeyboardButton(text="📊 Графики цен")]
        ])
    else:
        keyboard.append([KeyboardButton(text="➕ Добавить товар")])
    
    # Добавляем кнопку настроек только для администраторов
    if user_id in ADMIN_IDS:
        keyboard[-1].append(KeyboardButton(text="⚙️ Настройки"))
    
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Создание клавиатуры для управления товаром."""
    keyboard = [
        [
            InlineKeyboardButton(text="📊 График (24ч)", callback_data=f"graph_{product_id}_24"),
            InlineKeyboardButton(text="📊 График (7д)", callback_data=f"graph_{product_id}_168")
        ],
        [
            InlineKeyboardButton(text="⚙️ Изменить порог", callback_data=f"change_threshold_{product_id}"),
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_{product_id}")
        ],
        [InlineKeyboardButton(text="◀️ Назад к списку", callback_data="back_to_list")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_time_range_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Создание клавиатуры для выбора временного диапазона."""
    keyboard = [
        [
            InlineKeyboardButton(text="📊 24 часа", callback_data=f"graph_{product_id}_24"),
            InlineKeyboardButton(text="📊 7 дней", callback_data=f"graph_{product_id}_168")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_graphs")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_threshold_keyboard(product_id: int = None) -> InlineKeyboardMarkup:
    """Создание клавиатуры для выбора порога."""
    keyboard = [
        [
            InlineKeyboardButton(text="⚡️ 500₽", callback_data=f"threshold_500_{product_id}" if product_id else "threshold_500"),
            InlineKeyboardButton(text="⚡️ 1000₽", callback_data=f"threshold_1000_{product_id}" if product_id else "threshold_1000")
        ],
        [
            InlineKeyboardButton(text="⚡️ 3000₽", callback_data=f"threshold_3000_{product_id}" if product_id else "threshold_3000"),
            InlineKeyboardButton(text="⚡️ 5000₽", callback_data=f"threshold_5000_{product_id}" if product_id else "threshold_5000")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_add")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для настроек."""
    keyboard = [
        [
            InlineKeyboardButton(text="⏱ 5 минут", callback_data="interval_5"),
            InlineKeyboardButton(text="⏱ 10 минут", callback_data="interval_10")
        ],
        [
            InlineKeyboardButton(text="⏱ 15 минут", callback_data="interval_15"),
            InlineKeyboardButton(text="⏱ 30 минут", callback_data="interval_30")
        ],
        [InlineKeyboardButton(text="🔄 Проверить сейчас", callback_data="check_now")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def generate_price_graph(product_id: int, hours: int) -> Optional[bytes]:
    """Генерация графика изменения цен."""
    try:
        history = db.get_price_history(product_id, hours)
        if not history:
            return None

        prices = [price for price, _ in history]
        timestamps = [datetime.strptime(ts, '%Y-%m-%d %H:%M:%S') for _, ts in history]

        # Получаем информацию о товаре для заголовка
        product = db.get_product(product_id)
        product_name = product[2] if product else "Товар"

        plt.figure(figsize=(10, 6))
        plt.plot(timestamps, prices, marker='o')
        plt.title(f'Изменение цены: {product_name}')
        plt.xlabel('Время')
        plt.ylabel('Цена (₽)')
        plt.grid(True)
        plt.xticks(rotation=45)
        
        # Устанавливаем разумные пределы по времени
        if len(timestamps) > 1:
            time_range = max(timestamps) - min(timestamps)
            plt.xlim(min(timestamps) - time_range * 0.1, max(timestamps) + time_range * 0.1)
        else:
            # Если только одна точка, показываем период в 1 час
            single_time = timestamps[0]
            plt.xlim(single_time - timedelta(hours=0.5), single_time + timedelta(hours=0.5))
        
        # Форматируем метки времени
        plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d.%m %H:%M'))
        
        # Устанавливаем интервал между метками времени
        plt.gca().xaxis.set_major_locator(plt.matplotlib.dates.AutoDateLocator())
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        logger.error(f"Ошибка при генерации графика: {e}")
        return None

@dp.message(Command("start"))
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
    
    # Отправляем приветственное сообщение
    welcome_message = await message.answer(
        welcome_text, 
        reply_markup=get_main_keyboard(message.from_user.id)
    )
    
    # Пытаемся закрепить сообщение
    try:
        await welcome_message.pin(disable_notification=True)
    except Exception as e:
        logger.error(f"Не удалось закрепить сообщение: {e}")
        
    # Отправляем дополнительное сообщение с инструкцией
    await message.answer(
        "ℹ️ Для начала работы нажмите кнопку '➕ Добавить товар' и отправьте ссылку на товар с Яндекс.Маркета."
    )

@dp.message(lambda message: message.text == "📋 Мои товары")
async def show_products(message: types.Message):
    """Показать список товаров пользователя."""
    products = db.get_user_products(message.from_user.id)
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
                callback_data=f"select_product_{product_id}"
            )
        ])
    
    await message.reply(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.message(lambda message: message.text == "➕ Добавить товар")
async def start_add_product(message: types.Message, state: FSMContext):
    """Начало процесса добавления товара."""
    await message.reply("Отправьте ссылку на товар с Яндекс.Маркета:")
    await state.set_state(ProductStates.waiting_for_url)

@dp.message(lambda message: message.text == "📊 Графики цен")
async def show_graphs_menu(message: types.Message):
    """Показать меню графиков."""
    products = db.get_user_products(message.from_user.id)
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
            InlineKeyboardButton(
                text=f"📊 {name}",
                callback_data=f"select_graph_{product_id}"
            )
        ])
    
    await message.reply(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.message(lambda message: message.text == "⚙️ Настройки")
async def show_settings(message: types.Message):
    """Показать настройки."""
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ У вас нет доступа к настройкам.")
        return
        
    products_count = len(db.get_user_products(message.from_user.id))
    current_interval = db.get_check_interval()
    text = (
        "⚙️ Настройки бота:\n\n"
        f"• Отслеживаемых товаров: {products_count}\n"
        f"• Интервал проверки цен: каждые {current_interval} минут\n"
        f"• Последняя проверка: {datetime.now().strftime('%H:%M:%S')}\n"
        f"• Статус: активен\n\n"
        "Выберите новый интервал проверки цен:"
    )
    await message.reply(text, reply_markup=get_settings_keyboard())

@dp.message(ProductStates.waiting_for_url)
async def process_url(message: types.Message, state: FSMContext):
    """Обработка URL товара."""
    url = message.text.strip()
    if not validators.url(url):
        await message.reply("❌ Пожалуйста, отправьте действительный URL товара.")
        return

    product_info = await get_product_info(url)
    if not product_info:
        await message.reply("❌ Не удалось получить информацию о товаре. Проверьте ссылку.")
        return

    await state.update_data(url=url, name=product_info["name"], price=product_info["price"])
    await message.reply(
        f"Выберите порог изменения цены:\n"
        f"Текущая цена: {product_info['price']}₽",
        reply_markup=get_threshold_keyboard()
    )
    await state.set_state(ProductStates.waiting_for_threshold)

@dp.message(ProductStates.waiting_for_threshold)
async def process_threshold(message: types.Message, state: FSMContext):
    """Обработка порога изменения цены."""
    try:
        threshold = int(message.text)
        if threshold <= 0:
            await message.reply("❌ Порог должен быть положительным числом.")
            return
    except ValueError:
        await message.reply("❌ Пожалуйста, введите число.")
        return

    data = await state.get_data()
    if db.add_product(message.from_user.id, data["url"], data["name"], data["price"]):
        await message.reply(
            f"✅ Товар добавлен!\n"
            f"📦 {data['name']}\n"
            f"💰 Цена: {data['price']}₽\n"
            f"⚡️ Порог: {threshold}₽",
            reply_markup=get_main_keyboard(message.from_user.id)
        )
    else:
        await message.reply("❌ Произошла ошибка при добавлении товара.")

    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("graph_"))
async def process_graph_callback(callback_query: types.CallbackQuery):
    """Обработка запроса на показ графика."""
    _, product_id, hours = callback_query.data.split("_")
    product_id = int(product_id)
    hours = int(hours)

    graph_data = await generate_price_graph(product_id, hours)
    if graph_data:
        await callback_query.message.answer_photo(
            types.BufferedInputFile(graph_data, filename="graph.png"),
            caption=f"График изменения цены за последние {hours} часов"
        )
        # Добавляем кнопки управления после графика
        await callback_query.message.answer(
            "Выберите действие:",
            reply_markup=get_product_keyboard(product_id)
        )
    else:
        await callback_query.message.reply("❌ Не удалось сгенерировать график.")

@dp.callback_query(lambda c: c.data.startswith("delete_"))
async def process_delete_callback(callback_query: types.CallbackQuery):
    """Обработка запроса на удаление товара."""
    product_id = int(callback_query.data.split("_")[1])
    if db.delete_product(product_id, callback_query.from_user.id):
        await callback_query.message.edit_text("✅ Товар удален.")
    else:
        await callback_query.message.reply("❌ Не удалось удалить товар.")

@dp.callback_query(lambda c: c.data.startswith("change_threshold_"))
async def process_threshold_update(callback_query: types.CallbackQuery):
    """Обработка запроса на изменение порога."""
    product_id = int(callback_query.data.split("_")[2])
    product = db.get_product(product_id)
    if product:
        _, _, name, price, threshold = product
        await callback_query.message.edit_text(
            f"📦 {name}\n"
            f"💰 Текущая цена: {price}₽\n"
            f"⚡️ Текущий порог: {threshold}₽\n\n"
            "Выберите новый порог:",
            reply_markup=get_threshold_keyboard(product_id)
        )
    else:
        await callback_query.message.edit_text("❌ Товар не найден.")

@dp.callback_query(lambda c: c.data.startswith("threshold_"))
async def process_threshold_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора порога."""
    try:
        parts = callback_query.data.split("_")
        threshold = int(parts[1])
        data = await state.get_data()
        
        # Проверяем, есть ли уже данные о товаре
        if "url" in data:
            # Добавляем новый товар
            if db.add_product(callback_query.from_user.id, data["url"], data["name"], data["price"], threshold):
                await callback_query.message.edit_text(
                    f"✅ Товар добавлен!\n"
                    f"📦 {data['name']}\n"
                    f"💰 Цена: {data['price']}₽\n"
                    f"⚡️ Порог: {threshold}₽"
                )
                await callback_query.message.answer(
                    "Используйте кнопки ниже для навигации:",
                    reply_markup=get_main_keyboard(callback_query.from_user.id)
                )
            else:
                await callback_query.message.edit_text("❌ Произошла ошибка при добавлении товара.")
        elif len(parts) > 2:
            # Обновляем порог для существующего товара
            product_id = int(parts[2])
            if db.set_threshold(product_id, callback_query.from_user.id, threshold):
                product = db.get_product(product_id)
                if product:
                    _, _, name, price, _ = product
                    await callback_query.message.edit_text(
                        f"✅ Порог успешно обновлен!\n"
                        f"📦 {name}\n"
                        f"💰 Цена: {price}₽\n"
                        f"⚡️ Новый порог: {threshold}₽",
                        reply_markup=get_product_keyboard(product_id)
                    )
                else:
                    await callback_query.message.edit_text("❌ Товар не найден.")
            else:
                await callback_query.message.edit_text("❌ Не удалось обновить порог.")
        else:
            await callback_query.message.edit_text("❌ Неверный формат данных.")
        
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при обработке порога: {e}")
        await callback_query.message.edit_text("❌ Произошла ошибка при обработке порога.")
        await state.clear()

@dp.callback_query(lambda c: c.data.startswith("select_graph_"))
async def process_graph_selection(callback_query: types.CallbackQuery):
    """Обработка выбора товара для графика."""
    product_id = int(callback_query.data.split("_")[2])
    await callback_query.message.reply(
        "Выберите период для графика:",
        reply_markup=get_time_range_keyboard(product_id)
    )

@dp.callback_query(lambda c: c.data.startswith("select_product_"))
async def process_product_selection(callback_query: types.CallbackQuery):
    """Обработка выбора товара."""
    product_id = int(callback_query.data.split("_")[2])
    product = db.get_product(product_id)
    if product:
        _, _, name, price, threshold = product
        text = f"📦 {name}\n💰 Цена: {price}₽\n⚡️ Порог: {threshold}₽"
        await callback_query.message.edit_text(text, reply_markup=get_product_keyboard(product_id))
    else:
        await callback_query.message.edit_text("❌ Товар не найден.")

@dp.callback_query(lambda c: c.data == "back_to_list")
async def process_back_to_list(callback_query: types.CallbackQuery):
    """Обработка возврата к списку товаров."""
    products = db.get_user_products(callback_query.from_user.id)
    if not products:
        await callback_query.message.edit_text("У вас пока нет отслеживаемых товаров.")
        return

    text = "Выберите товар для управления:"
    keyboard = []
    for product_id, _, name, price, threshold in products:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📦 {name} | {price}₽ | ⚡️ {threshold}₽",
                callback_data=f"select_product_{product_id}"
            )
        ])
    
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.callback_query(lambda c: c.data == "back_to_graphs")
async def process_back_to_graphs(callback_query: types.CallbackQuery):
    """Обработка возврата к списку товаров для графиков."""
    products = db.get_user_products(callback_query.from_user.id)
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
            InlineKeyboardButton(
                text=f"📊 {name}",
                callback_data=f"select_graph_{product_id}"
            )
        ])
    
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.callback_query(lambda c: c.data == "back_to_add")
async def process_back_to_add(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка возврата к добавлению товара."""
    await callback_query.message.edit_text("Отправьте ссылку на товар с Яндекс.Маркета:")
    await state.set_state(ProductStates.waiting_for_url)

@dp.callback_query(lambda c: c.data.startswith("interval_"))
async def process_interval_selection(callback_query: types.CallbackQuery):
    """Обработка выбора интервала проверки."""
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ У вас нет доступа к настройкам.", show_alert=True)
        return
        
    try:
        interval = int(callback_query.data.split("_")[1])
        if interval not in [5, 10, 15, 30]:
            raise ValueError("Недопустимый интервал")
            
        if db.set_check_interval(interval):
            await callback_query.message.edit_text(
                f"✅ Интервал проверки цен успешно изменен на {interval} минут.\n\n"
                "⚙️ Настройки бота:\n"
                f"• Отслеживаемых товаров: {len(db.get_user_products(callback_query.from_user.id))}\n"
                f"• Интервал проверки цен: каждые {interval} минут\n"
                f"• Последняя проверка: {datetime.now().strftime('%H:%M:%S')}\n"
                f"• Статус: активен\n\n"
                "Выберите новый интервал проверки цен:",
                reply_markup=get_settings_keyboard()
            )
            await callback_query.answer("✅ Интервал обновлен")
        else:
            await callback_query.answer("❌ Ошибка при обновлении интервала", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при установке интервала: {e}")
        await callback_query.answer("❌ Произошла ошибка", show_alert=True)

@dp.callback_query(lambda c: c.data == "back_to_main")
async def process_back_to_main(callback_query: types.CallbackQuery):
    """Обработка возврата в главное меню."""
    await callback_query.message.edit_text(
        "Выберите действие:",
        reply_markup=get_main_keyboard(callback_query.from_user.id)
    )

@dp.message(Command("help"))
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
    await message.answer(help_text, reply_markup=get_main_keyboard(message.from_user.id))

# async def check_prices():
#     """Проверка цен всех товаров."""
#     logger.info("=== Начало проверки цен ===")
#     try:
#         products = db.get_all_products()
#         logger.info(f"Найдено товаров для проверки: {len(products)}")
        
#         # Собираем уникальные user_id для обновления интерфейса
#         user_ids = set()
        
#         for product_id, user_id, url, last_price, threshold in products:
#             logger.info(f"Подготовка проверки товара {product_id} для пользователя {user_id}")
#             logger.info(f"  • URL: {url}")
#             logger.info(f"  • Последняя цена: {last_price}₽")
#             logger.info(f"  • Порог: {threshold}₽")
#             await check_single_product(product_id, user_id, url, last_price, threshold)
#             user_ids.add(user_id)
        
#         # Обновляем интерфейс для каждого пользователя
#         for user_id in user_ids:
#             try:
#                 user_products = db.get_user_products(user_id)
#                 if user_products:
#                     text = "📋 Ваши товары:\n\n"
#                     keyboard = []
#                     for product_id, _, name, price, threshold in user_products:
#                         text += f"📦 {name}\n💰 Цена: {price}₽\n⚡️ Порог: {threshold}₽\n\n"
#                         keyboard.append([
#                             InlineKeyboardButton(
#                                 text=f"📦 {name} | {price}₽ | ⚡️ {threshold}₽",
#                                 callback_data=f"select_product_{product_id}"
#                             )
#                         ])
#                     await bot.send_message(user_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
#             except Exception as e:
#                 logger.error(f"Ошибка при обновлении интерфейса для пользователя {user_id}: {e}")
            
#         logger.info("=== Проверка цен завершена ===")
#     except Exception as e:
#         logger.error(f"Ошибка при проверке цен: {e}")

async def check_prices():
    """Проверка цен всех товаров."""
    logger.info("=== Начало проверки цен ===")
    try:
        products = db.get_all_products()
        logger.info(f"Найдено товаров для проверки: {len(products)}")
        
        for product_id, user_id, url, last_price, threshold in products:
            logger.info(f"Подготовка проверки товара {product_id} для пользователя {user_id}")
            await check_single_product(product_id, user_id, url, last_price, threshold)
        
        logger.info("=== Проверка цен завершена ===")
    except Exception as e:
        logger.error(f"Ошибка при проверке цен: {e}")

async def check_single_product(product_id: int, user_id: int, url: str, last_price: int, threshold: int):
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
                    logger.info(f"  • Статус: Цена выросла на {price_diff}₽ (превышен порог {threshold}₽)")
                else:
                    message = (
                        f"📉 Цена упала!\n"
                        f"📦 {product_info['name']}\n"
                        f"Была: {last_price}₽, стала: {current_price}₽\n"
                        f"Разница: {price_diff}₽"
                    )
                    logger.info(f"  • Статус: Цена упала на {abs_price_diff}₽ (превышен порог {threshold}₽)")
                
                logger.info(f"  • Отправка уведомления пользователю {user_id}")
                await bot.send_message(user_id, message)
                aiogram_logger.info(f"  • Уведомление отправлено пользователю {user_id}")
                
                if db.update_price(product_id, current_price):
                    db_logger.info(f"  • Цена успешно обновлена в базе данных")
                else:
                    db_logger.error(f"  • Ошибка обновления цены в базе данных")
            except TelegramAPIError as e:
                aiogram_logger.error(f"  • Ошибка отправки уведомления: {e}")
        else:
            # Если цена изменилась, но не достигла порога, просто обновляем её
            if price_diff != 0:
                db.update_price(product_id, current_price)
                logger.info(f"  • Статус: Цена изменилась на {price_diff}₽ (не достигнут порог {threshold}₽)")
            else:
                logger.info(f"  • Статус: Цена не изменилась")
    except Exception as e:
        logger.error(f"Ошибка при проверке товара {product_id}: {e}")

@dp.callback_query(lambda c: c.data == "check_now")
async def process_check_now(callback_query: types.CallbackQuery):
    """Обработка запроса на немедленную проверку цен."""
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ У вас нет доступа к настройкам.", show_alert=True)
        return
    
    await callback_query.message.edit_text("🔄 Запускаю проверку цен...")
    await check_prices()
    
    # Показываем настройки
    products = db.get_user_products(callback_query.from_user.id)
    products_count = len(products)
    current_interval = db.get_check_interval()
    text = (
        "✅ Проверка цен завершена!\n\n"
        "⚙️ Настройки бота:\n"
        f"• Отслеживаемых товаров: {products_count}\n"
        f"• Интервал проверки цен: каждые {current_interval} минут\n"
        f"• Последняя проверка: {datetime.now().strftime('%H:%M:%S')}\n"
        f"• Статус: активен\n\n"
        "Выберите действие:"
    )
    await callback_query.message.answer(text, reply_markup=get_settings_keyboard())
    await callback_query.answer("✅ Проверка завершена")

async def main():
    """Основная функция запуска бота."""
    try:
        # Проверка цен при перезапуске
        await check_prices()  # Добавлено для проверки цен сразу после запуска
        
        scheduler = AsyncIOScheduler()
        # Получаем интервал из базы данных
        check_interval = db.get_check_interval()
        scheduler.add_job(check_prices, "interval", minutes=check_interval)
        scheduler.start()
        
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")