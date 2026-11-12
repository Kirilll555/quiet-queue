from django.db import models

class Institution(models.Model):
    name = models.CharField("Название", max_length=255)
    category = models.CharField("Тип", max_length=100)

    def __str__(self):
        return self.name

class InstitutionRequest(models.Model):
    name = models.CharField("Название", max_length=255)
    category = models.CharField("Тип", max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField("Обработана", default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Заявка: {self.name}"

class QueueReport(models.Model):
    QUEUE_LEVEL_CHOICES = [
        ("low", "Небольшая очередь"),
        ("medium", "Умеренная очередь"),
        ("high", "Много людей"),
    ]

    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="reports")
    queue_level = models.CharField(max_length=6, choices=QUEUE_LEVEL_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.institution.name}: {self.get_queue_level_display()}"