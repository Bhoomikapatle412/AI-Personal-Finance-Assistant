import unittest
from datetime import date
from decimal import Decimal

from app import create_app
from extensions import db
from models import User, Category, Ledger
from models.budget import Budget
from models.enums import EntryType, PaymentMethod

from services.financial_report_service import (
    get_financial_summary,
    get_income_expense_trend,
    get_category_expense_breakdown,
    get_payment_method_breakdown,
    get_budget_vs_actual,
)


class TestFinancialReportService(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite://"
        )

        self.app_context = self.app.app_context()
        self.app_context.push()

        db.create_all()

        self.user = User(
            full_name="Test User",
            email="test@example.com",
            password_hash="test-password-hash"
        )

        self.other_user = User(
            full_name="Other User",
            email="other@example.com",
            password_hash="test-password-hash"
        )

        db.session.add_all([self.user, self.other_user])
        db.session.commit()

        self.user_id = self.user.id

        self.category = Category(
            name="Food",
            icon="utensils",
            color="#22c55e",
            is_default=True,
            user_id=None
        )

        self.other_category = Category(
            name="Shopping",
            icon="shopping-cart",
            color="#ef4444",
            is_default=True,
            user_id=None
        )

        db.session.add_all([
            self.category,
            self.other_category
        ])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def add_transaction(
        self,
        entry_type,
        amount,
        transaction_date,
        category=None,
        payment_method=PaymentMethod.UPI,
        user_id=None
    ):
        transaction = Ledger(
            user_id=user_id or self.user_id,
            category_id=(category or self.category).id,
            entry_type=entry_type,
            amount=Decimal(str(amount)),
            description=f"Test {entry_type.value}",
            payment_method=payment_method,
            transaction_date=transaction_date
        )

        db.session.add(transaction)
        db.session.commit()

        return transaction

    # --------------------------------------------------------
    # FINANCIAL SUMMARY
    # --------------------------------------------------------

    def test_financial_summary_calculates_totals(self):
        self.add_transaction(
            EntryType.INCOME, 50000, date(2026, 1, 5)
        )

        self.add_transaction(
            EntryType.EXPENSE, 10000, date(2026, 1, 10)
        )

        self.add_transaction(
            EntryType.REFUND, 2000, date(2026, 1, 15)
        )

        self.add_transaction(
            EntryType.SAVINGS, 5000, date(2026, 1, 20)
        )

        self.add_transaction(
            EntryType.INVESTMENT, 3000, date(2026, 1, 22)
        )

        self.add_transaction(
            EntryType.LOAN, 4000, date(2026, 1, 25)
        )

        self.add_transaction(
            EntryType.TRANSFER, 1000, date(2026, 1, 28)
        )

        summary = get_financial_summary(
            self.user_id,
            date(2026, 1, 1),
            date(2026, 1, 31)
        )

        self.assertEqual(summary["income"], Decimal("50000.00"))
        self.assertEqual(summary["expenses"], Decimal("10000.00"))
        self.assertEqual(summary["refunds"], Decimal("2000.00"))
        self.assertEqual(summary["net_expenses"], Decimal("8000.00"))
        self.assertEqual(summary["net_cash_flow"], Decimal("42000.00"))
        self.assertEqual(summary["savings"], Decimal("5000.00"))
        self.assertEqual(summary["investments"], Decimal("3000.00"))
        self.assertEqual(summary["loans"], Decimal("4000.00"))
        self.assertEqual(summary["transaction_count"], 7)

    def test_summary_excludes_transactions_outside_date_range(self):
        self.add_transaction(
            EntryType.INCOME, 10000, date(2025, 12, 31)
        )

        self.add_transaction(
            EntryType.INCOME, 5000, date(2026, 1, 15)
        )

        summary = get_financial_summary(
            self.user_id,
            date(2026, 1, 1),
            date(2026, 1, 31)
        )

        self.assertEqual(summary["income"], Decimal("5000.00"))
        self.assertEqual(summary["transaction_count"], 1)

    def test_summary_excludes_other_users_transactions(self):
        self.add_transaction(
            EntryType.INCOME, 10000, date(2026, 1, 10)
        )

        self.add_transaction(
            EntryType.INCOME,
            90000,
            date(2026, 1, 10),
            user_id=self.other_user.id
        )

        summary = get_financial_summary(
            self.user_id,
            date(2026, 1, 1),
            date(2026, 1, 31)
        )

        self.assertEqual(summary["income"], Decimal("10000.00"))

    def test_invalid_date_range_is_rejected(self):
        with self.assertRaises(ValueError):
            get_financial_summary(
                self.user_id,
                date(2026, 2, 1),
                date(2026, 1, 1)
            )

    def test_savings_rate_is_zero_without_income(self):
        self.add_transaction(
            EntryType.EXPENSE, 1000, date(2026, 1, 10)
        )

        summary = get_financial_summary(
            self.user_id,
            date(2026, 1, 1),
            date(2026, 1, 31)
        )

        self.assertEqual(summary["savings_rate"], Decimal("0"))

    # --------------------------------------------------------
    # INCOME AND EXPENSE TRENDS
    # --------------------------------------------------------

    def test_monthly_trend_groups_transactions(self):
        self.add_transaction(
            EntryType.INCOME, 30000, date(2026, 1, 5)
        )

        self.add_transaction(
            EntryType.EXPENSE, 5000, date(2026, 1, 10)
        )

        self.add_transaction(
            EntryType.INCOME, 40000, date(2026, 2, 5)
        )

        trend = get_income_expense_trend(
            self.user_id,
            date(2026, 1, 1),
            date(2026, 2, 28),
            group_by="monthly"
        )

        self.assertEqual(len(trend), 2)
        self.assertEqual(trend[0]["period"], "2026-01")
        self.assertEqual(trend[0]["income"], Decimal("30000.00"))
        self.assertEqual(trend[0]["expenses"], Decimal("5000.00"))

        self.assertEqual(trend[1]["period"], "2026-02")
        self.assertEqual(trend[1]["income"], Decimal("40000.00"))

    def test_daily_trend_groups_transactions(self):
        self.add_transaction(
            EntryType.INCOME, 5000, date(2026, 1, 5)
        )

        self.add_transaction(
            EntryType.EXPENSE, 1000, date(2026, 1, 5)
        )

        self.add_transaction(
            EntryType.EXPENSE, 2000, date(2026, 1, 6)
        )

        trend = get_income_expense_trend(
            self.user_id,
            date(2026, 1, 5),
            date(2026, 1, 6),
            group_by="daily"
        )

        self.assertEqual(len(trend), 2)

        self.assertEqual(trend[0]["period"], "2026-01-05")
        self.assertEqual(trend[0]["income"], Decimal("5000.00"))
        self.assertEqual(trend[0]["expenses"], Decimal("1000.00"))

        self.assertEqual(trend[1]["period"], "2026-01-06")
        self.assertEqual(trend[1]["expenses"], Decimal("2000.00"))

    def test_quarterly_trend_groups_correctly(self):
        self.add_transaction(
            EntryType.INCOME, 10000, date(2026, 1, 10)
        )

        self.add_transaction(
            EntryType.EXPENSE, 2000, date(2026, 4, 10)
        )

        trend = get_income_expense_trend(
            self.user_id,
            date(2026, 1, 1),
            date(2026, 6, 30),
            group_by="quarterly"
        )

        self.assertEqual(
            [item["period"] for item in trend],
            ["2026-Q1", "2026-Q2"]
        )

    def test_yearly_trend_groups_correctly(self):
        self.add_transaction(
            EntryType.INCOME, 50000, date(2025, 6, 10)
        )

        self.add_transaction(
            EntryType.EXPENSE, 10000, date(2025, 8, 15)
        )

        self.add_transaction(
            EntryType.INCOME, 80000, date(2026, 3, 20)
        )

        self.add_transaction(
            EntryType.EXPENSE, 20000, date(2026, 7, 10)
        )

        trend = get_income_expense_trend(
            self.user_id,
            date(2025, 1, 1),
            date(2026, 12, 31),
            group_by="yearly"
        )

        self.assertEqual(len(trend), 2)

        self.assertEqual(trend[0]["period"], "2025")
        self.assertEqual(trend[0]["income"], Decimal("50000.00"))
        self.assertEqual(trend[0]["expenses"], Decimal("10000.00"))

        self.assertEqual(trend[1]["period"], "2026")
        self.assertEqual(trend[1]["income"], Decimal("80000.00"))
        self.assertEqual(trend[1]["expenses"], Decimal("20000.00"))

    def test_invalid_trend_grouping_is_rejected(self):
        with self.assertRaises(ValueError):
            get_income_expense_trend(
                self.user_id,
                date(2026, 1, 1),
                date(2026, 1, 31),
                group_by="weekly"
            )

    # --------------------------------------------------------
    # CATEGORY BREAKDOWN
    # --------------------------------------------------------

    def test_category_breakdown_calculates_net_expenses(self):
        self.add_transaction(
            EntryType.EXPENSE, 5000, date(2026, 1, 5)
        )

        self.add_transaction(
            EntryType.REFUND, 1000, date(2026, 1, 10)
        )

        breakdown = get_category_expense_breakdown(
            self.user_id,
            date(2026, 1, 1),
            date(2026, 1, 31)
        )

        self.assertEqual(len(breakdown), 1)
        self.assertEqual(breakdown[0]["category_name"], "Food")
        self.assertEqual(breakdown[0]["expenses"], Decimal("5000.00"))
        self.assertEqual(breakdown[0]["refunds"], Decimal("1000.00"))
        self.assertEqual(
            breakdown[0]["net_expenses"],
            Decimal("4000.00")
        )

    def test_category_breakdown_handles_refunds_exceeding_expenses(self):
        self.add_transaction(
            EntryType.EXPENSE, 1000, date(2026, 1, 5)
        )

        self.add_transaction(
            EntryType.REFUND, 1500, date(2026, 1, 10)
        )

        breakdown = get_category_expense_breakdown(
            self.user_id,
            date(2026, 1, 1),
            date(2026, 1, 31)
        )

        self.assertEqual(len(breakdown), 1)
        self.assertEqual(
            breakdown[0]["expenses"],
            Decimal("1000.00")
        )
        self.assertEqual(
            breakdown[0]["refunds"],
            Decimal("1500.00")
        )
        self.assertEqual(
            breakdown[0]["net_expenses"],
            Decimal("-500.00")
        )

    # --------------------------------------------------------
    # PAYMENT METHOD BREAKDOWN
    # --------------------------------------------------------

    def test_payment_method_breakdown_groups_transactions(self):
        self.add_transaction(
            EntryType.EXPENSE,
            2000,
            date(2026, 1, 5),
            payment_method=PaymentMethod.UPI
        )

        self.add_transaction(
            EntryType.EXPENSE,
            3000,
            date(2026, 1, 10),
            payment_method=PaymentMethod.CASH
        )

        self.add_transaction(
            EntryType.REFUND,
            500,
            date(2026, 1, 15),
            payment_method=PaymentMethod.UPI
        )

        breakdown = get_payment_method_breakdown(
            self.user_id,
            date(2026, 1, 1),
            date(2026, 1, 31)
        )

        self.assertEqual(len(breakdown), 2)

        upi = next(
            item for item in breakdown
            if item["payment_method"] == "UPI"
        )

        self.assertEqual(upi["expenses"], Decimal("2000.00"))
        self.assertEqual(upi["refunds"], Decimal("500.00"))
        self.assertEqual(upi["net_expenses"], Decimal("1500.00"))

    def test_payment_method_breakdown_handles_refunds_exceeding_expenses(self):
        self.add_transaction(
            EntryType.EXPENSE,
            1000,
            date(2026, 1, 5),
            payment_method=PaymentMethod.UPI
        )

        self.add_transaction(
            EntryType.REFUND,
            1500,
            date(2026, 1, 10),
            payment_method=PaymentMethod.UPI
        )

        breakdown = get_payment_method_breakdown(
            self.user_id,
            date(2026, 1, 1),
            date(2026, 1, 31)
        )

        self.assertEqual(len(breakdown), 1)
        self.assertEqual(
            breakdown[0]["payment_method"], "UPI"
        )
        self.assertEqual(
            breakdown[0]["expenses"], Decimal("1000.00")
        )
        self.assertEqual(
            breakdown[0]["refunds"], Decimal("1500.00")
        )
        self.assertEqual(
            breakdown[0]["net_expenses"], Decimal("-500.00")
        )

    # --------------------------------------------------------
    # BUDGET VS ACTUAL
    # --------------------------------------------------------

    def test_budget_comparison_uses_complete_months_only(self):
        budget_january = Budget(
            user_id=self.user_id,
            category_id=self.category.id,
            amount=10000,
            month=1,
            year=2026
        )

        budget_february = Budget(
            user_id=self.user_id,
            category_id=self.category.id,
            amount=12000,
            month=2,
            year=2026
        )

        db.session.add_all([
            budget_january,
            budget_february
        ])
        db.session.commit()

        self.add_transaction(
            EntryType.EXPENSE, 8000, date(2026, 1, 15)
        )

        self.add_transaction(
            EntryType.EXPENSE, 14000, date(2026, 2, 15)
        )

        comparison = get_budget_vs_actual(
            self.user_id,
            date(2026, 1, 15),
            date(2026, 2, 28)
        )

        # January is excluded because the selected range
        # does not contain the complete month.
        self.assertEqual(len(comparison), 1)

        self.assertEqual(comparison[0]["month"], 2)
        self.assertEqual(
            comparison[0]["budget_amount"],
            Decimal("12000.00")
        )
        self.assertEqual(
            comparison[0]["actual_amount"],
            Decimal("14000.00")
        )
        self.assertTrue(comparison[0]["is_over_budget"])

    def test_budget_comparison_returns_empty_without_complete_month(self):
        comparison = get_budget_vs_actual(
            self.user_id,
            date(2026, 1, 10),
            date(2026, 1, 20)
        )

        self.assertEqual(comparison, [])

    def test_budget_comparison_excludes_other_users_budgets(self):
        budget = Budget(
            user_id=self.other_user.id,
            category_id=self.category.id,
            amount=10000,
            month=1,
            year=2026
        )

        db.session.add(budget)
        db.session.commit()

        comparison = get_budget_vs_actual(
            self.user_id,
            date(2026, 1, 1),
            date(2026, 1, 31)
        )

        self.assertEqual(comparison, [])


if __name__ == "__main__":
    unittest.main()