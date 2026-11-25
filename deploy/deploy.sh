#!/usr/bin/env bash
set -euo pipefail
umask 077

sha=${1:?Usage: bash deploy/deploy.sh COMMIT_SHA}
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo "Invalid commit SHA" >&2; exit 1; }
release=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
root=/opt/quiet-queue
[[ "$release" == "$root/releases/$sha" ]] || { echo "Unexpected release directory" >&2; exit 1; }
test -s "$root/.env"

# Keep certificate and database volume names identical to the existing installation.
export APP_IMAGE="quiet-queue:$sha"
compose=(docker compose --project-name quiet-queue --env-file "$root/.env"
    -f "$release/compose.yaml" -f "$release/compose.production.yaml"
    -f "$release/compose.release.yaml")

exec 9>"$root/.deploy.lock"
flock -w 600 9
"${compose[@]}" config --quiet
docker image inspect "$APP_IMAGE" >/dev/null

# Never proceed without backing up the currently running site's database.
mkdir -p "$root/backups"
chmod 700 "$root/backups"
backup="$root/backups/$(date -u +%Y%m%dT%H%M%S)-$sha.sqlite3"
trap 'rm -f -- "$backup.tmp"' EXIT
docker exec -i quiet-queue-web-1 python - /data/db.sqlite3 \
    < "$release/deploy/backup_sqlite.py" > "$backup.tmp"
test -s "$backup.tmp"
mv -- "$backup.tmp" "$backup"
echo "Database backup saved: $backup"

# Migration failure leaves the old app running. Schema changes need compatible migrations.
"${compose[@]}" run --rm --no-deps web python manage.py migrate --noinput
"${compose[@]}" up -d --no-build --wait --wait-timeout 180
curl --fail --show-error --silent --max-time 15 http://127.0.0.1:8000/healthz/
printf '\n'
printf '%s\n' "$sha" > "$root/.active-release.tmp"
mv -- "$root/.active-release.tmp" "$root/.active-release"
"${compose[@]}" ps
echo "Release $sha deployed. Public HTTPS must be checked separately."
