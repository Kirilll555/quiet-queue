from django.core.management import call_command
from django.db import migrations


def load_institutions(apps, schema_editor):
    call_command("loaddata", "institutions.json")


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0007_auto_20261125_1421"),
    ]

    operations = [
        migrations.RunPython(load_institutions, migrations.RunPython.noop),
    ]
