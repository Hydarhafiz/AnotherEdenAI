#!/usr/bin/env python3
"""Run the explicitly opt-in Feature H1 real-data comparison.

This command is intentionally separate from the normal recommender entry
point. It requires an OpenRouter key and a live Neo4j database at invocation
time; importing the module or running offline tests performs no network I/O.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

import httpx
from neo4j import AsyncGraphDatabase

from src.workflow.h1_evaluation import load_h1_scenarios, run_h1_evaluation
from src.workflow.production import ProductionRetrievalService


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _openrouter_transport():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY must be set for the paid H1 command")

    def send(request):
        response = httpx.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=request.payload,
            timeout=90.0,
        )
        if response.status_code >= 400:
            return {"error": {"code": f"provider.http_{response.status_code}", "message": "OpenRouter returned an HTTP error"}}
        try:
            body = response.json()
        except ValueError:
            return {"error": {"code": "provider.invalid_json", "message": "OpenRouter returned invalid JSON"}}
        return body if isinstance(body, dict) else {"error": {"code": "provider.invalid_envelope", "message": "OpenRouter returned a non-object response"}}

    return send


def _neo4j_settings() -> tuple[str, tuple[str, str]]:
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    auth_text = os.environ.get("NEO4J_AUTH", "neo4j/anothereden")
    username, separator, password = auth_text.partition("/")
    if not separator or not username or not password:
        raise RuntimeError("NEO4J_AUTH must use the username/password form")
    return uri, (username, password)


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    scenarios = load_h1_scenarios(args.request_fixture, scenario_ids=args.case_id)
    uri, auth = _neo4j_settings()
    driver = AsyncGraphDatabase.driver(uri, auth=auth)
    try:
        return await run_h1_evaluation(scenarios, ProductionRetrievalService(driver), _openrouter_transport())
    finally:
        await driver.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the paid, opt-in Feature H1 A/B evaluation")
    parser.add_argument("--request-fixture", type=Path, required=True, help="JSON scenario or Feature H request fixture")
    parser.add_argument("--case-id", action="append", required=True, help="Selected case ID; repeat five to eight times")
    parser.add_argument("--output", type=Path, help="Optional sanitized report path; stdout by default")
    args = parser.parse_args()
    if not 5 <= len(args.case_id) <= 8:
        parser.error("select five to eight --case-id values for the initial H1 evaluation")
    report = asyncio.run(_run(args))
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
