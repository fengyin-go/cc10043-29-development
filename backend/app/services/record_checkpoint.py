"""记录检查点领域服务：管理接入任务的断点位置，支持恢复和回溯，提供检查点的确认和过期管理。

数据链路位置：断点管理层，为接入任务提供可靠的断点记录和恢复依据，是续采策略的数据基础。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.base import BaseModuleService
from app.store import store


class RecordCheckpointService(BaseModuleService):
    MODULE = "record_checkpoint"
    ENTITY = "检查点"
    OPERATION_TERM = "接入"
    LIST_FIELDS = ["关联接入任务", "检查点类型", "检查点值", "创建时间", "确认状态"]
    REQUIRED_FIELDS = ["关联接入任务", "检查点类型", "检查点值"]
    STATUS_ORDER = ["待确认", "已确认", "已过期"]
    ACTION_RULES = {"确认检查点": "已确认", "废弃检查点": "已过期"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：断点记录与恢复 ----

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        """确认/废弃检查点后，同步接入起点核验的有效边界。"""
        entry, message = super().run_action(entry_id, action)
        if entry is not None and action in ("确认检查点", "废弃检查点"):
            refreshed = self._refresh_start_verify(entry)
            if refreshed and action == "确认检查点":
                message += f"；已向 {refreshed} 张核验单补充有效边界"
        return entry, message

    @staticmethod
    def _refresh_start_verify(entry: dict[str, Any]) -> int:
        """把检查点状态变化通知给接入起点核验，返回受影响的核验单数量。"""
        from app.services import service_for
        verifier = service_for("start_verify")
        if verifier is None or not hasattr(verifier, "refresh_partition"):
            return 0
        partition = str(entry.get("关联接入任务", ""))
        return len(verifier.refresh_partition(partition))

    def create_checkpoint(self, task_name: str, point_type: str, point_value: str) -> dict[str, Any]:
        """创建新的检查点记录。"""
        rows = store.rows(self.MODULE)
        cp_id = max((int(r.get("id", 0)) for r in rows), default=0) + 1
        now = datetime.now(timezone.utc).isoformat()
        checkpoint = {
            "id": cp_id, "关联接入任务": task_name, "检查点类型": point_type,
            "检查点值": point_value, "创建时间": now, "确认状态": "待确认",
            "status": "待确认", "pending": True, "abnormal": False,
        }
        rows.append(checkpoint)
        return {"ok": True, "message": "检查点已创建", "checkpoint": checkpoint}

    def get_latest_checkpoint(self, task_name: str) -> dict[str, Any] | None:
        """获取指定接入任务的最新已确认检查点。"""
        rows = store.rows(self.MODULE)
        matched = [r for r in rows if task_name in str(r.get("关联接入任务", ""))
                   and r.get("status") == "已确认"]
        if not matched:
            return None
        return max(matched, key=lambda r: str(r.get("创建时间", "")))

    def validate_checkpoint_chain(self, entry_id: int) -> dict[str, Any]:
        """校验检查点链的完整性：是否存在断链或顺序异常。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": "检查点不存在"}
        task = entry.get("关联接入任务", "")
        rows = store.rows(self.MODULE)
        chain = sorted(
            [r for r in rows if task in str(r.get("关联接入任务", ""))],
            key=lambda r: str(r.get("创建时间", "")))
        gaps = []
        for i in range(1, len(chain)):
            prev_val = chain[i - 1].get("检查点值", "")
            curr_val = chain[i].get("检查点值", "")
            if prev_val >= curr_val:
                gaps.append(f"检查点值非递增: {prev_val} → {curr_val}")
        return {
            "ok": len(gaps) == 0,
            "task": task,
            "chain_length": len(chain),
            "gaps": gaps,
        }

    def route_to_resume(self, entry_id: int) -> dict[str, Any] | None:
        """检查点路由到续采策略，返回匹配的续采规则。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return None
        point_type = entry.get("检查点类型", "")
        policies = store.rows("resume_policy")
        for policy in policies:
            if policy.get("status") == "已启用" and point_type in policy.get("续采起点类型", ""):
                return {"policy": policy, "checkpoint": entry}
        return None

    def audit_expired_checkpoints(self) -> list[int]:
        """审计过期检查点并批量标记。"""
        rows = store.rows(self.MODULE)
        expired_ids = []
        now = datetime.now(timezone.utc)
        for row in rows:
            if row.get("status") != "待确认":
                continue
            created_str = str(row.get("创建时间", ""))
            try:
                created = datetime.fromisoformat(created_str)
                if (now - created).days > 30:
                    row["status"] = "已过期"
                    expired_ids.append(int(row.get("id", 0)))
            except ValueError:
                continue
        if expired_ids:
            audit_rows = store.rows("stream_audit")
            aid = max((int(r.get("id", 0)) for r in audit_rows), default=0) + 1
            audit_rows.append({
                "id": aid, "处理时间": now.isoformat(), "数据源": "record_checkpoint",
                "消息总数": str(len(expired_ids)), "成功数": str(len(expired_ids)),
                "失败原因分布": "", "status": "正常", "pending": True, "abnormal": False,
            })
        return expired_ids

    def commit_offset(self, entry_id: int) -> str | None:
        """将已确认检查点提交到偏移量管理。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None or entry.get("status") != "已确认":
            return None
        offset_rows = store.rows("offset_manager")
        oid = max((int(r.get("id", 0)) for r in offset_rows), default=0) + 1
        now = datetime.now(timezone.utc).isoformat()
        offset_rows.append({
            "id": oid, "消费组": entry.get("关联接入任务", ""),
            "Topic/Queue": entry.get("关联接入任务", ""),
            "分区/分片": "0", "当前Offset": entry.get("检查点值", "0"),
            "消费延迟": "0", "status": "正常", "pending": True, "abnormal": False,
        })
        return now