# Another Eden Agentic AI (Constraint Optimization System)

## Project Overview
An Agentic AI system that optimizes RPG character builds using a Knowledge Graph. 
It solves the "Mule Problem" (allocating limited shared resources to maximize party efficiency).

## Architecture
- **Data Engineering:** Python Scrapers (BeautifulSoup) -> Normalized CSVs.
- **Knowledge Graph:** Nodes (Character, Trait, Grasta) linked by interactions.
- **Agent Logic:** 1. Identifies user intent ("Build Cerius").
  2. Traverses the graph to find compatible 'Shareable' buffs.
  3. Filters for specific 'Self' buffs based on Weapon/Element.

## Technology Stack
- **ETL:** Python, Pandas, BeautifulSoup
- **Database:** (To be added: Neo4j / ChromaDB)
- **LLM:** (To be added: Local Llama 3 / DeepSeek)

## Environment Variables

Copy `.env.example` to `.env` and fill in the required values.

| Variable | Required | Purpose |
|----------|----------|---------|
| `NEO4J_URI` | yes | Neo4j bolt URI (e.g. `bolt://localhost:7687`) |
| `NEO4J_AUTH` | yes | Neo4j credentials in `user/pass` format |
| `LLM_PROVIDER` | yes | One of `anthropic`, `openrouter`, `bedrock`, `ollama` |
| `ANTHROPIC_API_KEY` | conditional | Required when `LLM_PROVIDER=anthropic` |
| `OPENROUTER_API_KEY` | conditional | Required when `LLM_PROVIDER=openrouter` |
| `OLLAMA_MODEL` | no | Model name for `LLM_PROVIDER=ollama` (default: `llama3.2`) |
| `ETL_MODE` | no | `strict` (default) or `lenient` |
| `ADMIN_KEY` | yes | Secret for admin-only web routes; sent as `X-Admin-Key` header |

## How to Run (Data Pipeline)
1. `python master_scraper.py` - Fetches live data from Wiki.
2. `python optimize_character.py` - Runs the deterministic optimization logic.