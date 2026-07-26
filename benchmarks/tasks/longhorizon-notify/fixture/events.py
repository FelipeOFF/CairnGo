"""A minimal synchronous event bus."""


class EventBus:
    def __init__(self):
        self._handlers = {}

    def subscribe(self, event_type, handler):
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event_type, payload):
        for handler in self._handlers.get(event_type, []):
            handler(payload)
