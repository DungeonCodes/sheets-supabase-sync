from __future__ import annotations

import unittest

from sheets_supabase_sync.contracts import ContractStatus, SourceContract, validate_contract


class SourceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = SourceContract("Respostas", 1, ("id", "name"), ("id",), {"id": "text"}, min_rows=1)

    def test_contract_states(self) -> None:
        self.assertEqual(ContractStatus.PASSED, validate_contract(self.contract, "Respostas", [{"id": "1", "name": "Ana"}]).status)
        self.assertEqual(ContractStatus.FAILED, validate_contract(self.contract, "Outra", [{"id": "1", "name": "Ana"}]).status)
        self.assertEqual(ContractStatus.BLOCKED, validate_contract(self.contract, "Respostas", [{"name": "Ana"}]).status)
        self.assertEqual(ContractStatus.FAILED, validate_contract(self.contract, "Respostas", []).status)

    def test_contract_schema_and_volume_warnings(self) -> None:
        blocked = validate_contract(self.contract, "Respostas", [{"id": "1", "name": "Ana"}], previous_headers=("id", "name", "old"))
        self.assertEqual(ContractStatus.BLOCKED, blocked.status)
        warning_contract = SourceContract("Respostas", 1, ("id",), ("id",), {}, min_rows=2)
        self.assertEqual(ContractStatus.WARNING, validate_contract(warning_contract, "Respostas", [{"id": "1"}]).status)
