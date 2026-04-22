"""Chat services: state hydration, greeting, market cards, background tasks."""
from backend.services.chat.background import generate_session_title, update_coach_memo
from backend.services.chat.greeting import build_greeting
from backend.services.chat.market_cards import extract_market_cards, get_card_for_node
from backend.services.chat.state import hydrate_state

__all__ = [
    "build_greeting",
    "extract_market_cards",
    "generate_session_title",
    "get_card_for_node",
    "hydrate_state",
    "update_coach_memo",
]
