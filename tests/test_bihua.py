# tests/test_bihua.py
import unittest
from bihua import say_hello

class TestBihua(unittest.TestCase):
    def test_say_hello(self):
        self.assertEqual(say_hello("World"), "Hello, World!")

if __name__ == '__main__':
    unittest.main()
