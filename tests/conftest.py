import importlib
import sys
from pathlib import Path


def reload_module(module_name: str):
    if module_name in sys.modules:
        del sys.modules[module_name]
    return importlib.import_module(module_name)


def load_database_module(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("TOKEN", "dummy-token")
    monkeypatch.setenv("YA_COOKIE", "dummy-cookie")
    monkeypatch.setenv("ADMIN_IDS", "1")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("CHECK_INTERVAL", "30")
    monkeypatch.setenv("PRICE_THRESHOLD", "500")

    for module_name in ["config", "database", "app.core.config", "app.db.database"]:
        sys.modules.pop(module_name, None)

    reload_module("config")
    reload_module("app.core.config")
    return reload_module("database")


def load_bot_module(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("TOKEN", "123456:TESTTOKEN")
    monkeypatch.setenv("YA_COOKIE", "dummy-cookie")
    monkeypatch.setenv("ADMIN_IDS", "1")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "bot-test.db"))
    monkeypatch.setenv("CHECK_INTERVAL", "30")
    monkeypatch.setenv("PRICE_THRESHOLD", "500")

    for module_name in [
        "config",
        "database",
        "bot",
        "app.core.config",
        "app.db.database",
        "app.runtime",
        "app.handlers",
        "app.handlers.common",
        "app.handlers.products",
        "app.handlers.graphs",
    ]:
        sys.modules.pop(module_name, None)

    reload_module("config")
    reload_module("database")
    return reload_module("bot")
