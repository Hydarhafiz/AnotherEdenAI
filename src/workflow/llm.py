"""LLM provider abstraction for AnotherEdenAI workflow.

Controls which LLM backend is used by role:
    GENERATE_CYPHER and VALIDATE are pinned to Claude/Anthropic for syntax reliability.
    PLAN and ANALYZE can route through Kimi via LLM_REASONING_PROVIDER or LLM_AB_BUCKET.
    LLM_PROVIDER=anthropic   (default) -> ChatAnthropic (Sonnet or Haiku by role)
    LLM_PROVIDER=openrouter            -> ChatOpenAI via OpenRouter proxy (Sonnet or Haiku by role)
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

# Anthropic / OpenRouter model IDs
_SONNET = "claude-sonnet-4-6"
_HAIKU = "claude-haiku-4-6-20251001"

# OpenRouter model IDs (anthropic models served via proxy)
_OR_SONNET = "nvidia/nemotron-3-super-120b-a12b:free"
_OR_HAIKU = "nvidia/nemotron-3-super-120b-a12b:free"

# Moonshot/Kimi OpenAI-compatible API
_KIMI = os.getenv("KIMI_MODEL", "kimi-k2-0905-preview")

# AWS Bedrock model IDs
_BEDROCK_SONNET = "anthropic.claude-3-5-sonnet-20241022-v2:0"
_BEDROCK_HAIKU = "anthropic.claude-3-5-haiku-20241022-v1:0"


def _provider_for_role(role: str) -> str:
    """Resolve provider with strict Claude routing for syntax-sensitive roles."""
    normalized = role.lower()
    if normalized in {"cypher", "validator"}:
        return "anthropic"
    if normalized in {"planner", "analyzer", "plan", "analyze"}:
        ab_bucket = os.getenv("LLM_AB_BUCKET", "").lower()
        if ab_bucket in {"kimi", "moonshot"}:
            return "kimi"
        return os.getenv("LLM_REASONING_PROVIDER", os.getenv("LLM_PROVIDER", "anthropic")).lower()
    return os.getenv("LLM_PROVIDER", "anthropic").lower()


def get_llm(role: str = "default") -> BaseChatModel:
    """Return a BaseChatModel based on LLM_PROVIDER env var.

    LLM_PROVIDER=anthropic   (default) -> ChatAnthropic (Sonnet or Haiku by role)
    LLM_PROVIDER=openrouter            -> ChatOpenAI via OpenRouter proxy
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
        model = _OR_HAIKU if role == "validator" else _OR_SONNET
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
