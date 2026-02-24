from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(String, primary_key=True)
    bank_id = Column(String, nullable=False, default="demo")
    alert_type = Column(String, nullable=False)
    alert_metadata = Column(JSON, nullable=False)
    rule_triggered = Column(String, nullable=False)
    rule_description = Column(Text, nullable=False)
    rule_thresholds = Column(JSON, nullable=False)
    rule_evaluation = Column(JSON, nullable=False)
    transaction_id = Column(String, nullable=True)
    customer_id = Column(String, nullable=True)
    sanctions_hit_preview = Column(JSON, nullable=True)


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String, primary_key=True)
    bank_id = Column(String, nullable=False, default="demo")
    snapshot = Column(JSON, nullable=False)


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String, primary_key=True)
    bank_id = Column(String, nullable=False, default="demo")
    snapshot = Column(JSON, nullable=False)


class Aggregate(Base):
    __tablename__ = "aggregates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bank_id = Column(String, nullable=False, default="demo")
    customer_id = Column(String, nullable=False)
    rule_triggered = Column(String, nullable=False)
    window_days = Column(Integer, nullable=True)
    aggregates = Column(JSON, nullable=False)
    linked_transactions = Column(JSON, nullable=False, default=list)


class SanctionsHit(Base):
    __tablename__ = "sanctions_hits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bank_id = Column(String, nullable=False, default="demo")
    alert_id = Column(String, nullable=False)
    hit_id = Column(String, nullable=False)
    list_source = Column(String, nullable=False)
    matched_fields = Column(JSON, nullable=False)
    score = Column(Float, nullable=False)
    features = Column(JSON, nullable=False)
    prior_decision = Column(String, nullable=True)


class ConnectorFetchAudit(Base):
    __tablename__ = "connector_fetch_audit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String, nullable=False)
    endpoint = Column(String, nullable=False)
    parameters = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
