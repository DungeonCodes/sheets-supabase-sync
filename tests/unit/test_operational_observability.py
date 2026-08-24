from __future__ import annotations

import logging
import unittest
from datetime import UTC, datetime, timedelta

from sheets_supabase_sync.alerting import AlertDeduplicator, AlertPolicy, InMemoryAlertSink, OperationalReporter, SmtpAlertSink
from sheets_supabase_sync.operational_events import OperationalEvent, Severity, sanitize_text


def event(severity: Severity, *, category: str = "database", source: str = "safe-source") -> OperationalEvent:
    return OperationalEvent(datetime(2026, 8, 24, tzinfo=UTC), "postgres", "sync", "failed", severity, source, "safe-run", 1, 3, False, category, category, 10, 0)


class OperationalObservabilityTests(unittest.TestCase):
    def test_severity_policy_and_ambiguous_outcome(self) -> None:
        self.assertFalse(AlertPolicy().eligible(event(Severity.WARNING)))
        self.assertTrue(AlertPolicy().eligible(event(Severity.ERROR)))
        ambiguous = event(Severity.CRITICAL, category="ambiguous_outcome")
        self.assertTrue(AlertPolicy().eligible(ambiguous))
        self.assertFalse(ambiguous.retryable)

    def test_deduplication_and_cooldown(self) -> None:
        dedupe = AlertDeduplicator(timedelta(minutes=10))
        first = event(Severity.ERROR)
        self.assertTrue(dedupe.allow(first))
        self.assertFalse(dedupe.allow(first))
        self.assertTrue(dedupe.allow(event(Severity.ERROR, category="authentication")))
        later = OperationalEvent(first.timestamp + timedelta(minutes=10), first.component, first.operation, first.outcome, first.severity, first.source_ref, first.execution_id, first.attempt, first.max_attempts, first.retryable, first.error_category)
        self.assertTrue(dedupe.allow(later))

    def test_reporter_does_not_alert_retry_or_corrupt_on_transport_failure(self) -> None:
        sink = InMemoryAlertSink()
        reporter = OperationalReporter(logging.getLogger("test.observer"), sink)
        reporter.emit(event(Severity.WARNING))
        reporter.emit(event(Severity.ERROR))
        reporter.emit(event(Severity.ERROR))
        self.assertEqual(1, len(sink.events))

        class BrokenSink:
            def send(self, ignored):
                raise RuntimeError("password=never-log")
        OperationalReporter(logging.getLogger("test.broken"), BrokenSink()).emit(event(Severity.ERROR, category="permanent"))

    def test_sanitization_hides_secrets_urls_and_payloads(self) -> None:
        for value in ("password=secret", "postgresql://user:secret@example", "Authorization: token-value"):
            self.assertEqual("sensitive_detail_hidden", sanitize_text(value))
        self.assertNotIn("payload", event(Severity.INFO).as_json())

    def test_smtp_is_mockable_and_disabled_transport_is_safe(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "disabled"):
            SmtpAlertSink(None, None, None).send(event(Severity.ERROR))
        sent = []
        class FakeSmtp:
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def send_message(self, message): sent.append(message)
        SmtpAlertSink("mail.example", "sender@example", "ops@example", lambda _: FakeSmtp()).send(event(Severity.CRITICAL, category="ambiguous_outcome"))
        self.assertEqual(1, len(sent))
        self.assertNotIn("postgresql", sent[0].as_string().lower())
