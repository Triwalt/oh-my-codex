import unittest

from src.normalization import normalize_email, normalize_sku


class TestNormalization(unittest.TestCase):
    def test_normalize_sku(self):
        self.assertEqual(normalize_sku(" ab-12  cd "), "AB-12-CD")

    def test_normalize_email(self):
        self.assertEqual(normalize_email("  Alice.Sales@Example.COM "), "alice.sales@example.com")

    def test_normalize_email_invalid(self):
        with self.assertRaises(ValueError):
            normalize_email("bad-address")


if __name__ == "__main__":
    unittest.main()
