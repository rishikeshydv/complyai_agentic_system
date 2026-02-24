from __future__ import annotations

import argparse
import json
import os
from typing import Any

from sqlalchemy import text

from core.laws_search_v2.db import SQLLawRepository
from core.laws_search_v2.postprocess.indexers import ElasticsearchLawIndexer
from core.laws_search_v2.postprocess.postprocessor import PostProcessor


class _NoopLawIndexer:
    def ensure_indices(self) -> None:
        return

    def index_chunks(self, chunks, docs_by_id):
        return (0, 0)

    def index_obligations(self, obligations, chunks_by_id, docs_by_id):
        return (0, 0)

    def search_obligations(self, query, top_k, jurisdiction=None, agency=None, instrument_type=None):
        return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill laws_search_v2 artifacts from existing regulatory_documents")
    parser.add_argument("--batch-size", type=int, default=200, help="documents per batch")
    parser.add_argument("--max-docs", type=int, default=0, help="stop after processing N docs (0 = all)")
    parser.add_argument("--start-after-id", type=int, default=0, help="resume from regulatory_documents.id > value")
    parser.add_argument(
        "--use-es",
        action="store_true",
        help="index reg_chunks/reg_obligations in Elasticsearch while backfilling",
    )
    return parser.parse_args()


def fetch_batch(repo: SQLLawRepository, batch_size: int, last_id: int) -> list[dict[str, Any]]:
    stmt = text(
        """
        SELECT id, citation, title, jurisdiction, agency, instrument_type,
               effective_date, effective_from, effective_to,
               body_text, source_url, content_hash, version_id, doc_family_id, metadata
        FROM regulatory_documents
        WHERE id > :last_id
        ORDER BY id ASC
        LIMIT :limit
        """
    )
    with repo.engine.begin() as conn:
        rows = conn.execute(stmt, {"last_id": last_id, "limit": batch_size}).fetchall()
    return [dict(row._mapping) for row in rows]


def main() -> int:
    args = parse_args()

    db_url = os.getenv("LAWS_V2_DATABASE_URL")
    repo = SQLLawRepository(database_url=db_url)

    if args.use_es:
        try:
            indexer = ElasticsearchLawIndexer()
        except Exception:
            indexer = _NoopLawIndexer()
    else:
        indexer = _NoopLawIndexer()

    processor = PostProcessor(repository=repo, indexer=indexer)

    total_docs = 0
    total_stats = {
        "processed_documents": 0,
        "chunks_upserted": 0,
        "obligations_upserted": 0,
        "chunk_indexed_success": 0,
        "chunk_indexed_failed": 0,
        "obligation_indexed_success": 0,
        "obligation_indexed_failed": 0,
    }

    last_id = int(args.start_after_id or 0)
    batch_num = 0
    while True:
        rows = fetch_batch(repo, args.batch_size, last_id)
        if not rows:
            break

        batch_num += 1
        try:
            stats = processor.process_documents(docs=rows)
        except Exception as exc:
            if args.use_es:
                # Keep DB backfill progressing even if Elasticsearch has transient issues.
                processor_no_es = PostProcessor(repository=repo, indexer=_NoopLawIndexer())
                stats = processor_no_es.process_documents(docs=rows)
                stats["index_error"] = str(exc)
            else:
                raise
        for key, value in stats.items():
            if key.endswith("_error"):
                continue
            total_stats[key] = total_stats.get(key, 0) + int(value)

        total_docs += len(rows)
        last_id = int(rows[-1]["id"])
        print(
            json.dumps(
                {
                    "batch": batch_num,
                    "batch_docs": len(rows),
                    "last_id": last_id,
                    "batch_stats": stats,
                },
                default=str,
            ),
            flush=True,
        )

        if args.max_docs and total_docs >= args.max_docs:
            break

    print(json.dumps({"status": "ok", "processed_docs": total_docs, "stats": total_stats}, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
