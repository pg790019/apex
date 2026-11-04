import unittest
from main import generate_multiples_of_two

class TestMultiples(unittest.TestCase):
    def test_multiples(self):
        result = generate_multiples_of_two()
        self.assertEqual(result, [i for i in range(2, 201, 2)])

if __name__ == '__main__':
    unittest.main()
