import asyncio
import logging
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse

import aiohttp
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup

from app.core.config import YA_COOKIE

logger = logging.getLogger("bot")

ALLOWED_MARKET_HOSTS = frozenset({"market.yandex.ru", "market.yandex.com"})
ALLOWED_REDIRECT_HOSTS = ALLOWED_MARKET_HOSTS | frozenset({"ya.cc"})


class InvalidMarketUrl(ValueError):
    """URL не указывает на разрешенный домен Яндекс.Маркета."""


def _normalize_allowed_url(url: str, allowed_hosts: frozenset[str]) -> str:
    parsed = urlparse(url.strip())
    hostname = (parsed.hostname or "").lower().rstrip(".")

    if parsed.scheme != "https":
        raise InvalidMarketUrl("Ссылка должна использовать https")
    if parsed.username or parsed.password:
        raise InvalidMarketUrl("Ссылка не должна содержать учетные данные")
    if hostname not in allowed_hosts:
        raise InvalidMarketUrl("Домен ссылки не разрешен")

    normalized = parsed._replace(netloc=hostname, fragment="")
    return urlunparse(normalized)


def normalize_yandex_market_url(url: str) -> str:
    """Проверка и нормализация URL товара Яндекс.Маркета.

    Важно не отправлять `YA_COOKIE` на произвольные пользовательские URL.
    """
    return _normalize_allowed_url(url, ALLOWED_MARKET_HOSTS)


def normalize_market_redirect_url(url: str) -> str:
    """Проверка redirect: разрешаем Market и официальный shortener ya.cc."""
    return _normalize_allowed_url(url, ALLOWED_REDIRECT_HOSTS)


def build_market_headers(url: str) -> dict[str, str]:
    """Заголовки запроса; cookie добавляется только для доменов Market."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/58.0.3029.110 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://market.yandex.ru/",
    }
    hostname = (urlparse(url).hostname or "").lower().rstrip(".")
    if hostname in ALLOWED_MARKET_HOSTS:
        headers["Cookie"] = YA_COOKIE
    return headers


def parse_price_text(price_text: str) -> int:
    cleaned = "".join(char for char in price_text if char.isprintable())
    cleaned = cleaned.replace(" ", "").replace("\xa0", "").replace("₽", "")
    digits = "".join(char for char in cleaned if char.isdigit())
    if not digits:
        raise ValueError(f"Не удалось найти цифры в цене: {price_text!r}")
    return int(digits)


def parse_product_html(html: str) -> Optional[dict]:
    """Извлечение названия и цены из HTML Яндекс.Маркета с fallback-селекторами."""
    soup = BeautifulSoup(html, "html.parser")

    name_elem = soup.find("h1", {"data-auto": "productCardTitle"}) or soup.find(
        "h1",
        {"data-auto": "product-title"},
    )
    if not name_elem:
        og_title = soup.find("meta", property="og:title")
        name = og_title.get("content", "").strip() if og_title else ""
    else:
        name = name_elem.text.strip()

    if not name:
        logger.error("Не удалось найти название товара на странице")
        logger.debug("HTML страницы: %s...", html[:500])
        return None

    price_selectors = [
        ("span", {"data-auto": "snippet-price-current"}),
        ("span", {"data-auto": "price-value"}),
        ("span", {"data-auto": "mainPrice"}),
        ("div", {"data-auto": "price"}),
    ]
    price_elem = None
    for tag, attrs in price_selectors:
        price_elem = soup.find(tag, attrs)
        if price_elem:
            break

    if price_elem:
        try:
            return {"name": name, "price": parse_price_text(price_elem.text)}
        except ValueError as e:
            logger.error("Ошибка при преобразовании цены '%s': %s", price_elem.text, e)

    for meta_name in ("product:price:amount", "og:price:amount"):
        meta_price = soup.find("meta", property=meta_name)
        if meta_price and meta_price.get("content"):
            try:
                return {"name": name, "price": parse_price_text(meta_price["content"])}
            except ValueError:
                continue

    logger.error("Не удалось найти цену товара на странице")
    return None


async def get_product_info(url: str) -> Optional[dict]:
    """Получение информации о товаре с Яндекс.Маркета."""
    try:
        try:
            url = normalize_yandex_market_url(url)
        except InvalidMarketUrl as e:
            logger.warning("Отклонен URL товара: %s", e)
            return None

        timeout = ClientTimeout(total=30)
        logger.info(f"Начало запроса к {url}")

        async with aiohttp.ClientSession(timeout=timeout) as session:
            html = None
            for _ in range(4):
                async with session.get(
                    url,
                    headers=build_market_headers(url),
                    allow_redirects=False,
                ) as response:
                    if 300 <= response.status < 400:
                        redirect_url = response.headers.get("Location")
                        if not redirect_url:
                            logger.error("Яндекс.Маркет вернул redirect без Location для %s", url)
                            return None
                        try:
                            next_url = normalize_market_redirect_url(urljoin(url, redirect_url))
                        except InvalidMarketUrl:
                            parsed = urlparse(urljoin(url, redirect_url))
                            logger.error(
                                "Отклонен redirect Яндекс.Маркета на небезопасный host: %s",
                                parsed.hostname,
                            )
                            return None
                        logger.info("Следую безопасному redirect Яндекс.Маркета: %s", next_url)
                        url = next_url
                        continue

                    if response.status != 200:
                        logger.error(f"Ошибка при получении страницы {url}: {response.status}")
                        logger.error(f"Заголовки ответа: {response.headers}")
                        return None
                    html = await response.text()
                    break
            else:
                logger.error("Слишком много redirect при запросе к Яндекс.Маркету")
                return None

            if html is None:
                logger.error("Не удалось получить HTML страницы Яндекс.Маркета")
                return None

            logger.info(f"Получен ответ от {url}, размер: {len(html)} байт")
            product_info = parse_product_html(html)
            if product_info:
                logger.info(f"Найдено название товара: {product_info['name']}")
                logger.info(f"Найдена цена товара: {product_info['price']}₽")
            return product_info
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка сети при запросе к {url}: {e}")
        return None
    except asyncio.TimeoutError as e:
        logger.error(f"Таймаут при запросе к {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении информации о товаре {url}: {e}")
        return None
