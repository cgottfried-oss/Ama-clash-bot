from __future__ import annotations



def format_event_card(event: dict):
    modifier = event["modifier"]

    return (
        f"🌍 {event['title']}\n"
        f"{event['description']}\n\n"
        f"🎯 Target: {event['target']}\n"
        f"⚡ Modifier: {modifier['name']}"
    )



def format_event_list(events: list[dict]):
    return "\n\n".join([
        format_event_card(event)
        for event in events
    ])
