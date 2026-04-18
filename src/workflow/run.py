"""CLI entry point for AnotherEdenAI team recommendation pipeline.

Usage:
    python -m src.workflow.run --roster "Aldo,Ciel,Shion" --query "best blunt zone team"
"""
import argparse
import asyncio
import json
import os

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

from .graph import build_graph

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_AUTH = tuple(os.getenv("NEO4J_AUTH", "neo4j/anothereden").split("/", 1))


async def main(roster: list[str], query: str) -> dict:
    """Run the AnotherEden AI team recommendation pipeline.

    Args:
        roster: List of player-owned character names (may be un-normalized).
        query: Natural language team-building query from the player.

    Returns:
        final_output dict from the workflow graph, or empty dict on failure.
    """
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    try:
        graph = build_graph(driver=driver)
        initial_state = {
            "user_query": query,
            "roster": roster,
            "plan_strategy": "",
            "cypher_query": "",
            "db_results": [],
            "validation_errors": [],
            "retry_count": 0,
            "analysis_result": "",
            "final_output": {},
        }
        result = await graph.ainvoke(initial_state)
        return result.get("final_output", {})
    except Exception as exc:  # noqa: BLE001
        # Graceful degradation: return error dict instead of raising.
        # Covers LLM credential errors, Neo4j connection failures, etc.
        return {"error": str(exc), "error_type": type(exc).__name__}
    finally:
        await driver.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AnotherEden AI team recommender")
    parser.add_argument("--roster", required=True, help="Comma-separated character names")
    parser.add_argument("--query", required=True, help="Natural language team query")
    args = parser.parse_args()

    roster_list = [name.strip() for name in args.roster.split(",") if name.strip()]
    result = asyncio.run(main(roster_list, args.query))
    print(json.dumps(result, indent=2))
