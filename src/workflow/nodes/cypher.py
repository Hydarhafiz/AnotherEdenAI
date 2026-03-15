"""GENERATE_CYPHER node — translates plan strategy into a Neo4j Cypher query.

Calls get_llm(role='cypher') from src.workflow.llm.
Injects full SCHEMA.md content and few-shot Cypher examples into the system prompt.
Strips markdown code fences from LLM output.
Returns only: {"cypher_query": str}
"""
import re

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import get_llm
from ..state import WorkflowState

# ---------------------------------------------------------------------------
# Schema context — hardcoded from SCHEMA.md (stable Phase 1 contract)
# ---------------------------------------------------------------------------

SCHEMA_CONTEXT = """
## Graph Schema

### Node Labels and Properties

**Character**
- name (STRING, unique) — canonical wiki name
- element (STRING) — Fire, Water, Wind, Earth, Thunder, Light, Dark, Null
- weapon (STRING) — Sword, Blade, Bow, Spear, Hammer, Staff, Mace, Tome, Fist, Katana
- light_shadow (STRING) — "Light" or "Shadow"

**Trait**
- name (STRING, unique) — personality trait name shared by Characters and Grastas

**Grasta**
- name (STRING, unique) — display name
- category (STRING) — Attack | Life | Support | Special | VC
- tier (INTEGER) — grasta tier level (read from data-tier attribute)
- stats (STRING) — stat bonuses (e.g., "INT +10 SPD +10")
- is_shareable (BOOLEAN) — true if data-share="1"
- personality_req (STRING, nullable) — trait name required; null for VC and weapon-based grastas

**Ore**
- name (STRING, unique) — ore display name
- stats (STRING) — stats/effect description
- source (STRING) — drop location

NOTE: Ore nodes are standalone entities. There is NO ENHANCES relationship in the graph.
Ore application is a dynamic player/AI decision at query time — do NOT use ENHANCES edges.

### Relationship Types

**(:Character)-[:HAS_TRAIT]->(:Trait)**
Character equipped with a personality trait. No relationship properties.

**(:Grasta)-[:REQUIRES_TRAIT]->(:Trait)**
Grasta requires a personality trait to equip. No relationship properties.
IMPORTANT: Only non-VC grastas with a personality_req have this relationship.
VC Grastas have NO REQUIRES_TRAIT edges.
""".strip()

# ---------------------------------------------------------------------------
# Few-shot Cypher examples
# ---------------------------------------------------------------------------

FEW_SHOT_EXAMPLES = """
## Cypher Query Examples

### Example 1: Find fire characters from a roster
```
MATCH (c:Character)
WHERE c.element = 'Fire' AND c.name IN $roster
RETURN c.name, c.element, c.weapon
```

### Example 2: Find traits for specific characters
```
MATCH (c:Character)-[:HAS_TRAIT]->(t:Trait)
WHERE c.name IN $roster
RETURN c.name, collect(t.name) AS traits
```

### Example 3: Find shareable attack grastas by trait
```
MATCH (c:Character)-[:HAS_TRAIT]->(t:Trait)<-[:REQUIRES_TRAIT]-(g:Grasta)
WHERE c.name IN $roster AND g.category = 'Attack' AND g.is_shareable = true
RETURN c.name, t.name, g.name, g.stats
```

### Example 4: Find attack grastas available to a roster
```
MATCH (c:Character)-[:HAS_TRAIT]->(t:Trait)<-[:REQUIRES_TRAIT]-(g:Grasta)
WHERE c.name IN $roster AND g.category = 'Attack'
RETURN c.name, collect(DISTINCT g.name) AS attack_grastas
ORDER BY c.name
```

## Constraints
- NEVER use an ENHANCES relationship — it does not exist in the graph
- Ore nodes are standalone — do not attempt to traverse relationships from Ore
- VC Grastas have NO REQUIRES_TRAIT edges — do not include them in trait-based lookups
- Always use $roster as the parameter for the user's character list
- Return raw Cypher only — no markdown formatting, no code fences
""".strip()

# ---------------------------------------------------------------------------
# Combined system prompt
# ---------------------------------------------------------------------------

CYPHER_SYSTEM_PROMPT = f"""{SCHEMA_CONTEXT}

{FEW_SHOT_EXAMPLES}

## Instructions
Generate a single Cypher query that answers the user's question.
Use $roster as the parameter for the user's character list.
Return raw Cypher only — no markdown formatting, no code fences, no explanation."""


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from a Cypher query string.

    Handles:
        ```cypher\\nQUERY\\n```
        ```\\nQUERY\\n```
        Any trailing/leading whitespace

    Args:
        text: Raw LLM response content.

    Returns:
        Cleaned Cypher string.
    """
    text = text.strip()
    # Remove opening fence with optional language tag
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    # Remove closing fence
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def generate_cypher_node(state: WorkflowState) -> dict:
    """Generate a Cypher query based on the plan strategy.

    Injects full schema context and few-shot examples into the system prompt.
    Includes validation_errors on retry so the LLM can self-correct.
    Strips markdown code fences from the response.

    Owned keys: cypher_query

    Args:
        state: Current WorkflowState containing plan_strategy, user_query,
               roster, and optionally validation_errors.

    Returns:
        Dict containing only {"cypher_query": str}.
    """
    llm = get_llm(role="cypher")

    roster_str = ", ".join(state["roster"]) if state["roster"] else "no characters specified"
    human_parts = [
        f"Strategy: {state['plan_strategy']}",
        f"Query: {state['user_query']}",
        f"Roster: {roster_str}",
    ]

    # Include validation error history on retry so the LLM can self-correct
    validation_errors = state.get("validation_errors", [])
    if validation_errors:
        errors_str = "\n".join(f"- {e}" for e in validation_errors)
        human_parts.append(
            f"\nPrevious errors (please correct these in your new query):\n{errors_str}"
        )

    human_content = "\n".join(human_parts)

    messages = [
        SystemMessage(content=CYPHER_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]

    response = llm.invoke(messages)
    cleaned_cypher = _strip_markdown_fences(response.content)
    return {"cypher_query": cleaned_cypher}
