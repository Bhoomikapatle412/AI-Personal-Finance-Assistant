
import unittest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from services.financial_goal_service import (
    get_goal_progress,
    _to_decimal,
)


class TestFinancialGoalService(unittest.TestCase):

    def create_goal(self, target, contributions=None, target_date=None):
        return SimpleNamespace(
            target_amount=Decimal(str(target)),
            contributions=[
                SimpleNamespace(amount=Decimal(str(amount)))
                for amount in (contributions or [])
            ],
            target_date=target_date
        )

    def test_goal_progress_without_contributions(self):
        goal = self.create_goal("10000")

        result = get_goal_progress(goal)

        self.assertEqual(result["saved_amount"], Decimal("0"))
        self.assertEqual(result["remaining_amount"], Decimal("10000"))
        self.assertEqual(result["progress_percentage"], 0)

    def test_goal_progress_with_contributions(self):
        goal = self.create_goal("10000", ["2000", "3000"])

        result = get_goal_progress(goal)

        self.assertEqual(result["saved_amount"], Decimal("5000"))
        self.assertEqual(result["remaining_amount"], Decimal("5000"))
        self.assertEqual(result["progress_percentage"], 50)

    def test_completed_goal(self):
        goal = self.create_goal("10000", ["6000", "4000"])

        result = get_goal_progress(goal)

        self.assertTrue(result["is_completed"])
        self.assertEqual(result["remaining_amount"], Decimal("0"))
        self.assertEqual(result["progress_percentage"], 100)

    def test_progress_never_exceeds_100_percent(self):
        goal = self.create_goal("10000", ["12000"])

        result = get_goal_progress(goal)

        self.assertEqual(result["progress_percentage"], 100)
        self.assertEqual(result["remaining_amount"], Decimal("0"))

    def test_monthly_savings_required(self):
        goal = self.create_goal(
            "12000",
            ["2000"],
            date(2027, 5, 24)
        )

        result = get_goal_progress(
            goal,
            today=date(2027, 1, 24)
        )

        self.assertEqual(
            result["monthly_savings_required"],
            Decimal("2500.00")
        )

    def test_no_target_date(self):
        goal = self.create_goal("10000", ["2000"])

        result = get_goal_progress(goal)

        self.assertIsNone(result["monthly_savings_required"])

    def test_decimal_conversion(self):
        self.assertEqual(_to_decimal("250.50"), Decimal("250.50"))

    def test_invalid_decimal(self):
        with self.assertRaises(ValueError):
            _to_decimal("invalid")

    def test_non_finite_decimal(self):
        with self.assertRaises(ValueError):
            _to_decimal("NaN")


if __name__ == "__main__":
    unittest.main()
