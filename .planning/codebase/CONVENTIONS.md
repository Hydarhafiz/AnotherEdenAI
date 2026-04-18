# Coding Conventions

**Analysis Date:** 2026-03-14

## Naming Patterns

**Files:**
- Lowercase with underscores: `master_scraper.py`, `optimize_character.py`, `separate_trait_grasta.py`
- Descriptive names that reflect purpose/module name

**Functions:**
- Snake_case: `scrape_characters()`, `get_meta_build()`, `scrape_grasta_general()`
- Descriptive action verbs: `get_*`, `scrape_*`, `load_*`, `generate_*`
- Single responsibility principle observed: `scrape_characters()` only scrapes characters

**Variables:**
- Snake_case: `df_chars`, `df_grasta`, `df_ores`, `target_char`, `char_traits`
- DataFrame prefix pattern: `df_*` for pandas DataFrames
- Collection suffixes: plural nouns for lists/sets (`personalities`, `shareables`, `char_traits`, `grasta_traits`)
- Configuration constants: SCREAMING_SNAKE_CASE (`TARGET_CHAR`, `URLS`, `HEADERS`, `FILES`)

**Types:**
- No explicit type hints used in codebase
- Implicit typing through naming: `df_*` for DataFrames, `*_list` pattern not used but implicit in set operations

## Code Style

**Formatting:**
- Line length: Code appears to respect reasonable line limits (max observed ~120 characters)
- Indentation: 4 spaces consistently
- No formatter configured (no `.prettierrc` or black config detected)
- No linting configuration (no `.eslintrc` or `pylint.rc` detected)

**Linting:**
- Not detected - no configuration files present
- Code would benefit from `pylint`, `black`, or `flake8` configuration

## Import Organization

**Order:**
1. Standard library imports: `requests`, `pandas`, `ast`, `random`
2. Third-party imports: `BeautifulSoup` (from `bs4`)
3. Local imports: None present in current codebase

**Pattern:**
- All imports at top of file
- No wildcard imports observed
- Organized by convention but not enforced

**Path Aliases:**
- Not applicable - no alias system in use
- Configuration uses dictionaries: `URLS = {...}`, `FILES = {...}`

## Error Handling

**Patterns:**
- Bare `except:` clauses used extensively (anti-pattern):
  - `master_scraper.py` line 27-28: `except Exception as e:` (better)
  - `master_scraper.py` line 52: `except: continue` (bare except)
  - `optimize_character.py` line 22: `except: pass` (bare except)
  - `separate_trait_grasta.py` line 19: `except: continue` (bare except)

**Error Recovery:**
- Silent failures preferred in data collection (`except: continue`)
- Web request errors caught with `response.raise_for_status()` (line 25 of `master_scraper.py`)
- Missing data handled with defaults: `if not soup: return []` (line 35 of `master_scraper.py`)
- Empty DataFrame checks: `if char_row.empty:` return error message (line 29 of `optimize_character.py`)

## Logging

**Framework:** Console output using `print()` statements

**Patterns:**
- Status messages: `print(f"Fetching {url}...")` (line 23 of `master_scraper.py`)
- Progress reports: `print(f"Parsing {len(rows)} characters...")` (line 39 of `master_scraper.py`)
- Result summaries: `print("\nSUCCESS! Files Generated:")` (line 199 of `master_scraper.py`)
- Section headers: `print("\n=== AUTOMATED KG SCHEMA DESIGN (UPDATED) ===")` (line 132 of `master_scraper.py`)
- Report formatting with alignment: `print("="*40)` (line 65 of `optimize_character.py`)

**When to Log:**
- User-facing operations: scraping start/end, file generation
- Data processing milestones: parsing rows, extracting traits
- Report generation and results
- No debug-level logging for development

## Comments

**When to Comment:**
- Purpose statements for sections: `# --- CONFIGURATION ---`, `# --- SCRAPERS ---`, `# --- EXECUTION ---`
- Complex logic explanation: `# Logic: Find Shareable Grastas that match the character's traits` (line 40 of `optimize_character.py`)
- FIX/Note comments for known issues: `# FIX: Uses 'equip-row-entry' based on your HTML snippet` (line 99 of `master_scraper.py`)
- Edge case documentation: `# Note: In your scraper, weapon grastas often have 'data-weapon' attributes or are generic` (line 49 of `optimize_character.py`)

**JSDoc/TSDoc:**
- Not applicable - Python codebase with no docstrings
- No function-level documentation present
- Comments preferred over docstrings for explanation

## Function Design

**Size:** Small to medium functions (10-40 lines)

**Parameters:**
- Limited parameter count: 1-3 parameters typical
- `scrape_grasta_general(category, url)` - 2 parameters (line 55 of `master_scraper.py`)
- `get_meta_build(char_name, df_c, df_g, df_o)` - 4 parameters (line 26 of `optimize_character.py`)
- Data structures passed whole (DataFrames) rather than sliced

**Return Values:**
- Explicit returns of pandas DataFrames: `return pd.DataFrame(data)`
- Early returns for error cases: `if not soup: return []` (line 57 of `master_scraper.py`)
- Multiple return implicit None when not specified: Many functions return implicitly on error paths

**Function Cohesion:**
- Single responsibility observed: each function does one thing
- Pure functions preferred where possible: deterministic transformations
- No hidden state or side effects except I/O (file reads/writes in main block)

## Module Design

**Exports:**
- All functions in module are public (no underscore prefix pattern)
- Main-guard pattern used: `if __name__ == "__main__":` (standard Python practice)
- Script-based architecture: each file is executable independently

**Barrel Files:**
- Not applicable - each module is standalone
- No `__init__.py` files or package structure

## Data Structures and Patterns

**Primary Data Structure:**
- Pandas DataFrames (`df_*` pattern) used throughout for tabular data
- Lists collected in loops before converting to DataFrame:
  ```python
  data = []
  for row in rows:
      data.append({...})
  return pd.DataFrame(data)
  ```

**Configuration Pattern:**
- Dictionary-based configuration at module top:
  ```python
  URLS = {...}
  HEADERS = {...}
  FILES = {...}
  TARGET_CHAR = "Rufus"
  ```

**Conditional Logic:**
- Boolean flags: `(df_g['is_shareable'] == True)` (line 43 of `optimize_character.py`)
- String containment checks: `.str.contains(pattern, case=False, na=False)`
- Chained pandas filters: Multiple conditions combined with `&`

---

*Convention analysis: 2026-03-14*
