import sqlite3
import tempfile
import unittest
from pathlib import Path

import backend.db as db_module


LEGACY_SCHEMA = """
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    prompt TEXT NOT NULL,
    mode TEXT NOT NULL CHECK(mode IN ('text','opening','closing','frames','reference')),
    duration INTEGER NOT NULL CHECK(duration IN (5,10)),
    seed TEXT NOT NULL,
    status TEXT NOT NULL,
    position INTEGER NOT NULL,
    input_path TEXT,
    input_name TEXT,
    first_frame_path TEXT,
    first_frame_name TEXT,
    last_frame_path TEXT,
    last_frame_name TEXT,
    output_path TEXT,
    prompt_id TEXT,
    progress REAL NOT NULL DEFAULT 0,
    phase TEXT NOT NULL DEFAULT 'queued',
    step INTEGER NOT NULL DEFAULT 0,
    total_steps INTEGER NOT NULL DEFAULT 0,
    eta_seconds REAL,
    error TEXT,
    metrics_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT
);
CREATE INDEX idx_jobs_queue ON jobs(status, position);
"""


class DatabaseMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="h3-db-test-")
        self.path = Path(self.temp.name) / "jobs.sqlite3"
        self.original_path = db_module.DB_PATH
        db_module.DB_PATH = self.path
        connection = sqlite3.connect(self.path)
        try:
            connection.executescript(LEGACY_SCHEMA)
            connection.executemany(
                """
                INSERT INTO jobs
                  (id,prompt,mode,duration,seed,status,position,output_path,progress,phase,
                   step,total_steps,metrics_json,created_at,updated_at,finished_at)
                VALUES(?,?,?,?,?,'completed',?,?,?,?,?,?,?, ?,?,?)
                """,
                [
                    ("turbo-old", "one", "text", 5, "1", 1, "one.mp4", 1, "completed", 4, 4, '{"generation_seconds":10}', "2026-01-01", "2026-01-01", "2026-01-01"),
                    ("reference-old", "two", "reference", 5, "2", 2, "two.mp4", 1, "completed", 20, 20, '{"generation_seconds":20}', "2026-01-02", "2026-01-02", "2026-01-02"),
                ],
            )
            connection.commit()
        finally:
            connection.close()

    def tearDown(self):
        db_module.DB_PATH = self.original_path
        self.temp.cleanup()

    def test_migration_preserves_rows_and_backfills_profiles(self):
        db_module.init_db()
        db_module.init_db()

        connection = sqlite3.connect(self.path)
        try:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            rows = connection.execute(
                "SELECT id,engine,turbo_profile,encoder,steps,width,height,output_path,reference_audio_name FROM jobs ORDER BY id"
            ).fetchall()
        finally:
            connection.close()

        self.assertEqual(rows, [
            ("reference-old", "standard", "v1", "native", 20, 736, 416, "two.mp4", None),
            ("turbo-old", "turbo", "v1", "native", 4, 736, 416, "one.mp4", None),
        ])
        connection = sqlite3.connect(self.path)
        try:
            tables = {row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        finally:
            connection.close()
        self.assertTrue({"sequences", "sequence_items"}.issubset(tables))
        self.assertEqual(
            [item["id"] for item in db_module.list_jobs()],
            ["reference-old", "turbo-old"],
        )

    def test_failed_rebuild_rolls_back_and_keeps_the_source_table(self):
        connection = sqlite3.connect(self.path)
        try:
            # A NULL status violates the rebuilt table and aborts the copy.
            connection.executescript("""
                CREATE TABLE jobs_broken AS SELECT * FROM jobs;
                DROP TABLE jobs;
                ALTER TABLE jobs_broken RENAME TO jobs;
                UPDATE jobs SET status=NULL WHERE id='turbo-old';
            """)
            connection.commit()
        finally:
            connection.close()

        with self.assertRaises(sqlite3.IntegrityError):
            db_module.init_db()

        connection = sqlite3.connect(self.path)
        try:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertNotIn("jobs_legacy", tables)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 2)
        finally:
            connection.close()

    def test_rebuild_keeps_history_from_experimental_engines(self):
        db_module.init_db()
        connection = sqlite3.connect(self.path)
        try:
            connection.execute("UPDATE jobs SET engine='turbo',turbo_profile='official' WHERE id='turbo-old'")
            connection.execute("UPDATE jobs SET engine='fused',mode='text',steps=4 WHERE id='reference-old'")
            connection.commit()
            rows = dict(connection.execute("SELECT id,engine FROM jobs"))
        finally:
            connection.close()
        self.assertEqual(rows, {"turbo-old": "turbo", "reference-old": "fused"})


if __name__ == "__main__":
    unittest.main()
