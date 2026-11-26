from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import OperationalError
from django.test import Client
from django.urls import reverse
from django.utils.html import escape

from pages.models import Cabinet, Institution, InstitutionRequest, QueueReport


@pytest.mark.parametrize(
    "level,expected", [("low", "low"), ("medium", "medium"), ("high", "high")]
)
def test_catalog(now, place, room, report, client, django_user_model, level, expected):
    place.latitude, place.longitude = 42, 47
    place.save()
    Institution.objects.create(name="Центр здоровья", category="Поликлиника")
    Institution.objects.create(name="Филиал", category="МФЦ")
    report("medium", at=now - timedelta(minutes=1))
    report(level)
    report("high", cabinet=room, at=now - timedelta(hours=1))
    report("low", user=None)
    report(
        "low",
        user=django_user_model.objects.create_user("старый"),
        at=now - timedelta(hours=1, microseconds=1),
    )
    response = client.get("/", {"q": " Цент ", "category": " МФЦ "})
    (entry,) = response.context["institutions"]
    assert (entry.queue_level, entry.reports_count) == (expected, 1)
    (cabinet,) = entry.queue_cabinets
    assert (cabinet.queue_level, cabinet.reports_count) == ("high", 1)
    (marker,) = response.context["map_institutions"]
    assert (marker["latitude"], marker["longitude"], marker["rate_url"]) == (
        42,
        47,
        f"/rate/?institution_id={place.pk}",
    )
    assert not client.get("/", {"q": "Нет совпадений"}).context["institutions"]


def test_unknown_status_and_escaping(client, place):
    place.name = "Центр <архив>"
    place.save()
    response = client.get("/")
    (entry,) = response.context["institutions"]
    assert entry.queue_level == "unknown" and entry.average_score is None
    assert response.context["map_institutions"] == []
    assert escape(place.name) in response.content.decode()


@pytest.mark.parametrize(
    "institution,cabinet,level,message",
    [
        ("", "", "low", "выберите учреждение"),
        ("abc", "", "low", "выберите учреждение"),
        (-1, "", "low", "не найдено"),
        ("своё", "abc", "low", "кабинет из списка"),
        ("своё", "чужой", "low", "не относится"),
        ("своё", "", "", "уровень загруженности"),
    ],
)
def test_rate_invalid(member, place, institution, cabinet, level, message):
    if cabinet == "чужой":
        other = Institution.objects.create(name="Почта", category="Почта")
        cabinet = Cabinet.objects.create(institution=other, name="Окно").pk
    response = member.post(
        "/rate/",
        {
            "institution_id": place.pk if institution == "своё" else institution,
            "cabinet_id": cabinet,
            "queue_level": level,
        },
    )
    assert message in response.content.decode()
    assert not QueueReport.objects.exists()


@pytest.mark.parametrize("with_room", [True, False])
def test_rate_and_repeat(member, place, room, with_room):
    data = {
        "institution_id": place.pk,
        "cabinet_id": room.pk if with_room else "",
        "queue_level": "high",
    }
    first = member.post("/rate/", data, follow=True)
    assert first.redirect_chain == [(f"/rate/?institution_id={place.pk}", 302)]
    assert "сохранена" in first.content.decode()
    assert "через 15 минут" in member.post("/rate/", data, follow=True).content.decode()
    row = QueueReport.objects.get()
    assert row.cabinet_id == (room.pk if with_room else None)
    assert row.user_id == int(member.session["_auth_user_id"])


@pytest.mark.parametrize("error", ["database is locked", "disk full"])
def test_storage_errors(member, place, error):
    data = {"institution_id": place.pk, "queue_level": "high"}
    with patch("pages.views.submit_queue_report", side_effect=OperationalError(error)):
        if "locked" in error:
            assert (
                "База данных занята"
                in member.post("/rate/", data, follow=True).content.decode()
            )
        else:
            with pytest.raises(OperationalError, match=error):
                member.post("/rate/", data)
    assert not QueueReport.objects.exists()


def test_suggestion_and_moderation(client, admin_client, db):
    assert client.get("/suggest/").status_code == 200
    assert (
        "заполните все поля" in client.post("/suggest/", {"name": " "}).content.decode()
    )
    response = client.post(
        "/suggest/", {"name": " Почта ", "category": " Почта "}, follow=True
    )
    assert "на модерацию" in response.content.decode()
    item = InstitutionRequest.objects.get()
    assert (item.name, item.category, item.is_processed) == ("Почта", "Почта", False)
    assert not Institution.objects.exists()
    url = reverse("admin:pages_institutionrequest_changelist")
    for count in [1, 0]:
        response = admin_client.post(
            url,
            {"action": "approve_requests", "_selected_action": item.pk},
            follow=True,
        )
        assert f"добавлено учреждений: {count}" in response.content.decode()
    item.refresh_from_db()
    assert item.is_processed
    assert Institution.objects.get().name == item.name


@pytest.mark.parametrize(
    "model", ["institution", "cabinet", "queuereport", "institutionrequest"]
)
def test_admin_access(member, admin_client, model):
    url = reverse(f"admin:pages_{model}_changelist")
    assert member.get(url).url.startswith("/admin/login/")
    assert admin_client.get(url).status_code == 200


def test_auth_flow(client, db, django_user_model):
    assert client.post("/rate/").url == "/accounts/login/?next=/rate/"
    assert client.get("/accounts/signup/").context["is_signup"]
    data = {"username": "тест", "password1": "Qa!459319x", "password2": "Qa!459319x"}
    assert client.post("/accounts/signup/", data).url == "/accounts/login/"
    assert django_user_model.objects.get().check_password(data["password1"])
    assert "username" in client.post("/accounts/signup/", data).context["form"].errors
    login = {
        "username": data["username"],
        "password": data["password1"],
        "next": "/rate/",
    }
    assert (
        client.post("/accounts/login/", {**login, "password": "ошибка"})
        .context["form"]
        .errors
    )
    assert client.post("/accounts/login/", login).url == "/rate/"
    assert client.get("/accounts/signup/").url == "/"
    assert client.get("/accounts/logout/").status_code == 405
    assert client.post("/accounts/logout/").url == "/"
    assert client.get("/rate/").status_code == 302


@pytest.mark.parametrize(
    "url",
    [
        "/rate/",
        "/suggest/",
        "/accounts/login/",
        "/accounts/signup/",
        "/accounts/logout/",
    ],
)
def test_post_requires_csrf(db, user, url):
    browser = Client(enforce_csrf_checks=True)
    browser.force_login(user)
    assert browser.post(url).status_code == 403


def test_prediction_form(client, place, room, now):
    url = reverse("ai_prediction")
    first = client.get(url, {"institution_id": place.pk})
    assert first.context["forecast"] is None
    assert first.context["form"].initial["institution_id"] == str(place.pk)
    for fields, invalid in [
        ({"visit_date": ""}, "visit_date"),
        ({"visit_date": "2026-02-31"}, "visit_date"),
        ({"visit_date": (now.date() - timedelta(days=1)).isoformat()}, "visit_date"),
        ({"institution_id": "не число"}, "institution_id"),
        ({"cabinet_id": -1}, "cabinet_id"),
    ]:
        response = client.get(
            url, {"institution_id": place.pk, "visit_date": now.date(), **fields}
        )
        assert invalid in response.context["form"].errors
        assert response.context["forecast"] is None
    response = client.get(
        url,
        {"institution_id": place.pk, "visit_date": now.date(), "cabinet_id": room.pk},
    )
    assert response.context["cabinet"] == room
    assert "Недостаточно данных для рекомендации" in response.content.decode()


@pytest.mark.parametrize(
    "first,second,average,status",
    [
        ("low", "medium", 1.5, "medium"),
        ("medium", "high", 2.5, "high"),
    ],
)
def test_average_boundary(
    client, report, django_user_model, first, second, average, status
):
    report(first)
    report(second, user=django_user_model.objects.create_user("другой"))
    (place,) = client.get("/").context["institutions"]
    assert (place.average_score, place.queue_level, place.reports_count) == (
        average,
        status,
        2,
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "password,confirmation", [("коротко", "коротко"), ("Qa!459319x", "другой")]
)
def test_signup_password_rejected(client, django_user_model, password, confirmation):
    response = client.post(
        "/accounts/signup/",
        {
            "username": "читатель",
            "password1": password,
            "password2": confirmation,
        },
    )
    assert "password2" in response.context["form"].errors
    assert not django_user_model.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_reports(place, user):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.contrib.messages import get_messages
    from django.db import connections

    clients = [Client(), Client()]
    for session in clients:
        session.force_login(user)
    barrier = Barrier(2)
    data = {"institution_id": place.pk, "queue_level": "low"}

    def send(session):
        try:
            barrier.wait(timeout=5)
            response = session.post("/rate/", data)
            assert response.status_code == 302
            assert response.url == f"/rate/?institution_id={place.pk}"
            (message,) = get_messages(response.wsgi_request)
            return message.tags
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(send, clients))
    saved = place.reports.count()
    assert saved <= 1
    assert outcomes.count("success") == saved
    assert set(outcomes) <= {"success", "warning", "error"}
    if not saved:
        assert outcomes == ["error", "error"]
    # Если обе транзакции встретили блокировку, последующая попытка должна пройти.
    clients[0].post("/rate/", data)
    assert place.reports.count() == 1


def test_csrf_valid_submission(user, place):
    browser = Client(enforce_csrf_checks=True)
    browser.force_login(user)
    page = browser.get("/rate/")
    token = page.cookies["csrftoken"].value
    data = {"institution_id": place.pk, "queue_level": "medium"}
    assert browser.post("/rate/", data).status_code == 403
    assert not QueueReport.objects.exists()
    assert (
        browser.post("/rate/", {**data, "csrfmiddlewaretoken": token}).status_code
        == 302
    )
    row = QueueReport.objects.get()
    assert (row.user, row.institution, row.queue_level) == (user, place, "medium")


@pytest.mark.xfail(
    strict=True,
    raises=pytest.RaisesExc(AssertionError, match="BUG-05"),
    reason="BUG-05: роль просмотра видит действие публикации",
)
def test_read_only_staff_cannot_moderate(client, user):
    from django.contrib.auth.models import Permission

    user.is_staff = True
    user.save(update_fields=["is_staff"])
    user.user_permissions.add(
        Permission.objects.get(codename="view_institutionrequest")
    )
    client.force_login(user)
    InstitutionRequest.objects.create(name="Заявка", category="МФЦ")
    page = client.get(reverse("admin:pages_institutionrequest_changelist"))
    assert page.status_code == 200
    assert client.get(reverse("admin:pages_institution_add")).status_code == 403
    actions = page.context["action_form"]
    choices = dict(actions.fields["action"].choices) if actions else {}
    assert "approve_requests" not in choices, "BUG-05: доступно одобрение"


def test_external_next_stays_local(client, user):
    response = client.post(
        "/accounts/login/",
        {
            "username": user.username,
            "password": "Q-Test!493",
            "next": "https://example.invalid/",
        },
    )
    assert response.url == "/"
    assert client.session["_auth_user_id"] == str(user.pk)


@pytest.mark.parametrize(
    "url",
    ["/", "/suggest/", "/ai-prediction/", "/accounts/login/", "/accounts/signup/"],
)
def test_public_routes_support_head(client, db, url):
    response = client.head(url)
    assert response.status_code == 200
    assert response.content == b""


def test_unknown_route_returns_404(client):
    assert client.get("/does-not-exist/").status_code == 404
