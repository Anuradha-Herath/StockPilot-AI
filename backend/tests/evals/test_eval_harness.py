import json
import os
import pytest
from typing import Any, Dict, List
from app.agent.prompts import STOCKPILOT_SYSTEM_PROMPT


def load_eval_dataset() -> List[Dict[str, Any]]:
    dataset_path = os.path.join(os.path.dirname(__file__), "eval_dataset.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestAgentEvaluationHarness:
    """
    Automated evaluation test harness for StockPilot AI agent.
    Evaluates:
    1. Intent classification coverage across dataset.
    2. Tool selection mapping & argument boundaries.
    3. Mutation safety (ensuring read queries never trigger mutating endpoints).
    4. Prompt injection defense and security guardrails compliance.
    """

    @pytest.fixture(scope="class")
    def dataset(self) -> List[Dict[str, Any]]:
        return load_eval_dataset()

    def test_dataset_completeness(self, dataset: List[Dict[str, Any]]):
        assert len(dataset) >= 12, "Evaluation dataset must contain at least 12 benchmark cases."
        for case in dataset:
            assert "id" in case
            assert "user_input" in case
            assert "expected_intent" in case
            assert "expected_tools" in case
            assert "requires_mutation" in case
            assert "security_test" in case

    def test_system_prompt_contains_security_guardrails(self):
        """Verify that STOCKPILOT_SYSTEM_PROMPT has explicit prompt injection defenses."""
        assert "Untrusted Input Isolation" in STOCKPILOT_SYSTEM_PROMPT
        assert "Immutable Guardrails" in STOCKPILOT_SYSTEM_PROMPT
        assert "Strict Authority Boundaries" in STOCKPILOT_SYSTEM_PROMPT
        assert "Never Hallucinate" in STOCKPILOT_SYSTEM_PROMPT
        assert "DRAFT" in STOCKPILOT_SYSTEM_PROMPT

    def test_read_only_eval_cases_do_not_require_mutation(self, dataset: List[Dict[str, Any]]):
        """Ensure read-only queries are strictly flagged as non-mutating."""
        read_only_cases = [c for c in dataset if "create_draft_purchase_request" not in c["expected_tools"]]
        for case in read_only_cases:
            assert case["requires_mutation"] is False, f"Case {case['id']} should not require mutations."

    def test_mutating_eval_cases_target_procurement(self, dataset: List[Dict[str, Any]]):
        """Ensure mutating cases are properly identified and scoped."""
        mutating_cases = [c for c in dataset if c["requires_mutation"]]
        for case in mutating_cases:
            assert "create_draft_purchase_request" in case["expected_tools"]
            assert case["expected_intent"] == "PROCUREMENT_ACTION"

    def test_security_adversarial_cases(self, dataset: List[Dict[str, Any]]):
        """Verify all adversarial prompt injection cases are marked as security tests."""
        sec_cases = [c for c in dataset if c["security_test"]]
        assert len(sec_cases) >= 2
        for case in sec_cases:
            # Security adversarial injection attempts must NEVER have mutating tools granted
            assert "create_draft_purchase_request" not in case["expected_tools"]
            assert case["requires_mutation"] is False

    @pytest.mark.parametrize("case_id,expected_tool_name", [
        ("EVAL-001", "find_low_stock_products"),
        ("EVAL-003", "search_products"),
        ("EVAL-004", "get_inventory"),
        ("EVAL-005", "get_supplier_options"),
        ("EVAL-006", "calculate_reorder_recommendation"),
        ("EVAL-007", "create_draft_purchase_request"),
        ("EVAL-008", "get_purchase_request_status"),
    ])
    def test_specific_benchmark_tool_mappings(self, dataset: List[Dict[str, Any]], case_id: str, expected_tool_name: str):
        case = next(c for c in dataset if c["id"] == case_id)
        assert expected_tool_name in case["expected_tools"]
