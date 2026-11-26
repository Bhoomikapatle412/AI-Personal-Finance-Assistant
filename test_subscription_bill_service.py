
import unittest
from datetime import date
from unittest.mock import patch

from app import create_app
from extensions import db
from models import User, Category, Ledger
from models.enums import EntryType, PaymentMethod
from models.subscription_bill import SubscriptionBill, BillPayment

from services.subscription_bill_service import (
    create_subscription_bill,
    record_bill_payment,
    calculate_next_due_date,
)


class TestSubscriptionBillService(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite://",
        )

        self.app_context = self.app.app_context()
        self.app_context.push()

        db.create_all()

        self.user = User(
            full_name="Test User",
            email="test@example.com",
            password_hash="test-password-hash",
        )

        self.other_user = User(
            full_name="Other User",
            email="other@example.com",
            password_hash="test-password-hash",
        )

        db.session.add_all([self.user, self.other_user])
        db.session.commit()

        self.default_category = Category(
            name="Entertainment",
            icon="film",
            color="#6366f1",
            is_default=True,
            user_id=None,
        )

        self.custom_category = Category(
            name="My Subscriptions",
            icon="wallet",
            color="#22c55e",
            is_default=False,
            user_id=self.user.id,
        )

        self.other_category = Category(
            name="Other User Category",
            icon="shopping-cart",
            color="#ef4444",
            is_default=False,
            user_id=self.other_user.id,
        )

        self.invalid_category = Category(
            name="Unowned Category",
            icon="folder",
            color="#64748b",
            is_default=False,
            user_id=None,
        )

        db.session.add_all([
            self.default_category,
            self.custom_category,
            self.other_category,
            self.invalid_category,
        ])
        db.session.commit()

        self.user_id = self.user.id
        self.category_id = self.default_category.id

        self.start_date = date(2026, 1, 31)

        self.bill = create_subscription_bill(
            user_id=self.user_id,
            category_id=self.category_id,
            name="Test Netflix",
            item_type="subscription",
            expected_amount="649.00",
            frequency="monthly",
            start_date=self.start_date,
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # --------------------------------------------------------
    # PAYMENT RECORDING
    # --------------------------------------------------------

    def test_payment_creates_bill_payment_and_ledger_entry(self):
        payment = record_bill_payment(
            user_id=self.user_id,
            bill_id=self.bill.id,
            amount="699.00",
            payment_date=date(2026, 1, 30),
            payment_method=PaymentMethod.UPI,
            due_date=self.start_date,
            notes="Monthly subscription payment",
        )

        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, 699)

        self.assertEqual(BillPayment.query.count(), 1)
        self.assertEqual(Ledger.query.count(), 1)

        ledger = Ledger.query.first()

        self.assertEqual(ledger.user_id, self.user_id)
        self.assertEqual(ledger.entry_type, EntryType.EXPENSE)
        self.assertEqual(ledger.amount, 699)
        self.assertEqual(ledger.payment_method, PaymentMethod.UPI)

    def test_payment_advances_next_due_date_from_scheduled_date(self):
        record_bill_payment(
            user_id=self.user_id,
            bill_id=self.bill.id,
            amount="649.00",
            payment_date=date(2026, 2, 5),
            payment_method=PaymentMethod.UPI,
            due_date=self.start_date,
        )

        updated_bill = db.session.get(SubscriptionBill, self.bill.id)

        # January 31 -> February 28.
        self.assertEqual(
            updated_bill.next_due_date,
            date(2026, 2, 28),
        )

    def test_actual_payment_amount_can_differ_from_expected_amount(self):
        payment = record_bill_payment(
            user_id=self.user_id,
            bill_id=self.bill.id,
            amount="750.50",
            payment_date=date(2026, 1, 31),
            payment_method=PaymentMethod.UPI,
            due_date=self.start_date,
        )

        self.assertEqual(payment.amount, 750.50)
        self.assertEqual(self.bill.expected_amount, 649.00)

    # --------------------------------------------------------
    # DUPLICATE PAYMENT PROTECTION
    # --------------------------------------------------------

    def test_duplicate_payment_for_previous_cycle_is_rejected(self):
        record_bill_payment(
            user_id=self.user_id,
            bill_id=self.bill.id,
            amount="649.00",
            payment_date=date(2026, 1, 31),
            payment_method=PaymentMethod.UPI,
            due_date=self.start_date,
        )

        with self.assertRaisesRegex(ValueError, "outdated"):
            record_bill_payment(
                user_id=self.user_id,
                bill_id=self.bill.id,
                amount="649.00",
                payment_date=date(2026, 1, 31),
                payment_method=PaymentMethod.UPI,
                due_date=self.start_date,
            )

        self.assertEqual(BillPayment.query.count(), 1)
        self.assertEqual(Ledger.query.count(), 1)

    # --------------------------------------------------------
    # CATEGORY OWNERSHIP VALIDATION
    # --------------------------------------------------------

    def test_default_category_is_allowed(self):
        bill = create_subscription_bill(
            user_id=self.user_id,
            category_id=self.default_category.id,
            name="Default Category Test",
            item_type="subscription",
            expected_amount=100,
            frequency="monthly",
            start_date=date(2026, 1, 1),
        )

        self.assertIsNotNone(bill)

    def test_own_custom_category_is_allowed(self):
        bill = create_subscription_bill(
            user_id=self.user_id,
            category_id=self.custom_category.id,
            name="Custom Category Test",
            item_type="bill",
            expected_amount=200,
            frequency="monthly",
            start_date=date(2026, 1, 1),
        )

        self.assertIsNotNone(bill)

    def test_another_users_category_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid category"):
            create_subscription_bill(
                user_id=self.user_id,
                category_id=self.other_category.id,
                name="Invalid Category Test",
                item_type="subscription",
                expected_amount=100,
                frequency="monthly",
                start_date=date(2026, 1, 1),
            )

    def test_unowned_non_default_category_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid category"):
            create_subscription_bill(
                user_id=self.user_id,
                category_id=self.invalid_category.id,
                name="Unowned Category Test",
                item_type="subscription",
                expected_amount=100,
                frequency="monthly",
                start_date=date(2026, 1, 1),
            )

    # --------------------------------------------------------
    # TRANSACTION ROLLBACK
    # --------------------------------------------------------

    def test_failed_payment_rolls_back_ledger_and_payment(self):
        original_due_date = self.bill.next_due_date

        # Force an error after the ledger entry has been flushed,
        # but before the payment transaction can be committed.
        with patch(
            "services.subscription_bill_service.calculate_next_due_date",
            side_effect=RuntimeError("Simulated payment failure"),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "Simulated payment failure",
            ):
                record_bill_payment(
                    user_id=self.user_id,
                    bill_id=self.bill.id,
                    amount="649.00",
                    payment_date=date(2026, 1, 31),
                    payment_method=PaymentMethod.UPI,
                    due_date=original_due_date,
                )

        self.assertEqual(Ledger.query.count(), 0)
        self.assertEqual(BillPayment.query.count(), 0)

        updated_bill = db.session.get(SubscriptionBill, self.bill.id)

        self.assertEqual(
            updated_bill.next_due_date,
            original_due_date,
        )

    # --------------------------------------------------------
    # DATE CALCULATION
    # --------------------------------------------------------

    def test_monthly_schedule_preserves_original_day(self):
        next_date = calculate_next_due_date(
            date(2026, 1, 31),
            "monthly",
            anchor_day=31,
        )

        self.assertEqual(next_date, date(2026, 2, 28))

    def test_monthly_schedule_restores_original_day(self):
        next_date = calculate_next_due_date(
            date(2026, 2, 28),
            "monthly",
            anchor_day=31,
        )

        self.assertEqual(next_date, date(2026, 3, 31))

    def test_yearly_schedule_preserves_leap_day_anchor(self):
        next_date = calculate_next_due_date(
            date(2024, 2, 29),
            "yearly",
            anchor_day=29,
            anchor_month=2,
        )

        self.assertEqual(next_date, date(2025, 2, 28))


if __name__ == "__main__":
    unittest.main()
