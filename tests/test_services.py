from datetime import timedelta

import pytest
from django.db import IntegrityError

from pages.models import Institution, QueueReport, ReportCooldown
from pages.services import build_visit_forecast, submit_queue_report


@pytest.mark.parametrize("age,allowed", [(899, False), (900, True), (901, True)])
def test_legacy_cooldown(now, place, user, report, age, allowed):
    report(at=now - timedelta(seconds=age))
    saved = submit_queue_report(
        user=user, institution=place, cabinet=None, queue_level="low"
    )
    assert saved is allowed
    assert place.reports.count() == 1 + int(allowed)


def test_independent_queues(place, room, user, django_user_model):
    other = django_user_model.objects.create_user("второй")
    for person, cabinet, expected in [
        (user, None, True),
        (user, room, True),
        (other, None, True),
        (user, room, False),
    ]:
        assert (
            submit_queue_report(
                user=person, institution=place, cabinet=cabinet, queue_level="medium"
            )
            is expected
        )
    assert place.reports.count() == 3


def test_failed_write_rolls_back(place, user, monkeypatch):
    def fail(**kwargs):
        raise IntegrityError("сбой записи")

    monkeypatch.setattr(QueueReport.objects, "create", fail)
    with pytest.raises(IntegrityError, match="сбой записи"):
        submit_queue_report(
            user=user, institution=place, cabinet=None, queue_level="low"
        )
    assert not ReportCooldown.objects.exists()
    assert not QueueReport.objects.exists()


@pytest.mark.parametrize(
    "hours,days,message",
    [
        ("08:00–18:00", -1, "будущую дату"),
        ("круглосуточно", 1, "формате"),
        ("24:00-25:00", 1, "не поддерживается"),
        ("18:00-08:00", 0, "не поддерживается"),
        ("08:60-19:00", 0, "не поддерживается"),
        ("08:00-19:60", 0, "не поддерживается"),
    ],
)
def test_forecast_error(now, place, hours, days, message):
    place.working_hours = hours
    result = build_visit_forecast(
        institution=place, visit_date=now.date() + timedelta(days=days)
    )
    assert message in result["error"]
    assert result["slots"] == [] and result["best_slot"] is None


def test_foreign_room(now, room):
    other = Institution.objects.create(name="Почта", category="Почта")
    result = build_visit_forecast(
        institution=other, cabinet=room, visit_date=now.date()
    )
    assert "не относится" in result["error"]


@pytest.mark.parametrize(
    "days,expected", [(0, ["11:00"]), (1, ["09:00", "10:00", "11:00"])]
)
def test_whole_future_hours(now, place, days, expected):
    place.working_hours = "8:30 — 12:15 (демо)"
    result = build_visit_forecast(
        institution=place, visit_date=now.date() + timedelta(days=days)
    )
    assert [slot["start"] for slot in result["slots"]] == expected
    assert all(slot["label"] == "Недостаточно данных" for slot in result["slots"])
    assert result["best_slot"] is None


@pytest.mark.parametrize(
    "levels,score,label",
    [
        (["low"] * 6, 1, "небольшая"),
        (["low", "medium"] * 3, 1.5, "умеренная"),
        (["medium", "high"] * 3, 2.5, "много"),
    ],
)
def test_forecast_history(
    now, place, room, report, user, django_user_model, levels, score, label
):
    second = django_user_model.objects.create_user("второй")
    for i, level in enumerate(levels):
        at = (now - timedelta(weeks=1 + i // 2)).replace(hour=12)
        person = [user, second][i % 2]
        report("high", at=at - timedelta(minutes=1), user=person)
        report(level, at=at, user=person)
    sampled_hour = now.replace(hour=12)
    for at, fields in [
        (now - timedelta(minutes=1), {}),
        (sampled_hour - timedelta(days=1), {}),
        (sampled_hour - timedelta(weeks=4), {"level": "other"}),
        (sampled_hour - timedelta(weeks=4), {"user": None}),
        (sampled_hour - timedelta(weeks=4), {"cabinet": room}),
    ]:
        report(at=at, **fields)
    result = build_visit_forecast(institution=place, visit_date=now.date())
    slot = result["best_slot"]
    assert (
        slot["start"],
        slot["score"],
        slot["reports_count"],
        slot["days_count"],
    ) == ("12:00", score, 6, 3)
    assert label in slot["label"]
    assert sum(s["reports_count"] for s in result["slots"]) == 6


@pytest.mark.parametrize(
    "week_offsets,enough",
    [
        ([1, 2, 3, 3], False),
        ([1, 1, 2, 2, 2], False),
        ([1, 1, 2, 2, 3], True),
    ],
)
def test_forecast_thresholds_and_tie(
    now, place, room, report, django_user_model, week_offsets, enough
):
    for i, week in enumerate(week_offsets):
        person = django_user_model.objects.create_user(f"посетитель{i}")
        for hour in [12, 13]:
            at = (now - timedelta(weeks=week)).replace(hour=hour)
            report("low", user=person, at=at, cabinet=room)
    result = build_visit_forecast(
        institution=place, visit_date=now.date(), cabinet=room
    )
    if enough:
        assert result["best_slot"]["start"] == "12:00"
    else:
        assert result["best_slot"] is None


def test_best_slot_by_score(now, place, report, django_user_model):
    for week in range(1, 6):
        person = django_user_model.objects.create_user(f"автор{week}")
        for hour, level in [(12, "high"), (13, "low")]:
            report(
                level, user=person, at=(now - timedelta(weeks=week)).replace(hour=hour)
            )
    forecast = build_visit_forecast(institution=place, visit_date=now.date())
    assert (forecast["best_slot"]["start"], forecast["best_slot"]["score"]) == (
        "13:00",
        1,
    )


def test_forecast_without_complete_hour(now, place):
    place.working_hours = "10:30-11:15"
    forecast = build_visit_forecast(
        institution=place,
        visit_date=now.date() + timedelta(days=1),
    )
    assert forecast == {"error": "", "slots": [], "best_slot": None}
