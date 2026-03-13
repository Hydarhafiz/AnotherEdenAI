# Architecture

**Analysis Date:** 2026-03-14

## Pattern Overview

**Overall:** Layered Data Pipeline Architecture with ETL → Knowledge Graph Traversal → Optimization

**Key Characteristics:**
- Sequential data processing pipeline (scrape → normalize → analyze → output)
- Knowledge Graph model of RPG entities and relationships
- Deterministic optimization logic based on character traits and equipment compatibility
- Separation of concerns: data collection, trait management, and optimization strategy

## Layers

**Data Collection Layer (ETL):**
- Purpose: Fetch and parse raw data from external wiki sources
- Location: `master_scraper.py`
- Contains: Web scraper functions, HTML parsing logic, data transformation to DataFrames
- Depends on: requests, BeautifulSoup libraries
- Used by: Subsequent processing layers that consume CSV outputs

**Data Normalization Layer:**
- Purpose: Unify scraped data into consistent formats and handle trait extraction
- Location: `separate_trait_grasta.py`
- Contains: Trait deduplication logic, merging character traits with grasta requirements
- Depends on: Pandas, AST parsing for list deserialization
- Used by: Optimization layer that queries processed data

**Optimization & Analysis Layer:**
- Purpose: Apply constraint satisfaction logic to recommend character builds
- Location: `optimize_character.py`
- Contains: Character lookup, personality-based grasta filtering, self-buff selection, ore pairing
- Depends on: Normalized CSV files, pandas DataFrames
- Used by: Final report generation and strategic recommendations

**Output Layer:**
- Purpose: Generate human-readable build recommendations and CSV artifacts
- Location: All three modules (print statements, CSV exports)
- Contains: Mermaid.js schema visualization, formatted console output, structured data exports
- Depends on: Upstream data processing
- Used by: End users, game strategists

## Data Flow

**Scraping Pipeline:**

1. `get_soup()` fetches HTML from wiki URLs with proper User-Agent headers
2. Category-specific scrapers (`scrape_characters()`, `scrape_grasta_general()`, `scrape_vc_grasta()`, `scrape_ores()`) extract rows from HTML tables
3. DataFrames are concatenated (`pd.concat()`) for multi-category grasta data
4. CSV files are persisted: `ae_characters.csv`, `ae_grasta_master.csv`, `ae_ores.csv`
5. `generate_updated_schema()` produces Mermaid.js visualization of Knowledge Graph structure

**Trait Management Flow:**

1. `load_data()` reads the three CSV files and parses list-formatted personality strings
2. `separate_trait_grasta.py` extracts unique traits from both character personalities and grasta requirements
3. Union operation combines trait sets to handle traits present in grastas but not yet assigned to characters
4. `ae_traits.csv` serves as master reference for all valid traits in the system

**Optimization & Reporting Flow:**

1. Target character is specified via `TARGET_CHAR` configuration
2. `get_meta_build()` searches for matching character record by name
3. Two-tier grasta strategy is applied:
   - **"Mule" Grastas** (shareable): Filter for `is_shareable==True` AND personality matches character traits
   - **"Self" Grastas** (self-buffs): Filter for tiers 2-3, non-shareable, weapon/element matches (heuristic)
4. Ore pairing is assigned via rotation through meta ores list
5. Formatted report is printed to console with strategic commentary

**State Management:**

- **No persistent state machine** - all processing is stateless and deterministic
- **Configuration via constants** at module top level (URLS dict, TARGET_CHAR, FILES dict, meta_ores list)
- **Data state** is managed entirely through DataFrames (in-memory during execution, on-disk as CSVs between runs)
- **No transactions or rollback** - idempotent operations suitable for batch processing

## Key Abstractions

**Knowledge Graph Representation:**
- Purpose: Model relationships between Characters, Traits, Grastas, and Ores
- Examples: `Character` (name, element, weapon, light_shadow), `Trait` (personality requirement), `Grasta` (name, category, tier, stats, personality_req, is_shareable), `Ore` (name, stats, source)
- Pattern: Entity-relationship model with four primary node types and three relationship types (HAS_TRAIT, REQUIRES_TRAIT, ENHANCES)
- Implemented as: Relational DataFrames with foreign key-like columns (personality_req, is_shareable flags)

**Scraper Functions:**
- Purpose: Encapsulate HTML parsing logic for different data sources
- Examples: `scrape_characters()`, `scrape_grasta_general()`, `scrape_vc_grasta()`, `scrape_ores()`
- Pattern: Each returns a Pandas DataFrame; internal try-except catches malformed rows
- Implementation: BeautifulSoup CSS selectors on hardcoded class names (character-row-entry, grasta-row-entry, equip-row-entry)

**Optimization Strategy:**
- Purpose: Convert character metadata to actionable build recommendations
- Examples: Shareable grasta matching, weapon-based self-buff selection, meta ore assignment
- Pattern: Filter-and-pair logic operating on DataFrame boolean masks
- Implementation: `get_meta_build()` chains `df[condition1 & condition2]` operations

## Entry Points

**master_scraper.py (Main):**
- Location: `master_scraper.py` (lines 180-206)
- Triggers: Manual execution `python master_scraper.py` or scheduled batch job
- Responsibilities: Orchestrate all scraper functions, concatenate results, save three CSV files, generate and print schema diagram

**optimize_character.py (Main):**
- Location: `optimize_character.py` (lines 86-88)
- Triggers: Manual execution `python optimize_character.py` or post-scrape analysis workflow
- Responsibilities: Load normalized CSV data, run optimization for TARGET_CHAR, print formatted build recommendations

**separate_trait_grasta.py (Main):**
- Location: `separate_trait_grasta.py` (lines 38-41)
- Triggers: Runs after `master_scraper.py` to deduplicate and enrich trait data
- Responsibilities: Extract trait union from characters and grastas, save `ae_traits.csv`, print confirmation

## Error Handling

**Strategy:** Graceful degradation with try-except blocks; continue processing on individual row failures

**Patterns:**

- **Web scraping errors** (`get_soup()`, lines 22-29): requests exceptions caught, None returned, calling scraper checks for None and returns empty DataFrame
- **HTML parsing errors** (lines 52, 75, 95, 127 in scrapers): Individual row try-except blocks with bare `continue` statement; malformed rows are silently skipped
- **CSV parsing errors** (`separate_trait_grasta.py`, lines 19-20): ast.literal_eval failures caught and ignored, trait not added to set
- **Character lookup failure** (`optimize_character.py`, lines 29-30): Returns error message string instead of raising exception
- **Missing columns** (grasta tier parsing, line 52): String conversion of potentially None/NaN values followed by membership check

## Cross-Cutting Concerns

**Logging:** Print-based approach only (no logging framework)
- Informational: `print(f"Fetching {url}...")` in get_soup, `print(f"Parsing {len(rows)} characters...")` in scrapers
- Results: Print final CSV counts and sample data to console
- No error logging beyond function-level exceptions

**Validation:** Minimal validation; relies on wiki structure stability
- HTML structure validation: Hardcoded CSS class names assumed correct (character-row-entry, grasta-row-entry)
- Data type validation: String containment checks for weapon/element matching (case-insensitive)
- Personality parsing: ast.literal_eval verifies list format; non-list strings rejected
- Completeness: Empty DataFrame checks before processing (e.g., line 205)

**Authentication:** User-Agent spoofing via HEADERS dict
- Browser User-Agent string to avoid bot detection
- No API keys, tokens, or credentials in code (wiki is public)
- Headers hard-coded at module level for web requests

---

*Architecture analysis: 2026-03-14*
