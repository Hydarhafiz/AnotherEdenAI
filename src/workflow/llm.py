"""LLM provider abstraction for AnotherEdenAI workflow.

Controls which LLM backend is used by role:
    LLM_PROVIDER=openrouter  (default) -> ChatOpenAI via OpenRouter proxy
    LLM_PROVIDER=anthropic             -> ChatAnthropic (Sonnet or Haiku by role)
    LLM_PROVIDER=bedrock               -> ChatBedrockConverse (Sonnet or Haiku by role)
    LLM_PROVIDER=ollama                -> ChatOllama (local, zero API cost)

All workflow nodes call get_llm(role=...) — no node imports a provider directly.
"""
import os

from langchain_anthropic import ChatAnthropic
from langchain_aws import ChatBedrockConverse
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

# Anthropic model IDs
_SONNET = "claude-sonnet-4-6"
_HAIKU = "claude-haiku-4-6-20251001"

# OpenRouter model IDs. Use one model for all roles by default, with an optional
# cheaper/faster validator override.
_OR_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
_OR_VALIDATOR_MODEL = os.getenv("OPENROUTER_VALIDATOR_MODEL", _OR_MODEL)

# Moonshot/Kimi OpenAI-compatible API
_KIMI = os.getenv("KIMI_MODEL", "kimi-k2-0905-preview")

# AWS Bedrock model IDs
_BEDROCK_SONNET = "anthropic.claude-3-5-sonnet-20241022-v2:0"
_BEDROCK_HAIKU = "anthropic.claude-3-5-haiku-20241022-v1:0"


def _provider_for_role(role: str) -> str:
    """Resolve the configured provider for every workflow role."""
    return os.getenv("LLM_PROVIDER", "openrouter").lower()


def get_llm(role: str = "default") -> BaseChatModel:
    """Return a BaseChatModel based on LLM_PROVIDER env var.

    LLM_PROVIDER=openrouter  (default) -> ChatOpenAI via OpenRouter proxy
    LLM_PROVIDER=anthropic             -> ChatAnthropic (Sonnet or Haiku by role)
    LLM_PROVIDER=bedrock               -> ChatBedrockConverse
    LLM_PROVIDER=ollama                -> ChatOllama (local, zero API cost)

    Args:
        role: Node role hint. "validator" uses Haiku (cheaper); all others use Sonnet.

    Returns:
        A configured BaseChatModel instance.
    """
    provider = _provider_for_role(role)

    if provider in {"kimi", "moonshot"}:
        return ChatOpenAI(
            model=_KIMI,
            openai_api_base=os.getenv("MOONSHOT_API_BASE", "https://api.moonshot.ai/v1"),
            openai_api_key=os.getenv("MOONSHOT_API_KEY", ""),
            request_timeout=90,
        )

    if provider == "openrouter":
        model = _OR_VALIDATOR_MODEL if role == "validator" else _OR_MODEL
        return ChatOpenAI(
            model=model,
            openai_api_base="https://openrouter.ai/api/v1",
            openai_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            request_timeout=90,
        )

    if provider == "bedrock":
        model = _BEDROCK_HAIKU if role == "validator" else _BEDROCK_SONNET
        return ChatBedrockConverse(model=model)

    if provider == "ollama":
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        return ChatOllama(model=model)

    # Default: anthropic
    model = _HAIKU if role == "validator" else _SONNET
    return ChatAnthropic(model=model)
