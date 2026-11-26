from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Загружает реальные учреждения из фикстуры"

    def handle(self, *args, **options):
        call_command("loaddata", "institutions.json", verbosity=0)
        self.stdout.write(self.style.SUCCESS("Учреждения загружены"))
