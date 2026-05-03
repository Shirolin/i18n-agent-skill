import json
import os
from typing import Any

import aiofiles

from i18n_agent_skill.models import RegressionResult, TranslationStatus

SNAPSHOT_FILE = ".i18n-snapshots.json"


class TranslationSnapshotManager:
    """
    Snapshot and Status Manager: Records historical high-score translations
    and tracks entry lifecycle status.
    """

    def __init__(self, workspace_root: str):
        self.path = os.path.join(workspace_root, SNAPSHOT_FILE)

    async def _read_snapshots(self) -> dict[str, Any]:
        if not os.path.exists(self.path):
            return {}
        try:
            async with aiofiles.open(self.path, encoding="utf-8") as f:
                content = await f.read()
                if not content.strip():
                    return {}
                return json.loads(content)
        except (json.JSONDecodeError, OSError):
            # If snapshot is corrupted, treat as empty but don't crash
            return {}

    async def _write_snapshots(self, snapshots: dict[str, Any]):
        async with aiofiles.open(self.path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(snapshots, indent=2, ensure_ascii=False, sort_keys=True))

    async def get_status(self, key: str) -> TranslationStatus:
        """Get entry status, defaults to DRAFT"""
        snapshots = await self._read_snapshots()
        if key not in snapshots:
            return TranslationStatus.DRAFT
        return TranslationStatus(snapshots[key].get("status", TranslationStatus.DRAFT))

    async def check_regression(self, key: str, current_score: int) -> RegressionResult | None:
        """
        Check if the current translation score is lower than the historical maximum.
        """
        snapshots = await self._read_snapshots()
        if key not in snapshots:
            return None

        snapshot_score = snapshots[key].get("score", 0)
        if current_score < snapshot_score:
            msg = (
                f"Quality Regression Warning: Entry '{key}' has a current score "
                f"({current_score}) lower than the historical maximum "
                f"({snapshot_score}). Please check for regression."
            )
            return RegressionResult(
                is_degraded=True,
                snapshot_score=snapshot_score,
                current_score=current_score,
                warning_message=msg,
            )

        return None

    async def update_snapshot(
        self,
        key: str,
        translation: str,
        score: int,
        status: TranslationStatus = TranslationStatus.DRAFT,
        content_hash: str | None = None,
    ):
        """
        Update snapshot. Updates only if the score is higher/equal or status is promoted.
        """
        snapshots = await self._read_snapshots()
        existing = snapshots.get(key, {})
        old_score = existing.get("score", 0)
        old_status = TranslationStatus(existing.get("status", TranslationStatus.DRAFT))

        # If status is higher (e.g., DRAFT -> APPROVED), or score is higher, update
        status_priority = {
            TranslationStatus.DRAFT: 0,
            TranslationStatus.REVIEWED: 1,
            TranslationStatus.APPROVED: 2,
        }

        if (
            key not in snapshots
            or score >= old_score
            or status_priority[status] > status_priority[old_status]
            or (status == TranslationStatus.APPROVED and content_hash != existing.get("hash"))
        ):
            snapshots[key] = {
                "translation": translation,
                "score": score,
                "status": status.value,
                "hash": content_hash or existing.get("hash"),
            }
            await self._write_snapshots(snapshots)
