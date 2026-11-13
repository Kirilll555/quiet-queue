from django.db import models


class Institution(models.Model):
    name = models.CharField("Название", max_length=255)
    category = models.CharField("Тип", max_length=100)
    address = models.CharField("Адрес", max_length=255, default="г. Махачкала")
    working_hours = models.CharField("Часы работы", max_length=100, default="08:00 - 18:00")

    def __str__(self):
        return self.name


class Cabinet(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="cabinets")
    name = models.CharField("Название кабинета", max_length=255)
    cabinet_type = models.CharField("Специализация", max_length=100, blank=True)

    def __str__(self):
        return f"{self.institution.name} - {self.name}"


class QueueReport(models.Model):
    QUEUE_LEVEL_CHOICES = [
        ("low", "Небольшая очередь"),
        ("medium", "Умеренная очередь"),
        ("high", "Много людей"),
    ]

    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="reports")
    cabinet = models.ForeignKey(Cabinet, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports")
    queue_level = models.CharField(max_length=6, choices=QUEUE_LEVEL_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        if self.cabinet:
            return f"{self.institution.name} ({self.cabinet.name}): {self.get_queue_level_display()}"
        return f"{self.institution.name}: {self.get_queue_level_display()}"


class InstitutionRequest(models.Model):
    name = models.CharField("Название", max_length=255)
    category = models.CharField("Тип", max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField("Обработана", default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Заявка: {self.name}"