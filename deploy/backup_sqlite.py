"""Write a consistent SQLite snapshot to stdout; usable through docker exec -i."""

import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path


def main():
    source = Path(sys.argv[1]).resolve(strict=True)
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "snapshot.sqlite3"
        with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as original:
            with sqlite3.connect(target) as snapshot:
                original.backup(snapshot)
                if snapshot.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                    raise RuntimeError("Database backup integrity check failed")
        with target.open("rb") as stream:
            shutil.copyfileobj(stream, sys.stdout.buffer)


if __name__ == "__main__":
    main()
