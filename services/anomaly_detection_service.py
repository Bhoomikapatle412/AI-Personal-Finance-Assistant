from statistics import median
from datetime import date, timedelta

from extensions import db
from models.ledger import Ledger
from models.enums import EntryType


MIN_HISTORY = 8
ANOMALY_THRESHOLD = 3.5


def calculate_mad(values):
    """Calculate Median Absolute Deviation."""
    if not values:
        return 0

    med = median(values)
    deviations = [abs(value - med) for value in values]

    return median(deviations)


def calculate_robust_z_score(value, values):
    """Calculate robust Z-score using median and MAD."""
    if not values:
        return 0

    med = median(values)
    mad = calculate_mad(values)

    if mad == 0:
        return float("inf") if value > med else 0

    return 0.6745 * (value - med) / mad


def detect_anomaly(amount, historical_amounts):
    """Detect unusually large transactions."""

    if len(historical_amounts) < MIN_HISTORY:
        return {
            "is_anomaly": False,
            "score": 0,
            "severity": None,
            "message": "Not enough transaction history."
        }

    score = calculate_robust_z_score(amount, historical_amounts)
    is_anomaly = score >= ANOMALY_THRESHOLD

    if not is_anomaly:
        return {
            "is_anomaly": False,
            "score": round(score, 2),
            "severity": None,
            "message": None
        }

    if score >= 6:
        severity = "high"
    elif score >= 4.5:
        severity = "medium"
    else:
        severity = "low"

    historical_median = median(historical_amounts)

    return {
        "is_anomaly": True,
        "score": round(score, 2),
        "severity": severity,
        "message": (
            f"This expense of ₹{amount:,.2f} is unusually high "
            f"compared with your typical expense of "
            f"₹{historical_median:,.2f} in this category."
        )
    }


def get_user_anomalies(user_id, today=None):
    """Detect unusual expenses for a specific user."""

    today = today or date.today()
    start_date = today - timedelta(days=90)

    transactions = (
        Ledger.query
        .filter(
            Ledger.user_id == user_id,
            Ledger.entry_type == EntryType.EXPENSE,
            Ledger.transaction_date >= start_date,
            Ledger.transaction_date <= today,
        )
        .order_by(Ledger.transaction_date.asc())
        .all()
    )

    anomalies = []

    for transaction in transactions:
        historical_amounts = [
            float(previous.amount)
            for previous in transactions
            if previous.category_id == transaction.category_id
            and previous.transaction_date < transaction.transaction_date
        ]

        result = detect_anomaly(
            float(transaction.amount),
            historical_amounts
        )

        if result["is_anomaly"]:
            anomalies.append({
                "transaction_id": transaction.id,
                "amount": float(transaction.amount),
                "description": transaction.description,
                "merchant": transaction.merchant,
                "date": transaction.transaction_date,
                "category": (
                    transaction.category.name
                    if transaction.category
                    else "Uncategorized"
                ),
                "severity": result["severity"],
                "score": result["score"],
                "message": result["message"],
            })

    anomalies.sort(
        key=lambda item: item["date"],
        reverse=True
    )

    return anomalies