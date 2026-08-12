Implement the order-notification pipeline across `notifications.py` and `app.py`:

1. In `notifications.py`, implement `NotificationLog` with:
   - `self.entries` starting as an empty list
   - `record_notification(log)` — a function that returns a handler callable;
     calling that handler with a payload dict appends the payload to `log.entries`
   - `NotificationLog.summary()` returning a dict `{"count": <len(entries)>}`

2. In `app.py`, implement `setup(bus, log)` so that a handler built from
   `record_notification(log)` is subscribed to both the `"order_placed"` and
   `"order_shipped"` event types on `bus` (an `EventBus` from `events.py`).
   Other event types must not be logged.

See `tests/test_pipeline.py` for the exact expected behavior.
