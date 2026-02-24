from __future__ import annotations

from pathlib import Path

import yaml
from passlib.context import CryptContext
from sqlalchemy import and_, delete, select

from core.config import settings
from core.db.models import (
    Base,
    ControlCitationMap,
    LawCitation,
    ProposedRuleMap,
    RegulatoryControlObjective,
    RegulatoryMapping,
    RegulatoryRuleMap,
    RegulatoryTypology,
    User,
)
from core.db.session import SessionLocal, engine
from core.laws_search_v2.bootstrap import bootstrap_laws_v2

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def _laws_file() -> Path:
    return settings.shared_root / "laws" / "citations.yaml"


def _laws_v2_file() -> Path:
    return settings.shared_root / "laws" / "mapping_v2.yaml"


def seed_users(db) -> None:
    if db.scalar(select(User.id).limit(1)):
        return

    users = [
        User(email="analyst@comply.local", password_hash=pwd_context.hash("analyst123"), role="ANALYST"),
        User(email="reviewer@comply.local", password_hash=pwd_context.hash("reviewer123"), role="REVIEWER"),
        User(email="admin@comply.local", password_hash=pwd_context.hash("admin123"), role="ADMIN"),
    ]
    db.add_all(users)
    db.commit()


def seed_laws_and_mappings(db) -> None:
    if db.scalar(select(LawCitation.citation_id).limit(1)):
        return

    with _laws_file().open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    citations = data.get("citations", [])
    mappings = data.get("mappings", [])

    db.add_all(
        [
            LawCitation(
                citation_id=row["citation_id"],
                alert_type=row["alert_type"],
                jurisdiction=row["jurisdiction"],
                title=row["title"],
                text_snippet=row.get("text_snippet"),
            )
            for row in citations
        ]
    )

    db.add_all(
        [
            RegulatoryMapping(
                bank_id="default",
                alert_type=row["alert_type"],
                rule_triggered=row["rule_triggered"],
                citation_ids=row.get("citation_ids", []),
                why_relevant_template=row.get("why_relevant_template", "NOT PROVIDED"),
            )
            for row in mappings
        ]
    )
    db.commit()


def seed_law_mapping_v2(db) -> None:
    with _laws_v2_file().open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    typologies = data.get("typologies", [])
    controls = data.get("controls", [])
    control_map_rows = data.get("control_to_citations", [])
    rule_maps = data.get("rule_maps", [])

    # Seed parents first (idempotent), commit, then children to avoid FK-order surprises.
    existing_typology_ids = set(db.scalars(select(RegulatoryTypology.typology_id)).all())
    for row in typologies:
        tid = row["typology_id"]
        if tid in existing_typology_ids:
            continue
        db.add(
            RegulatoryTypology(
                typology_id=tid,
                name=row["name"],
                signals_definition=row.get("signals_definition", {}),
                default_control_ids=row.get("default_control_ids", []),
            )
        )
    db.commit()

    existing_control_ids = set(db.scalars(select(RegulatoryControlObjective.control_id)).all())
    for row in controls:
        cid = row["control_id"]
        if cid in existing_control_ids:
            continue
        db.add(
            RegulatoryControlObjective(
                control_id=cid,
                name=row["name"],
                description=row.get("description", "NOT PROVIDED"),
                expected_artifacts=row.get("expected_artifacts", []),
                jurisdiction_scope=row.get("jurisdiction_scope", "federal"),
            )
        )
    db.commit()

    # Refresh mappings deterministically from seed data.
    db.execute(delete(ControlCitationMap))
    for row in control_map_rows:
        db.add(
            ControlCitationMap(
                control_id=row["control_id"],
                citation_ids=row.get("citation_ids", []),
                jurisdiction_filter=row.get("jurisdiction_filter"),
                priority=int(row.get("priority", 100)),
            )
        )
    db.commit()

    for row in rule_maps:
        existing = db.scalar(
            select(RegulatoryRuleMap).where(
                and_(
                    RegulatoryRuleMap.bank_id == row.get("bank_id", "default"),
                    RegulatoryRuleMap.alert_type == row["alert_type"],
                    RegulatoryRuleMap.rule_triggered == row["rule_triggered"],
                )
            )
        )
        if existing:
            continue
        db.add(
            RegulatoryRuleMap(
                bank_id=row.get("bank_id", "default"),
                alert_type=row["alert_type"],
                rule_triggered=row["rule_triggered"],
                typology_id=row.get("typology_id"),
                control_ids=row.get("control_ids"),
                citation_ids=row.get("citation_ids"),
                confidence=str(row.get("confidence", "NOT PROVIDED")),
                version=row.get("version", "v1"),
                owner=row.get("owner"),
            )
        )
    db.commit()


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    bootstrap_laws_v2()
    db = SessionLocal()
    try:
        seed_users(db)
        seed_laws_and_mappings(db)
        seed_law_mapping_v2(db)
    finally:
        db.close()


def main() -> None:
    seed()


if __name__ == "__main__":
    main()
