import os
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from django.utils import timezone
from playwright.sync_api import expect, sync_playwright

from pages.models import Institution, InstitutionRequest, QueueReport
from tests.js_coverage import FunctionCoverage

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

# Подмена реализует только используемые приложением методы API карты.
MAP_API = """
window.markers = [];
window.ymaps = {
    ready: callback => callback(),
    Placemark: class {
        constructor(coords, properties) { Object.assign(this, {coords, properties}); }
    },
    Map: class {
        geoObjects = {add: marker => window.markers.push(marker), getBounds: () => []};
        container = {fitToViewport() {}};
        setCenter(coords) { window.mapCenter = coords; }
        setBounds() { window.boundsSet = true; }
    }
};
"""


@pytest.fixture(scope="session")
def js_coverage(pytestconfig):
    coverage = (
        FunctionCoverage(pytestconfig.rootpath)
        if os.getenv("QA_JS_COVERAGE") == "1"
        else None
    )
    yield coverage
    if coverage is not None:
        coverage.write()


@pytest.fixture
def open_page(live_server, js_coverage):
    @contextmanager
    def start(map_api=MAP_API):
        with sync_playwright() as driver:
            channel = os.getenv("QA_BROWSER_CHANNEL")
            if channel is None and Path("/Applications/Google Chrome.app").exists():
                channel = "chrome"
            browser = driver.chromium.launch(channel=channel or None)
            try:
                with browser.new_context(
                    base_url=live_server.url,
                    service_workers="block",
                    viewport={"width": 390, "height": 844},
                ) as context:
                    yield from browser_page(
                        context, live_server.url, js_coverage, map_api
                    )
            finally:
                browser.close()

    return start


def browser_page(context, base_url, coverage, map_api):
    errors = []
    origin = urlsplit(base_url)

    current = context.new_page()
    if coverage is not None:
        session = context.new_cdp_session(current)
        session.send("Profiler.enable")
        session.send(
            "Profiler.startPreciseCoverage", {"callCount": True, "detailed": False}
        )

    def intercept(route):
        url = urlsplit(route.request.url)
        if (url.scheme, url.netloc) == (origin.scheme, origin.netloc):
            route.continue_()
        elif url.hostname == "api-maps.yandex.ru":
            route.fulfill(content_type="application/javascript", body=map_api)
        else:
            route.abort()

    context.route("**/*", intercept)
    current.on("pageerror", lambda error: errors.append(str(error)))

    def checkpoint():
        if coverage is not None:
            coverage.sample(session, origin)

    try:
        yield current, checkpoint
    finally:
        if coverage is not None:
            coverage.sample(session, origin)
            session.send("Profiler.stopPreciseCoverage")
    assert errors == []


def test_mobile_catalog(open_page, place):
    with open_page() as (page, checkpoint):
        page.goto("/")
        expect(page.locator("html")).to_have_attribute("lang", "ru")
        expect(page.locator(".skip-link")).to_have_attribute("href", "#main-content")
        expect(page.get_by_role("heading", level=1)).to_have_count(1)
        expect(
            page.get_by_role("searchbox", name="Название учреждения")
        ).to_be_visible()
        expect(page.get_by_role("combobox", name="Тип учреждения")).to_be_visible()
        expect(page.locator(".institution-card")).to_contain_text(place.name)
        expect(page.locator("#show-map")).to_be_disabled()
        page.locator("#nav-toggle").click()
        expect(page.locator("#nav-menu")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.locator("#nav-toggle")).to_be_focused()
        expect(page.locator("#nav-menu")).to_be_hidden()
        page.locator("#reading-mode-toggle").click()
        checkpoint()
        page.reload()
        expect(page.locator("html")).to_have_attribute("data-reading-mode", "on")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.locator("[name=q]").fill("Отсутствует")
        checkpoint()
        page.get_by_role("button", name="Найти").click()
        expect(page.locator(".empty-state")).to_be_visible()


@pytest.mark.parametrize("count", [0, 1, 2])
def test_map_mock(open_page, settings, count):
    settings.YANDEX_MAPS_API_KEY = "учебный"
    for i in range(count):
        Institution.objects.create(
            name=f"Центр <{i}>", category="МФЦ", latitude=42, longitude=47
        )
    with open_page() as (page, _):
        page.goto("/")
        page.locator("#show-map").click()
        expect(page.locator("#institution-list")).to_be_hidden()
        if count:
            assert len(page.evaluate("window.markers")) == count
            assert (
                page.evaluate("window.markers[0].properties.hintContent")
                == "Центр &lt;0&gt;"
            )
            if count == 1:
                assert page.evaluate("window.mapCenter") == [42, 47]
            else:
                assert page.evaluate("window.boundsSet")
        else:
            expect(page.locator("#map-message")).to_contain_text(
                "Учреждения пока не добавлены"
            )
        page.locator("#show-list").click()
        expect(page.locator("#institution-list")).to_be_visible()
        page.set_viewport_size({"width": 1280, "height": 800})
        expect(page.locator("#institution-map-panel")).to_be_visible()
        expect(page.locator("#institution-list")).to_be_visible()


def test_visitor_journey(open_page, place, room):
    with open_page() as (page, checkpoint):
        page.goto("/accounts/signup/")
        page.locator("[name=username]").fill("демо")
        for field in ["password1", "password2"]:
            page.locator(f"[name={field}]").fill("Qa!459319x")
        page.locator(".auth-form button").click()
        expect(page.locator("h1")).to_have_text("Войти")
        page.goto("/rate/")
        expect(page.locator("[name=next]")).to_have_value("/rate/")
        page.locator("[name=username]").fill("демо")
        page.locator("[name=password]").fill("Qa!459319x")
        page.locator(".auth-form button").click()
        expect(page.locator("#cabinet_id")).to_be_disabled()
        page.locator("#institution_id").select_option(str(place.pk))
        page.locator("#cabinet_id").select_option(str(room.pk))
        checkpoint()
        page.locator("button[value=low]").click()
        expect(page.locator(".flash-message")).to_contain_text("сохранена")
        page.goto("/ai-prediction/")
        page.locator("#institution_id").select_option(str(place.pk))
        page.locator("#cabinet_id").select_option(str(room.pk))
        page.locator("[name=visit_date]").fill(
            (timezone.localdate() + timedelta(days=1)).isoformat()
        )
        checkpoint()
        page.locator(".forecast-form button").click()
        expect(page.locator(".forecast-result")).to_contain_text("Недостаточно данных")
        expect(page.locator("#cabinet_id")).to_have_value(str(room.pk))
        page.goto("/suggest/")
        page.locator("#name").fill("Почта 1")
        page.locator("#category").select_option("Почта")
        page.locator(".suggest-form button").click()
        expect(page.locator(".flash-message")).to_contain_text("на модерацию")
        page.locator("#nav-toggle").click()
        page.get_by_role("button", name="Выйти").click()
        page.goto("/rate/")
        expect(page.locator("h1")).to_have_text("Войти")
    assert QueueReport.objects.get().cabinet_id == room.pk
    assert InstitutionRequest.objects.get().name == "Почта 1"


def test_map_sdk_failure_keeps_catalog(open_page, settings, place):
    settings.YANDEX_MAPS_API_KEY = "учебный"
    with open_page(map_api="window.ymaps = {ready: (ok, fail) => fail()};") as (
        page,
        _,
    ):
        page.goto("/")
        expect(page.locator("#show-map")).to_have_text("Карта недоступна")
        expect(page.locator("#show-map")).to_be_disabled()
        expect(page.locator(".institution-card")).to_contain_text(place.name)
