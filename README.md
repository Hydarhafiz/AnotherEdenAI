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

## How to Run (Data Pipeline)
1. `python master_scraper.py` - Fetches live data from Wiki.
2. `python optimize_character.py` - Runs the deterministic optimization logic.