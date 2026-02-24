from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from connector.db.models import Aggregate, Alert, Base, Customer, SanctionsHit, Transaction
from connector.db.session import SessionLocal, engine


def _sample_data_root() -> Path:
    return Path(__file__).resolve().parents[2] / "seed_data"


def seed() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.scalar(select(Alert.alert_id).limit(1)):
            return

        aml_alert = Alert(
            alert_id="ALERT-001",
            bank_id="demo",
            alert_type="AML",
            alert_metadata={"source_system": "core-aml-rules-engine", "created_at": "2026-02-08T01:00:00Z"},
            rule_triggered="CASH_SPIKE_30D",
            rule_description="30-day cash deposits exceeded profile threshold",
            rule_thresholds={"cash_deposit_total_30d": 25000, "cash_deposit_count_30d": 8},
            rule_evaluation={
                "conditions_triggered": [
                    {
                        "field": "historical_aggregates.cash_deposit_total_30d",
                        "operator": ">=",
                        "threshold": 25000,
                        "actual": 31250,
                        "window_days": 30,
                    },
                    {
                        "field": "historical_aggregates.cash_deposit_count_30d",
                        "operator": ">=",
                        "threshold": 8,
                        "actual": 11,
                        "window_days": 30,
                    },
                ]
            },
            transaction_id="TX-928771",
            customer_id="CUST-10009",
            sanctions_hit_preview=None,
        )

        sanctions_alert = Alert(
            alert_id="ALERT-002",
            bank_id="demo",
            alert_type="SANCTIONS",
            alert_metadata={"source_system": "sanctions-screening-engine", "created_at": "2026-02-08T02:00:00Z"},
            rule_triggered="OFAC_NAME_SCREEN_MATCH",
            rule_description="Customer name matched with high confidence on sanctions list",
            rule_thresholds={"score_threshold": 0.85},
            rule_evaluation={
                "conditions_triggered": [
                    {
                        "field": "screening.score",
                        "operator": ">=",
                        "threshold": 0.85,
                        "actual": 0.92,
                        "window_days": None,
                    }
                ]
            },
            transaction_id=None,
            customer_id="CUST-20021",
            sanctions_hit_preview={"hit_id": "HIT-OFAC-7781", "score": 0.92},
        )

        tx_primary = Transaction(
            transaction_id="TX-928771",
            bank_id="demo",
            snapshot={
                "transaction_id": "TX-928771",
                "type": "cash_deposit",
                "amount": 9500,
                "currency": "USD",
                "channel": "branch",
                "occurred_at": "2026-02-06T19:00:00Z",
                "description": "Business cash intake",
            },
        )

        tx_linked_1 = Transaction(
            transaction_id="TX-928700",
            bank_id="demo",
            snapshot={
                "transaction_id": "TX-928700",
                "type": "cash_deposit",
                "amount": 7900,
                "currency": "USD",
                "channel": "branch",
                "occurred_at": "2026-01-29T15:00:00Z",
                "description": "cash deposit 7,900",
            },
        )

        tx_linked_2 = Transaction(
            transaction_id="TX-928710",
            bank_id="demo",
            snapshot={
                "transaction_id": "TX-928710",
                "type": "cash_deposit",
                "amount": 6250,
                "currency": "USD",
                "channel": "branch",
                "occurred_at": "2026-01-31T11:00:00Z",
                "description": "cash deposit 6,250",
            },
        )

        customer_aml = Customer(
            customer_id="CUST-10009",
            bank_id="demo",
            snapshot={
                "customer_id": "CUST-10009",
                "customer_type": "SMB",
                "segment": "Hospitality",
                "kyc_risk_rating": "High",
                "edd": True,
                "prior_alerts_12m": 2,
                "prior_sar_12m": 0,
            },
        )

        customer_sanctions = Customer(
            customer_id="CUST-20021",
            bank_id="demo",
            snapshot={
                "customer_id": "CUST-20021",
                "customer_type": "Individual",
                "segment": "Retail",
                "kyc_risk_rating": "Medium",
                "edd": False,
                "prior_alerts_12m": 1,
                "prior_sar_12m": 0,
                "legal_name": "Jonathan Kareem Rahman",
            },
        )

        aml_agg = Aggregate(
            bank_id="demo",
            customer_id="CUST-10009",
            rule_triggered="CASH_SPIKE_30D",
            window_days=30,
            aggregates={
                "avg_cash_deposit_90d": 2800,
                "cash_deposit_count_30d": 11,
                "cash_deposit_total_30d": 31250,
            },
            linked_transactions=[
                {"transaction_id": "TX-928700", "description": "cash deposit 7,900"},
                {"transaction_id": "TX-928710", "description": "cash deposit 6,250"},
            ],
        )

        sanctions_agg = Aggregate(
            bank_id="demo",
            customer_id="CUST-20021",
            rule_triggered="OFAC_NAME_SCREEN_MATCH",
            window_days=None,
            aggregates={
                "recent_screening_matches_30d": 1,
                "max_screening_score_30d": 0.92,
            },
            linked_transactions=[],
        )

        sanctions_hit = SanctionsHit(
            alert_id="ALERT-002",
            bank_id="demo",
            hit_id="HIT-OFAC-7781",
            list_source="OFAC SDN",
            matched_fields=["full_name", "dob", "country"],
            score=0.92,
            features={"name_similarity": 0.96, "dob_match": True, "country_match": True},
            prior_decision="NOT PROVIDED",
        )

        db.add_all(
            [
                aml_alert,
                sanctions_alert,
                tx_primary,
                tx_linked_1,
                tx_linked_2,
                customer_aml,
                customer_sanctions,
                aml_agg,
                sanctions_agg,
                sanctions_hit,
            ]
        )
        db.commit()
    finally:
        db.close()


def main() -> None:
    seed()


if __name__ == "__main__":
    main()
