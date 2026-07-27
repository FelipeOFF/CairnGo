import unittest

from todo import TodoList


class TestTodoList(unittest.TestCase):
    def setUp(self):
        self.todos = TodoList()
        self.todos.add("write report", priority=2)
        self.todos.add("water plants", priority=0)
        self.todos.add("fix bug", priority=5)
        self.todos.complete("water plants")

    def test_pending_excludes_done_items(self):
        pending_texts = [item.text for item in self.todos.pending()]
        self.assertNotIn("water plants", pending_texts)
        self.assertIn("write report", pending_texts)
        self.assertIn("fix bug", pending_texts)

    def test_pending_sorted_by_priority_descending(self):
        pending_texts = [item.text for item in self.todos.pending()]
        self.assertEqual(pending_texts, ["fix bug", "write report"])

    def test_summary_counts(self):
        self.assertEqual(self.todos.summary(),
                          {"total": 3, "pending": 2, "done": 1})

    def test_summary_updates_after_more_completions(self):
        self.todos.complete("fix bug")
        self.assertEqual(self.todos.summary(),
                          {"total": 3, "pending": 1, "done": 2})


if __name__ == "__main__":
    unittest.main()
