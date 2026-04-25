---
phase: 5
slug: integration-polish-and-portfolio-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-25
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23 |
| **Config file** | `pytest.ini` (root) |
| **Quick run command** | `pytest -m 'not integration' --tb=short -q` |
| **Full suite command** | `pytest --tb=short` |
| **Estimated runtime** | ~60 seconds (unit), ~3-5 minutes (full with integration) |

---

## Sampling Rate

- **After every task commit:** Run `pytest -m 'not integration' --tb=short -q`
- **After every plan wave:** Run `pytest --tb=short` (requires AuraDB Free `.env`)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds (unit), 5 minutes (integration)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 1 | OUTPUT-02/03 | — | N/A | unit | `pytest tests/workflow/test_format.py -x` | ✅ | ⬜ pending |
| 5-01-02 | 01 | 1 | OUTPUT-04 | T-5-01 | AlternativesOutput validates 3 comps | unit | `pytest tests/workflow/test_format.py -x` | ✅ W0 | ⬜ pending |
| 5-01-03 | 01 | 1 | OUTPUT-04 | — | N/A | integration | `pytest tests/integration/test_e2e_phase5.py::test_empty_result_returns_alternatives -x -m integration` | ❌ W0 | ⬜ pending |
| 5-01-04 | 01 | 1 | OUTPUT-05 | — | N/A | unit | `pytest tests/web/unit/test_streaming.py -x` | ✅ | ⬜ pending |
| 5-02-01 | 02 | 2 | OUTPUT-02/03 | — | N/A | integration | `pytest tests/integration/test_e2e_phase5.py::test_happy_path_has_attribution -x -m integration` | ❌ W0 | ⬜ pending |
| 5-02-02 | 02 | 2 | OUTPUT-04 | — | N/A | integration | `pytest tests/integration/test_e2e_phase5.py::test_empty_result_returns_alternatives -x -m integration` | ❌ W0 | ⬜ pending |
| 5-02-03 | 02 | 2 | QUERY-04 | — | N/A | integration | `pytest tests/integration/test_e2e_phase5.py::test_name_normalization -x -m integration` | ❌ W0 | ⬜ pending |
| 5-02-04 | 02 | 2 | AGENT-05 | — | N/A | integration | `pytest tests/integration/test_e2e_phase5.py::test_retry_cap_exhaustion -x -m integration` | ❌ W0 | ⬜ pending |
| 5-02-05 | 02 | 2 | WEB-05 | T-5-02 | Admin endpoint requires ADMIN_KEY | integration | `pytest tests/integration/test_e2e_phase5.py::test_admin_refresh -x -m integration` | ❌ W0 | ⬜ pending |
| 5-03-01 | 03 | 2 | OUTPUT-01–05 | — | N/A | manual | README cold-clone walkthrough | ❌ W0 | ⬜ pending |
| 5-04-01 | 04 | 3 | DEPLOY-01 | T-5-03 | Secrets never in Docker image | manual/CI | CI pipeline run | ❌ W0 | ⬜ pending |
| 5-04-02 | 04 | 3 | DEPLOY-02/03 | T-5-04 | HTTPS, no plaintext secrets | manual | `curl https://<ecs-url>/health` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/integration/test_e2e_phase5.py` — stubs for OUTPUT-02, OUTPUT-03, OUTPUT-04, and all 5 D-07 scenarios
- [ ] `src/web/routes/health.py` or inline in `pages.py` — `GET /health` returns `{"status": "ok"}` for DEPLOY-03 health checks
- [ ] `src/web/templates/partials/alternatives.html` — stub for OUTPUT-04 UI accordion rendering
- [ ] `Dockerfile` — required before 05-04 can be tested in CI
- [ ] `.github/workflows/deploy.yml` — DEPLOY-01

*Existing test infrastructure covers OUTPUT-01 (test_format.py 26 tests) and OUTPUT-05 (test_streaming.py)*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Recruiter cold-clone path works end-to-end | OUTPUT-01–05 | Requires human judgment, fresh environment | Follow README from scratch on a clean machine/repo; verify pytest passes and browser shows result |
| Public URL accessible after CI/CD deploy | DEPLOY-02/03 | Requires live AWS infrastructure | Push to main → CI pipeline runs → curl public URL → expect 200 |
| Latency ≤ 15s under normal conditions | SC-5 | Requires real LLM + DB round trip | Submit query via browser, observe CloudWatch `latency_ms:` log line |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s (unit) / 5m (integration)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
