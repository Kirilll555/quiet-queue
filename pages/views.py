from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone
from django.db.models import Prefetch
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import OperationalError

from .services import submit_queue_report, REPORT_COOLDOWN_MINUTES
from .models import Cabinet, Institution, QueueReport, InstitutionRequest
from .forms import SignUpForm, ForecastForm
from .services import build_visit_forecast


def index(request):
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    one_hour_ago = timezone.now() - timedelta(hours=1)

    recent_reports = QueueReport.objects.filter(
        created_at__gte=one_hour_ago,
        user__isnull=False,
    ).order_by("-created_at", "-id")

    institutions = Institution.objects.order_by("name")

    if query:
        institutions = institutions.filter(name__icontains=query)

    if category:
        institutions = institutions.filter(category=category)

    institutions = institutions.prefetch_related(
        Prefetch(
            "reports",
            queryset=recent_reports,
            to_attr="recent_reports",
        ),
        Prefetch(
            "cabinets",
            queryset=Cabinet.objects.order_by("name"),
            to_attr="queue_cabinets",
        ),
    )

    def set_queue_status(target, reports):
        latest_by_user = {}

        for report in reports:
            if report.user_id not in latest_by_user:
                latest_by_user[report.user_id] = report

        unique_reports = list(latest_by_user.values())
        target.reports_count = len(unique_reports)
        target.average_score = None

        if not unique_reports:
            target.queue_level = "unknown"
            target.queue_label = "Нет свежих отметок"
            target.updated_label = "Нет отметок за последний час"
            return

        scores = {
            "low": 1,
            "medium": 2,
            "high": 3,
        }
        average = sum(
            scores[report.queue_level] for report in unique_reports
        ) / len(unique_reports)

        target.average_score = round(average, 2)

        if average < 1.5:
            target.queue_level = "low"
            target.queue_label = "Небольшая очередь"
        elif average < 2.5:
            target.queue_level = "medium"
            target.queue_label = "Умеренная очередь"
        else:
            target.queue_level = "high"
            target.queue_label = "Много людей"

        target.updated_label = timezone.localtime(
            unique_reports[0].created_at
        ).strftime("%H:%M")

    for institution in institutions:
        general_reports = []
        reports_by_cabinet = {}

        for report in institution.recent_reports:
            if report.cabinet_id is None:
                general_reports.append(report)
            else:
                reports_by_cabinet.setdefault(
                    report.cabinet_id, []
                ).append(report)

        set_queue_status(institution, general_reports)

        for cabinet in institution.queue_cabinets:
            set_queue_status(
                cabinet,
                reports_by_cabinet.get(cabinet.id, []),
            )

    map_institutions = [
        {
            "id": institution.id,
            "name": institution.name,
            "address": institution.address,
            "latitude": float(institution.latitude),
            "longitude": float(institution.longitude),
            "queue_label": institution.queue_label,
            "rate_url": (
                f"{reverse('rate')}?institution_id={institution.id}"
            ),
        }
        for institution in institutions
        if institution.latitude is not None
        and institution.longitude is not None
    ]

    return render(request, "pages/index.html", {
        "institutions": institutions,
        "query": query,
        "category": category,
        "map_institutions": map_institutions,
        "yandex_maps_api_key": settings.YANDEX_MAPS_API_KEY,
    })


@login_required
def rate_queue(request):
    institutions = Institution.objects.order_by("name")
    cabinets_data = list(
        Cabinet.objects.order_by("name").values(
            "id", "name", "cabinet_type", "institution_id"
        )
    )

    selected_institution_id = request.GET.get("institution_id", "")
    selected_cabinet_id = ""

    if request.method == "POST":
        selected_institution_id = request.POST.get("institution_id", "")
        selected_cabinet_id = request.POST.get("cabinet_id", "")
        queue_level = request.POST.get("queue_level", "")

        institution = None
        cabinet = None
        error = ""

        try:
            institution_id = int(selected_institution_id)
        except (ValueError, TypeError):
            error = "Пожалуйста, выберите учреждение."
        else:
            institution = Institution.objects.filter(
                id=institution_id
            ).first()

            if institution is None:
                error = "Учреждение не найдено. Выберите другое."

        if not error and selected_cabinet_id:
            try:
                cabinet_id = int(selected_cabinet_id)
            except (ValueError, TypeError):
                error = "Пожалуйста, выберите кабинет из списка."
            else:
                cabinet = Cabinet.objects.filter(
                    id=cabinet_id,
                    institution=institution,
                ).first()

                if cabinet is None:
                    error = "Выбранный кабинет не относится к этому учреждению."
                    selected_cabinet_id = ""

        valid_queue_levels = {
            value for value, label in QueueReport.QUEUE_LEVEL_CHOICES
        }

        if not error and queue_level not in valid_queue_levels:
            error = "Пожалуйста, выберите уровень загруженности."

        if error:
            messages.error(request, error)
        else:
            try:
                saved = submit_queue_report(
                    user=request.user,
                    institution=institution,
                    cabinet=cabinet,
                    queue_level=queue_level,
                )
            except OperationalError as exc:
                if "locked" not in str(exc).lower():
                    raise

                messages.error(
                    request,
                    "База данных занята. Повторите отправку через несколько секунд.",
                )
                return redirect(
                    f"{reverse('rate')}?institution_id={institution.id}"
                )

            if not saved:
                messages.warning(
                    request,
                    "Вы уже оценили эту очередь. Повторная отметка доступна "
                    f"через {REPORT_COOLDOWN_MINUTES} минут после предыдущей.",
                )
                return redirect(
                    f"{reverse('rate')}?institution_id={institution.id}"
                )

            location = institution.name
            if cabinet is not None:
                location = f"{institution.name}, {cabinet.name}"

            messages.success(
                request,
                f"Спасибо! Отметка для {location} сохранена.",
            )
            return redirect(
                f"{reverse('rate')}?institution_id={institution.id}"
            )

    return render(request, "pages/rate.html", {
        "institutions": institutions,
        "cabinets_data": cabinets_data,
        "selected_institution_id": selected_institution_id,
        "selected_cabinet_id": selected_cabinet_id,
    })


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
    submitted = bool(request.GET)
    form = ForecastForm(request.GET if submitted else None)
    forecast = None
    institution = None
    cabinet = None
    visit_date = None

    if submitted and form.is_valid():
        institution = form.cleaned_data["institution_id"]
        cabinet = form.cleaned_data["cabinet_id"]
        visit_date = form.cleaned_data["visit_date"]

        forecast = build_visit_forecast(
            institution=institution,
            cabinet=cabinet,
            visit_date=visit_date,
        )

    cabinets_data = list(
        Cabinet.objects.order_by("name").values(
            "id", "name", "cabinet_type", "institution_id"
        )
    )

    return render(request, "pages/prediction.html", {
        "form": form,
        "forecast": forecast,
        "institution": institution,
        "cabinet": cabinet,
        "visit_date": visit_date,
        "cabinets_data": cabinets_data,
    })

def register(request):
    if request.user.is_authenticated:
        return redirect("index")

    form = SignUpForm(
        request.POST if request.method == "POST" else None
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            "Аккаунт создан. Войдите под своим ником и паролем.",
        )
        return redirect("login")

    return render(request, "pages/auth.html", {
        "form": form,
        "is_signup": True,
    })