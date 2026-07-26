import unittest

from app import setup
from events import EventBus
from notifications import NotificationLog


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.bus = EventBus()
        self.log = NotificationLog()
        setup(self.bus, self.log)

    def test_relevant_events_are_logged(self):
        self.bus.publish("order_placed", {"order_id": 1})
        self.bus.publish("order_shipped", {"order_id": 1})
        self.assertEqual(self.log.entries,
                          [{"order_id": 1}, {"order_id": 1}])

    def test_irrelevant_events_are_not_logged(self):
        self.bus.publish("order_cancelled", {"order_id": 2})
        self.assertEqual(self.log.entries, [])

    def test_order_preserved_across_multiple_events(self):
        self.bus.publish("order_placed", {"order_id": 1})
        self.bus.publish("order_placed", {"order_id": 2})
        self.bus.publish("order_shipped", {"order_id": 1})
        self.assertEqual(self.log.entries,
                          [{"order_id": 1}, {"order_id": 2}, {"order_id": 1}])

    def test_summary_counts_entries(self):
        self.bus.publish("order_placed", {"order_id": 1})
        self.bus.publish("order_shipped", {"order_id": 1})
        self.assertEqual(self.log.summary(), {"count": 2})

    def test_fresh_log_starts_empty(self):
        self.assertEqual(self.log.entries, [])
        self.assertEqual(self.log.summary(), {"count": 0})


if __name__ == "__main__":
    unittest.main()
