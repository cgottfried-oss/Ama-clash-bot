from __future__ import annotations

import random
import time
import uuid

from clash_mmo.game.ai_events.templates import EVENT_TEMPLATES


def generate_ai_event(now: int | None = None, template_id: str | None = None) -> dict:
    now = int(now or time.time())
    templates = EVENT_TEMPLATES
    if template_id:
        matching = [template for template in templates if template.get("id") == template_id]
        if matching:
            templates = matching
    template = dict(random.choice(templates))
    duration = int(template.get("duration_minutes", 60) or 60) * 60
    template["event_id"] = f"event-{uuid.uuid4().hex[:10]}"
    template["created_at"] = now
    template["starts_at"] = now
    template["ends_at"] = now + duration
    template["status"] = "active"
    return template
