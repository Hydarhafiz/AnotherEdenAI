"""Unit tests for the LLM provider factory (src/workflow/llm.py).

All providers are exercised via monkeypatched LLM_PROVIDER env var.
The actual provider constructors are mocked at the src.workflow.llm module level
so no API credentials or network calls are required.

Strategy: patch the module-level names (e.g. src.workflow.llm.ChatOpenAI) after
reloading the module with the desired LLM_PROVIDER env var, then call get_llm()
within the patch context.
"""
import importlib
from unittest.mock import MagicMock, patch

import pytest

import src.workflow.llm as llm_module


def _reload_with_provider(monkeypatch, provider):
    """Set LLM_PROVIDER and reload src.workflow.llm so the module-level import
    order doesn't interfere.  Returns the freshly-loaded module."""
    if provider is None:
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
    else:
        monkeypatch.setenv("LLM_PROVIDER", provider)
    importlib.reload(llm_module)
    return llm_module


# ---------------------------------------------------------------------------
# OpenRouter tests
# ---------------------------------------------------------------------------

class TestOpenRouter:
    def test_get_llm_openrouter_returns_chatopenai(self, monkeypatch):
        mod = _reload_with_provider(monkeypatch, "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

        mock_instance = MagicMock()
        with patch.object(mod, "ChatOpenAI", return_value=mock_instance) as mock_cls:
            result = mod.get_llm(role="default")

        mock_cls.assert_called_once()
        assert result is mock_instance

    def test_get_llm_openrouter_default_role_uses_sonnet(self, monkeypatch):
        mod = _reload_with_provider(monkeypatch, "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

        captured_kwargs = {}

        def fake_chatopenai(**kwargs):
            captured_kwargs.update(kwargs)
            return MagicMock()

        with patch.object(mod, "ChatOpenAI", side_effect=fake_chatopenai):
            mod.get_llm(role="planner")

        model = captured_kwargs.get("model", "")
        assert "sonnet" in model or "claude-3.5" in model, (
            f"Expected sonnet/claude-3.5 model for planner role, got: {model}"
        )

    def test_get_llm_openrouter_validator_role_uses_haiku(self, monkeypatch):
        mod = _reload_with_provider(monkeypatch, "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

        captured_kwargs = {}

        def fake_chatopenai(**kwargs):
            captured_kwargs.update(kwargs)
            return MagicMock()

        with patch.object(mod, "ChatOpenAI", side_effect=fake_chatopenai):
            mod.get_llm(role="validator")

        model = captured_kwargs.get("model", "")
        assert "haiku" in model, (
            f"Expected haiku model for validator role, got: {model}"
        )

    def test_get_llm_openrouter_uses_openrouter_base_url(self, monkeypatch):
        mod = _reload_with_provider(monkeypatch, "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

        captured_kwargs = {}

        def fake_chatopenai(**kwargs):
            captured_kwargs.update(kwargs)
            return MagicMock()

        with patch.object(mod, "ChatOpenAI", side_effect=fake_chatopenai):
            mod.get_llm()

        base_url = captured_kwargs.get("openai_api_base", "")
        assert "openrouter.ai" in base_url, (
            f"Expected openrouter.ai in base_url, got: {base_url}"
        )


# ---------------------------------------------------------------------------
# Bedrock tests
# ---------------------------------------------------------------------------

class TestBedrock:
    def test_get_llm_bedrock_returns_chatbedrockconverse(self, monkeypatch):
        mod = _reload_with_provider(monkeypatch, "bedrock")

        mock_instance = MagicMock()
        with patch.object(mod, "ChatBedrockConverse", return_value=mock_instance) as mock_cls:
            result = mod.get_llm(role="default")

        mock_cls.assert_called_once()
        assert result is mock_instance


# ---------------------------------------------------------------------------
# Ollama tests
# ---------------------------------------------------------------------------

class TestOllama:
    def test_get_llm_ollama_returns_chatollama(self, monkeypatch):
        mod = _reload_with_provider(monkeypatch, "ollama")

        mock_instance = MagicMock()
        with patch.object(mod, "ChatOllama", return_value=mock_instance) as mock_cls:
            result = mod.get_llm(role="default")

        mock_cls.assert_called_once()
        assert result is mock_instance


# ---------------------------------------------------------------------------
# Anthropic / backward-compat tests
# ---------------------------------------------------------------------------

class TestAnthropic:
    def test_get_llm_anthropic_returns_chatanthropic(self, monkeypatch):
        mod = _reload_with_provider(monkeypatch, "anthropic")

        mock_instance = MagicMock()
        with patch.object(mod, "ChatAnthropic", return_value=mock_instance) as mock_cls:
            result = mod.get_llm(role="default")

        mock_cls.assert_called_once()
        assert result is mock_instance

    def test_get_llm_default_provider_is_anthropic(self, monkeypatch):
        mod = _reload_with_provider(monkeypatch, None)

        mock_instance = MagicMock()
        with patch.object(mod, "ChatAnthropic", return_value=mock_instance) as mock_cls:
            result = mod.get_llm()

        mock_cls.assert_called_once()
        assert result is mock_instance
