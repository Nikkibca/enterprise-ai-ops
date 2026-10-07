from datetime import datetime, timedelta, timezone

from app.db import SessionLocal
from app.models import Payment, PaymentFailure


def seed_data() -> None:
    db = SessionLocal()

    try:
        # Keep the script safe to rerun.
        db.query(PaymentFailure).delete()
        db.query(Payment).delete()
        db.commit()

        now = datetime.now(timezone.utc)

        payments = [
            Payment(
                status="success",
                amount=120.50,
                provider="stripe",
                created_at=now - timedelta(days=1, hours=1),
            ),
            Payment(
                status="success",
                amount=85.00,
                provider="stripe",
                created_at=now - timedelta(days=1, hours=2),
            ),
            Payment(
                status="failed",
                amount=210.75,
                provider="stripe",
                created_at=now - timedelta(days=1, hours=3),
            ),
            Payment(
                status="failed",
                amount=99.99,
                provider="stripe",
                created_at=now - timedelta(days=1, hours=4),
            ),
            Payment(
                status="success",
                amount=450.00,
                provider="adyen",
                created_at=now - timedelta(days=1, hours=5),
            ),
            Payment(
                status="failed",
                amount=175.25,
                provider="adyen",
                created_at=now - timedelta(days=1, hours=6),
            ),
            Payment(
                status="success",
                amount=60.00,
                provider="adyen",
                created_at=now - timedelta(hours=2),
            ),
            Payment(
                status="failed",
                amount=300.00,
                provider="stripe",
                created_at=now - timedelta(hours=3),
            ),
            Payment(
                status="failed",
                amount=125.50,
                provider="stripe",
                created_at=now - timedelta(hours=4),
            ),
            Payment(
                status="failed",
                amount=89.90,
                provider="adyen",
                created_at=now - timedelta(hours=5),
            ),
        ]

        db.add_all(payments)
        db.flush()

        failures = [
            PaymentFailure(
                payment_id=payments[2].id,
                error_code="PAYMENT_TIMEOUT",
                error_message="Payment provider request timed out.",
                provider="stripe",
                created_at=payments[2].created_at,
            ),
            PaymentFailure(
                payment_id=payments[3].id,
                error_code="PAYMENT_TIMEOUT",
                error_message="Payment provider request timed out.",
                provider="stripe",
                created_at=payments[3].created_at,
            ),
            PaymentFailure(
                payment_id=payments[5].id,
                error_code="PROVIDER_ERROR",
                error_message="Payment provider returned an upstream error.",
                provider="adyen",
                created_at=payments[5].created_at,
            ),
            PaymentFailure(
                payment_id=payments[7].id,
                error_code="PAYMENT_TIMEOUT",
                error_message="Payment provider request timed out.",
                provider="stripe",
                created_at=payments[7].created_at,
            ),
            PaymentFailure(
                payment_id=payments[8].id,
                error_code="PAYMENT_TIMEOUT",
                error_message="Payment provider request timed out.",
                provider="stripe",
                created_at=payments[8].created_at,
            ),
            PaymentFailure(
                payment_id=payments[9].id,
                error_code="PROVIDER_ERROR",
                error_message="Payment provider returned an upstream error.",
                provider="adyen",
                created_at=payments[9].created_at,
            ),
        ]

        db.add_all(failures)
        db.commit()

        print("Operational data seeded successfully.")
        print(f"Payments inserted: {len(payments)}")
        print(f"Payment failures inserted: {len(failures)}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_data()