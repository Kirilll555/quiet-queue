from datetime import timedelta

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