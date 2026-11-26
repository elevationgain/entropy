"""report_fields(): the test writer's `Red evidence` count (review R1.3). Pure text in, nothing read from disk."""

import unittest

from tests.test_loop_card import entropy


def red(evidence):
    return entropy.report_fields("## Test writer report — round 1\nRed evidence: " + evidence + "\nNot covered: none").get("red")


class TestRedCount(unittest.TestCase):
    def test_per_test_lines(self):
        self.assertEqual(red("tests/a.py::t1 — red (missing)\ntests/a.py::t2 — red (wrong)"), 2)

    def test_summary_line(self):
        self.assertEqual(red("all 26 red: loop_card is missing"), 26)

    def test_summary_with_guards(self):
        self.assertEqual(red("5 red, 5 guards green"), 5)

    def test_none(self):
        self.assertEqual(red("none"), 0)


if __name__ == "__main__":
    unittest.main()
