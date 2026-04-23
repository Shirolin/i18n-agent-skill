import json
import os
from typing import Any

import aiofiles

from i18n_agent_skill.models import RegressionResult

SNAPSHOT_FILE = ".i18n-snapshots.json"


class TranslationSnapshotManager:
    """
    快照回归管理器：记录历史上得分最高的翻译，防止翻译质量下降。
    """

    def __init__(self, workspace_root: str):
        self.path = os.path.join(workspace_root, SNAPSHOT_FILE)

    async def _read_snapshots(self) -> dict[str, Any]:
        if not os.path.exists(self.path):
            return {}
        try:
            async with aiofiles.open(self.path, encoding="utf-8") as f:
                content = await f.read()
                data: dict[str, Any] = json.loads(content)
                return data
        except Exception:
            return {}

    async def _write_snapshots(self, snapshots: dict[str, Any]):
        async with aiofiles.open(self.path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(snapshots, indent=2, ensure_ascii=False, sort_keys=True))

    async def check_regression(self, key: str, current_score: int) -> RegressionResult | None:
        """
        检查当前翻译得分是否低于历史最高快照得分。
        """
        snapshots = await self._read_snapshots()
        if key not in snapshots:
            return None

        snapshot_score = snapshots[key].get("score", 0)
        if current_score < snapshot_score:
            msg = (
                f"质量退化告警：词条 '{key}' 的当前评分 ({current_score}) "
                f"低于历史最高快照得分 ({snapshot_score})。请检查是否存在翻译退化。"
            )
            return RegressionResult(
                is_degraded=True,
                snapshot_score=snapshot_score,
                current_score=current_score,
                warning_message=msg,
            )

        return None

    async def update_snapshot(self, key: str, translation: str, score: int):
        """
        更新快照。仅当当前得分大于等于历史得分时更新。
        """
        snapshots = await self._read_snapshots()
        if key not in snapshots or score >= snapshots[key].get("score", 0):
            snapshots[key] = {"translation": translation, "score": score}
            await self._write_snapshots(snapshots)
