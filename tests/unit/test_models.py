"""Unit tests for Pydantic ETL validation models.

Wave 0 stubs — these tests are skipped until src/etl/models.py is implemented in Plan 01-02.

Requirements covered:
- DATA-02: Pydantic strict vs lenient mode validation
"""
import pytest


@pytest.mark.skip(reason="TODO Plan 01-02: implement src/etl/models.py with CharacterRow")
def test_character_strict_mode():
    """Verify that an invalid CharacterRow raises ValidationError in strict mode.

    TODO: Set ETL_MODE=strict (or monkeypatch constants.STRICT=True).
    Pass a raw dict with an invalid/missing field to CharacterRow.model_validate().
    Expected: pydantic.ValidationError is raised.

    Reference: 01-RESEARCH.md Pattern 2 — Pydantic v2 ETL Models with ETL_MODE Toggle
    """
    pass


@pytest.mark.skip(reason="TODO Plan 01-02: implement src/etl/models.py with CharacterRow")
def test_character_lenient_mode():
    """Verify that an invalid CharacterRow is skipped (returns None) in lenient mode.

    TODO: Set ETL_MODE=lenient (or monkeypatch constants.STRICT=False).
    Pass a raw dict with an invalid/missing field to the parse_character() wrapper.
    Expected: None is returned (no exception raised), warning printed to stdout.

    Reference: 01-RESEARCH.md Pattern 2 — Pydantic v2 ETL Models with ETL_MODE Toggle
    """
    pass


@pytest.mark.skip(reason="TODO Plan 01-02: implement src/etl/models.py with GrastaRow")
def test_grasta_vc_no_personality_req():
    """Verify that a VC GrastaRow has personality_req=None.

    TODO: Create a raw dict representing a VC grasta row (category="VC", no data-personality).
    Pass to GrastaRow.model_validate().
    Expected: personality_req is None (not an empty string, not a "Character: ..." string).

    Reference: 01-RESEARCH.md Pitfall 3 — VC Grastas Creating Spurious REQUIRES_TRAIT Edges
    """
    pass
