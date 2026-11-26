import os
import shutil
import subprocess
import sys
import time
import urllib.request

OLLAMA_API = "http://localhost:11434"
OLLAMA_PATHS = [
    "/usr/local/bin/ollama",
    "/opt/homebrew/bin/ollama",
    os.path.expanduser("~/Applications/Ollama.app/Contents/Resources/ollama"),
    "/Applications/Ollama.app/Contents/Resources/ollama",
]


def find_ollama():
    which = shutil.which("ollama")
    if which:
        return which
    for path in OLLAMA_PATHS:
        if os.path.exists(path):
            return path
    return None


def install_ollama():
    print("Ollama не найден. Устанавливаю официальным скриптом...")
    print("Потребуется пароль администратора.")
    subprocess.run(
        ["/bin/sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
        check=False,
    )

    if find_ollama() is not None:
        return True

    if shutil.which("brew"):
        print("Пробую установить через Homebrew...")
        subprocess.run(["brew", "install", "ollama"], check=False)

    if find_ollama() is not None:
        return True

    print("Не удалось установить Ollama автоматически.")
    print("Скачайте Ollama.dmg с https://ollama.com, установите "
          "и перезапустите start_mac.py")
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
    venv_python = os.path.join(".venv", "bin", "python")
    if os.path.exists(venv_python):
        print("Виртуальное окружение найдено.")
        return venv_python
    print("Создаю виртуальное окружение...")
    python3 = shutil.which("python3")
    if python3 is None:
        sys.exit("python3 не найден. Установите Command Line Tools: "
                 "xcode-select --install")
    subprocess.run([python3, "-m", "venv", ".venv"], check=True)
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
    print("=== Инициализация проекта quiet-queue (macOS) ===")
    venv_python = ensure_venv()
    install_requirements(venv_python)
    run_migrations(venv_python)
    seed_data(venv_python)
    ensure_ollama()

    print("\nЗапускаю сервер: http://127.0.0.1:8000\n")
    subprocess.run([venv_python, "manage.py", "runserver"])


if __name__ == "__main__":
    main()
