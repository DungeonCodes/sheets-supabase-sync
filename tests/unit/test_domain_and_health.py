from __future__ import annotations

import logging
import unittest
from datetime import UTC, date, datetime, timedelta

from sheets_supabase_sync.errors import ErrorCode, SyncError, classify_http_error, safe_error_message
from sheets_supabase_sync.hashing import deterministic_hash
from sheets_supabase_sync.health import AlertSeverity, SourceHealth, alerts_for
from sheets_supabase_sync.normalization import infer_type
from sheets_supabase_sync.observability import log_event
from sheets_supabase_sync.retries import retry
from sheets_supabase_sync.source_reader import FakeSourceReader
from sheets_supabase_sync.source_urls import extract_spreadsheet_id


class DomainAndHealthTests(unittest.TestCase):
    def test_extract_spreadsheet_id_and_reject_invalid_url(self) -> None:
        self.assertEqual("abcDEF_123456", extract_spreadsheet_id("https://docs.google.com/spreadsheets/d/abcDEF_123456/edit#gid=0"))
        with self.assertRaises(ValueError):
            extract_spreadsheet_id("https://example.test/sheet")

    def test_type_inference(self) -> None:
        self.assertEqual("text", infer_type(["ana", None]))
        self.assertEqual("integer", infer_type([1, 2]))
        self.assertEqual("numeric", infer_type([1.5, 2]))
        self.assertEqual("boolean", infer_type([True, False]))
        self.assertEqual("date", infer_type([date(2026, 8, 3), "2026-08-04"]))
        self.assertEqual("text", infer_type([None, ""]))

    def test_hash_and_retries(self) -> None:
        self.assertEqual(deterministic_hash({"a": 1}), deterministic_hash({"a": 1}))
        self.assertNotEqual(deterministic_hash({"a": 1}), deterministic_hash({"a": 2}))
        attempts = [0]
        def operation() -> str:
            attempts[0] += 1
            if attempts[0] < 3:
                raise SyncError(ErrorCode.TRANSIENT, "temporario", True)
            return "ok"
        self.assertEqual("ok", retry(operation, pause=lambda _: None))

    def test_error_classification_fake_reader_and_safe_message(self) -> None:
        self.assertEqual(ErrorCode.QUOTA, classify_http_error(429).code)
        with self.assertRaises(SyncError):
            FakeSourceReader({}).read("sheet", "aba")
        self.assertEqual("Erro sensivel ocultado", safe_error_message(RuntimeError("postgresql://user:senha@host")))

    def test_alerts_and_safe_logging(self) -> None:
        now = datetime(2026, 8, 3, 12, tzinfo=UTC)
        health = SourceHealth(True, 180, last_success_at=now - timedelta(minutes=271), consecutive_failures=3)
        self.assertEqual({AlertSeverity.CRITICAL}, {alert.severity for alert in alerts_for(health, now)})
        logger = logging.getLogger("test.safe")
        with self.assertLogs(logger, "INFO") as records:
            log_event(logger, "sync_failed", data_source_id="source", password="no", rows_read=1)
        self.assertNotIn("password", records.output[0])
