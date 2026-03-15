"""LLM provider abstraction for AnotherEdenAI workflow.

Controls which LLM backend is used via the LLM_PROVIDER environment variable:
    LLM_PROVIDER=ollama    -> ChatOllama (local, zero API cost)
    LLM_PROVIDER=anthropic -> ChatAnthropic (default, Sonnet or Haiku by role)

All workflow nodes call get_llm(role=...) — no node imports ChatAnthropic directly.
"""
import os

from langchain_core.language_models import BaseChatModel

_SONNET = "claude-sonnet-4-6"
_HAIKU = "claude-haiku-4-6-20251001"


def get_llm(role: str = "default") -> BaseChatModel:
    """Return a BaseChatModel based on LLM_PROVIDER env var.

    LLM_PROVIDER=ollama  -> ChatOllama (local, zero API cost)
    LLM_PROVIDER=anthropic (default) -> ChatAnthropic (Sonnet or Haiku by role)

    Args:
        role: Node role hint. "validator" uses Haiku (cheaper); all others use Sonnet.

    Returns:
        A configured BaseChatModel instance.
    """
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        return ChatOllama(model=model)
    # Default: anthropic
    from langchain_anthropic import ChatAnthropic

    model = _HAIKU if role == "validator" else _SONNET
    return ChatAnthropic(model=model)
