import unittest

from src.math_quality import detect_outliers_iqr, moving_average


class TestMathQuality(unittest.TestCase):
    def test_moving_average_basic(self):
        self.assertEqual(moving_average([1, 2, 3, 4], 2), [1.5, 2.5, 3.5])

    def test_moving_average_window_too_large(self):
        self.assertEqual(moving_average([1, 2], 3), [])

    def test_moving_average_invalid_window(self):
        with self.assertRaises(ValueError):
            moving_average([1, 2], 0)

    def test_detect_outliers_iqr(self):
        values = [10, 11, 11, 12, 12, 12, 13, 200]
        self.assertEqual(detect_outliers_iqr(values), [200])


if __name__ == "__main__":
    unittest.main()
