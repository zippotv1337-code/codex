from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass
from itertools import combinations

from .models import POSE_SLOT_ORDER, PoseSlot


TOP_PICK_WEIGHTS = {
    "quality_score": 0.30,
    "persona_fit_score": 0.25,
    "coherence_score": 0.20,
    "stage_fit_score": 0.15,
    "novelty_score": 0.10,
}


@dataclass(frozen=True)
class AssetQaResult:
    ready: bool
    reasons: tuple[str, ...]


def weighted_score(asset: sqlite3.Row | dict) -> float:
    return sum(float(asset[field]) * weight for field, weight in TOP_PICK_WEIGHTS.items())


def select_diverse_top_picks(
    connection: sqlite3.Connection,
    content_id: int,
    limit: int = 3,
    exclude_published: bool = False,
) -> tuple[int, ...]:
    """Rank by quality and fit, then keep the selected poses meaningfully diverse."""
    rows = list(
        connection.execute(
            """
            SELECT id, pose_slot, similarity_group, quality_score,
                   persona_fit_score, coherence_score, stage_fit_score,
                   novelty_score
            FROM assets
            WHERE content_id = ?
              AND (? = 0 OR published_status != 'PUBLISHED')
            """,
            (content_id, int(exclude_published)),
        ).fetchall()
    )
    action_poses = {PoseSlot.FULL_BODY_ACTION.value, PoseSlot.CANDID.value}
    candidates: list[tuple[float, tuple[int, ...], tuple[sqlite3.Row, ...]]] = []
    for group in combinations(rows, min(limit, len(rows))):
        poses = {str(row["pose_slot"]) for row in group}
        similarity = Counter(str(row["similarity_group"] or "") for row in group)
        if len(poses) != len(group):
            continue
        if any(key and count > 2 for key, count in similarity.items()):
            continue
        if not any(str(row["pose_slot"]) in action_poses for row in group):
            continue
        ids = tuple(sorted(int(row["id"]) for row in group))
        candidates.append((sum(weighted_score(row) for row in group), ids, group))

    if candidates:
        _, _, selected = max(candidates, key=lambda candidate: (candidate[0], tuple(-value for value in candidate[1])))
        ranked_selected = sorted(selected, key=lambda row: (-weighted_score(row), int(row["id"])))
    else:
        # Incomplete legacy packages still get deterministic picks; QA keeps them
        # out of READY_FOR_REVIEW until the pose and similarity rules are met.
        ranked_selected = sorted(rows, key=lambda row: (-weighted_score(row), int(row["id"])))[:limit]

    selected_ids = tuple(int(row["id"]) for row in ranked_selected)
    connection.execute("UPDATE assets SET is_top_pick = 0 WHERE content_id = ?", (content_id,))
    if selected_ids:
        placeholders = ",".join("?" for _ in selected_ids)
        connection.execute(
            f"UPDATE assets SET is_top_pick = 1, status = 'CURATED' "
            f"WHERE id IN ({placeholders})",
            selected_ids,
        )
    return selected_ids


def qa_assets(rows: list[sqlite3.Row] | tuple[sqlite3.Row, ...]) -> AssetQaResult:
    reasons: list[str] = []
    if len(rows) != 5:
        reasons.append("asset_count_must_equal_five")

    hashes = [str(row["perceptual_hash"]) for row in rows]
    if len(set(hashes)) != len(hashes):
        reasons.append("duplicate_asset_hash")

    expected_poses = {slot.value for slot in POSE_SLOT_ORDER}
    poses = [str(row["pose_slot"]) for row in rows]
    if set(poses) != expected_poses:
        reasons.append("pose_matrix_incomplete")

    groups = Counter(str(row["similarity_group"] or "") for row in rows)
    if any(group and count > 2 for group, count in groups.items()):
        reasons.append("too_many_similar_assets")

    top = [row for row in rows if bool(row["is_top_pick"])]
    if len(top) != 3:
        reasons.append("top_pick_count_must_equal_three")
    elif len({str(row["pose_slot"]) for row in top}) < 3:
        reasons.append("top_picks_not_pose_diverse")
    elif not any(
        str(row["pose_slot"])
        in {PoseSlot.FULL_BODY_ACTION.value, PoseSlot.CANDID.value}
        for row in top
    ):
        reasons.append("top_picks_need_action_or_candid")

    return AssetQaResult(ready=not reasons, reasons=tuple(reasons))
