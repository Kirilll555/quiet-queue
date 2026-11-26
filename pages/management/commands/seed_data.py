import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from pages.models import Institution, Cabinet, QueueReport, ReportCooldown, InstitutionRequest

LEVELS = ["low", "medium", "high"]

LEVEL_WEIGHTS = {
    0: [0.35, 0.45, 0.20],
    1: [0.30, 0.50, 0.20],
    2: [0.25, 0.50, 0.25],
    3: [0.20, 0.45, 0.35],
    4: [0.30, 0.45, 0.25],
    5: [0.45, 0.40, 0.15],
    6: [0.55, 0.35, 0.10],
}

HOUR_WEIGHTS = {
    8: [0.40, 0.40, 0.20],
    9: [0.25, 0.45, 0.30],
    10: [0.15, 0.40, 0.45],
    11: [0.15, 0.45, 0.40],
    12: [0.30, 0.45, 0.25],
    13: [0.45, 0.40, 0.15],
    14: [0.40, 0.45, 0.15],
    15: [0.30, 0.45, 0.25],
    16: [0.35, 0.45, 0.20],
    17: [0.50, 0.35, 0.15],
    18: [0.50, 0.40, 0.10],
    19: [0.55, 0.35, 0.10],
}


def pick_level(weekday, hour):
    hour_weights = HOUR_WEIGHTS.get(hour, [1, 1, 1])
    base = LEVEL_WEIGHTS[weekday]
    weights = [a * b for a, b in zip(base, hour_weights)]
    return random.choices(LEVELS, weights=weights, k=1)[0]


def parse_working_hours(working_hours):
    start_str, end_str = working_hours.split("-")
    return int(start_str.strip().split(":")[0]), int(end_str.strip().split(":")[0])


class Command(BaseCommand):
    help = 'Загружает реальные данные учреждений Махачкалы и демо-оценки очередей'

    def handle(self, *args, **kwargs):
        self.stdout.write('Очистка старых данных...')
        QueueReport.objects.all().delete()
        Cabinet.objects.all().delete()
        Institution.objects.all().delete()
        InstitutionRequest.objects.all().delete()
        ReportCooldown.objects.all().delete()

        User = get_user_model()
        user, created = User.objects.get_or_create(username='tester')

        self.stdout.write('Добавление учреждений...')

        data = [
            {
                'name': 'ГБУ РД "Поликлиника №1"',
                'category': 'Поликлиника',
                'address': 'г. Махачкала, ул. Лаптиева, 55',
                'working_hours': '08:00 - 18:00',
                'latitude': 42.977000,
                'longitude': 47.495000,
                'cabinets': ['Кабинет №1 (Терапевт)', 'Кабинет №2 (Хирург)', 'Кабинет №3 (Окулист)'],
            },
            {
                'name': 'ГБУ РД "Поликлиника №4"',
                'category': 'Поликлиника',
                'address': 'г. Махачкала, ул. Ирчи Казака, 31',
                'working_hours': '08:00 - 17:00',
                'latitude': 42.973000,
                'longitude': 47.485000,
                'cabinets': ['Кабинет №1 (Терапевт)', 'Кабинет №2 (Стоматолог)'],
            },
            {
                'name': 'МФЦ "Мои документы" (Центральный)',
                'category': 'МФЦ',
                'address': 'г. Махачкала, ул. Коркмасова, 33',
                'working_hours': '08:00 - 20:00',
                'latitude': 42.983000,
                'longitude': 47.500000,
                'cabinets': ['Окно №1', 'Окно №2', 'Окно №3', 'Окно №4'],
            },
            {
                'name': 'МФЦ "Мои документы" (Кировский)',
                'category': 'МФЦ',
                'address': 'г. Махачкала, пр. И. Шамиля, 44',
                'working_hours': '08:00 - 20:00',
                'latitude': 42.970000,
                'longitude': 47.470000,
                'cabinets': ['Окно №1', 'Окно №2'],
            },
            {
                'name': 'Отделение Почты России №1',
                'category': 'Почта',
                'address': 'г. Махачкала, ул. Буйнакского, 10',
                'working_hours': '09:00 - 18:00',
                'latitude': 42.981000,
                'longitude': 47.502000,
                'cabinets': ['Окно приема', 'Окно выдачи'],
            }
        ]

        now = timezone.localtime()
        reports_created = 0

        for item in data:
            inst = Institution.objects.create(
                name=item['name'],
                category=item['category'],
                address=item['address'],
                working_hours=item['working_hours'],
                latitude=item['latitude'],
                longitude=item['longitude']
            )

            cabinets = []
            for cab_name in item['cabinets']:
                cab = Cabinet.objects.create(
                    institution=inst,
                    name=cab_name,
                    cabinet_type='Прием'
                )
                cabinets.append(cab)

            start_hour, end_hour = parse_working_hours(item['working_hours'])

            for day_offset in range(42, 0, -1):
                day = now - timedelta(days=day_offset)
                for hour in range(start_hour, end_hour):
                    report_time = day.replace(
                        hour=hour,
                        minute=random.randint(0, 59),
                        second=0,
                        microsecond=0,
                    )
                    QueueReport.objects.create(
                        user=user,
                        institution=inst,
                        queue_level=pick_level(day.weekday(), hour),
                        created_at=report_time,
                    )
                    reports_created += 1

                    if cabinets:
                        QueueReport.objects.create(
                            user=user,
                            institution=inst,
                            cabinet=cabinets[0],
                            queue_level=pick_level(day.weekday(), hour),
                            created_at=report_time + timedelta(minutes=1),
                        )
                        reports_created += 1

            self.stdout.write(self.style.SUCCESS(f'Успешно добавлено: {inst.name}'))

        self.stdout.write(self.style.SUCCESS(f'Создано отчётов: {reports_created}'))
        self.stdout.write(self.style.SUCCESS('База данных успешно наполнена!'))
