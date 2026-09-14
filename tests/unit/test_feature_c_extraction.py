"""Milestone 6 Feature C full-catalog extraction and authority regressions."""

import json
from pathlib import Path

import pytest

from src.etl.capability_taxonomy import propose
from src.etl.feature_c_extraction import (
    build_feature_c_extraction_report,
    load_canonical_catalog,
    validate_rule_fixtures,
)


CATALOG = Path("src/etl/kit_catalog.json")
FIXTURES = Path("src/etl/capability_feature_c_fixtures.json")
NEW_RULES = {
    "cap-burst-window",
    "cap-enemy-attack-type-resistance-down",
    "cap-enemy-buff-dispel",
    "cap-enemy-intelligence-down",
    "cap-enemy-magic-resistance-down",
    "cap-enemy-physical-resistance-down",
    "cap-enemy-power-down",
    "cap-enemy-speed-down",
    "cap-enemy-type-resistance-down",
    "cap-fixed-damage-response",
    "cap-multi-entity-damage",
    "cap-multi-hit-action",
    "cap-party-speed-up",
    "cap-remove-active-zone",
    "cap-repeatable-setup",
    "cap-restore-statuses",
    "cap-typed-damage",
}


@pytest.fixture(scope="module")
def report():
    return build_feature_c_extraction_report()


def _facts_by_id():
    payload, _, facts = load_canonical_catalog(CATALOG)
    assert payload["canonical_count"] == 367
    return {str(fact.get("skill_id") or fact.get("passive_skill_id")): fact for fact in facts}


def test_full_catalog_attempt_and_receipts_are_exact(report):
    scope = report["scope"]

    assert scope["canonical_identity_count"] == 367
    assert scope["extraction_attempt_count"] == 367
    assert scope["extraction_attempted_for_all_identities"] is True
    assert scope["legal_kit_receipts"]["receipt_count"] == 367
    assert scope["legal_kit_receipts"]["complete_receipt_count"] == 367
    assert scope["legal_kit_receipts"]["ready"] is True
    assert scope["new_rule_count"] == len(NEW_RULES)
    assert set(scope["new_rule_ids"]) == NEW_RULES


def test_each_new_rule_has_source_backed_positive_negative_and_regression_fixtures():
    facts = list(_facts_by_id().values())
    validation = validate_rule_fixtures(facts, FIXTURES)

    assert validation["rule_count"] == len(NEW_RULES)
    assert validation["case_count"] == len(NEW_RULES) * 3
    assert {row["case"] for row in validation["checks"]} == {"positive", "misleading_negative", "regression"}
    assert all(row["source_fact_id"].startswith(("skill:", "passive:")) for row in validation["checks"])


def test_target_scope_and_qualifiers_remain_source_specific():
    facts = _facts_by_id()
    single = {row["rule_id"]: row for row in propose(facts["skill:3bf0d55a753ab920d4c4"])}
    group = {row["rule_id"]: row for row in propose(facts["skill:41458f213cdeb36f7939"])}

    assert single["cap-typed-damage"]["proposed_target"] == "single_enemy"
    assert json.loads(single["cap-typed-damage"]["proposed_qualifiers_json"])["attack_type"] == ["Slash"]
    assert json.loads(single["cap-typed-damage"]["proposed_qualifiers_json"])["element"] == ["Fire"]
    assert group["cap-typed-damage"]["proposed_target"] == "all_enemies"
    assert group["cap-multi-entity-damage"]["proposed_target"] == "all_enemies"
    assert group["cap-multi-hit-action"]["proposed_target"] == "single_enemy"


def test_fixed_response_target_and_negative_direction_are_distinct():
    facts = _facts_by_id()
    party = next(row for row in propose(facts["skill:4fcc820d45f08d355f6f"]) if row["rule_id"] == "cap-fixed-damage-response")
    self_only = next(row for row in propose(facts["passive:2a5e2976457ee8534503"]) if row["rule_id"] == "cap-fixed-damage-response")
    offense = [row for row in propose(facts["skill:3c19a3d18c01e81bd6e9"]) if row["rule_id"] == "cap-fixed-damage-response"]

    assert party["proposed_target"] == "party"
    assert self_only["proposed_target"] == "self"
    assert offense == []


def test_unreviewed_proposals_are_separate_from_authority_and_queues_are_bounded(report):
    states = report["proposal_state_distribution"]
    assert set(states) == {"proven_present", "proven_absent", "unknown", "ambiguous", "rejected", "untagged"}
    assert states["proven_absent"] == 0
    assert report["newly_covered_families"]["reviewed_new_rule_families"] == []
    assert report["semantic_policy"]["unreviewed_generated_authority"] is False
    assert report["semantic_policy"]["runtime_scoring_or_retrieval_changed"] is False
    assert report["proposal_authority"]["unreviewed_authoritative_proposal_count"] == 0
    assert report["proposal_authority"]["generated_proposals_authoritative"] is False
    for queue in report["bounded_review_queues"].values():
        assert len(queue) <= 45
        assert all(item["semantic_state"] in {"unknown", "ambiguous"} for item in queue)
        assert all(item["authoritative"] is False for item in queue)


def test_replay_and_prior_artifacts_are_preserved(report):
    preservation = report["preservation"]

    assert preservation["replay_deterministic"] is True
    assert preservation["proposal_digest"] == preservation["replay_digest"]
    assert preservation["review_decision_count"] == 323
    assert preservation["gold_fixture_count"] == 12
    assert preservation["taxonomy_override_count"] == 9
    assert preservation["negative_fixtures_preserved"] is True
    assert preservation["feature_a_baseline_metrics"]["high_value_capability_attempted"] == 329
    assert preservation["feature_a_baseline_metrics"]["facts_unknown"] == 5103
