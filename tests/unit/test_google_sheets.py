from __future__ import annotations

import json
import logging
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from sheets_supabase_sync.errors import ErrorCode, SyncError, classify_http_error, safe_error_message
from sheets_supabase_sync.google_config import SHEETS_READONLY_SCOPE, load_google_sheets_config
from sheets_supabase_sync.google_sheets import GoogleSheetsReader, validate_fictitious_fixture
from sheets_supabase_sync.retries import RetryPolicy


class FakeTransport:
    def __init__(self, metadata=None, values=None, failures=None) -> None:
        self.metadata = metadata or {"sheets": [{"properties": {"title": "Fixture"}}]}
        self.values = values or {"values": [["codigo", "quantidade"], ["A-1", "2"]]}
        self.failures = list(failures or [])
        self.calls: list[str] = []

    def _respond(self, kind: str, payload):
        self.calls.append(kind)
        if self.failures:
            raise self.failures.pop(0)
        return payload

    def get_metadata(self, spreadsheet_id: str, timeout_seconds: float):
        return self._respond("metadata", self.metadata)

    def get_values(self, spreadsheet_id: str, sheet_range: str, timeout_seconds: float):
        return self._respond("values", self.values)


def reader(transport: FakeTransport, pauses: list[float] | None = None) -> GoogleSheetsReader:
    return GoogleSheetsReader(
        transport,
        retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=1, max_delay_seconds=4, max_elapsed_seconds=20, jitter_ratio=0),
        pause=(pauses if pauses is not None else []).append,
        random_value=lambda: 0,
        clock=lambda: datetime(2026, 8, 6, 12, tzinfo=UTC),
    )


class GoogleConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.repository = self.base / "repository"
        self.repository.mkdir()
        self.credential = self.base / "credential.json"
        self.credential.write_text(json.dumps({"type": "service_account", "private_key": "hidden", "client_email": "fixture@project.iam.gserviceaccount.com", "token_uri": "https://oauth2.googleapis.com/token"}), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_environment(self, credential: Path | None = None, spreadsheet_id: str = "private-fixture-123", sheet_name: str = "Fixture") -> None:
        chosen = credential or self.credential
        (self.repository / ".env.local").write_text(f"GOOGLE_SERVICE_ACCOUNT_FILE={chosen}\nGOOGLE_TEST_SPREADSHEET_ID={spreadsheet_id}\nGOOGLE_TEST_SHEET_NAME={sheet_name}\n", encoding="utf-8")

    def test_valid_configuration(self) -> None:
        self.write_environment()
        config = load_google_sheets_config(self.repository)
        self.assertEqual("Fixture", config.sheet_name)

    def test_missing_credential(self) -> None:
        self.write_environment(self.base / "missing.json")
        with self.assertRaisesRegex(SyncError, "ausente") as raised:
            load_google_sheets_config(self.repository)
        self.assertEqual(ErrorCode.CREDENTIAL_MISSING, raised.exception.code)

    def test_invalid_json(self) -> None:
        self.credential.write_text("not-json", encoding="utf-8")
        self.write_environment()
        with self.assertRaises(SyncError) as raised:
            load_google_sheets_config(self.repository)
        self.assertEqual(ErrorCode.CREDENTIAL_INVALID, raised.exception.code)

    def test_credential_inside_repository_is_rejected(self) -> None:
        credential = self.repository / "credential.json"
        credential.write_text(self.credential.read_text(encoding="utf-8"), encoding="utf-8")
        self.write_environment(credential)
        with self.assertRaises(SyncError) as raised:
            load_google_sheets_config(self.repository)
        self.assertEqual(ErrorCode.CREDENTIAL_INVALID, raised.exception.code)

    def test_placeholder_and_empty_sheet_name_are_invalid(self) -> None:
        self.write_environment(spreadsheet_id="replace-with-id")
        with self.assertRaises(SyncError):
            load_google_sheets_config(self.repository)
        self.write_environment(sheet_name="")
        with self.assertRaises(SyncError):
            load_google_sheets_config(self.repository)

    def test_scope_is_exactly_readonly(self) -> None:
        self.assertEqual("https://www.googleapis.com/auth/spreadsheets.readonly", SHEETS_READONLY_SCOPE)
        self.assertNotIn("drive", SHEETS_READONLY_SCOPE)

    def test_invalid_retry_configuration_is_rejected(self) -> None:
        self.write_environment()
        with (self.repository / ".env.local").open("a", encoding="utf-8") as environment:
            environment.write("GOOGLE_RETRY_MAX_ATTEMPTS=zero\n")
        with self.assertRaises(SyncError) as raised:
            load_google_sheets_config(self.repository)
        self.assertEqual(ErrorCode.CONFIGURATION, raised.exception.code)


class GoogleReaderTests(unittest.TestCase):
    def test_valid_header_and_deterministic_result(self) -> None:
        first = reader(FakeTransport()).read("secret-id", "Fixture")
        second = reader(FakeTransport()).read("secret-id", "Fixture")
        self.assertEqual(("codigo", "quantidade"), first.header)
        self.assertEqual(first.source_hash, second.source_hash)
        self.assertEqual(datetime(2026, 8, 6, 12, tzinfo=UTC), first.read_at)

    def test_spreadsheet_not_found(self) -> None:
        transport = FakeTransport(failures=[classify_http_error(404)])
        with self.assertRaises(SyncError) as raised:
            reader(transport).read("secret-id", "Fixture")
        self.assertEqual(ErrorCode.NOT_FOUND, raised.exception.code)
        self.assertEqual(1, len(transport.calls))

    def test_sheet_not_found(self) -> None:
        transport = FakeTransport(metadata={"sheets": [{"properties": {"title": "Other"}}]})
        with self.assertRaises(SyncError) as raised:
            reader(transport).read("secret-id", "Fixture")
        self.assertEqual(ErrorCode.SHEET_NOT_FOUND, raised.exception.code)
        self.assertEqual(["metadata"], transport.calls)

    def test_permission_denied_does_not_retry(self) -> None:
        transport = FakeTransport(failures=[classify_http_error(403)])
        with self.assertRaises(SyncError):
            reader(transport).read("secret-id", "Fixture")
        self.assertEqual(1, len(transport.calls))

    def test_authentication_rejected_does_not_retry(self) -> None:
        transport = FakeTransport(failures=[classify_http_error(401)])
        with self.assertRaises(SyncError) as raised:
            reader(transport).read("secret-id", "Fixture")
        self.assertEqual(ErrorCode.AUTHENTICATION, raised.exception.code)
        self.assertEqual(1, len(transport.calls))

    def test_http_429_retries(self) -> None:
        pauses: list[float] = []
        transport = FakeTransport(failures=[classify_http_error(429)])
        result = reader(transport, pauses).read("secret-id", "Fixture")
        self.assertEqual([1], pauses)
        self.assertEqual(1, result.retry_count)

    def test_http_503_retries(self) -> None:
        transport = FakeTransport(failures=[classify_http_error(503)])
        self.assertEqual(1, reader(transport).read("secret-id", "Fixture").retry_count)

    def test_all_supported_server_errors_retry(self) -> None:
        for status in (500, 502, 503, 504):
            with self.subTest(status=status):
                transport = FakeTransport(failures=[classify_http_error(status)])
                self.assertEqual(1, reader(transport).read("secret-id", "Fixture").retry_count)

    def test_permanent_http_errors_never_retry(self) -> None:
        for status in (400, 401, 403, 404):
            with self.subTest(status=status):
                transport = FakeTransport(failures=[classify_http_error(status)])
                with self.assertRaises(SyncError):
                    reader(transport).read("secret-id", "Fixture")
                self.assertEqual(1, len(transport.calls))

    def test_timeout_retries(self) -> None:
        error = SyncError(ErrorCode.TIMEOUT, "timeout", True)
        transport = FakeTransport(failures=[error])
        self.assertEqual(1, reader(transport).read("secret-id", "Fixture").retry_count)

    def test_connection_error_retries(self) -> None:
        error = SyncError(ErrorCode.NETWORK, "connection", True)
        transport = FakeTransport(failures=[error])
        self.assertEqual(1, reader(transport).read("secret-id", "Fixture").retry_count)

    def test_retries_exhausted(self) -> None:
        transient = classify_http_error(503)
        transport = FakeTransport(failures=[transient, transient, transient])
        with self.assertRaises(SyncError):
            reader(transport).read("secret-id", "Fixture")
        self.assertEqual(3, len(transport.calls))

    def test_retry_after_is_respected(self) -> None:
        pauses: list[float] = []
        transport = FakeTransport(failures=[classify_http_error(429, 7)])
        reader(transport, pauses).read("secret-id", "Fixture")
        self.assertEqual([7], pauses)

    def test_empty_header(self) -> None:
        with self.assertRaises(SyncError) as raised:
            reader(FakeTransport(values={"values": [["codigo", ""]]})).read("secret-id", "Fixture")
        self.assertEqual(ErrorCode.SCHEMA, raised.exception.code)

    def test_duplicate_header(self) -> None:
        with self.assertRaises(SyncError) as raised:
            reader(FakeTransport(values={"values": [["codigo", "codigo"]]})).read("secret-id", "Fixture")
        self.assertEqual(ErrorCode.SCHEMA, raised.exception.code)

    def test_normalized_duplicate_header(self) -> None:
        with self.assertRaises(SyncError):
            reader(FakeTransport(values={"values": [["Codigo", "codigo!"]]})).read("secret-id", "Fixture")

    def test_empty_sheet(self) -> None:
        with self.assertRaises(SyncError) as raised:
            reader(FakeTransport(values={"values": []})).read("secret-id", "Fixture")
        self.assertEqual(ErrorCode.EMPTY_SHEET, raised.exception.code)

    def test_empty_rows_missing_values_and_source_number(self) -> None:
        transport = FakeTransport(values={"values": [["a", "b"], ["1"], [], ["2", "3"]]})
        result = reader(transport).read("secret-id", "Fixture")
        self.assertEqual((2, 4), tuple(row.source_row_number for row in result.rows))
        self.assertEqual(("1", ""), result.rows[0].values)
        self.assertEqual(1, result.empty_rows_ignored)

    def test_values_remain_text_and_ordered(self) -> None:
        result = reader(FakeTransport(values={"values": [["a", "b"], [12, "2026-08-06"]]})).read("secret-id", "Fixture")
        self.assertEqual(("12", "2026-08-06"), result.rows[0].values)

    def test_invalid_metadata_and_row_are_rejected(self) -> None:
        with self.assertRaises(SyncError):
            reader(FakeTransport(metadata={"bad": []})).read("secret-id", "Fixture")
        with self.assertRaises(SyncError):
            reader(FakeTransport(values={"values": [["a"], "bad"]})).read("secret-id", "Fixture")

    def test_logs_are_sanitized(self) -> None:
        logger = logging.getLogger("test.google.sanitized")
        instance = GoogleSheetsReader(FakeTransport(), pause=lambda _: None, random_value=lambda: 0, logger=logger)
        with self.assertLogs(logger, "INFO") as records:
            instance.read("spreadsheet-secret", "Fixture")
        output = " ".join(records.output)
        self.assertNotIn("spreadsheet-secret", output)
        self.assertNotIn("A-1", output)
        self.assertNotIn("codigo", output)

    def test_retry_log_has_operational_allowlist(self) -> None:
        logger = logging.getLogger("test.google.retry.fields")
        transport = FakeTransport(failures=[classify_http_error(429, 2)])
        instance = GoogleSheetsReader(
            transport,
            retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=1, max_delay_seconds=4, max_elapsed_seconds=20, jitter_ratio=0),
            pause=lambda _: None,
            random_value=lambda: 0,
            logger=logger,
        )
        with self.assertLogs(logger, "INFO") as captured:
            instance.read("spreadsheet-secret", "Fixture")
        retry_line = next(line for line in captured.output if "google_sheet_retry" in line)
        for field in ("operation", "attempt", "max_attempts", "error_category", "retryable", "backoff_ms", "duration_ms", "outcome"):
            self.assertIn(field, retry_line)
        self.assertNotIn("spreadsheet-secret", retry_line)

    def test_no_supabase_access_is_part_of_reader_boundary(self) -> None:
        transport = FakeTransport()
        reader(transport).read("secret-id", "Fixture")
        self.assertEqual(["metadata", "values"], transport.calls)

    def test_secrets_are_hidden_in_safe_errors(self) -> None:
        self.assertEqual("Erro sensivel ocultado", safe_error_message(RuntimeError("private_key=secret")))
        error = classify_http_error(401)
        self.assertNotIn("secret-id", error.message)

    def test_personal_data_patterns_are_rejected(self) -> None:
        personal_header = reader(FakeTransport(values={"values": [["email"], ["fake@example.test"]]})).read("secret-id", "Fixture")
        with self.assertRaises(SyncError):
            validate_fictitious_fixture(personal_header)
        personal_value = reader(FakeTransport(values={"values": [["codigo"], ["someone@example.test"]]})).read("secret-id", "Fixture")
        with self.assertRaises(SyncError):
            validate_fictitious_fixture(personal_value)

    def test_fictitious_non_personal_fixture_is_accepted(self) -> None:
        result = reader(FakeTransport()).read("secret-id", "Fixture")
        validate_fictitious_fixture(result)


if __name__ == "__main__":
    unittest.main()
