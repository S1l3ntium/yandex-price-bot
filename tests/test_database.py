from tests.conftest import load_database_module


def test_add_product_preserves_threshold(monkeypatch, tmp_path):
    database_module = load_database_module(monkeypatch, tmp_path)
    db = database_module.Database()

    try:
        assert db.add_product(1, "https://example.com/item", "Test product", 10000, 777)
        products = db.get_user_products(1)

        assert len(products) == 1
        assert products[0][4] == 777
    finally:
        db.close()


def test_update_price_writes_history(monkeypatch, tmp_path):
    database_module = load_database_module(monkeypatch, tmp_path)
    db = database_module.Database()

    try:
        assert db.add_product(1, "https://example.com/item", "Test product", 10000, 500)
        product_id = db.get_user_products(1)[0][0]

        assert db.update_price(product_id, 9500)

        history = db.get_price_history(product_id, hours=24)
        assert len(history) == 2
        assert history[-1][0] == 9500
    finally:
        db.close()


def test_update_price_rejects_missing_product(monkeypatch, tmp_path):
    database_module = load_database_module(monkeypatch, tmp_path)
    db = database_module.Database()

    try:
        assert not db.update_price(999, 9500)
        assert db.get_price_history(999, hours=24) == []
    finally:
        db.close()


def test_delete_product_removes_related_history(monkeypatch, tmp_path):
    database_module = load_database_module(monkeypatch, tmp_path)
    db = database_module.Database()

    try:
        assert db.add_product(1, "https://example.com/item", "Test product", 10000, 500)
        product_id = db.get_user_products(1)[0][0]
        assert db.has_price_history(product_id)

        assert db.delete_product(product_id, 1)
        assert db.get_user_products(1) == []
        assert not db.has_price_history(product_id)
    finally:
        db.close()


def test_get_product_respects_user_id(monkeypatch, tmp_path):
    database_module = load_database_module(monkeypatch, tmp_path)
    db = database_module.Database()

    try:
        assert db.add_product(1, "https://example.com/item", "Test product", 10000, 500)
        product_id = db.get_user_products(1)[0][0]

        assert db.get_product(product_id, 1) is not None
        assert db.get_product(product_id, 2) is None
    finally:
        db.close()
