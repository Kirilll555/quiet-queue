"""Create a local Compose secret, preserving an existing .env file."""
import secrets
from pathlib import Path

path = Path(__file__).resolve().parent.parent / '.env'
try:
    with path.open('x', encoding='utf-8') as stream:
        stream.write(f'DJANGO_SECRET_KEY={secrets.token_urlsafe(64)}\n')
    path.chmod(0o600)
    print('Created .env. Keep it out of Git.')
except FileExistsError:
    print('.env already exists; unchanged. Ensure it contains DJANGO_SECRET_KEY.')
