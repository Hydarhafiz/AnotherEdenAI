# Codebase Structure

**Analysis Date:** 2026-03-14

## Directory Layout

```
AnotherEdenAI/
├── master_scraper.py           # Web scraper: fetches wiki data, generates CSVs + schema
├── optimize_character.py       # Build optimizer: analyzes character traits, recommends grastas
├── separate_trait_grasta.py    # Trait deduplicator: extracts unique traits from all sources
├── README.md                   # Project overview and documentation
├── LICENSE                     # MIT License
├── .gitignore                  # Git ignore rules
└── .planning/
    └── codebase/               # Architecture planning documents (this file lives here)
```

## Directory Purposes

**Project Root:**
- Purpose: Main source directory containing all executable Python modules
- Contains: ETL scripts, optimization logic, no subdirectories
- Key files: Three main executable modules and documentation

## Key File Locations

**Entry Points:**

- `master_scraper.py`: Execute to scrape wiki, generate CSVs (ae_characters.csv, ae_grasta_master.csv, ae_ores.csv), print schema
- `optimize_character.py`: Execute to generate build recommendations for a target character (modify TARGET_CHAR constant before running)
- `separate_trait_grasta.py`: Execute after master_scraper to extract and deduplicate traits into ae_traits.csv

**Configuration:**

- `master_scraper.py` (lines 7-19): URLS dict with wiki page targets, HEADERS dict with User-Agent
- `optimize_character.py` (lines 6-11): TARGET_CHAR (character name to optimize), FILES dict (CSV input paths)
- `separate_trait_grasta.py`: No configuration constants; operates on fixed CSV filenames

**Core Logic:**

- `master_scraper.py` (lines 31-128): Scraper functions for characters, grastas (4 categories), VC grastas, ores
- `master_scraper.py` (lines 131-177): Schema generator producing Mermaid.js visualization
- `optimize_character.py` (lines 26-83): Meta build strategy (character lookup, mule grasta filter, self buff selection)
- `separate_trait_grasta.py` (lines 8-34): Trait extraction and union logic

**Data Files (Generated at Runtime):**

- `ae_characters.csv`: Character metadata (name, element, weapon, light_shadow, personalities)
- `ae_grasta_master.csv`: Unified grasta database (name, category, tier, stats, personality_req, is_shareable)
- `ae_ores.csv`: Ore metadata (name, category, stats, source)
- `ae_traits.csv`: Master trait list (unique traits from characters and grastas)

## Naming Conventions

**Files:**

- Module files: lowercase with underscores (`master_scraper.py`, `optimize_character.py`, `separate_trait_grasta.py`)
- CSV outputs: `ae_` prefix (Another Eden abbreviation) with descriptive plural names (`ae_characters.csv`, `ae_grasta_master.csv`)
- Trait file: `ae_traits.csv` (singular, master reference)
- Documentation: uppercase with .md extension (`README.md`)

**Functions:**

- Scraper functions: verb prefix + noun (`scrape_characters()`, `scrape_grasta_general()`, `scrape_vc_grasta()`, `scrape_ores()`)
- Utility functions: descriptive verb phrases (`get_soup()`, `load_data()`, `get_meta_build()`, `generate_updated_schema()`)
- Private helpers: no explicit private convention used; all functions public

**Variables:**

- DataFrame objects: df_ prefix + entity name (`df_chars`, `df_c`, `df_g`, `df_o`, `df_grasta`, `df_chars`)
- Series/scalar: lowercase with underscores (`char_row`, `p_str`, `p_list`, `char_traits`, `grasta_traits`, `all_traits`, `meta_ores`)
- Configuration constants: UPPERCASE_WITH_UNDERSCORES (URLS, HEADERS, TARGET_CHAR, FILES)
- Loop indices: single letters or semantic names (`row`, `idx`, `col`, `p`)

**Types:**

- No explicit type hints in codebase
- Classes: Not used; functional/procedural style throughout
- DataFrames: typed implicitly by pandas operations

## Where to Add New Code

**New Feature (e.g., Additional Scraper):**

- Primary code: Add new `scrape_<entity>()` function in `master_scraper.py` following existing pattern (get_soup call, rows loop, try-except per row, return DataFrame)
- Integration: Concatenate result to `df_grasta_master` or create new standalone DataFrame, export to CSV in main block
- Tests: Write standalone script to verify output shape and sample rows (no automated test framework)

**New Optimization Strategy:**

- Implementation: Add new strategy function in `optimize_character.py` following `get_meta_build()` pattern
- Input: Character row, DataFrame references (df_c, df_g, df_o)
- Output: Print formatted recommendations or return structured dict
- Configuration: Add strategy selection logic to main block (if-elif based on strategy name)

**New Analysis Module:**

- Location: Create new file at project root (e.g., `analyze_matchups.py`)
- Dependencies: Import from existing CSV files using `pd.read_csv()`
- Data loading: Use `load_data()` pattern from `optimize_character.py`
- Execution: Add to README.md as additional run step

**Utilities:**

- Shared helpers: No utils module exists; keep helper functions in the module where they're used (e.g., `get_soup()` in master_scraper.py)
- If multiple modules need a function, duplicate it or add to new `utils.py` module with appropriate imports

## Special Directories

**`.planning/codebase/`:**
- Purpose: Architecture and structure documentation (ARCHITECTURE.md, STRUCTURE.md, future docs)
- Generated: No (manually authored)
- Committed: Yes (tracked in git)

**`.git/`:**
- Purpose: Version control metadata
- Generated: Yes (created by git init)
- Committed: No (never committed)

**No generated directories expected** - output CSVs, Mermaid diagrams go to project root only

## File Organization Patterns

**Module-level structure pattern (all three modules):**

```python
# 1. Imports
import [library]

# 2. Configuration
[CONSTANT_DICT or VARIABLE]

# 3. Helper functions
def helper_function():
    pass

# 4. Main function(s)
def main_processing():
    pass

# 5. Entry point
if __name__ == "__main__":
    # Orchestration logic
```

**Example from `master_scraper.py`:**
- Lines 1-4: Imports (requests, BeautifulSoup, pandas, ast)
- Lines 7-19: URLS and HEADERS configuration
- Lines 21-128: Helper and scraper functions
- Lines 131-177: Schema generation function
- Lines 180-206: Main execution block

## Suggested Directory Expansion (For Future Growth)

If project scales beyond current scope:

```
AnotherEdenAI/
├── src/                        # New: organize modules by function
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── character_scraper.py
│   │   ├── grasta_scraper.py
│   │   └── ore_scraper.py
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── trait_processor.py
│   │   └── data_normalizer.py
│   ├── optimizers/
│   │   ├── __init__.py
│   │   ├── build_optimizer.py
│   │   └── strategy_engine.py
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── data/                       # New: CSV storage directory
│   ├── raw/                    # Freshly scraped data
│   ├── processed/              # Normalized data
│   └── output/                 # Build recommendations
├── tests/                      # New: automated tests
│   ├── test_scrapers.py
│   ├── test_optimization.py
│   └── fixtures/               # Test data
├── config/                     # New: external configuration
│   ├── scraper_config.yaml
│   └── optimization_config.yaml
└── scripts/                    # New: orchestration scripts
    ├── run_pipeline.sh
    └── run_optimization.sh
```

---

*Structure analysis: 2026-03-14*
