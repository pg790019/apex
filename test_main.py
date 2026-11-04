import unittest
from main import subtract

class TestSubtract(unittest.TestCase):
    def test_positive_numbers(self):
        self.assertEqual(subtract(5, 3), 2)

    def test_zero(self):
        self.assertEqual(subtract(0, 0), 0)

    def test_negative_numbers(self):
        self.assertEqual(subtract(-4, -6), 2)

    def test_invalid_input(self):
        with self.assertRaises(TypeError):
            subtract('a', 3)

if __name__ == '__main__':
    unittest.main()