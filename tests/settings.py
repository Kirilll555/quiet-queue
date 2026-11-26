"""Настройки для всех тестов, включая тестовый HTTP-сервер."""

from pathlib import Path
from tempfile import TemporaryDirectory

from config.settings import *

# Тип базы известен до старта live_server, даже при отдельном запуске нагрузки.
_db_directory = TemporaryDirectory(prefix="quiet-queue-qa-", ignore_cleanup_errors=True)
_db_root = Path(_db_directory.name)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": _db_root / "bootstrap.sqlite3",
        "TEST": {"NAME": _db_root / "test.sqlite3"},
    }
}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
YANDEX_MAPS_API_KEY = ""

STORAGES = {
    **STORAGES,
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
