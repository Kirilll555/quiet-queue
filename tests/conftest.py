from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from pages.models import Cabinet, Institution, QueueReport


@pytest.fixture
def now(monkeypatch):
    moment = datetime(2026, 6, 1, 10, 30, tzinfo=ZoneInfo("Europe/Moscow"))
    monkeypatch.setattr(timezone, "now", lambda: moment)
    return moment


@pytest.fixture
def place(db):
    return Institution.objects.create(name="Центр", category="МФЦ")


@pytest.fixture
def room(place):
    return Cabinet.objects.create(institution=place, name="Кабинет 1")


@pytest.fixture
def user(db, django_user_model):
    return django_user_model.objects.create_user("гость", password="Q-Test!493")


@pytest.fixture
def member(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def report(place, user):
    def create(level="low", *, at=None, **fields):
        fields.setdefault("user", user)
        fields.setdefault("institution", place)
        row = QueueReport.objects.create(queue_level=level, **fields)
        if at is not None:
            QueueReport.objects.filter(pk=row.pk).update(created_at=at)
            row.refresh_from_db()
        return row

    return create
