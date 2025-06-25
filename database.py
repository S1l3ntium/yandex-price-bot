import sqlite3
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
import logging
from config import CHECK_INTERVAL

# Получаем логгер для базы данных
logger = logging.getLogger('database')

class Database:
    def __init__(self):
        """Инициализация базы данных."""
        self.db_path = "prices.db"
        self.conn = None
        self.cursor = None
        self.connect()
        self.init_db()
        logger.info("База данных инициализирована")

    def connect(self) -> None:
        """Установка соединения с базой данных."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            logger.info("Успешное подключение к базе данных")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при подключении к базе данных: {e}")
            raise

    def init_db(self):
        """Инициализация базы данных."""
        try:
            # Создаем таблицу для хранения настроек
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            # Создаем таблицу для хранения цен
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    name TEXT NOT NULL,
                    last_price INTEGER NOT NULL,
                    threshold INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Создаем таблицу для истории цен
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    price INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES prices (id)
                )
            """)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
            raise

    def get_check_interval(self) -> int:
        """Получение интервала проверки цен."""
        try:
            self.cursor.execute("SELECT value FROM settings WHERE key = 'check_interval'")
            result = self.cursor.fetchone()
            return int(result[0]) if result else CHECK_INTERVAL
        except Exception as e:
            logger.error(f"Ошибка при получении интервала проверки: {e}")
            return CHECK_INTERVAL

    def set_check_interval(self, interval: int) -> bool:
        """Установка интервала проверки цен."""
        try:
            self.cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ('check_interval', str(interval))
            )
            self.conn.commit()
            logger.info(f"Установлен новый интервал проверки: {interval} минут")
            return True
        except Exception as e:
            logger.error(f"Ошибка при установке интервала проверки: {e}")
            return False

    def create_tables(self) -> None:
        """Создание необходимых таблиц в базе данных."""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    name TEXT NOT NULL,
                    last_price INTEGER NOT NULL,
                    threshold INTEGER DEFAULT 500
                )
            """)
            
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    price INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES prices(id)
                )
            """)
            self.conn.commit()
            logger.info("Таблицы успешно созданы")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при создании таблиц: {e}")
            raise

    def add_product(self, user_id: int, url: str, name: str, price: int, threshold: int = 500) -> bool:
        """Добавление нового товара для отслеживания."""
        try:
            self.cursor.execute(
                "INSERT INTO prices (user_id, url, name, last_price, threshold) VALUES (?, ?, ?, ?, ?)",
                (user_id, url, name, price, threshold)
            )
            product_id = self.cursor.lastrowid
            
            self.cursor.execute(
                "INSERT INTO price_history (product_id, price) VALUES (?, ?)",
                (product_id, price)
            )
            
            self.conn.commit()
            logger.info(f"Добавлен новый товар для пользователя {user_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при добавлении товара: {e}")
            return False

    def get_user_products(self, user_id: int) -> List[Tuple]:
        """Получение списка товаров пользователя."""
        try:
            self.cursor.execute("SELECT id, url, name, last_price, threshold FROM prices WHERE user_id = ?", (user_id,))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении списка товаров: {e}")
            return []

    def delete_product(self, product_id: int, user_id: int) -> bool:
        """Удаление товара из отслеживания."""
        try:
            self.cursor.execute(
                "DELETE FROM prices WHERE id = ? AND user_id = ?",
                (product_id, user_id)
            )
            self.conn.commit()
            logger.info(f"Удален товар {product_id} для пользователя {user_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при удалении товара: {e}")
            return False

    def has_price_history(self, product_id: int) -> bool:
        """Проверка наличия истории цен для товара."""
        try:
            self.cursor.execute(
                "SELECT COUNT(*) FROM price_history WHERE product_id = ?",
                (product_id,)
            )
            return self.cursor.fetchone()[0] > 0
        except sqlite3.Error as e:
            logger.error(f"Ошибка при проверке истории цен: {e}")
            return False

    def update_price(self, product_id: int, new_price: int) -> bool:
        """Обновление цены товара и добавление записи в историю."""
        try:
            cursor = self.conn.cursor()
            
            # Обновляем текущую цену
            cursor.execute('''
                UPDATE prices
                SET last_price = ?
                WHERE id = ?
            ''', (new_price, product_id))
            
            # Всегда добавляем запись в историю
            cursor.execute('''
                INSERT INTO price_history (product_id, price)
                VALUES (?, ?)
            ''', (product_id, new_price))
            
            self.conn.commit()
            logger.info(f"Обновлена цена товара {product_id}: {new_price}₽")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении цены товара {product_id}: {e}")
            return False

    def set_threshold(self, product_id: int, user_id: int, threshold: int) -> bool:
        """Установка индивидуального порога изменения цены."""
        try:
            self.cursor.execute(
                "UPDATE prices SET threshold = ? WHERE id = ? AND user_id = ?",
                (threshold, product_id, user_id)
            )
            self.conn.commit()
            logger.info(f"Установлен новый порог {threshold} для товара {product_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при установке порога: {e}")
            return False

    def get_all_products(self) -> List[Tuple]:
        """Получение всех отслеживаемых товаров."""
        try:
            self.cursor.execute("SELECT id, user_id, url, last_price, threshold FROM prices")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении всех товаров: {e}")
            return []

    def get_price_history(self, product_id: int, hours: int = 24) -> List[Tuple]:
        """Получение истории цен товара за указанный период."""
        try:
            self.cursor.execute("""
                SELECT price, timestamp 
                FROM price_history 
                WHERE product_id = ? 
                AND timestamp >= datetime('now', ?)
                ORDER BY timestamp
            """, (product_id, f'-{hours} hours'))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении истории цен: {e}")
            return []

    def get_product(self, product_id: int) -> Optional[Tuple]:
        """Получение информации о конкретном товаре."""
        try:
            self.cursor.execute(
                "SELECT id, url, name, last_price, threshold FROM prices WHERE id = ?",
                (product_id,)
            )
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Ошибка при получении товара: {e}")
            return None

    def close(self) -> None:
        """Закрытие соединения с базой данных."""
        if self.conn:
            self.conn.close()
            logger.info("Соединение с базой данных закрыто")

if __name__ == "__main__":
    init_db()