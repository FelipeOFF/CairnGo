import unittest

from convert import celsius_to_fahrenheit


class TestConvert(unittest.TestCase):
    def test_freezing(self):
        self.assertEqual(celsius_to_fahrenheit(0), 32)

    def test_boiling(self):
        self.assertEqual(celsius_to_fahrenheit(100), 212)

    def test_body_temp(self):
        self.assertEqual(round(celsius_to_fahrenheit(37), 1), 98.6)


if __name__ == "__main__":
    unittest.main()
