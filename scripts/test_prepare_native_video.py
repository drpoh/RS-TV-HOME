"""Unit tests for the display-rotation planner, no private media or TV required."""
import unittest
from prepare_native_video import clockwise_plus_90


class RotationPlanTests(unittest.TestCase):
    def test_existing_display_matrix_plus_clockwise_quarter_turn(self):
        self.assertEqual(clockwise_plus_90(-180), 90)
        self.assertEqual(clockwise_plus_90(-90), -180)
        self.assertEqual(clockwise_plus_90(0), -90)
        self.assertEqual(clockwise_plus_90(90), 0)
        self.assertEqual(clockwise_plus_90(180), 90)

    def test_normalized_equivalence(self):
        for original in range(-360, 361, 90):
            expected = (original - 90 + 180) % 360 - 180
            self.assertEqual(clockwise_plus_90(original), expected)


if __name__ == "__main__":
    unittest.main()
