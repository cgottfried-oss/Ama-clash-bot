from __future__ import annotations

# Target-specific modifier keys applied to state when an event activates.
# Each target gets its own namespace in state["active_event_modifiers"] so
# multiple simultaneous events don't collide and resolve() can cleanly remove them.

TARGET_MODIFIER_MAP = {
    "territories": "territory_points_bonus",
    "marketplace": "market_tax_bonus",
    "raids": "raid_damage_bonus",
    "matchmaking": "matchmaking_rating_bonus",
    "seasonal_ladder": "season_xp_bonus",
}

# Fallback key when an unknown target is generated.
DEFAULT_MODIFIER_KEY = "reward_multiplier"


def apply_event_effect(state: dict, event: dict):
    """Write the event's modifier into the correct target namespace in state.

    Before this patch, apply_event_effect blindly appended every event to
    state["modifiers"] without using the target field, so the target was
    effectively ignored. Now the modifier is stored under its target-specific
    key so consumers (raid, marketplace, territory, etc.) can actually read it.
    """
    state.setdefault("modifiers", [])
    state["modifiers"].append(event)

    # Also write into the normalized active_event_modifiers bucket.
    active = state.setdefault("active_event_modifiers", {})

    target = str(event.get("target") or "").strip().lower()
    modifier = event.get("modifier") or {}
    effect_key = str(modifier.get("effect") or "").strip()
    value = modifier.get("value")

    # Resolve which state key this target actually affects.
    resolved_key = TARGET_MODIFIER_MAP.get(target, effect_key or DEFAULT_MODIFIER_KEY)

    if value is not None:
        # Additive stacking: multiple events on the same target accumulate.
        try:
            current = float(active.get(resolved_key, 0) or 0)
            active[resolved_key] = current + float(value)
        except (TypeError, ValueError):
            active[resolved_key] = value

    # Tag the event with the resolved key so resolve_event_effect can undo it.
    event["_resolved_modifier_key"] = resolved_key
    event["_resolved_modifier_value"] = value

    return state


def resolve_event_effect(event: dict):
    """Mark event inactive. The caller is responsible for cleaning up
    active_event_modifiers using _resolved_modifier_key if needed."""
    event["active"] = False
    return event
