---
phase: quick-4
plan: 4
subsystem: workflow/llm
tags: [llm, provider, openrouter, bedrock, ollama, factory]
dependency_graph:
  requires: []
  provides: [openrouter-provider, bedrock-provider, four-provider-llm-factory]
  affects: [src/workflow/llm.py, all workflow nodes via get_llm()]
tech_stack:
  added: [langchain-aws>=1.4, langchain-openai>=1.1]
  patterns: [provider-factory-pattern, monkeypatch-module-attribute-testing]
key_files:
  created: [tests/workflow/test_llm.py]
  modified: [src/workflow/llm.py, .env.example, requirements.txt]
decisions:
  - "langchain-aws and langchain-openai added to requirements.txt — required for new provider branches"
  - "Module-level imports used for all four providers — enables patch.object() testing without reload complexity"
  - "OpenRouter uses ChatOpenAI with openai_api_base override — OpenRouter is OpenAI-compatible endpoint"
metrics:
  duration: "2m 46s"
  completed: "2026-03-16"
  tasks_completed: 2
  files_changed: 4
---

# Phase quick-4: Update LLM Factory to Support OpenRouter, Bedrock, and Ollama Providers Summary

**One-liner:** Extended `get_llm()` factory to support 4 LLM backends (openrouter via ChatOpenAI, bedrock via ChatBedrockConverse, ollama, anthropic) selected by `LLM_PROVIDER` env var with role-based model selection.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add openrouter and bedrock branches to get_llm() factory (TDD) | 935f84b | src/workflow/llm.py, tests/workflow/test_llm.py, requirements.txt |
| 2 | Update .env.example with OPENROUTER_API_KEY documentation | d8a300d | .env.example |

## What Was Built

### src/workflow/llm.py
Extended the provider factory from 2 providers (anthropic, ollama) to 4:
- `openrouter`: `ChatOpenAI` with `openai_api_base="https://openrouter.ai/api/v1"` and `OPENROUTER_API_KEY`. Uses `anthropic/claude-3.5-sonnet` for default roles, `anthropic/claude-haiku-3` for validator role.
- `bedrock`: `ChatBedrockConverse` with AWS Bedrock model IDs. Uses `anthropic.claude-3-5-sonnet-20241022-v2:0` for default, `anthropic.claude-3-5-haiku-20241022-v1:0` for validator.
- `ollama` and `anthropic` branches retained unchanged.
- All four provider classes moved to module-level imports to support `patch.object()` in tests.

### tests/workflow/test_llm.py (new)
8 unit tests covering all four provider branches using `monkeypatch` + `patch.object(mod, ...)`:
- `TestOpenRouter`: 4 tests (returns ChatOpenAI, sonnet for default role, haiku for validator, openrouter.ai base_url)
- `TestBedrock`: 1 test (returns ChatBedrockConverse)
- `TestOllama`: 1 test (returns ChatOllama)
- `TestAnthropic`: 2 tests (returns ChatAnthropic, default provider when LLM_PROVIDER unset)

### .env.example
Updated LLM_PROVIDER comment block to list all four options with descriptions. Added `OPENROUTER_API_KEY=sk-or-...` commented documentation.

## Verification

```
tests/workflow/ — 82 passed in 0.71s
```

All pre-existing 74 tests continue to pass. New 8 tests cover all provider branches.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] Installed missing langchain-aws and langchain-openai packages**
- **Found during:** Task 1 test collection
- **Issue:** `ModuleNotFoundError: No module named 'langchain_aws'` — packages not in requirements.txt or venv
- **Fix:** `pip install langchain-aws langchain-openai`, added both to requirements.txt
- **Files modified:** requirements.txt
- **Commit:** 935f84b

**2. [Rule 1 - Bug] Rewrote test strategy from importlib.reload inside patch to patch.object()**
- **Found during:** Task 1 RED phase — initial test approach used `patch("src.workflow.llm.ChatOpenAI")` string-based patching after reload, which failed because `src.workflow.__init__` imports through `graph.py` causing namespace issues
- **Fix:** Import the module once at test-module level, use `importlib.reload(llm_module)` before entering patch context, then use `patch.object(mod, "ChatOpenAI", ...)` on the reloaded module object
- **Files modified:** tests/workflow/test_llm.py
- **Commit:** 935f84b

## Self-Check: PASSED

| Item | Status |
|------|--------|
| tests/workflow/test_llm.py | FOUND |
| src/workflow/llm.py | FOUND |
| .env.example | FOUND |
| commit 935f84b | FOUND |
| commit d8a300d | FOUND |
