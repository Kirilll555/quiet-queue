import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from pages.models import Cabinet, InstitutionRequest, QueueReport, ReportCooldown


def test_model_labels_and_relations(user, place, room, report):
    general = report()
    personal = report("high", cabinet=room)
    assert str(place) == "Центр"
    assert str(room) == "Центр - Кабинет 1"
    assert str(general) == "Центр: Небольшая очередь"
    assert str(personal) == "Центр (Кабинет 1): Много людей"
    assert list(user.queue_reports.all()) == [personal, general]
    assert list(room.reports.all()) == [personal]
    assert place.cabinets.get() == room
    assert not InstitutionRequest(name="Почта").is_processed
    assert str(InstitutionRequest(name="Почта")) == "Заявка: Почта"
    room.delete()
    user.delete()
    personal.refresh_from_db()
    assert personal.cabinet_id is None and personal.user_id is None
    Cabinet.objects.create(institution=place, name="Архив")
    place.delete()
    assert not Cabinet.objects.exists()
    assert not QueueReport.objects.exists()


@pytest.mark.parametrize(
    "lat,lon,valid",
    [
        (None, None, True),
        (-90, -180, True),
        (90, 180, True),
        ("90.000001", 0, False),
        ("-90.000001", 0, False),
        (0, "180.000001", False),
        (0, "-180.000001", False),
    ],
)
def test_coordinates(place, lat, lon, valid):
    place.latitude, place.longitude = lat, lon
    if valid:
        place.full_clean()
    else:
        with pytest.raises(ValidationError):
            place.full_clean()


def test_cooldown_constraint(place, user, now):
    fields = {
        "institution": place,
        "user": user,
        "queue_key": "general",
        "next_allowed_at": now,
    }
    ReportCooldown.objects.create(**fields)
    with pytest.raises(IntegrityError), transaction.atomic():
        ReportCooldown.objects.create(**fields)
    user.delete()
    assert not ReportCooldown.objects.exists()


def test_queue_level_choice_validation(place):
    report = QueueReport(institution=place, queue_level="unknown")
    with pytest.raises(ValidationError) as caught:
        report.full_clean()
    assert set(caught.value.message_dict) == {"queue_level"}
