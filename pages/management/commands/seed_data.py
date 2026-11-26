from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from pages.models import Institution, Cabinet, QueueReport, ReportCooldown, InstitutionRequest


class Command(BaseCommand):
    help = 'Загружает реальные данные учреждений Махачкалы'

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
                'reports': ['low', 'low', 'medium']
            },
            {
                'name': 'ГБУ РД "Поликлиника №4"',
                'category': 'Поликлиника',
                'address': 'г. Махачкала, ул. Ирчи Казака, 31',
                'working_hours': '08:00 - 17:00',
                'latitude': 42.973000,
                'longitude': 47.485000,
                'cabinets': ['Кабинет №1 (Терапевт)', 'Кабинет №2 (Стоматолог)'],
                'reports': ['medium', 'medium', 'high']
            },
            {
                'name': 'МФЦ "Мои документы" (Центральный)',
                'category': 'МФЦ',
                'address': 'г. Махачкала, ул. Коркмасова, 33',
                'working_hours': '08:00 - 20:00',
                'latitude': 42.983000,
                'longitude': 47.500000,
                'cabinets': ['Окно №1', 'Окно №2', 'Окно №3', 'Окно №4'],
                'reports': ['high', 'high', 'high']
            },
            {
                'name': 'МФЦ "Мои документы" (Кировский)',
                'category': 'МФЦ',
                'address': 'г. Махачкала, пр. И. Шамиля, 44',
                'working_hours': '08:00 - 20:00',
                'latitude': 42.970000,
                'longitude': 47.470000,
                'cabinets': ['Окно №1', 'Окно №2'],
                'reports': ['low', 'medium']
            },
            {
                'name': 'Отделение Почты России №1',
                'category': 'Почта',
                'address': 'г. Махачкала, ул. Буйнакского, 10',
                'working_hours': '09:00 - 18:00',
                'latitude': 42.981000,
                'longitude': 47.502000,
                'cabinets': ['Окно приема', 'Окно выдачи'],
                'reports': ['medium']
            }
        ]

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

            now = timezone.now()
            for i, level in enumerate(item['reports']):
                QueueReport.objects.create(
                    user=user,
                    institution=inst,
                    queue_level=level,
                    created_at=now - timedelta(minutes=10 + i * 5)
                )

            if cabinets and item['reports']:
                QueueReport.objects.create(
                    user=user,
                    institution=inst,
                    cabinet=cabinets[0],
                    queue_level=item['reports'][0],
                    created_at=now - timedelta(minutes=5)
                )

            self.stdout.write(self.style.SUCCESS(f'Успешно добавлено: {inst.name}'))

        self.stdout.write(self.style.SUCCESS('База данных успешно наполнена!'))