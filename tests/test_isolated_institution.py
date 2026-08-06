from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from sheets_supabase_sync.batch import synchronize_independently
from sheets_supabase_sync.config import load_institution_config
from sheets_supabase_sync.diff import compare, has_blocking_schema_change
from sheets_supabase_sync.identifiers import normalize_headers, validate_identifier
from sheets_supabase_sync.mirror_schema import create_table_sql, propose_schema
from sheets_supabase_sync.orchestration import synchronize_due_sources, synchronize_one_source
from sheets_supabase_sync.snapshot import build_snapshot
from sheets_supabase_sync.sources import DataSource, InstitutionConfig
from sheets_supabase_sync.scheduling import due_sources
from sheets_supabase_sync.synchronizer import synchronize
from sheets_supabase_sync.sql_generator import generate_schema_request_sql


class IsolatedInstitutionTests(unittest.TestCase):
    def source(self, name: str, table: str, **kwargs: object) -> DataSource:
        return DataSource(name, "sheet", "tab", table, ("id",), 180, **kwargs)

    def test_config_has_no_organization_or_tenant(self) -> None:
        config = load_institution_config(Path("configs/examples/institution.example.json"))
        serialized = json.dumps(config, default=str)
        self.assertNotIn("organization_id", serialized)
        self.assertNotIn("tenant_id", serialized)
        self.assertEqual("isolated", config.project_mode)

    def test_two_sources_have_independent_mirrors(self) -> None:
        config = InstitutionConfig("Instituicao", "isolated", (self.source("a", "pesquisa_satisfacao"), self.source("b", "avaliacao_trilhas")))
        self.assertEqual(["pesquisa_satisfacao", "avaliacao_trilhas"], [source.target_table for source in config.sources])

    def test_same_target_table_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "target_table"):
            InstitutionConfig("Instituicao", "isolated", (self.source("a", "espelho"), self.source("b", "espelho")))

    def test_due_sources_respects_three_hour_interval(self) -> None:
        now = datetime(2026, 8, 3, 12, tzinfo=UTC)
        due = self.source("due", "tabela_due", last_sync_at=now - timedelta(minutes=180))
        recent = self.source("recent", "tabela_recent", last_sync_at=now - timedelta(minutes=179))
        self.assertEqual([due], due_sources([due, recent], now))

    def test_disabled_source_is_not_due(self) -> None:
        now = datetime(2026, 8, 3, 12, tzinfo=UTC)
        source = self.source("disabled", "tabela_disabled", enabled=False)
        self.assertEqual([], due_sources([source], now))

    def test_one_source_failure_does_not_stop_another(self) -> None:
        sources = [self.source("ok", "tabela_ok"), self.source("bad", "tabela_bad")]
        outcomes = synchronize_independently(sources, lambda source: {"done": source.name} if source.name == "ok" else (_ for _ in ()).throw(ValueError("fixture invalida")))
        self.assertEqual([True, False], [outcome.succeeded for outcome in outcomes])

    def test_orchestration_runs_only_due_sources(self) -> None:
        now = datetime(2026, 8, 3, 12, tzinfo=UTC)
        due = self.source("due", "tabela_due", last_sync_at=now - timedelta(hours=3))
        future = self.source("future", "tabela_future", last_sync_at=now)
        outcomes = synchronize_due_sources([due, future], now, lambda source: {"source": source.name})
        self.assertEqual(["due"], [outcome.source_name for outcome in outcomes])
        self.assertTrue(synchronize_one_source(due, lambda source: {"source": source.name}).succeeded)

    def test_invalid_target_table_and_injection_are_refused(self) -> None:
        for value in ("Tabela", "select", "valid; drop table data_sources", "1_tabela"):
            with self.assertRaises(ValueError):
                validate_identifier(value)

    def test_normalized_header_collision_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "Colisao"):
            normalize_headers(["E-mail", "E mail"])

    def test_reserved_header_is_refused(self) -> None:
        for identifier in ("current_schema", "current_user", "session_user", "user", "table", "select", "from", "where"):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                normalize_headers([identifier])

    def test_schema_sql_has_no_cross_mirror_foreign_key(self) -> None:
        schema_a = propose_schema("pesquisa_satisfacao", [{"id": 1, "nota": 5}])
        schema_b = propose_schema("avaliacao_trilhas", [{"id": 1, "trilha": "A"}])
        sql_a, sql_b = create_table_sql(schema_a), create_table_sql(schema_b)
        self.assertIn("public.pesquisa_satisfacao", sql_a)
        self.assertIn("public.avaliacao_trilhas", sql_b)
        self.assertNotIn("FOREIGN KEY", sql_a + sql_b)

    def test_new_column_is_safe_but_destructive_change_is_blocked(self) -> None:
        old = build_snapshot("source", [{"id": "1", "score": 1}], "id")
        new_column = build_snapshot("source", [{"id": "1", "score": 1, "city": "Sapucaia"}], "id")
        destructive = build_snapshot("source", [{"id": "1", "score": "um"}], "id")
        self.assertFalse(has_blocking_schema_change(compare(new_column, old)))
        self.assertTrue(has_blocking_schema_change(compare(destructive, old)))

    def test_blocked_schema_preserves_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = root / "snapshot.json"
            config = self.source("source", "espelho")
            synchronize([{"id": "1", "score": 1}], _legacy_config(config), snapshot, root / "first")
            before = snapshot.read_text(encoding="utf-8")
            with patch("sheets_supabase_sync.synchronizer.apply_sql_locally"), self.assertRaisesRegex(ValueError, "bloqueante"):
                synchronize([{"id": "1", "score": "um"}], _legacy_config(config), snapshot, root / "blocked", mode="apply-local", database_url="postgresql://localhost:5432/postgres")
            self.assertEqual(before, snapshot.read_text(encoding="utf-8"))

    def test_blocked_change_generates_operational_schema_request(self) -> None:
        old = build_snapshot("source", [{"id": "1", "score": 1}], "id")
        changed = build_snapshot("source", [{"id": "1", "score": "um"}], "id")
        sql = generate_schema_request_sql(compare(changed, old), "pesquisa-satisfacao")
        self.assertIn("schema_change_requests", sql)
        self.assertIn("blocked_schema_change", sql)
        self.assertIn("previous_schema", sql)
        self.assertIn("proposed_schema", sql)
        self.assertNotIn("current_schema", sql)

    def test_raw_payload_is_preserved_in_schema_sql(self) -> None:
        sql = create_table_sql(propose_schema("cadastro_participantes", [{"id": 1, "nome": "Ana"}]))
        self.assertIn("raw_data jsonb not null", sql)


def _legacy_config(source: DataSource):
    from sheets_supabase_sync.config import SyncConfig
    return SyncConfig(source.name, source.business_key[0], source.target_table)
