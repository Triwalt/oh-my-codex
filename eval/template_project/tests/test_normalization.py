import unittest

from src.normalization import normalize_name, normalize_phone


class TestNormalization(unittest.TestCase):
    def test_normalize_name(self):
        self.assertEqual(normalize_name("  aLIce   joHNson "), "Alice Johnson")

    def test_normalize_phone_10_digits(self):
        self.assertEqual(normalize_phone("(212) 555-0199"), "+1-212-555-0199")

    def test_normalize_phone_11_digits(self):
        self.assertEqual(normalize_phone("+1 415 555 0100"), "+1-415-555-0100")

    def test_normalize_phone_invalid(self):
        with self.assertRaises(ValueError):
            normalize_phone("12345")


if __name__ == "__main__":
    unittest.main()
