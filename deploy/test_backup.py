import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("backup_sqlite.py")


class BackupTests(unittest.TestCase):
    def test_snapshot_includes_committed_wal_data(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.sqlite3"
            with sqlite3.connect(source) as connection:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("CREATE TABLE notes (text TEXT)")
                connection.execute("INSERT INTO notes VALUES ('keep this record')")
                connection.commit()
                # Keep the source open so data may still be in its WAL file.
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), str(source)],
                    capture_output=True, check=True,
                )
                backup = Path(directory) / "backup.sqlite3"
                backup.write_bytes(result.stdout)
                with sqlite3.connect(backup) as snapshot:
                    self.assertEqual(snapshot.execute("PRAGMA integrity_check").fetchone(), ("ok",))
                    self.assertEqual(snapshot.execute("SELECT text FROM notes").fetchall(), [("keep this record",)])

    def test_missing_database_fails_without_creating_one(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "missing.sqlite3"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(source)], capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b"")
            self.assertFalse(source.exists())
