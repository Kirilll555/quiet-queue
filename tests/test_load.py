from concurrent.futures import ThreadPoolExecutor
from math import ceil
from time import perf_counter
from urllib.request import ProxyHandler, build_opener

import pytest

from pages.models import Institution


@pytest.mark.load
@pytest.mark.django_db(transaction=True)
def test_parallel_reads(live_server):
    Institution.objects.bulk_create(
        [Institution(name=f"Центр {n}", category="МФЦ") for n in range(20)]
    )
    paths = [
        ("/", "Центр 19"),
        ("/?q=missing", "empty-state"),
        ("/ai-prediction/", "forecast-form"),
        ("/suggest/", "suggest-form"),
    ] * 12

    def fetch(case):
        path, marker = case
        start = perf_counter()
        with build_opener(ProxyHandler({})).open(
            live_server.url + path, timeout=10
        ) as response:
            assert response.status == 200
            assert response.url == live_server.url + path
            html = response.read().decode()
            assert marker in html
            if path == "/":
                assert html.count('class="institution-card"') == 20
            elif path.startswith("/?"):
                assert 'class="institution-card"' not in html
        return perf_counter() - start

    start = perf_counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        times = sorted(pool.map(fetch, paths))
    elapsed = perf_counter() - start
    p95 = times[ceil(0.95 * len(times)) - 1]
    print(
        f"Нагрузка: {len(times)} ответов, 4 потока, {elapsed:.3f} с, "
        f"{len(times) / elapsed:.1f} запр/с, p95 {1000 * p95:.1f} мс"
    )
