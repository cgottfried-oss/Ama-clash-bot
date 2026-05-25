from __future__ import annotations


class EventBus:
    def __init__(self):
        self._listeners = {}

    def subscribe(self, event_name: str, callback):
        self._listeners.setdefault(event_name, [])
        self._listeners[event_name].append(callback)

    async def emit(self, event_name: str, payload: dict | None = None):
        listeners = self._listeners.get(event_name, [])

        for callback in listeners:
            await callback(payload or {})


# Global singleton for MMO systems.
event_bus = EventBus()
