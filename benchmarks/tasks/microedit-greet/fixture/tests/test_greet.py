import unittest

from greet import greet


class TestGreet(unittest.TestCase):
    def test_docstring_fixed(self):
        self.assertEqual(greet.__doc__, "Return a friendly greeting for NAME.")

    def test_behavior_unchanged(self):
        self.assertEqual(greet("Ada"), "Hello, Ada!")


if __name__ == "__main__":
    unittest.main()
