from datetime import UTC
from zoneinfo import ZoneInfo

from app.services.graphs import parse_db_timestamp


def test_parse_db_timestamp_treats_sqlite_timestamp_as_utc():
    timestamp = parse_db_timestamp("2026-07-26 11:30:00", ZoneInfo("Europe/Moscow"))

    assert timestamp.tzinfo is not None
    assert timestamp.hour == 14
    assert timestamp.utcoffset() == ZoneInfo("Europe/Moscow").utcoffset(timestamp)
    assert timestamp.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S") == "2026-07-26 11:30:00"
