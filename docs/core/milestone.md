# AnotherEdenAI Milestone 7: Frontend Portfolio Experience

## Objective And Approval

Status: Complete (2026-11-06). M7-1, M7-2 and M7-3 are complete. The owner approved the final M7-3 interface and accepted Milestone 7. M6/H2 remains paused and incomplete; M8 release requirements remain open.

Deliver a limited, explainable portfolio MVP using the existing recommendation engine: select a supported boss and owned character forms, submit, receive up to three legal candidates when available, inspect frontline/reserves and equipped skills, and understand the supporting evidence and limitations. Exploratory GraphRAG remains a separate supported mode.

The owner explicitly approved extending the RR-A/RR-B sequencing exception to make M7 active and reuse this document. M6 is **paused and incomplete**, not closed or accepted. Its exact remaining P2/P3/H2 gates, evidence references, conditional P4 and resumption obligations live in [roadmap.md](roadmap.md#milestone-6-reviewed-knowledge-recommendation-pilot). The full prior plan remains available as `git show 49a0d62:docs/core/milestone.md`. Moving the workstream does not relax any M6 gate or discharge M8 release obligations.

M7-1 and M7-2 implementation and verification are recorded below, each in its own feature commit. The owner rejected the original M7-3 UI, approved the bounded amendment below, and accepted the final implementation after review. M7-3 is recorded with its frontend-only contract, final verification and owner acceptance below.

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

Status: Complete (2026-10-22). Outcome: a player sees what the legal candidate actually equips, which modeled facts support it, and what remains unproven, including in deterministic-only output.

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

Verification completed: 368 workflow/affected-web tests passed with one existing FastAPI TestClient deprecation warning. The fixture-backed real production smoke passed with three degraded recommendations, final legality and SSE contracts; the offline Chromium harness confirmed the rendered production evidence and degraded banner. A result produced by that smoke was visually inspected at 1440x1200 and 390x844 using the application's inline responsive CSS. The inspection page omitted CDN Pico assets and used a local variable shim, so it establishes result-copy readability and responsive layout only; CDN styling, keyboard usability and H2 gameplay were not assessed.

Entry/dependency: Stage 1 complete; no dependency on a new M6 positive. Excludes curation, scorer/ranking/search changes, battle validation, new mechanics and paid runs. Commit boundary: complete evidence projection, rendering, regressions and affected docs together.

### M7-2: Make Failures Understandable And Recoverable

Status: Complete; implemented and verified on 2026-10-22. Outcome: the user knows what failed, what action can help and whether the request has finished, while keeping selected ownership.

Before M7-2: `ProductionRequestError` supplied safe issue codes/fields/messages through `pipeline_error_payload`; format output had error classes. `app.js` substituted a generic retry label and silently closed some failures. POST errors reported status only; missing/reused jobs returned HTTP 404; render failures could end without a result. Empty-state copy referred to a nonexistent Grasta list and could equate unavailable evidence with an unsuitable roster.

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

Verification result (2026-10-22): 13 actual-script Node cases passed, including all existing typed issue codes, POST 422/404/5xx/network failures, missing and unavailable stream connections, stale selections, malformed/unavailable storage, terminal cleanup, no-result, render failure, and explicit fresh-job retry. All 45 web-unit tests passed with one existing Starlette/httpx deprecation warning. Offline Chromium passed both workflow success paths plus invalid POST, no-result, simulated disconnect, focused alert guidance, keyboard-reachable stale-selection removal, and explicit unique-job retries. The fixture-backed production smoke returned three degraded candidates that passed final legality and SSE checks. The browser used only a temporary HTML page and fixture graph; no Neo4j service, paid provider, live graph claim, or gameplay result was involved.

Entry/dependency: M7-1 output compatibility settled. Excludes backend request/schema redesign, graph repair, provider changes, job persistence/multiworker support and quota work. Commit boundary: complete error presentation and terminal lifecycle with regressions/docs together.

### M7-3: Guide Roster Selection And The Portfolio Demo

Status: Complete on 2026-11-06; final styled interface and Milestone 7 accepted by the owner. Outcome: someone unfamiliar with the mechanics can quickly identify the boss workflow, select a roster, run the bounded demo, visually understand a four-frontline/two-reserve candidate, and inspect its skills, explanations, evidence and limitations. Graph Q&A remains a distinct workflow.

Current base: Jinja templates and result partials render the page; `src/web/static/app.js` owns roster search/selection, localStorage, mode submission and SSE updates. The page uses inline CSS and the existing Pico CDN dependency. Existing M7-3 work adds novice guidance, selected-form feedback, F2P/default and evidence explanations, and an opt-in sample roster. Preserve that work while revising its information hierarchy and interactions. No frontend framework rewrite is in scope.

Required changes and reuse:

- Reorganize the existing Jinja page and partials into a clear recommendation workspace without changing the frontend framework. Keep native controls and the current request, API, job and SSE contracts. Use existing candidate, placement, skill, warning, source and limitation data; do not add candidate generation, ranking, legality, evidence or recommendation logic.
- Make the two supported workflows visibly distinct: “Boss recommendations” and “Graph Q&A” each receive their own heading, short explanation, input/action area and result context. Switching modes continues to use the existing mode and payload behavior; do not merge their result semantics.
- Put boss identity/selection first, followed by a searchable visual roster, selected-form feedback and the primary recommendation action. Collapse introductory instructions by default. On a 1440x900 desktop view and a 390x844 mobile view, the initial viewport must expose the boss choice, roster search, selected count and an immediately reachable primary action without first scrolling through instructional copy. Keep the roster usable by keyboard and avoid a trapped nested-scroll region.
- Use a compact visual character grid/list with clear selected states, names and the existing ownership controls. Keep the complete supported roster searchable and the explicit sample action. Preserve localStorage and sample semantics; do not silently replace saved ownership or auto-submit. Use neutral local placeholders until individual image assets pass the separate rights and identity gate below.
- Present each candidate as a visual formation: four clearly distinguished frontline positions and a separate two-position reserve row. Show exact validated placements and equipped skills from the final candidate. Put concise useful explanations, source-backed evidence and contextual limitations/warnings ahead of raw scorer labels and technical diagnostics. Do not translate incomplete evidence into a claim of strategic success.
- Keep technical details available in a collapsed disclosure. This includes raw scorer/fit labels, counters, source identifiers and operational diagnostics. Keep user-relevant caveats and warnings visible in the normal result view, grouped by candidate or topic rather than repeated without context. Use readable language for ordinary labels while retaining exact underlying values in the expanded detail.
- Style the existing page consistently for desktop and mobile. At 390 CSS pixels, controls, formation cards, skills, warnings and evidence must reflow without horizontal page overflow. Do not rely on an offline harness that removes the page styles to establish visual acceptance.
- Preserve existing form semantics, sample handling, request lifecycle, recovery, candidate ordering and legal result data. Keep automatic F2P additions, optional sidekick ownership, no declared SA/Light/Shadow and item-policy assumptions clear but concise in a collapsed guidance panel near the form. Do not call a roster under six selected characters invalid solely on count: backend F2P augmentation still applies; existing production input requires at least one user roster entry.
- Add an explicit “Use sample roster” action for the twenty normal-form Mushroom demo, reusing the canonical names above and current ownership controls. Intersect with loaded entity names, report any missing forms, and require user action before replacing saved selections. Declare no owned sidekicks/SA/high Light/Shadow; show the existing item-policy assumption. Do not auto-submit or claim the sample is H2 accepted. No separate sample API or runtime dependency on test fixtures.
- Keep Mushroom as the only selectable production boss; explain Rotte's diagnostic-only evidence limit. Preserve full catalog selection and exploratory mode. Keep all prior M7-3 novice and evidence guidance, but make secondary instructions collapsible and avoid repeating the same warning in multiple places.

Image rights are a separate research gate, not a prerequisite for the first redesign iteration. The wiki's stated CC BY-SA 4.0 license is not proof that every hosted image is licensed by an authorized rights holder. Before integrating any image, verify that individual file's page/source, creator or rights basis, applicable license, exact character/boss identity and form, and required attribution/change notice. Keep a small local manifest only for individually cleared assets; do not hotlink, bulk scrape or download during this redesign. Use the neutral placeholder whenever identity or rights remain unresolved. See the [CC BY-SA 4.0 terms](https://creativecommons.org/licenses/by-sa/4.0/) for attribution and ShareAlike conditions.

Current read-only inventory: the local 367-form catalog and schema include wiki detail-page URLs but no portrait/image field. The twenty sample entries match normal-form catalog names; their detail URLs establish article targets only, not image identity or rights. A captured Celestial Mushroom article references `File:350209901.png` (PNG, 484x498, with thumbnail URLs) in [the local source capture](../../src/etl/superboss_corpus/celestial-mushroom.html), but the individual file page's authorship, license and identity have not been verified. The wiki file pages were not accessible to the current web lookup, and no media was fetched. Therefore the first redesign iteration uses placeholders; a separate one-file-at-a-time review must clear each proposed asset before any later integration.

A static frontend manifest can support later cleared images without changing ETL: map each canonical character form or boss to a local asset and record its exact source/file page, identity, creator or rights basis, license, attribution, modifications, file format/dimensions and checksum. Serve cleared files locally rather than hotlinking; retain license/attribution alongside the assets and account for caching when replacing a reviewed file. This is a feasibility recommendation only; no manifest or image assets are added in this amendment.

Proposed page/component structure for owner review:

1. **Page shell (`index.html`):** compact title/status area; an accessible two-option mode switch for “Boss recommendations” and “Graph Q&A”; a collapsed “How this demo works” disclosure. The active mode gets its own heading and short description.
2. **Recommendation workspace:** a boss identity/selector panel first, then the existing character/sidekick roster tabs with a search field, selected-count/status, explicit sample action and selected checkbox tiles. Keep all catalog entries searchable and let the page scroll through the roster rather than trapping it in a small nested scroll box. Put optional preferences and detailed F2P/item assumptions in a nearby collapsed disclosure.
3. **Primary action:** keep the existing recommendation submit action with its current payload. Place it directly beside the selection controls on desktop and in a safe-area-aware sticky action strip on narrow screens so it stays reachable while the roster scrolls.
4. **Graph Q&A workspace:** a separate query field, “Ask the graph” action and result heading/context. Keep both modes within the existing submission/SSE lifecycle and preserve their current mode-specific payload and rendering semantics.
5. **Result stage:** reuse the existing progress, error, empty and result partials. Announce completion/status accessibly and focus the result heading when needed. Show a compact result status and contextual warnings before candidate details.
6. **Candidate cards:** show each candidate's label and a visual formation with four frontline positions and a separate two-reserve row. Expand a candidate to see its exact member skills and concise explanation. Keep the first candidate open by default; additional candidates retain their formation at a glance and open on keyboard activation.
7. **Evidence and diagnostics:** show useful final-candidate explanations, source links, relevant warnings and known limitations with the team. Place raw fit/scorer labels, counters, source IDs and other engineering diagnostics in a separate closed `<details>` disclosure. Preserve the existing evidence values and meanings.
8. **Image fallback:** use a locally styled neutral placeholder/initial tile for every character and boss in this iteration. A future manifest may supply an image only after that individual file's identity and reuse rights are cleared.

Execution after owner approval is one M7-3 feature route, `builder-executor -> tdd-loop`, with no intermediate commit: (1) restructure the shell, mode workspaces, boss/roster selection and reachable action while preserving local state and request behavior; (2) restyle result/candidate/evidence partials into the 4+2 formation and put useful explanations ahead of collapsed diagnostics; (3) adapt capability/browser regressions, verify unchanged API/SSE and candidate data, then complete the styled desktop/mobile and keyboard/accessibility walkthrough. The separate image-rights research produces a per-asset allow/placeholder decision before any later asset integration; it does not block the placeholder-based redesign.

Acceptance:

- **M7-3-01:** Boss recommendations and Graph Q&A are visibly separate workflows with their own labels, explanations, actions and result context. Each still sends the existing mode/payload and displays its existing result type.
- **M7-3-02:** Explicit sample selection sets the supported canonical forms and declared defaults, preserves existing selections until the action, handles unavailable entities honestly and does not expand curated eligibility. A normal reload restores supported saved ownership.
- **M7-3-03:** The boss choice, roster search, selected count and primary action are apparent in the first viewport at 1440x900 and 390x844; introductory instructions are collapsed by default. Search, selection, sample use and submission remain operable without an inaccessible nested roster scroll area.
- **M7-3-04:** Every candidate card presents four distinct validated frontline positions and two distinct validated reserves at a glance. Opening any candidate shows its exact equipped skills and useful evidence-backed explanation before technical diagnostics. Relevant warnings and limitations remain visible. No presentation label or explanation implies a win, strategic pass or completeness unsupported by the existing candidate/evidence contracts.
- **M7-3-05:** Raw scorer labels and technical diagnostics are available only in a collapsed detail area by default; no user-relevant warning, evidence limitation or source-backed explanation is hidden there. Warnings appear once at the scope supplied by the current result, preserving candidate context and source; no warning is removed based on inference.
- **M7-3-06:** F2P augmentation, form identity, item/upgrade assumptions and legal-versus-battle-verified distinction remain understandable. Rotte is not promoted to selectable/equally validated support. Sample selection preserves its current ownership, missing-form, default and no-auto-submit semantics.
- **M7-3-07:** The styled 1440x900 desktop and 390x844 mobile views have no horizontal page overflow and keep selection, results, skills, evidence and warnings readable. A real keyboard-only journey covers mode selection, boss selection, roster search/select/sample, submission, result details and recovery; focus remains visible and logical, control names/states are exposed, and success/error outcomes are announced or focused accessibly. Inspect the browser accessibility tree and perform a screen-reader spot check where available; offline DOM-only checks do not satisfy this criterion.
- **M7-3-08:** No image is integrated unless its identity and per-file reuse rights are verified and its required attribution is recorded. Unverified character/boss art uses a local neutral placeholder. No bulk scraping or remote hotlinking is introduced.
- **M7-3-09:** Existing sample, storage, API/SSE, candidate ordering, final legality, evidence, warning and recovery behavior remain unchanged. Automated checks and the styled manual walkthrough confirm the frontend-only boundary; M6/H2 and M8 gates stay open.

Verification after implementation: retain and adapt the existing actual-script, web-unit and fixture-backed production smoke coverage for sample/storage/mode/API/SSE/result/recovery behavior. Add browser coverage for the distinct modes, candidate formation/skills/evidence/diagnostic disclosures, accessible names/states and responsive overflow. Then inspect the actual styled fixture-backed page at 1440x900 and 390x844. Manually complete the keyboard-only journey in acceptance M7-3-07, review focus and announcements, inspect the accessibility tree, and spot-check with a screen reader where available. The offline DOM harness alone cannot establish visual or keyboard acceptance. No Neo4j service, paid model, provider change or live gameplay trial is required for this frontend work.

Final verification on 2026-11-06: `PYTHON_DOTENV_DISABLED=1 timeout 120s .venv/bin/pytest tests/web -q --tb=short` passed all 47 tests (one existing Starlette/httpx deprecation warning). Fixture-backed production smoke returned three deterministic-only recommendations that passed final legality and SSE checks. JavaScript syntax checks, Python compilation and `git diff --check` passed. Styled Chromium checks at 1440x900 and 390x844 found no horizontal overflow (document widths 1440/1440 and 390/390) and verified the boss, search, selected count and primary action in the initial viewport. A 45-pair text contrast audit measured a minimum ratio of 5.01:1; the disabled primary action measured 7.66:1. Keyboard input exercised mode switching, boss and roster selection, sample application, submission, disclosures and error recovery; accessibility-tree checks verified control names and states. The owner approved the final styled UI and keyboard journey on 2026-11-06. A separate screen-reader spot-check was not recorded. Temporary screenshots were generated under `/tmp/anothereden-m7-3-quality-screenshots`; they are not durable release artifacts.

Entry/dependency: M7-1 supplies candidate explanations and evidence limits; M7-2 supplies actionable errors and request recovery. The approved redesign followed the `builder-executor -> tdd-loop` route in the existing Jinja/CSS/JavaScript frontend; no external UI generator or framework rewrite was needed. Scope excluded backend/API/schema/graph/ETL changes, recommendation or ranking changes, new bosses/forms, expanded SA/Light/Shadow/item editors, chat, accounts, dashboards, deployment and paid LLM integration. Analyzer/provider qualification remains separate. The M7-3 feature commit contains the accepted frontend implementation, retained regression coverage and milestone update. M6/H2 and M8 obligations remain unchanged.

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

M7-3 changes frontend guidance, selection presentation, page structure and client-side sample selection only. Candidate generation, ranking, validation, request payloads, schemas, source/review identities, graph data, analyzer/provider behavior and provider settings remain unchanged. No OpenRouter or other paid provider is added or qualified by this UX amendment.
