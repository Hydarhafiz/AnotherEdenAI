"""Prompt-context compaction helpers for workflow LLM calls."""

from __future__ import annotations

from typing import Any


def compact_records(
    records: list[Any],
    *,
    max_records: int = 20,
    max_list_items: int = 6,
    max_string_chars: int = 240,
    max_dict_keys: int = 12,
) -> list[dict[str, Any]]:
    """Return a bounded, JSON-safe summary of Neo4j records for prompt context."""
    return [
        _compact_value(
            dict(record),
            max_list_items=max_list_items,
            max_string_chars=max_string_chars,
            max_dict_keys=max_dict_keys,
        )
        for record in records[:max_records]
    ]


def _compact_value(
    value: Any,
    *,
    max_list_items: int,
    max_string_chars: int,
    max_dict_keys: int,
) -> Any:
    if isinstance(value, str):
        return _truncate(value, max_string_chars)
    if isinstance(value, list):
        compacted = [
            _compact_value(
                item,
                max_list_items=max_list_items,
                max_string_chars=max_string_chars,
                max_dict_keys=max_dict_keys,
            )
            for item in value[:max_list_items]
        ]
        omitted = len(value) - max_list_items
        if omitted > 0:
            compacted.append(f"... {omitted} more items omitted")
        return compacted
    if isinstance(value, dict):
        items = list(value.items())[:max_dict_keys]
        compacted = {
            key: _compact_value(
                item_value,
                max_list_items=max_list_items,
                max_string_chars=max_string_chars,
                max_dict_keys=max_dict_keys,
            )
            for key, item_value in items
        }
        omitted = len(value) - max_dict_keys
        if omitted > 0:
            compacted["_omitted_keys"] = omitted
        return compacted
    return value


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}... [truncated {len(text) - limit} chars]"
