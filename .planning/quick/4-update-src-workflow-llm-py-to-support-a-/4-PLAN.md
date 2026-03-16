---
phase: quick-4
plan: 4
type: execute
wave: 1
depends_on: []
files_modified:
  - src/workflow/llm.py
  - .env.example
  - tests/workflow/test_llm.py
autonomous: true
requirements: []

must_haves:
  truths:
    - "LLM_PROVIDER=openrouter returns ChatOpenAI configured with OpenRouter base_url and anthropic/claude-3.5-sonnet"
    - "LLM_PROVIDER=openrouter with role=validator returns ChatOpenAI configured with anthropic/claude-haiku-3 (or haiku model)"
    - "LLM_PROVIDER=bedrock returns ChatBedrockConverse"
    - "LLM_PROVIDER=ollama returns ChatOllama at localhost:11434"
    - "LLM_PROVIDER=anthropic (legacy default) still returns ChatAnthropic for backward compatibility"
    - "All workflow nodes that call get_llm() continue to work unchanged"
    - "OPENROUTER_API_KEY documented in .env.example"
  artifacts:
    - path: "src/workflow/llm.py"
      provides: "3-way provider factory via get_llm(role)"
      exports: ["get_llm"]
    - path: ".env.example"
      provides: "OPENROUTER_API_KEY documentation"
      contains: "OPENROUTER_API_KEY"
    - path: "tests/workflow/test_llm.py"
      provides: "Unit tests for all three new providers"
      contains: "test_openrouter"
  key_links:
    - from: "src/workflow/llm.py"
      to: "langchain_openai.ChatOpenAI"
      via: "LLM_PROVIDER=openrouter branch"
      pattern: "ChatOpenAI.*base_url.*openrouter"
    - from: "src/workflow/llm.py"
      to: "langchain_aws.ChatBedrockConverse"
      via: "LLM_PROVIDER=bedrock branch"
      pattern: "ChatBedrockConverse"
    - from: "tests/workflow/test_llm.py"
      to: "src/workflow/llm.get_llm"
      via: "monkeypatch.setenv + direct import"
      pattern: "monkeypatch.setenv.*LLM_PROVIDER"
---

<objective>
Extend the LLM provider factory in src/workflow/llm.py to support three providers — openrouter, bedrock, and ollama — with the existing anthropic path retained for backward compatibility.

Purpose: Allows the graph to run against any of four LLM backends by changing a single env var, enabling cost-optimised development (openrouter) and air-gapped deployment (bedrock/ollama) with zero node-level changes.
Output: Updated llm.py, updated .env.example with OPENROUTER_API_KEY, and a new test_llm.py covering all provider branches.
</objective>

<execution_context>
@/home/shogunix/.claude/get-shit-done/workflows/execute-plan.md
@/home/shogunix/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/workflow/llm.py
@.env.example
@tests/workflow/conftest.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add openrouter and bedrock branches to get_llm() factory</name>
  <files>src/workflow/llm.py, tests/workflow/test_llm.py</files>
  <behavior>
    - test_get_llm_openrouter_returns_chatopenai: monkeypatch LLM_PROVIDER=openrouter, call get_llm(), assert isinstance result ChatOpenAI, assert result.openai_api_base contains "openrouter.ai"
    - test_get_llm_openrouter_validator_role_uses_haiku: monkeypatch LLM_PROVIDER=openrouter, call get_llm(role="validator"), assert result.model_name contains "haiku"
    - test_get_llm_openrouter_default_role_uses_sonnet: monkeypatch LLM_PROVIDER=openrouter, call get_llm(role="planner"), assert result.model_name contains "sonnet" or "claude-3.5"
    - test_get_llm_bedrock_returns_chatbedrockconverse: monkeypatch LLM_PROVIDER=bedrock, call get_llm(), assert isinstance result ChatBedrockConverse
    - test_get_llm_ollama_returns_chatollama: monkeypatch LLM_PROVIDER=ollama, call get_llm(), assert isinstance result ChatOllama
    - test_get_llm_anthropic_returns_chatanthropic: monkeypatch LLM_PROVIDER=anthropic, call get_llm(), assert isinstance result ChatAnthropic (backward compat)
    - test_get_llm_default_provider_is_anthropic: unset LLM_PROVIDER (monkeypatch.delenv with raising=False), call get_llm(), assert isinstance result ChatAnthropic
  </behavior>
  <action>
Write tests first in tests/workflow/test_llm.py, then update src/workflow/llm.py to pass them.

**tests/workflow/test_llm.py** — use monkeypatch to set/unset LLM_PROVIDER and OPENROUTER_API_KEY env vars without touching real env. Import get_llm from src.workflow.llm. Use isinstance checks on the returned object. Import ChatOpenAI from langchain_openai, ChatBedrockConverse from langchain_aws, ChatOllama from langchain_ollama, ChatAnthropic from langchain_anthropic. Mock the actual provider constructors if needed to avoid network calls — patch each class at the src.workflow.llm import level: `patch("src.workflow.llm.ChatOpenAI")` etc. so no credentials are needed at test time.

**src/workflow/llm.py** — add two new provider branches between the existing ollama and anthropic branches:

```
openrouter:
  from langchain_openai import ChatOpenAI
  _OR_SONNET = "anthropic/claude-3.5-sonnet"
  _OR_HAIKU  = "anthropic/claude-haiku-3"
  model = _OR_HAIKU if role == "validator" else _OR_SONNET
  return ChatOpenAI(
      model=model,
      openai_api_base="https://openrouter.ai/api/v1",
      openai_api_key=os.getenv("OPENROUTER_API_KEY", ""),
  )

bedrock:
  from langchain_aws import ChatBedrockConverse
  _BEDROCK_SONNET = "anthropic.claude-3-5-sonnet-20241022-v2:0"
  _BEDROCK_HAIKU  = "anthropic.claude-3-5-haiku-20241022-v1:0"
  model = _BEDROCK_HAIKU if role == "validator" else _BEDROCK_SONNET
  return ChatBedrockConverse(model=model)
```

Keep the existing ollama and anthropic branches unchanged. Default provider remains "anthropic" for backward compatibility. Update the module docstring to document the new openrouter and bedrock options.
  </action>
  <verify>
    <automated>cd /home/shogunix/AnotherEdenAI && python -m pytest tests/workflow/test_llm.py -v 2>&1 | tail -20</automated>
  </verify>
  <done>All test_llm.py tests pass. get_llm() correctly branches on LLM_PROVIDER for all four providers. Existing workflow node tests still pass (no regressions in tests/workflow/).</done>
</task>

<task type="auto">
  <name>Task 2: Update .env.example with OPENROUTER_API_KEY documentation</name>
  <files>.env.example</files>
  <action>
Add an openrouter section to .env.example documenting LLM_PROVIDER=openrouter and the required OPENROUTER_API_KEY. Update the existing LLM_PROVIDER comment block to list all four supported values. Final .env.example structure:

```
# LLM provider toggle (choose one):
#   anthropic   (default) — Uses Claude API; requires ANTHROPIC_API_KEY
#   openrouter            — Uses OpenRouter proxy; requires OPENROUTER_API_KEY
#   bedrock               — Uses AWS Bedrock; requires AWS credentials in env
#   ollama                — Uses local Ollama server; zero API cost
LLM_PROVIDER=anthropic

# Required when LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...

# Required when LLM_PROVIDER=openrouter
# OPENROUTER_API_KEY=sk-or-...

# Ollama model to use when LLM_PROVIDER=ollama (default: llama3.2)
OLLAMA_MODEL=llama3.2
```

Preserve the existing NEO4J_URI, NEO4J_AUTH, ETL_MODE lines unchanged at the top of the file.
  </action>
  <verify>grep -c "OPENROUTER_API_KEY" /home/shogunix/AnotherEdenAI/.env.example</verify>
  <done>.env.example contains OPENROUTER_API_KEY comment and LLM_PROVIDER comment block lists all four providers (anthropic, openrouter, bedrock, ollama).</done>
</task>

</tasks>

<verification>
Run full workflow test suite to confirm no regressions:

```bash
cd /home/shogunix/AnotherEdenAI && python -m pytest tests/workflow/ -v 2>&1 | tail -30
```

Expected: all pre-existing tests still pass, new test_llm.py tests pass.
</verification>

<success_criteria>
- tests/workflow/test_llm.py exists with at least 7 tests covering all provider branches
- All tests pass: python -m pytest tests/workflow/ -v exits 0
- src/workflow/llm.py handles LLM_PROVIDER in {openrouter, bedrock, ollama, anthropic}
- openrouter branch uses ChatOpenAI with openrouter.ai base_url and OPENROUTER_API_KEY
- bedrock branch uses ChatBedrockConverse
- .env.example documents OPENROUTER_API_KEY
- No existing workflow node (plan, cypher, validate, analyze, format) requires changes
</success_criteria>

<output>
After completion, create `.planning/quick/4-update-src-workflow-llm-py-to-support-a-/4-SUMMARY.md`
</output>
