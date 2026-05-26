from __future__ import annotations

import random
import uuid

from .modifiers import pick_event_modifier
from .targets import pick_event_target
from .templates import EVENT_TEMPLATES



def generate_world_event():
    template = random.choice(EVENT_TEMPLATES)
    modifier = pick_event_modifier()
    target = pick_event_target()

    return {
        "event_id": str(uuid.uuid4()),
        "title": template["title"],
        "description": template["description"],
        "type": template["type"],
        "target": target,
        "modifier": modifier,
        "active": True,
    }