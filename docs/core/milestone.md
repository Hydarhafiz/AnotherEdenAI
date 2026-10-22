# AnotherEdenAI Milestone 7: Frontend Portfolio Experience

## Objective And Approval

Status: Active implementation workstream; planning approved and the standalone planning deliverable completed on 2026-10-22. Features M7-1 through M7-3 are planned, not implemented.

Deliver a limited, explainable portfolio MVP using the existing recommendation engine: select a supported boss and owned character forms, submit, receive up to three legal candidates when available, inspect frontline/reserves and equipped skills, and understand the supporting evidence and limitations. Exploratory GraphRAG remains a separate supported mode.

The owner explicitly approved extending the RR-A/RR-B sequencing exception to make M7 active and reuse this document. M6 is **paused and incomplete**, not closed or accepted. Its exact remaining P2/P3/H2 gates, evidence references, conditional P4 and resumption obligations live in [roadmap.md](roadmap.md#milestone-6-reviewed-knowledge-recommendation-pilot). The full prior plan remains available as `git show 49a0d62:docs/core/milestone.md`. Moving the workstream does not relax any M6 gate or discharge M8 release obligations.

This session completes only the standalone planning deliverable. Stop after documentation checks and one planning commit. A separate chat starts implementation with M7-1; no builder or verification-role transition is authorized in this planning session.

## Verified Starting Point

- `9f0a33e` connects explicit production mode, Celestial Mushroom selection, optional preferences, roster/sidekick ownership and mode-specific progress; exploratory questions retain their own contract.
- `49a0d62` carries validated deterministic fallback through final formatting, affinity fidelity and graph-backed legality. Three degraded recommendations render with an explicit deterministic-only banner. Invalid candidates remain rejected; there is no recursive fallback or restoration of rejected proposals.
- Planning verification on 2026-10-22 repeated the existing 363 workflow/affected-web tests successfully, plus seven manual-pilot source regressions. The combined offline Chromium production smoke passed with three degraded recommendations. The sandbox reproduced the documented thread stall; bounded execution outside the sandbox passed. One existing FastAPI TestClient deprecation warning remains.
- The smoke uses real request handling, production retrieval/scoring/candidate generation, unavailable-analyzer fallback and final validators over fixture-backed driver records. It does **not** execute Cypher, establish live Neo4j freshness, qualify a paid provider or demonstrate gameplay usefulness. Its one local unconfigured-analyzer attempt makes no provider/network call.

Normal flow: `index.html` and `app.js` load graph entity names and local ownership selections -> `POST /api/query` stores a single-use in-memory job and returns progress HTML -> `GET /api/stream/{job_id}` runs the selected workflow -> deterministic production retrieval/scoring/packages/search -> bounded analyzer or validated deterministic fallback -> final output/affinity/legality checks -> Jinja result HTML over SSE. Progress uses JSON parsed once; result events carry HTML. Exploratory mode uses its existing PLAN/Cypher graph. Keep both paths and the POST/job/SSE contract; no new application layer or database is needed.

## Supported Presentation And Evidence Limits

| Identity | Current support | M7 presentation boundary |
| --- | --- | --- |
| `Celestial Mushroom` (request lookup), `celestial-mushroom` (canonical result/manifest ID) | Only current production selector option; strong twenty-form fixture smoke renders legal degraded candidates | Available as a limited candidate demo, explicitly not battle verified. Pierce/Blunt resistance; no listed weakness. Pain raises physical resistance, Poison raises type resistance, and the boss clears them/heals at turn end. AF stopper and other uncovered mechanics remain limitations. |
| `Rotte Rivel` (lookup), `rotte-rivel` (manifest ID) | Backend/source-pinned diagnostic candidates exist; absent from the UI selector | Keep outside selectable M7 recommendations. Explain its diagnostic-only status in coverage information. Marked-slot non-type Magic with Confuse/Bind is unresolved; Fire Magic versus combined Fire weakness/Magic resistance is REVIEW/UNKNOWN. Ordinary mitigation is not proven to counter HP-halving. No equal-validation claim or new boss admission. |

Pinned pool: exactly twenty **normal forms**, with complete legal-kit receipts in `tests/fixtures/m6_p2/pilot_scenarios.json` matching `src/etl/kit_catalog.json`:

- Automatic F2P additions: Aldo, Feinne, Cyrus, Deirdre, Azami, Gariyu, Cerrine, Levia.
- Other pilot forms: Shion, Toova, Suzette, Anabel, Radias, Prai, Aisha, Rosetta, Mariel, Yuna, Mana, Dunarith.

Use canonical graph names for requests; the fixture also pins character IDs. Normal-form evidence must not transfer to AS/ES/other forms. All 367 owned, data-complete catalog forms remain legally eligible; the pilot pool is neither a whitelist nor twenty fully reviewed kits. The thirty-boss corpus is preserved. No additional forms or bosses are curated or admitted here.

The browser currently declares no SA or Light/Shadow values: backend defaults exclude undeclared SA-only choices and use the conservative three-skill limit without known high points. Sidekicks are optional owned entities. The default `late_game_assumed` item policy assumes catalog access, not item ownership, and may supply labeled generic items. These assumptions and automatic F2P augmentation must be visible; M7 does not silently change availability or item policy.

## Frontend Audit And Scope Disposition

“Verified” below means current automated contract/rendering checks or the stated offline DOM check, not live-service or strategic acceptance.

| Requirement | Classification and current evidence | M7 disposition |
| --- | --- | --- |
| Production/exploratory separation, supported boss, optional preferences | Already implemented and verified: index/app.js, API/SSE tests and offline DOM | Preserve; M7-3 adds explanatory guidance. |
| Canonical character/sidekick selection, filtering and saved ownership | Implemented but incomplete: entity endpoint, checklists and localStorage work; no clear pilot/F2P/default guidance or storage recovery | M7-2 handles recoverable loading/storage failures; M7-3 guides selection. |
| SA and Light/Shadow input polish | Deferred: API/workflow accept fields, browser has no controls | Keep defaults visible; no new progression/profile editor. |
| Up to three legal candidate cards, four frontline/two reserves, equipped skills and builds | Already implemented and verified: `result.html`, rendering regressions and production smoke | Reuse cards/details; no visual redesign or guaranteed count/diversity. |
| Explanation, counterplay, risks, citations | Implemented but incomplete: output sections exist, deterministic fallback text is generic; boss affinity is validated but not displayed; fact-level evidence is lost before rendering | M7-1 exposes bounded backend evidence and explicit unavailable states. |
| Fit/confidence and rubric | Implemented but incomplete: labels derive from heuristic score/scorer uncertainty | M7-1 labels their modeled scope; never battle strength, review completeness or success likelihood. |
| Degraded-result banner and validation rejection | Already implemented and verified | Preserve prominent degraded state and all validators. |
| Missing reviewed skill evidence, harmful interactions, alternative Zones, switching | Missing reliable result-specific presentation, despite existing source/placement diagnostics | M7-1 adds grounded warnings without new strategic scoring. |
| Funnel, denominator, unknown and diversity reporting | Implemented internally but incomplete at UI boundary: `request_coverage`, candidate coverage/evidence diagnostics and placement scopes exist | M7-1 presents bounded relevant summaries; unknown stays unknown. |
| Invalid roster/boss, no candidates and pipeline failures | Implemented but incomplete: typed SSE issues exist; app.js discards details, connection failure can leave no explanation; empty copy invents a Grasta ownership input | M7-2 provides actionable messages and terminal progress behavior. |
| Sample roster | Missing, supported by existing selection contract and strong twenty-form smoke | M7-3 adds an explicit opt-in sample selection, with honest assumptions. |
| Mobile, keyboard and novice comprehension | Implemented but incomplete: responsive rules and native details exist; broad usability not verified | M7-3 verifies the supported journey at desktop/mobile sizes and by keyboard. |
| Data freshness/admin/system health views and public cost dashboard | Deferred beyond this limited MVP; an admin refresh endpoint is not a freshness observation | M8 owns operational visibility needed for safeguarded release. M7 shows unavailable evidence honestly. |
| Deployment, authentication, quota, spend limit, kill switch and provider qualification | Outside M7; remain M8 obligations | No infrastructure work or release-readiness claim. |

## Feature Sequence

Each package is a `build` feature using `builder-executor -> tdd-loop` in the **next chat**. Contained clarification may use `feature-planner`; return to the owner only for a material boundary change. Each completed feature owns one commit containing code, durable regressions, affected canonical documentation and this milestone's status update. No workflow-state commits.

### M7-1: Explain The Candidate And Its Limits

Status: Planned. Outcome: a player sees what the legal candidate actually equips, why modeled facts support it, and what remains unproven, including in deterministic-only output.

Currently: expandable cards already present members, skills, assumptions, risks and citations. `analyzer._candidate_proposal` mostly emits generic fallback prose and heuristic labels. `RecommendationSetOutput`/`TeamOutput` do not carry request coverage or selected-skill review diagnostics. The browser cannot recover these from formatted HTML.

Required changes and reuse:

- Retain `result.html` cards and existing `warnings`, `risks`, `key_facts`, counterplay, assumptions and citations. Reuse typed retrieval, backend candidate coverage/evidence, selected-skill diagnostics, placement and component-score scopes, source URLs and reviewed fact identities.
- Add only the bounded display projection needed to pass those existing facts through candidate resolution/final formatting. Optional additive output fields are admitted where existing fields cannot represent the summary; document them in architecture/validation guidance. No new endpoint, full catalog dump, graph schema or independent explanation engine.
- Bind explanations and warnings to **final validated members, equipped skills and placements**, including authorized swaps/package choices. Never attach stale original-candidate diagnostics after refinement. Unavailable or unjoinable evidence is explicitly unestablished, not zero or complete. Preserve final legality, affinity fidelity, finite allocations and analyzer bounds.
- Show boss affinities and useful selected-skill matchups only where inspected evidence supports them. Show source links beside supported claims; distinguish a legal unreviewed skill from reviewed capability proof. Do not fill a missing source with generated mechanics. Explain scope/target, including self-only effects.
- Surface relevant known harms and setup limits: selected Toova Venom against Mushroom; selected alternative Zone deployments (e.g. Flame's Serenade and Double Crush) cannot be claimed simultaneously active; reserve active-skill support/attacks require switching. Do not generalize this to all reserve passives or invent a rotation, Zone superiority or activation success.
- Use runtime retrieved facts and committed source authority, not imports from test fixtures. The existing pinned Mushroom interaction and source skill identities support narrowly keyed warning copy if runtime fields lack a structured warning; retain source provenance and tests for that mapping. Unknown Zone details permit only an explicit alternative/setup limitation, never a new capability claim.
- Keep the deterministic-only banner. Describe fit/rubric as internal ranking signals and confidence as limited scorer uncertainty, never battle confidence. Show reviewed selected-skill counts/denominators separately from source-effect coverage, which remains unestablished. Existing diagnostic uncertainty zero is not complete review. Show same-team/limited-diversity information when established; do not pad alternatives.

Acceptance:

- **M7-1-01:** One, two or three surviving candidates retain exact final frontline/reserve/skills/builds and validators; no fabricated alternatives or strategic PASS.
- **M7-1-02:** Reviewed effects show traceable sources and scope. Missing reviewed capability evidence remains explicit; denominators describe the selected skills. Missing diagnostics render as unavailable, including older/exploratory payloads.
- **M7-1-03:** Venom/Mushroom, alternative-Zone and reserve-switch warnings appear when relevant and do not imply concurrent Zones or active reserve protection. Nonmatching boss/skill/placement cases do not receive a false specific warning.
- **M7-1-04:** After a permitted refinement/swap, evidence matches final selections or is explicitly unavailable. Heuristic points, primary-damage coverage and labels never imply battle strength, full boss-counter coverage, source completeness or win probability.
- **M7-1-05:** Degraded status, generic-item/upgrade caveats and evidence limitations remain visible in the normal result view; exploratory single-team/alternatives and legacy optional fields still render.

Verification: extend existing workflow candidate/analyzer/format and web rendering suites for final-selection joins, unavailable evidence, warning presence/absence and label meaning; rerun the 363-test baseline selection plus affected regressions. Use the real fixture-backed production smoke rather than only synthetic HTML. Extend offline Chromium coverage to expand cards, inspect skills/affinities/warnings/citations and confirm degraded visibility. Manually inspect one desktop/mobile result for understandable language and readable critical warnings; this is UI acceptance, not H2 gameplay review. Record results during implementation.

Entry/dependency: Stage 1 complete; no dependency on a new M6 positive. Excludes curation, scorer/ranking/search changes, battle validation, new mechanics and paid runs. Commit boundary: complete evidence projection, rendering, regressions and affected docs together.

### M7-2: Make Failures Understandable And Recoverable

Status: Planned; follows M7-1. Outcome: the user knows what failed, what action can help and whether the request has finished, while keeping selected ownership.

Currently: `ProductionRequestError` supplies safe issue codes/fields/messages through `pipeline_error_payload`; format output has error classes. `app.js` substitutes a generic retry label and silently closes some failures. POST errors report status only; missing/reused jobs return HTTP 404; render failures can end without a result. Empty-state copy refers to a nonexistent Grasta list and can equate unavailable evidence with an unsuitable roster.

Required changes and reuse:

- Reuse typed issue codes, existing format error types, `error.html`/`empty.html`, POST/job/SSE and both mode trackers. Display safe field-specific guidance for missing/unsupported/unready/conflicting boss, invalid/unknown/ambiguous roster or sidekick, malformed input, incomplete data and unavailable legal candidates.
- Distinguish invalid input, insufficient supported evidence/candidates and operational failure. Empty candidate output does not prove gameplay infeasibility; adding characters is a suggestion only when supported. Remove obsolete Grasta-list advice.
- Complete the frontend lifecycle for entity-load/storage errors, POST validation/network failures, invalid/reused SSE job, SSE disconnect, render failure and `done` without result. Where needed, pass a safe existing-protocol error event from the bridge; do not expose raw internal exceptions or invent a new transport.
- Every terminal outcome stops timers, restores submission and leaves an actionable message; preserve selections. Retry explicitly creates a fresh job. No automatic request resubmission, provider retries or alternate fallback pipeline. Unknown failures get safe generic guidance rather than invented diagnostics.

Acceptance:

- **M7-2-01:** Typed input failures identify the affected field and next action; stale roster names can be corrected without erasing valid ownership. Boss conflicts direct the user to reconcile preferences/selection.
- **M7-2-02:** Zero-candidate, missing-data and final-validation failures remain failures with distinct supported guidance; none bypasses validation, claims game infeasibility or turns into invented teams.
- **M7-2-03:** Each listed POST/SSE/render/connection failure and no-result completion leaves no spinner or disabled submit control; user retry starts one new job. Invalid/reused job closes cleanly.
- **M7-2-04:** Entity or malformed localStorage failure leaves usable recovery guidance. Both modes preserve their input requirements and success paths; safe text is rendered without treating diagnostic strings as HTML.

Verification: extend actual-script Node, API/SSE and template suites with representative typed, zero-candidate, malformed-storage, invalid-job, interrupted/no-result and render-failure cases; keep unique transport/validation coverage. Offline Chromium must exercise an invalid request, a simulated disconnect/no-result completion and successful explicit retry, in addition to both existing success paths. Manually check keyboard-accessible error guidance and recovery. No live-service failure injection is required.

Entry/dependency: M7-1 output compatibility settled. Excludes backend request/schema redesign, graph repair, provider changes, job persistence/multiworker support and quota work. Commit boundary: complete error presentation and terminal lifecycle with regressions/docs together.

### M7-3: Guide Roster Selection And The Portfolio Demo

Status: Planned; follows M7-2. Outcome: someone unfamiliar with the mechanics can select a roster or explicitly try the sample, run the bounded demo and explain what the result establishes.

Currently: search/checklists/localStorage, optional owned sidekicks, mode selector and responsive result details work. Guidance, selected-count feedback, F2P/default explanations and an opt-in sample are absent.

Required changes and reuse:

- Keep existing form, native controls, responsive layout and card structure. Add concise instructions for forms, frontline/reserves, equipped skills, boss candidate coverage, source limitations, the deterministic backend/LLM division and optional preferences. Avoid a cosmetic redesign.
- Explain automatic F2P additions, optional sidekicks, no declared SA/Light/Shadow and assumed item access before submission. Do not call a roster under six selected characters invalid solely on count: backend F2P augmentation still applies; existing production input requires at least one user roster entry.
- Add an explicit “Use sample roster” action for the twenty normal-form Mushroom demo, reusing the canonical names above and current ownership controls. Intersect with loaded entity names, report any missing forms, and require user action before replacing saved selections. Declare no owned sidekicks/SA/high Light/Shadow; show the existing item-policy assumption. Do not auto-submit or claim the sample is H2 accepted. No separate sample API or runtime dependency on test fixtures.
- Keep Mushroom as the only selectable production boss; explain Rotte's diagnostic-only evidence limit. Preserve full catalog selection and exploratory mode. Add selected-roster feedback and verify labels/focus, keyboard operation and narrow-screen readability.

Acceptance:

- **M7-3-01:** A new user can follow select boss -> owned forms/sample -> submit -> inspect teams/skills -> read reasons/sources/limits without understanding internal workflow names.
- **M7-3-02:** Explicit sample selection sets the supported canonical forms and declared defaults, preserves existing selections until the action, handles unavailable entities honestly and does not expand curated eligibility. A normal reload restores supported saved ownership.
- **M7-3-03:** F2P augmentation, form identity, item/upgrade assumptions and legal-versus-battle-verified distinction are visible. Rotte is not promoted to selectable/equally validated support.
- **M7-3-04:** Desktop and approximately 390px mobile views have readable controls, result details and warnings without horizontal page overflow; the complete supported journey and mode switching work by keyboard with understandable labels/focus/error announcements.
- **M7-3-05:** All three feature contracts pass, affected canonical docs describe actual behavior, and the final retention/convergence sweep finds no displaced UI path or temporary artifact presented as product authority. M6/M8 gates stay open.

Verification: extend actual-script tests for sample application, saved-roster behavior, missing entities and unchanged payload defaults; retain normal-form/F2P contract checks. Run the combined fixture-backed smoke in offline Chromium with sample selection and expanded evidence at desktop/mobile sizes. Manually walk the journey by keyboard and review novice-facing language, default assumptions and visible failure recovery. This bounded UI check does not require a paid model, live database or battle trial. Run the complete baseline and affected tests at final M7 verification.

Entry/dependency: M7-1 warnings and M7-2 recovery available. Excludes advanced SA/Light/Shadow/item editors, expanded curation, extra bosses/forms, chat, accounts, dashboards and deployment. Commit boundary: complete guidance/sample/usability, durable browser regressions, final milestone update and retention cleanup together.

## Verification, Retention And Exit

Repository tools: Python/pytest in `.venv`, Node's syntax/test runner and the existing offline Chromium harness. No configured formatter/linter/type-checker is declared in `pyproject.toml`; this plan admits no tool installation, dependency, quality configuration or CI policy change. Use `node --check src/web/static/app.js`, affected Python syntax checks and `git diff --check` alongside behavioral verification.

Reusable baseline (disable dotenv loading; never inspect credentials):

```bash
timeout 55s .venv/bin/python -B - <<'PY'
from unittest.mock import patch
with patch('dotenv.load_dotenv', return_value=False):
    import pytest
    raise SystemExit(pytest.main([
        '--confcutdir=tests/workflow', '-p', 'no:cacheprovider', '-q',
        'tests/workflow', 'tests/web/unit/test_api.py',
        'tests/web/unit/test_streaming.py', 'tests/web/unit/test_production_ui.py',
        'tests/web/unit/test_feature_e_result_ui.py',
        'tests/web/unit/test_production_integration.py',
    ]))
PY
timeout 45s .venv/bin/python -B tests/web/browser_check.py --production-smoke
```

Expand the selection with each feature's affected tests. Use bounded execution outside the sandbox when the known local thread/socket bridge stalls; do not alter production concurrency or weaken assertions. Offline DOM checks remove external assets, so they do not prove CDN delivery or live production styling. Manual usability checks must inspect the actual styled page with local/stubbed services; record any asset limitation rather than claiming full visual acceptance from the stripped harness.

Retain capability regressions and source-authoritative fixtures already used by the supported flow; consolidate additions into existing suites. Keep command output, generated pages/reports, browser profiles and `.sdd/` ignored and temporary. Promote durable contracts and evidence limits to canonical docs; purge the completed handoff. Keep production and exploratory paths, their validators and existing cards; adapt their presentation in place, with no parallel UI/fallback implementation or temporary compatibility layer planned.

M7 exits only when M7-1 through M7-3 automated checks and recorded manual UI checks pass and canonical docs agree. M7 completion means frontend readiness for the bounded, honestly labeled candidate demo. It does not complete M6/P2/P3/H2, establish live graph freshness, qualify a provider or authorize public release. M8 retains registration, quotas, RM50 spend ceiling, kill switch, persistent accounting, deployment and paid-provider qualification. If a required warning cannot be grounded in existing evidence, show the limitation and return any proposed evidence/schema/engine expansion to the owner; do not reopen engine development inside M7.

Planning provenance: only planning intent and canonical documentation are revised. Runtime, scores, schemas, source/review identities, graph data, provider settings and release identity are unchanged by the planning deliverable.
