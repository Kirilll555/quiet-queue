from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone

from .models import Institution, QueueReport, InstitutionRequest


def index(request):
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()

    institutions = Institution.objects.all()

    if query:
        institutions = institutions.filter(name__icontains=query)

    if category:
        institutions = institutions.filter(category=category)

    one_hour_ago = timezone.now() - timedelta(hours=1)

    for inst in institutions:
        reports = inst.reports.filter(created_at__gte=one_hour_ago)
        latest_report = reports.first()

        inst.reports_count = reports.count()

        if latest_report:
            inst.queue_level = latest_report.queue_level
            inst.queue_label = latest_report.get_queue_level_display()
            inst.updated_label = timezone.localtime(latest_report.created_at).strftime("%H:%M")
        else:
            inst.queue_level = "unknown"
            inst.queue_label = "Нет свежих отметок"
            inst.updated_label = "Нет отметок за последний час"

    return render(request, "pages/index.html", {
        "institutions": institutions,
        "query": query,
        "category": category,
    })


def rate_queue(request):
    institutions = Institution.objects.all()

    if request.method == "POST":
        institution_id = request.POST.get("institution_id", "")
        queue_level = request.POST.get("queue_level", "")

        valid_queue_levels = {"low", "medium", "high"}

        if not institution_id:
            messages.error(request, "Пожалуйста, выберите учреждение.")
            return redirect("rate")

        if queue_level not in valid_queue_levels:
            messages.error(request, "Пожалуйста, выберите уровень загруженности.")
            return redirect(f"{reverse('rate')}?institution_id={institution_id}")

        institution = get_object_or_404(Institution, id=institution_id)

        QueueReport.objects.create(
            institution=institution,
            queue_level=queue_level,
        )

        messages.success(request, f"Спасибо! Отметка для {institution.name} сохранена.")
        return redirect(f"{reverse('rate')}?institution_id={institution.id}")

    return render(request, "pages/rate.html", {"institutions": institutions})


def suggest_institution(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        category = request.POST.get("category", "").strip()

        if name and category:
            InstitutionRequest.objects.create(
                name=name,
                category=category
            )
            messages.success(request, "Спасибо! Ваша заявка отправлена на модерацию.")
            return redirect("suggest")
        else:
            messages.error(request, "Пожалуйста, заполните все поля.")

    return render(request, 'pages/suggest.html')


def ai_prediction(request):
    ai_response = "ИИ проанализировал данные. Лучшее время для визита — завтра с утра."
    return render(request, 'pages/prediction.html', {'ai_text': ai_response})