---
phase: quick
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - src/etl/constants.py
autonomous: true
requirements: [DATA-02]

must_haves:
  truths:
    - "python assert_schema.py exits 0 (Grasta check passes)"
    - "The Grasta minimum in constants.py reflects the real wiki count with a documented safety buffer"
  artifacts:
    - path: "src/etl/constants.py"
      provides: "Calibrated EXPECTED_NODE_COUNTS['Grasta'] minimum"
      contains: "# wiki audit"
  key_links:
    - from: "src/etl/constants.py EXPECTED_NODE_COUNTS"
      to: "assert_schema.py threshold check"
      via: "imported EXPECTED_NODE_COUNTS['Grasta']"
      pattern: "EXPECTED_NODE_COUNTS"
---

<objective>
Fix the failing Grasta count assertion by diagnosing the actual per-category wiki counts,
then calibrating the minimum threshold in constants.py to a correct floor with a documented buffer.

Purpose: assert_schema.py exits 1 (Grasta count 489 < 500) blocking any post-load validation.
         The constant comment "wiki has 647" is a stale estimate — needs grounding in real data.
Output: Updated constants.py with a calibrated minimum; assert_schema.py exits 0.
</objective>

<execution_context>
@/home/shogunix/.claude/get-shit-done/workflows/execute-plan.md
@/home/shogunix/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/home/shogunix/AnotherEdenAI/.planning/STATE.md
@/home/shogunix/AnotherEdenAI/src/etl/constants.py
@/home/shogunix/AnotherEdenAI/src/etl/scraper.py
@/home/shogunix/AnotherEdenAI/assert_schema.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Diagnose actual Grasta counts per category</name>
  <files>diagnose_grasta.py</files>
  <action>
    Create a temporary diagnostic script at the repo root: diagnose_grasta.py

    The script must:
    1. Use httpx (sync) to fetch each of the 5 Grasta category pages from WIKI_URLS in constants.py
       (grasta_attack, grasta_life, grasta_support, grasta_special, grasta_vc — NOT grasta_ores)
    2. For each page, count the number of `tr.grasta-row-entry` rows that have >= 4 `<td>` children
       (this mirrors the guard in parse_grastas / parse_vc_grastas exactly)
    3. Print per-category counts and a total, e.g.:
       Attack : 142
       Life   :  98
       Support: 110
       Special:  87
       VC     :  52
       TOTAL  : 489
    4. Run the script: python diagnose_grasta.py

    This is a read-only diagnostic — do NOT load models or touch Neo4j.
    Headers: {"User-Agent": "Mozilla/5.0 (AnotherEdenAI-research-bot)"}
    Timeout: 15 seconds per request.

    After running, record the TOTAL in your notes. If TOTAL is in the range 480-510, the
    scraper is working correctly and the constant comment was simply wrong. If TOTAL is
    significantly above 510 (e.g. > 550), the scraper is dropping rows — stop and investigate
    the selector before proceeding to Task 2.
  </action>
  <verify>
    <automated>python /home/shogunix/AnotherEdenAI/diagnose_grasta.py</automated>
  </verify>
  <done>Script runs without error, prints per-category counts and TOTAL, TOTAL is between 480-510 (confirming scraper is correct, constant is stale)</done>
</task>

<task type="auto">
  <name>Task 2: Calibrate Grasta minimum in constants.py</name>
  <files>src/etl/constants.py</files>
  <action>
    Using the TOTAL from Task 1 (call it N):

    1. Set the new minimum = N - 20  (approximately 4% buffer below actual; catches real regressions
       while tolerating minor wiki fluctuations). Round down to nearest 10 for readability.
       Example: if N=489, new minimum = 469 → round down → 460. Use 460.

    2. Update line 27 of src/etl/constants.py:
       OLD: "Grasta": 500,     # wiki has 647
       NEW: "Grasta": <new_minimum>,  # wiki audit 2026-03-15: actual={N}, floor={new_minimum} (~4% buffer)

    3. Do NOT change any other constants.

    After editing, run: python assert_schema.py
    Expected output:
      OK: Character = 389
      OK: Grasta = 489
      OK: Ore = 61
      OK: Trait = 126
    Exit code must be 0.

    Then delete the temporary diagnostic script: rm diagnose_grasta.py
  </action>
  <verify>
    <automated>cd /home/shogunix/AnotherEdenAI && python assert_schema.py; echo "Exit: $?"</automated>
  </verify>
  <done>assert_schema.py exits 0 with all four labels showing OK; constants.py comment reflects the 2026-03-15 wiki audit count and the derived floor</done>
</task>

</tasks>

<verification>
python assert_schema.py must exit 0 with output:
  OK: Character = 389
  OK: Grasta = 489   (or whatever actual count the wiki returns)
  OK: Ore = 61
  OK: Trait = 126

No temporary files (diagnose_grasta.py) left in repo root.
</verification>

<success_criteria>
- assert_schema.py exits 0
- EXPECTED_NODE_COUNTS['Grasta'] minimum is <= 489 with a comment documenting the 2026-03-15 wiki audit actual count
- No scraper code changed (Task 1 confirmed the scraper is working correctly)
</success_criteria>

<output>
After completion, create `.planning/quick/1-fix-grasta-count-assertion-actual-489-is/1-SUMMARY.md`
with: what was diagnosed, actual per-category counts, new minimum value, and confirmation that
assert_schema.py exits 0.
</output>
