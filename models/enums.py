from enum import Enum


class EntryType(Enum):

    EXPENSE = "Expense"
    INCOME = "Income"
    TRANSFER = "Transfer"
    SAVINGS = "Savings"
    INVESTMENT = "Investment"
    LOAN = "Loan"
    REFUND = "Refund"


class PaymentMethod(Enum):

    CASH = "Cash"
    UPI = "UPI"
    DEBIT_CARD = "Debit Card"
    CREDIT_CARD = "Credit Card"
    NET_BANKING = "Net Banking"
    WALLET = "Wallet"
    OTHER = "Other"