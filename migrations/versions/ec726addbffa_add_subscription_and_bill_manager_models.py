
"""add subscription and bill manager models

Revision ID: ec726addbffa
Revises: 3d7aa3190cac
Create Date: 2026-11-26
"""

from alembic import op
import sqlalchemy as sa


revision = "ec726addbffa"
down_revision = "3d7aa3190cac"
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "subscription_bills",

        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),

        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("item_type", sa.String(length=20), nullable=False),

        sa.Column(
            "expected_amount",
            sa.Numeric(precision=10, scale=2),
            nullable=False
        ),

        sa.Column("frequency", sa.String(length=20), nullable=False),

        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("next_due_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),

        sa.Column("reminder_days", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),

        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"]
        ),

        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"]
        ),

        sa.PrimaryKeyConstraint("id")
    )

    op.create_index(
        "ix_subscription_bills_user_id",
        "subscription_bills",
        ["user_id"],
        unique=False
    )

    op.create_table(
        "bill_payments",

        sa.Column("id", sa.Integer(), nullable=False),

        sa.Column(
            "subscription_bill_id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column("user_id", sa.Integer(), nullable=False),

        sa.Column(
            "amount",
            sa.Numeric(precision=10, scale=2),
            nullable=False
        ),

        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),

        sa.Column(
            "payment_method",
            sa.Enum(
                "CASH",
                "UPI",
                "DEBIT_CARD",
                "CREDIT_CARD",
                "NET_BANKING",
                "WALLET",
                "OTHER",
                name="paymentmethod"
            ),
            nullable=False
        ),

        sa.Column("ledger_id", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),

        sa.ForeignKeyConstraint(
            ["subscription_bill_id"],
            ["subscription_bills.id"]
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"]
        ),

        sa.ForeignKeyConstraint(
            ["ledger_id"],
            ["ledger.id"]
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "ledger_id",
            name="uq_bill_payment_ledger_id"
        ),

        sa.UniqueConstraint(
            "subscription_bill_id",
            "due_date",
            name="uq_bill_payment_schedule_due_date"
        )
    )

    op.create_index(
        "ix_bill_payments_subscription_bill_id",
        "bill_payments",
        ["subscription_bill_id"],
        unique=False
    )

    op.create_index(
        "ix_bill_payments_user_id",
        "bill_payments",
        ["user_id"],
        unique=False
    )


def downgrade():

    op.drop_index(
        "ix_bill_payments_user_id",
        table_name="bill_payments"
    )

    op.drop_index(
        "ix_bill_payments_subscription_bill_id",
        table_name="bill_payments"
    )

    op.drop_table("bill_payments")

    op.drop_index(
        "ix_subscription_bills_user_id",
        table_name="subscription_bills"
    )

    op.drop_table("subscription_bills")
