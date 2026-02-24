from __future__ import annotations

import uuid

import pytest

from core.laws_search_v2.schemas import RegulatoryDocumentRecord


@pytest.fixture
def sample_document() -> RegulatoryDocumentRecord:
    return RegulatoryDocumentRecord(
        id=uuid.uuid4(),
        citation="31 CFR 1020.320",
        title="Reports by banks of suspicious transactions",
        jurisdiction="federal",
        agency="fincen",
        instrument_type="regulation",
        body_text=(
            "Section 1. Suspicious Activity Reporting\n\n"
            "A bank shall file a suspicious activity report for any transaction involving at least $5,000 "
            "when the bank knows, suspects, or has reason to suspect that the transaction involves funds "
            "derived from illegal activity.\n\n"
            "Section 2. Recordkeeping\n\n"
            "A bank must maintain records of each suspicious activity report and supporting documentation "
            "for five years from the date of filing.\n\n"
            "Section 3. OFAC Screening\n\n"
            "A financial institution must screen customers against OFAC sanctions lists and retain screening logs."
        ),
        source_url="https://example.test/31-cfr-1020-320",
        content_hash="abc123ffeeddaa778899",
        version_id="v1",
        doc_family_id="31cfr1020320",
    )
