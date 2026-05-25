"""Phase 5-8 AI generated world event systems."""

from .templates import EVENT_TEMPLATES
from .targets import EVENT_TARGETS, pick_event_target
from .modifiers import EVENT_MODIFIERS, pick_event_modifier
from .generator import generate_world_event
from .scheduler import should_spawn_event, mark_event_spawned
from .effects import apply_event_effect, resolve_event_effect
from .service import create_ai_event, get_active_events, resolve_ai_event
from .formatting import format_event_card, format_event_list

__all__ = [
    "EVENT_TEMPLATES",
    "EVENT_TARGETS",
    "EVENT_MODIFIERS",
    "pick_event_target",
    "pick_event_modifier",
    "generate_world_event",
    "should_spawn_event",
    "mark_event_spawned",
    "apply_event_effect",
    "resolve_event_effect",
    "create_ai_event",
    "get_active_events",
    "resolve_ai_event",
    "format_event_card",
    "format_event_list",
]
