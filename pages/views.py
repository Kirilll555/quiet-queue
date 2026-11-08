from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone

from .models import QueueReport

def index(request):
    institutions = [
        {
            "id": 1,
            "name": "Поликлиника №1 (демо)",
            "category": "Поликлиника",
        },
        {
            "id": 2,
            "name": "Поликлиника №2 (демо)",
            "category": "Поликлиника",
        },
        {
            "id": 3,
            "name": "Поликлиника №3 (демо)",
            "category": "Поликлиника",
        },
        {
            "id": 4,
            "name": "МФЦ «Центральный» (демо)",
            "category": "МФЦ",
        },
        {
            "id": 5,
            "name": "МФЦ №2 (демо)",
            "category": "МФЦ",
        },
    ]

    one_hour_ago = timezone.now() - timedelta(hours=1)

    for institution in institutions:
        reports = QueueReport.objects.filter(
            institution_id=institution["id"],
            created_at__gte=one_hour_ago,
        ).order_by("-created_at")

        latest_report = reports.first()
        institution["reports_count"] = reports.count()

        if latest_report:
            institution["queue_level"] = latest_report.queue_level
            institution["queue_label"] = latest_report.get_queue_level_display()
            institution["updated_label"] = timezone.localtime(
                latest_report.created_at
            ).strftime("%H:%M")
        else:
            institution["queue_level"] = "unknown"
            institution["queue_label"] = "Нет свежих отметок"
            institution["updated_label"] = "Нет отметок за последний час"

    return render(request, "pages/index.html", {"institutions": institutions})

def rate_queue(request):
    if request.method == "POST":
        institution_id = request.POST.get("institution_id", "")
        queue_level = request.POST.get("queue_level", "")

        valid_institution_ids = {"1", "2", "3", "4", "5"}
        valid_queue_levels = {"low", "medium", "high"}

        if institution_id not in valid_institution_ids:
            messages.error(request, "Пожалуйста, выберите учреждение.")
            return redirect("rate")

        if queue_level not in valid_queue_levels:
            messages.error(request, "Пожалуйста, выберите уровень загруженности.")
            return redirect(f"{reverse('rate')}?institution_id={institution_id}")

        QueueReport.objects.create(
            institution_id=int(institution_id),
            queue_level=queue_level,
        )

        messages.success(request, "Спасибо! Демо-отметка сохранена.")
        return redirect(f"{reverse('rate')}?institution_id={institution_id}")

    return render(request, "pages/rate.html")

def suggest_institution(request):
    return render(request, 'pages/suggest.html')

def ai_prediction(request):
    ai_response = "ИИ проанализировал данные. Лучшее время для визита — завтра с утра."
    return render(request, 'pages/prediction.html', {'ai_text': ai_response})