import os
import shutil
import subprocess
import sys
import time
import urllib.request

OLLAMA_API = "http://localhost:11434"
OLLAMA_INSTALL_COMMAND = (
    "irm https://ollama.com/install.ps1 | iex"
)


def find_ollama():
    which = shutil.which("ollama")
    if which:
        return which
    local = os.path.join(
        os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"
    )
    if os.path.exists(local):
        return local
    program_files = os.path.join(
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        "Ollama", "ollama.exe",
    )
    if os.path.exists(program_files):
        return program_files
    return None


def install_ollama():
    print("Ollama не найден. Устанавливаю официальным скриптом...")
    print("Скачивание и установка займут несколько минут, не закрывайте окно.")
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            OLLAMA_INSTALL_COMMAND,
        ],
        check=False,
    )

    if find_ollama() is not None:
        return True

    print("Не удалось установить Ollama автоматически.")
    print("Скачайте установщик с https://ollama.com/download/windows, "
          "запустите его и перезапустите start.py")
    return False


def wait_for_ollama(timeout=15):
    for _ in range(timeout):
        try:
            urllib.request.urlopen(f"{OLLAMA_API}/api/tags", timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


def ensure_ollama():
    ollama = find_ollama()

    try:
        urllib.request.urlopen(f"{OLLAMA_API}/api/tags", timeout=3)
        running = True
    except Exception:
        running = False

    if running:
        return

    if ollama is None:
        if not install_ollama():
            print("ИИ-советы будут отключены, статистический прогноз "
                  "продолжит работать.")
            return
        ollama = find_ollama()

    print("Запускаю Ollama-сервер...")
    subprocess.Popen(
        [ollama, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not wait_for_ollama():
        print("Ollama-сервер не ответил за 15 секунд. "
              "ИИ-советы будут отключены.")


def ensure_venv():
    venv_python = os.path.join(".venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        print("Виртуальное окружение найдено.")
        return venv_python
    print("Создаю виртуальное окружение...")
    subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
    return venv_python


def install_requirements(venv_python):
    print("Устанавливаю зависимости...")
    subprocess.run(
        [venv_python, "-m", "pip", "install", "--upgrade", "pip"],
        stdout=subprocess.DEVNULL,
    )
    subprocess.run([venv_python, "-m", "pip", "install", "-r", "requirements.txt"])


def run_migrations(venv_python):
    print("Применяю миграции...")
    subprocess.run([venv_python, "manage.py", "migrate"], check=True)


def seed_data(venv_python):
    print("Наполняю базу данными...")
    subprocess.run([venv_python, "manage.py", "seed_data"], check=True)


def main():
    print("=== Инициализация проекта quiet-queue ===")
    venv_python = ensure_venv()
    install_requirements(venv_python)
    run_migrations(venv_python)
    seed_data(venv_python)
    ensure_ollama()

    print("\nЗапускаю сервер: http://127.0.0.1:8000\n")
    subprocess.run([venv_python, "manage.py", "runserver"])


if __name__ == "__main__":
    main()
