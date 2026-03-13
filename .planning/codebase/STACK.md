# Technology Stack

**Analysis Date:** 2026-03-14

## Languages

**Primary:**
- Python 3.12.3 - Data pipeline, web scraping, data analysis, optimization engine

## Runtime

**Environment:**
- Python 3.12.3 (CPython)

**Package Manager:**
- pip (Python package manager)
- Lockfile: missing (no requirements.txt or poetry.lock detected)

## Frameworks

**Core:**
- No framework currently used - scripts executed as standalone Python modules

**Data Processing:**
- Pandas - Data manipulation, CSV reading/writing, DataFrame operations
- BeautifulSoup (bs4) - HTML parsing and web scraping from wiki

**Utilities:**
- ast - Built-in Python module for parsing string representations of lists/dicts
- random - Built-in Python module for random selection in optimization

## Key Dependencies

**Critical:**
- Pandas - Core data processing for character, grasta, and ore data transformation
- BeautifulSoup 4 (bs4) - Web scraping from `anothereden.wiki` for live game data
- requests - HTTP library for fetching wiki pages

**Standard Library Only (No External):**
- ast - String to Python object conversion
- random - Randomization for meta build selection

## Configuration

**Environment:**
- No `.env` file or environment variables detected
- Configuration is hardcoded in Python files:
  - URLs defined in `master_scraper.py` (lines 7-15)
  - User-Agent headers defined in `master_scraper.py` (lines 17-19)
  - Target character configuration in `optimize_character.py` (line 6)

**Build:**
- No build system detected (not a compiled project)
- No Docker/containerization setup

## Data Formats

**Input:**
- HTML pages from `anothereden.wiki` domain
- Expects specific HTML class selectors: `character-row-entry`, `grasta-row-entry`, `equip-row-entry`

**Output:**
- CSV format:
  - `ae_characters.csv` - Character data with traits
  - `ae_grasta_master.csv` - Grasta equipment data by category
  - `ae_ores.csv` - Ore/enhancement items
  - `ae_traits.csv` - Master list of unique traits

## Platform Requirements

**Development:**
- Python 3.12.3
- pip for package installation
- No virtual environment configured (`.venv` in `.gitignore` suggests local venv usage)

**Production:**
- Python 3.12.3 runtime
- Network access to `https://anothereden.wiki`
- File system write access for CSV output
- No database server required (file-based CSV storage)

## Known Limitations

**Architecture Gaps:**
- No dependency lock file (versions not pinned)
- No package versions specified anywhere
- Configuration is hardcoded, not externalized
- No logging framework (uses `print()` statements)
- No error recovery mechanism (try/except with `continue` swallows errors)

---

*Stack analysis: 2026-03-14*
