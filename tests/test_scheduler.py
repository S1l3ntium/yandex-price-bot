from datetime import datetime, timedelta

from tests.conftest import load_bot_module


class FakeJob:
    def __init__(self):
        self.next_run_time = datetime.now() + timedelta(minutes=5)


class FakeScheduler:
    def __init__(self, has_job=True, should_fail=False):
        self.job = FakeJob() if has_job else None
        self.should_fail = should_fail
        self.rescheduled_to = None
        self.added_to = None

    def get_job(self, _job_id):
        return self.job

    def reschedule_job(self, _job_id, trigger, minutes):
        if self.should_fail:
            raise RuntimeError("reschedule failed")
        assert trigger == "interval"
        self.rescheduled_to = minutes
        self.job = FakeJob()

    def add_job(self, _func, trigger, minutes, id):
        if self.should_fail:
            raise RuntimeError("add failed")
        assert trigger == "interval"
        assert id == "check_prices_job"
        self.added_to = minutes
        self.job = FakeJob()


class FakeDB:
    def __init__(self, initial_interval=30):
        self.current_interval = initial_interval
        self.saved_intervals = []

    def get_check_interval(self):
        return self.current_interval

    def set_check_interval(self, interval):
        self.current_interval = interval
        self.saved_intervals.append(interval)
        return True


def test_apply_check_interval_updates_scheduler(monkeypatch, tmp_path):
    bot_module = load_bot_module(monkeypatch, tmp_path)
    fake_db = FakeDB(initial_interval=30)
    fake_scheduler = FakeScheduler(has_job=True)

    monkeypatch.setattr(bot_module, "db", fake_db)
    monkeypatch.setattr(bot_module, "scheduler", fake_scheduler)

    assert bot_module.apply_check_interval(15) is True
    assert fake_db.current_interval == 15
    assert fake_scheduler.rescheduled_to == 15


def test_apply_check_interval_rolls_back_on_scheduler_error(monkeypatch, tmp_path):
    bot_module = load_bot_module(monkeypatch, tmp_path)
    fake_db = FakeDB(initial_interval=30)
    fake_scheduler = FakeScheduler(has_job=True, should_fail=True)

    monkeypatch.setattr(bot_module, "db", fake_db)
    monkeypatch.setattr(bot_module, "scheduler", fake_scheduler)

    assert bot_module.apply_check_interval(15) is False
    assert fake_db.current_interval == 30
    assert fake_db.saved_intervals == [15, 30]
