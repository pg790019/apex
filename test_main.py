import unittest
from main import multiply

class TestMultiply(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(multiply(3, 4), 12)

    def test_zero(self):
        self.assertEqual(multiply(0, 5), 0)

    def test_negative(self):
        self.assertEqual(multiply(-2, 8), -16)

    def test_invalid(self):
        with self.assertRaises(TypeError):
            multiply('a', 2)

if __name__ == '__main__':
    unittest.main()