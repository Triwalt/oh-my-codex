import unittest

from src.math_quality import moving_range, trimmed_mean


class TestMathQuality(unittest.TestCase):
    def test_trimmed_mean_basic(self):
        self.assertAlmostEqual(trimmed_mean([10, 11, 12, 100, 101], 0.2), 41.0)

    def test_trimmed_mean_empty(self):
        with self.assertRaises(ValueError):
            trimmed_mean([], 0.2)

    def test_trimmed_mean_invalid_ratio(self):
        with self.assertRaises(ValueError):
            trimmed_mean([1, 2, 3], 0.5)

    def test_moving_range(self):
        self.assertEqual(moving_range([3, 7, 6, 10]), [4, 1, 4])


if __name__ == "__main__":
    unittest.main()
