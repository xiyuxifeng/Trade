from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from config.database import dispose_cached_engine, get_session_factory  # noqa: E402
from src.models.stage2_canonical import RuleCandidate  # noqa: E402


LABELS = {
    "4836617e-adba-4938-81b5-8e4b00193bec": "rule_candidate",
    "9ba650ef-3722-4455-a3fc-b523020bdbcb": "research_hypothesis",
    "7d3e040a-9d08-45c6-8df7-271e80dc3995": "semantic_experience",
    "1e03e61c-9e82-4297-b912-86c65e884516": "risk_control_hint",
    "ac562719-87eb-4b6b-a864-ce72d44ea039": "data_requirement_hint",
    "e720b0de-0de8-4fa7-8911-e94c28039a69": "unusable_noise",
    "5b56a870-f864-4563-a69f-810351071aea": "rule_candidate",
}


def immutable_material(candidate: RuleCandidate) -> dict[str, object]:
    return {
        "id": str(candidate.rule_candidate_id),
        "canonical_payload": candidate.canonical_payload,
        "evidence_json": candidate.evidence_json,
        "missing_fields": candidate.missing_fields,
        "backtestability_status": candidate.backtestability_status,
        "review_state": str(candidate.review_state),
        "quality_status": str(candidate.quality_status),
    }


async def main() -> None:
    ids = [UUID(value) for value in LABELS]
    async with get_session_factory()() as session:
        rows = list(
            (
                await session.execute(
                    select(RuleCandidate)
                    .where(RuleCandidate.rule_candidate_id.in_(ids))
                    .order_by(RuleCandidate.rule_candidate_id)
                )
            ).scalars().all()
        )
    materials = [immutable_material(row) for row in rows]
    digest = hashlib.sha256(
        json.dumps(materials, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    results = []
    for row in rows:
        primary_type = LABELS[str(row.rule_candidate_id)]
        results.append(
            {
                "old_rule_candidate_id": str(row.rule_candidate_id),
                "expected_primary_type": primary_type,
                "old_status_is_not_authority": True,
                "lineage_required": [str(row.rule_candidate_id)],
                "formal_route": "blocked",
                "rationale": {
                    "rule_candidate": "bounded mechanics remain missing or depend on an upstream undefined concept",
                    "research_hypothesis": "measurable market claim but incomplete execution mechanics",
                    "semantic_experience": "core condition is subjective market language",
                    "risk_control_hint": "avoidance/filter discipline is not a standalone strategy",
                    "data_requirement_hint": "auction data availability is the primary unresolved need",
                    "unusable_noise": "narrative is too vague for a retained executable object",
                }[primary_type],
            }
        )
    print(
        json.dumps(
            {
                "requested_count": len(ids),
                "found_count": len(rows),
                "immutable_snapshot_sha256": digest,
                "type_distribution": {
                    label: sum(1 for item in results if item["expected_primary_type"] == label)
                    for label in sorted(set(LABELS.values()))
                },
                "unsupported_type": {
                    "primary_type": "executable_rule",
                    "reason": "no sampled old candidate proved the complete strict entry/exit/risk/sizing/timestamp/lookahead contract",
                },
                "items": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    await dispose_cached_engine()


if __name__ == "__main__":
    asyncio.run(main())
