from __future__ import annotations

import os
import unittest


DATABASE_URL = os.getenv("LOCAL_DATABASE_URL")


@unittest.skipUnless(
    os.getenv("RUN_SUPABASE_INTEGRATION") == "1" and DATABASE_URL,
    "PostgreSQL local nao configurado; use somente LOCAL_DATABASE_URL local.",
)
class OperationalPostgresTests(unittest.TestCase):
    def connect(self):
        import psycopg

        return psycopg.connect(DATABASE_URL, connect_timeout=5)

    def test_same_source_is_busy_and_different_source_is_not_blocked(self) -> None:
        with self.connect() as first, self.connect() as second:
            with first.cursor() as cursor:
                cursor.execute("SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0))", ("source-a",))
                self.assertTrue(cursor.fetchone()[0])
            with second.cursor() as cursor:
                cursor.execute("SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0))", ("source-a",))
                self.assertFalse(cursor.fetchone()[0])
                cursor.execute("SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0))", ("source-b",))
                self.assertTrue(cursor.fetchone()[0])
            first.rollback()
            second.rollback()

    def test_transaction_rollback_preserves_all_operational_counts(self) -> None:
        before = self._counts()
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0))", ("rollback-fixture",))
                self.assertTrue(cursor.fetchone()[0])
                cursor.execute("SELECT count(*) FROM public.sync_runs")
                raise RuntimeError("fault before commit")
        except RuntimeError:
            connection.rollback()
        finally:
            connection.close()
        self.assertEqual(before, self._counts())

    def _counts(self) -> tuple[int, ...]:
        tables = ("data_sources", "sync_runs", "raw_import_rows", "raw_current_rows")
        with self.connect() as connection, connection.cursor() as cursor:
            counts = []
            for table in tables:
                cursor.execute(f"SELECT count(*) FROM public.{table}")
                counts.append(cursor.fetchone()[0])
            connection.rollback()
        return tuple(counts)


if __name__ == "__main__":
    unittest.main()
