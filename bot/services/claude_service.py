"""Backward-compatibility shim — re-exports from ai_service (OpenAI)."""
from bot.services.ai_service import chat_for_profile, generate_route, adjust_route, LANG_NAMES

__all__ = ["chat_for_profile", "generate_route", "adjust_route", "LANG_NAMES"]
