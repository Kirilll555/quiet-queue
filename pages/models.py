from django.db import models


class QueueReport(models.Model):
    QUEUE_LEVEL_CHOICES = [
        ("low", "Небольшая очередь"),
        ("medium", "Умеренная очередь"),
        ("high", "Много людей"),
    ]

    institution_id = models.PositiveSmallIntegerField()
    queue_level = models.CharField(
        max_length=6,
        choices=QUEUE_LEVEL_CHOICES,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Учреждение {self.institution_id}: "
            f"{self.get_queue_level_display()}"
        )