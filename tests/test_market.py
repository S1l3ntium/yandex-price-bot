import sys

import pytest


def load_market_module(monkeypatch):
    monkeypatch.setenv("TOKEN", "dummy-token")
    monkeypatch.setenv("YA_COOKIE", "dummy-cookie")
    monkeypatch.setenv("ADMIN_IDS", "1")
    for module_name in ["app.core.config", "app.services.market"]:
        sys.modules.pop(module_name, None)
    import app.services.market as market

    return market


def test_normalize_yandex_market_url_allows_market_https(monkeypatch):
    market = load_market_module(monkeypatch)

    url = market.normalize_yandex_market_url("https://market.yandex.ru/product/123#reviews")

    assert url == "https://market.yandex.ru/product/123"


@pytest.mark.parametrize(
    "url",
    [
        "http://market.yandex.ru/product/123",
        "https://example.com/product/123",
        "https://127.0.0.1/product/123",
        "https://user:pass@market.yandex.ru/product/123",
    ],
)
def test_normalize_yandex_market_url_rejects_unsafe_urls(monkeypatch, url):
    market = load_market_module(monkeypatch)

    with pytest.raises(market.InvalidMarketUrl):
        market.normalize_yandex_market_url(url)


def test_market_redirect_allows_ya_cc_but_cookie_headers_do_not(monkeypatch):
    market = load_market_module(monkeypatch)

    redirect_url = market.normalize_market_redirect_url("https://ya.cc/m/ANSn3g")

    assert redirect_url == "https://ya.cc/m/ANSn3g"
    assert "Cookie" not in market.build_market_headers(redirect_url)
    assert "Cookie" in market.build_market_headers("https://market.yandex.ru/product/123")


def test_parse_product_html_primary_selectors(monkeypatch):
    market = load_market_module(monkeypatch)
    html = """
    <html><body>
      <h1 data-auto="productCardTitle">Камера</h1>
      <span data-auto="snippet-price-current">18 734 ₽</span>
    </body></html>
    """

    assert market.parse_product_html(html) == {"name": "Камера", "price": 18734}


def test_parse_product_html_meta_fallback(monkeypatch):
    market = load_market_module(monkeypatch)
    html = """
    <html><head>
      <meta property="og:title" content="Камера fallback">
      <meta property="product:price:amount" content="19990">
    </head></html>
    """

    assert market.parse_product_html(html) == {"name": "Камера fallback", "price": 19990}
