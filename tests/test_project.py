import pytest
from django.core.management import call_command, get_commands

from pages.models import InstitutionRequest


def test_entrypoints():
    from config.asgi import application as async_app
    from config.wsgi import application as sync_app

    assert callable(async_app) and callable(sync_app)
    call_command("check", verbosity=0)


@pytest.mark.django_db
def test_migrations_current():
    call_command(
        "makemigrations", "pages", dry_run=True, check_changes=True, verbosity=0
    )


@pytest.mark.django_db
@pytest.mark.xfail(
    strict=True,
    raises=pytest.RaisesExc(
        AttributeError,
        check=lambda exc: (
            exc.name == "Command"
            and getattr(exc.obj, "__name__", "")
            == "pages.management.commands.seed_data"
        ),
    ),
    reason="BUG-01: в seed_data нет класса Command",
)
def test_seed_command():
    assert get_commands()["seed_data"] == "pages"
    call_command("seed_data")


@pytest.mark.parametrize("field,length", [("name", 256), ("category", 101)])
@pytest.mark.django_db
@pytest.mark.xfail(
    strict=True,
    raises=pytest.RaisesExc(AssertionError, match="BUG-02"),
    reason="BUG-02: превышение длины поля заявки",
)
def test_suggestion_respects_model_lengths(client, field, length):
    response = client.post(
        "/suggest/", {"name": "Почта", "category": "Почта", field: "а" * length}
    )
    assert response.status_code in (200, 302, 400, 422)
    assert not InstitutionRequest.objects.exists(), (
        "BUG-02: сохранена слишком длинная заявка"
    )


def test_manage_check(monkeypatch, capsys):
    import runpy
    import sys
    from pathlib import Path

    monkeypatch.setattr(sys, "argv", ["manage.py", "check"])
    runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "manage.py"), run_name="__main__"
    )
    assert "no issues" in capsys.readouterr().out


def test_cli_explains_missing_dependency(monkeypatch):
    import sys

    import manage

    monkeypatch.setitem(sys.modules, "django.core.management", None)
    with pytest.raises(ImportError, match="Couldn't import Django") as caught:
        manage.main()
    assert isinstance(caught.value.__cause__, ImportError)


@pytest.mark.xfail(
    strict=True,
    raises=pytest.RaisesExc(AssertionError, match="BUG-03"),
    reason="BUG-03: кириллица чувствительна к регистру",
)
def test_catalog_cyrillic_case(client, place):
    assert [place] == list(
        client.get("/", {"q": place.name.lower()}).context["institutions"]
    ), "BUG-03: запись пропущена при смене регистра"


@pytest.mark.django_db
@pytest.mark.parametrize("category", ["Почта", "Другое"])
@pytest.mark.xfail(
    strict=True,
    raises=pytest.RaisesExc(AssertionError, match="BUG-04"),
    reason="BUG-04: тип учреждения отсутствует в фильтре",
)
def test_catalog_filter_offers_published_type(client, category):
    from pages.models import Institution

    Institution.objects.create(name="Филиал", category=category)
    response = client.get("/")
    from django.test.html import parse_html

    assert response.status_code == 200

    def elements(node):
        if hasattr(node, "children"):
            yield node
            for child in node.children:
                yield from elements(child)

    (select,) = (
        node
        for node in elements(parse_html(response.content.decode()))
        if node.name == "select" and dict(node.attributes).get("name") == "category"
    )
    options = {
        dict(node.attributes).get("value")
        for node in elements(select)
        if node.name == "option"
    }
    assert category in options, "BUG-04: тип отсутствует в фильтре"
