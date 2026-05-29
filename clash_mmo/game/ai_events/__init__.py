from __future__ import annotations

from clash_mmo.game.ai_events.effects import apply_event_effects
from clash_mmo.game.ai_events.formatting import format_event_embed, format_event_summary
from clash_mmo.game.ai_events.generator import generate_ai_event
from clash_mmo.game.ai_events.modifiers import get_active_event_modifiers
from clash_mmo.game.ai_events.scheduler import schedule_next_event
from clash_mmo.game.ai_events.service import ensure_event_state, get_active_events, resolve_event
from clash_mmo.game.ai_events.targets import get_event_target_pool
from clash_mmo.game.ai_events.templates import EVENT_TEMPLATES

__all__ = [
    "EVENT_TEMPLATES",
    "apply_event_effects",
    "ensure_event_state",
    "format_event_embed",
    "format_event_summary",
    "generate_ai_event",
    "get_active_event_modifiers",
    "get_active_events",
    "get_event_target_pool",
    "resolve_event",
    "schedule_next_event",
]
