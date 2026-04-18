# Codebase Concerns

**Analysis Date:** 2026-03-14

## Tech Debt

**Bare Except Clauses:**
- Issue: Multiple `except:` statements with no exception type specified or error handling logic. Silent failures mask data quality issues during scraping.
- Files: `master_scraper.py` (lines 52, 75, 95, 127), `optimize_character.py` (line 22), `separate_trait_grasta.py` (line 19)
- Impact: Parsing failures are silently skipped without logging. Row count discrepancies and missing data go unnoticed. Difficult to debug data pipeline failures.
- Fix approach: Replace bare `except:` with specific exception types (`except Exception as e:`) and log all caught exceptions with context (row index, URL, function name). Add counters to track how many rows/items were skipped.

**No Input Validation:**
- Issue: Web scraper and CSV parsers assume HTML structure and CSV format match expected schema without defensive checks.
- Files: `master_scraper.py` (lines 37-128), `optimize_character.py` (lines 15-17), `separate_trait_grasta.py` (lines 5-6)
- Impact: If wiki changes HTML structure or CSV schema changes, scripts fail silently or produce corrupt data. No mechanism to detect data format drift.
- Fix approach: Add schema validation after loading DataFrames (check required columns exist and have expected types). Add HTML structure assertions before accessing element indices (verify `len(cols) >= N` before `cols[N]`).

**Hardcoded Configuration:**
- Issue: URLs, file paths, character names, and target column names are scattered throughout code as magic strings.
- Files: `master_scraper.py` (lines 7-15, 18), `optimize_character.py` (lines 6, 8-10, 61), `separate_trait_grasta.py` (lines 5-6)
- Impact: Changes to wiki URLs, output file locations, or game data require editing multiple files. Brittle to environment changes.
- Fix approach: Consolidate all configuration into a single `config.py` file or YAML configuration file. Environment variables for paths that might differ between dev/prod.

**String Parsing with ast.literal_eval:**
- Issue: Uses `ast.literal_eval()` to parse list representations stored as strings in CSV columns (`personalities` column in `master_scraper.py` line 43, `optimize_character.py` line 21).
- Files: `optimize_character.py` (line 21), `separate_trait_grasta.py` (line 16)
- Impact: Unsafe deserialization of untrusted data. Could allow code injection if CSV data is tampered. Performance overhead of parsing strings repeatedly.
- Fix approach: Store lists as proper JSON in CSVs or use `pd.json_normalize()`. Parse once during load, not on each use. Add JSON schema validation.

## Known Bugs

**HTML Structure Assumption Fragility:**
- Symptoms: Scraper may fail to parse character/grasta data if wiki's HTML table class names or column positions change. Line 99 comment indicates prior issue with `equip-row-entry` class.
- Files: `master_scraper.py` (lines 37-128)
- Trigger: Wiki administrator updates page layout or HTML structure. Example: Character table row class changes from `"character-row-entry"` to `"char-row"`.
- Workaround: Manually inspect wiki HTML and update class names and column indices in scraper functions. Add unit tests with fixed HTML snapshots to catch future breaks.

**CSV Data Type Inconsistencies:**
- Symptoms: Tier values stored as strings instead of integers, causing type mismatches when filtering (`df_g['tier'].astype(str)` in `optimize_character.py` line 52).
- Files: `optimize_character.py` (line 52)
- Trigger: Run `optimize_character.py` after `master_scraper.py`. Grasta tier filtering requires string conversion due to how BeautifulSoup extracts and pandas stores the data.
- Workaround: Explicitly cast columns to correct types in `load_data()`. Schema validation to ensure consistent types across runs.

**Case Sensitivity in Character/Item Lookup:**
- Symptoms: Character name search uses `str.contains(char_name, case=False, ...)` but may fail if wiki stores names with special characters or accents inconsistently.
- Files: `optimize_character.py` (line 28)
- Trigger: Search for character with variant spelling (e.g., "Rufus" vs "rufus" vs "Rüfus"). Empty result set returned.
- Workaround: Normalize character names on load (strip whitespace, lowercase, remove accents). Add fuzzy matching for typos.

## Security Considerations

**Unvalidated Web Requests:**
- Risk: Scraper sends requests to external wiki without timeout limits or rate limiting. Could timeout indefinitely or be exploited for DDoS if many instances run.
- Files: `master_scraper.py` (lines 21-29)
- Current mitigation: None. `requests.get()` has default timeout of None (waits forever).
- Recommendations: Add `timeout=10` parameter to all `requests.get()` calls. Implement exponential backoff for retry logic. Add request rate limiting (sleep between requests).

**No HTTPS Verification:**
- Risk: Wiki URL is HTTP, not HTTPS. Requests could be intercepted and modified in transit.
- Files: `master_scraper.py` (lines 8-14)
- Current mitigation: None.
- Recommendations: Change all wiki URLs to HTTPS if available. Add certificate pinning if high-security environment needed.

**User-Agent Spoofing:**
- Risk: User-Agent header mimics Chrome browser, which may violate wiki's terms of service or trigger bot detection.
- Files: `master_scraper.py` (line 18)
- Current mitigation: None.
- Recommendations: Use proper `requests` User-Agent that identifies the script. Review wiki's robots.txt and API terms. Consider using wiki's official API if available.

**No Data Sanitization:**
- Risk: Scraped data (character names, stats text) written to CSV without sanitization. Could contain SQL injection payloads if later used in SQL queries.
- Files: `master_scraper.py` (lines 195-197)
- Current mitigation: None.
- Recommendations: Sanitize all scraped text fields. If data goes to database, use parameterized queries.

## Performance Bottlenecks

**Synchronous Web Requests:**
- Problem: Scraper fetches each wiki page sequentially (characters, then 6 grasta types, then ores). Total runtime grows linearly with number of pages.
- Files: `master_scraper.py` (lines 179-192)
- Cause: No concurrency. `get_soup()` blocks until response received.
- Improvement path: Use `asyncio` + `aiohttp` to fetch all pages concurrently. Reduces runtime from O(n) to O(1) page-fetches.

**String Operations in Hot Loop:**
- Problem: `separate_trait_grasta.py` iterates through all rows to parse traits with `ast.literal_eval()` inside loop.
- Files: `separate_trait_grasta.py` (lines 13-20)
- Cause: Parser runs on every row instead of batch parsing. Linear complexity with dataset size.
- Improvement path: Parse all traits once during CSV load. Cache result in memory. Use pandas vectorized operations.

**Inefficient DataFrame Filtering:**
- Problem: `optimize_character.py` creates multiple filtered DataFrames with repeated column scans.
- Files: `optimize_character.py` (lines 42-56)
- Cause: No indexing on common filter columns. Full table scans for each `isin()`, `contains()`, `astype()` call.
- Improvement path: Create indexes on `personality_req`, `is_shareable`, `tier` columns. Cache DataFrame dtypes. Use `pd.Categorical` for low-cardinality columns.

## Fragile Areas

**Web Scraper HTML Parsing:**
- Files: `master_scraper.py` (lines 33-128)
- Why fragile: Depends on exact HTML structure, CSS class names, and column ordering. Wiki updates break it silently. FIX comment on line 99 shows history of breaking changes.
- Safe modification: Add comprehensive unit tests with fixed HTML snapshots from multiple wiki states. Verify all `find_all()` and `find()` calls with try-except that logs failure. Add version detection to alert when structure changes.
- Test coverage: Likely zero. No unit tests for scraper functions exist in repo.

**Character Build Optimization Logic:**
- Files: `optimize_character.py` (lines 26-83)
- Why fragile: Hardcoded trait matching logic and ore selection use string matching and magic indices. If grasta data format changes or trait names change, logic breaks silently.
- Safe modification: Add parametric configuration for trait matching rules. Extract ore selection to pluggable algorithm. Add logging at each step.
- Test coverage: No tests for `get_meta_build()` function. No test fixtures for different character types.

**Trait Extraction Pipeline:**
- Files: `separate_trait_grasta.py` (entire file)
- Why fragile: Assumes CSV columns named exactly `personalities` and `personality_req`. If scraper renames columns, this silently produces wrong trait list.
- Safe modification: Add DataFrame schema validation before processing. Use column references instead of hardcoded names. Add assertions for expected data types.
- Test coverage: None. No tests verify that traits extracted match expected set.

## Scaling Limits

**Single Machine / Single Process:**
- Current capacity: Limited by one CPU core for scraping and processing. ~200-300 character/grasta/ore records typical.
- Limit: If Another Eden adds 10x more characters, scraping time grows proportionally. Current sequential approach becomes bottleneck.
- Scaling path: Implement async scraping (fetch all pages in parallel). Move to job queue (Celery + Redis) for distributed scraping. Use database instead of CSV for larger datasets.

**CSV as Data Store:**
- Current capacity: Files loaded entirely into memory. ~100KB per file typical.
- Limit: If dataset grows to millions of rows, pandas `read_csv()` will consume gigabytes of RAM. No query optimization possible.
- Scaling path: Migrate to PostgreSQL or SQLite. Implement lazy loading / pagination. Use columnar format (Parquet) if data size explodes.

**No Data Persistence Strategy:**
- Current capacity: Data regenerated from scratch on each run. No caching of wiki scrapes.
- Limit: If wiki is slow or down, all downstream analysis blocked. Wiki rate-limiting could cause repeated failures.
- Scaling path: Implement database with caching layer. Cache wiki scrapes with TTL (24 hours). Add fallback to last-known-good data.

## Dependencies at Risk

**BeautifulSoup4 HTML Parsing:**
- Risk: If BeautifulSoup major version changes, CSS selector syntax could change. If wikimedia changes HTML encoding, parser may fail.
- Impact: Entire scraper becomes non-functional.
- Migration plan: If needed, switch to `lxml` parser for better performance or `Selenium` for JavaScript-heavy pages. Add parser version pinning in `requirements.txt`.

**Pandas DataFrame Operations:**
- Risk: Pandas 3.0 planned for future with breaking changes to type inference and string handling.
- Impact: `ast.literal_eval()` handling and dtype casting could break.
- Migration plan: Pin Pandas version explicitly. Add type hints and explicit dtype specifications. Test with upcoming Pandas versions quarterly.

**No Explicit Dependency Management:**
- Risk: No `requirements.txt` or `setup.py` found. Implicit dependencies on installed system packages.
- Impact: Code won't run on another machine without manual pip install. Can't track dependency versions or security updates.
- Migration plan: Create `requirements.txt` with pinned versions. Add `poetry` or `pipenv` for lock file. Document Python version requirement (assume 3.8+).

## Missing Critical Features

**No Error Recovery or Retry Logic:**
- Problem: If web request fails, scraper stops entirely. No attempt to retry or continue with partial data.
- Blocks: Can't handle flaky networks or wiki maintenance windows.

**No Data Quality Metrics:**
- Problem: After scraping, no verification that data is complete. Row counts could indicate missing data but there's no automated check.
- Blocks: Downstream analysis might run on incomplete data without alerting user.

**No Output Validation:**
- Problem: Generated CSV files are not validated against expected schema before being used by downstream scripts.
- Blocks: Corrupt data propagates through pipeline silently.

**No Version Control for Data:**
- Problem: Each run overwrites CSV files. No history of data changes or ability to diff versions.
- Blocks: Can't detect when wiki data changed between runs.

**No Logging Framework:**
- Problem: Script uses only `print()` statements. No log levels, timestamps, or log file output.
- Blocks: Hard to debug production runs. Logs lost on container restart.

## Test Coverage Gaps

**No Unit Tests Detected:**
- What's not tested: All functions (`scrape_characters()`, `scrape_grasta_general()`, `scrape_ores()`, `load_data()`, `get_meta_build()`).
- Files: `master_scraper.py`, `optimize_character.py`, `separate_trait_grasta.py`
- Risk: Any change to parsing logic could break silently. No automated catch for regressions.
- Priority: High - scraper is critical path. 80% of bugs will be in parsing.

**No Integration Tests:**
- What's not tested: Full pipeline from scrape → optimize → report. End-to-end data flow.
- Files: Cross-file interactions between `master_scraper.py` → `optimize_character.py` → `separate_trait_grasta.py`.
- Risk: Data format mismatches between stages go undetected (e.g., column renames).
- Priority: High - integration is where real bugs surface.

**No Fixture/Mock Data:**
- What's not tested: Behavior with various HTML structures or CSV formats. Edge cases (empty table, missing columns, special characters).
- Files: All three scripts.
- Risk: Scraper behavior is untested against real-world HTML variations.
- Priority: Medium - would improve robustness significantly.

---

*Concerns audit: 2026-03-14*
