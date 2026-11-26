from datetime import timedelta
import re
from django.db import transaction
from django.utils import timezone

from .models import QueueReport, ReportCooldown


REPORT_COOLDOWN_MINUTES = 15


def submit_queue_report(*, user, institution, cabinet, queue_level):
    queue_key = f"cabinet:{cabinet.id}" if cabinet else "general"

    with transaction.atomic():
        now = timezone.now()

        latest_report = QueueReport.objects.filter(
            user=user,
            institution=institution,
            cabinet=cabinet,
        ).order_by("-created_at", "-id").first()

        initial_allowed_at = now
        if latest_report is not None:
            initial_allowed_at = latest_report.created_at + timedelta(
                minutes=REPORT_COOLDOWN_MINUTES
            )

        cooldown, created = ReportCooldown.objects.get_or_create(
            user=user,
            institution=institution,
            queue_key=queue_key,
            defaults={"next_allowed_at": initial_allowed_at},
        )

        claimed = ReportCooldown.objects.filter(
            pk=cooldown.pk,
            next_allowed_at__lte=now,
        ).update(
            next_allowed_at=now + timedelta(
                minutes=REPORT_COOLDOWN_MINUTES
            )
        )

        if claimed == 0:
            return False

        QueueReport.objects.create(
            user=user,
            institution=institution,
            cabinet=cabinet,
            queue_level=queue_level,
        )

    return True


FORECAST_MIN_DAYS = 3
FORECAST_MIN_REPORTS = 5

QUEUE_SCORES = {
    "low": 1,
    "medium": 2,
    "high": 3,
}


def build_visit_forecast(*, institution, visit_date, cabinet=None):
    now = timezone.localtime()
    today = now.date()

    if visit_date < today:
        return {
            "error": "Выберите сегодняшнюю или будущую дату.",
            "slots": [],
            "best_slot": None,
        }

    if cabinet is not None and cabinet.institution_id != institution.id:
        return {
            "error": "Кабинет не относится к выбранному учреждению.",
            "slots": [],
            "best_slot": None,
        }

    hours_match = re.fullmatch(
        r"\s*(\d{1,2}):(\d{2})\s*[-–—]\s*"
        r"(\d{1,2}):(\d{2})(?:\s*\(демо\))?\s*",
        institution.working_hours,
    )

    if hours_match is None:
        return {
            "error": (
                "Для расчёта нужен график в формате 08:00–18:00. "
                "Уточните расписание у учреждения."
            ),
            "slots": [],
            "best_slot": None,
        }

    start_hour, start_minute, end_hour, end_minute = map(
        int, hours_match.groups()
    )

    valid_hours = (
        0 <= start_hour <= 23
        and 0 <= end_hour <= 23
        and 0 <= start_minute <= 59
        and 0 <= end_minute <= 59
    )

    opening = start_hour * 60 + start_minute
    closing = end_hour * 60 + end_minute

    if not valid_hours or closing <= opening:
        return {
            "error": "Указанный график работы пока не поддерживается.",
            "slots": [],
            "best_slot": None,
        }

    reports = QueueReport.objects.filter(
        institution=institution,
        cabinet=cabinet,
        user__isnull=False,
        created_at__lt=now,
    ).order_by("-created_at", "-id")

    samples_by_hour = {}
    seen = set()

    for report in reports.iterator():
        local_time = timezone.localtime(report.created_at)

        if local_time.date() >= visit_date:
            continue

        if local_time.weekday() != visit_date.weekday():
            continue

        if report.queue_level not in QUEUE_SCORES:
            continue

        key = (
            report.user_id,
            local_time.date(),
            local_time.hour,
        )

        if key in seen:
            continue

        seen.add(key)
        samples_by_hour.setdefault(local_time.hour, []).append(
            (QUEUE_SCORES[report.queue_level], local_time.date())
        )

    slots = []

    for hour in range(24):
        slot_start = hour * 60
        slot_end = slot_start + 60

        if slot_start < opening or slot_end > closing:
            continue

        if visit_date == today and slot_start <= now.hour * 60 + now.minute:
            continue

        samples = samples_by_hour.get(hour, [])
        days_count = len({sample_date for score, sample_date in samples})
        reports_count = len(samples)

        enough_data = (
            days_count >= FORECAST_MIN_DAYS
            and reports_count >= FORECAST_MIN_REPORTS
        )

        average = None
        label = "Недостаточно данных"

        if enough_data:
            average = sum(score for score, sample_date in samples) / reports_count

            if average < 1.5:
                label = "Обычно небольшая очередь"
            elif average < 2.5:
                label = "Обычно умеренная очередь"
            else:
                label = "Обычно много людей"

        slots.append({
            "start": f"{hour:02d}:00",
            "end": f"{hour + 1:02d}:00",
            "score": average,
            "label": label,
            "reports_count": reports_count,
            "days_count": days_count,
        })

    available_slots = [
        slot for slot in slots
        if slot["score"] is not None
    ]

    best_slot = min(
        available_slots,
        key=lambda slot: slot["score"],
        default=None,
    )

    return {
        "error": "",
        "slots": slots,
        "best_slot": best_slot,
    }