from __future__ import annotations



def apply_event_effect(state: dict, event: dict):
    state.setdefault("modifiers", [])
    state["modifiers"].append(event)

    return state



def resolve_event_effect(event: dict):
    event["active"] = False
    return event
