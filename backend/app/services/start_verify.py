"""接入起点核验领域服务：为无断点分区核验有证据的续采起点。

数据链路位置：接入恢复层，夹在记录检查点与续采策略之间——
刚建立的分区和丢过检查点的老分区都先在这里拿到有证据的起点，
检查点确认入口向这里补充有效边界，续采策略收到依据后才允许实际读源。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.base import BaseModuleService
from app.store import store


def _to_int(value: Any) -> int | None:
    """把检查点值、上报位置等字符串安全转成整数，转不了就视为无证据。"""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


class StartVerifyService(BaseModuleService):
    MODULE = "start_verify"
    ENTITY = "核验单"
    OPERATION_TERM = "核验"
    LIST_FIELDS = ["分区标识", "起点证据类型", "最早可读位置", "未证实范围", "核验说明"]
    REQUIRED_FIELDS = ["分区标识"]
    STATUS_ORDER = ["待核验", "已核验", "缺证据", "续采中"]
    ACTION_RULES = {"执行核验": "已核验", "发起续采": "续采中"}
    NEGATIVE_ACTIONS = []

    # ---- 登记与动作 ----

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        entry, missing = super().create_entry(values)
        if entry is not None:
            # 证据类字段由核验流程填写，登记时只接受分区标识和源端上报。
            entry["起点证据类型"] = "待核验"
            entry["最早可读位置"] = ""
            entry["未证实范围"] = ""
            entry["核验说明"] = str(values.get("核验说明", "") or "待核验接入起点")
            entry["源端最早位置"] = str(values.get("源端最早位置", "") or "").strip()
            entry["已确认边界"] = ""
            entry["计划读取起点"] = ""
            entry["实际开读位置"] = ""
            entry["旧段线索"] = ""
        return entry, missing

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
        if action == "执行核验":
            result = self.verify_partition(entry_id)
            return store.find(self.MODULE, entry_id), result["message"]
        if action == "发起续采":
            result = self.begin_resume(entry_id)
            if not result["ok"]:
                return None, result["message"]
            return store.find(self.MODULE, entry_id), result["message"]
        return None, f"动作「{action}」不属于{self.MODULE}可执行范围"

    # ---- 业务扩展：起点核验与续采放行 ----

    def verify_partition(self, entry_id: int) -> dict[str, Any]:
        """对单个分区执行接入起点核验，结论落到核验单上。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"{self.ENTITY} {entry_id} 不存在或已归档"}
        evidence = self._resolve(entry)
        if not evidence["ok"]:
            entry["status"] = "缺证据"
            entry["pending"] = True
            entry["abnormal"] = True
            return {"ok": False, "message": f"核验结论：缺证据——{evidence['reason']}"}
        if entry.get("status") != "续采中":
            entry["status"] = "已核验"
        entry["pending"] = True
        entry["abnormal"] = False
        return {"ok": True, "message": f"核验通过：{entry['核验说明']}", "evidence": evidence}

    def begin_resume(self, entry_id: int) -> dict[str, Any]:
        """发起续采：开读前重核证据，拿到依据的分区才允许按计划实际读源。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"{self.ENTITY} {entry_id} 不存在或已归档"}
        evidence = self._resolve(entry)
        if not evidence["ok"]:
            entry["status"] = "缺证据"
            entry["pending"] = True
            entry["abnormal"] = True
            return {"ok": False, "message": f"续采未获起点依据，禁止开读：{evidence['reason']}"}
        entry["status"] = "续采中"
        entry["pending"] = True
        entry["abnormal"] = False
        plan = {
            "分区标识": entry.get("分区标识", ""),
            "读取起点": evidence["read_from"],
            "实际开读位置": evidence["fetch_from"],
            "未证实范围": entry.get("未证实范围", ""),
            "起点证据": entry.get("起点证据类型", ""),
            "旧段线索": entry.get("旧段线索", ""),
        }
        message = f"续采已开读：读取起点 {plan['读取起点']}，实际开读位置 {plan['实际开读位置']}"
        if plan["未证实范围"]:
            message += f"，未证实范围 {plan['未证实范围']}（留旧段线索追查）"
        self._audit_resume(plan)
        return {"ok": True, "message": message, "plan": plan}

    def refresh_partition(self, partition: str) -> list[dict[str, Any]]:
        """重核某分区全部核验单：检查点确认或废弃后同步有效边界。"""
        target = partition.strip()
        updated = []
        for row in store.rows(self.MODULE):
            if str(row.get("分区标识", "")).strip() != target:
                continue
            evidence = self._resolve(row)
            if row.get("status") == "续采中":
                updated.append(row)
                continue
            if evidence["ok"]:
                row["status"] = "已核验"
                row["abnormal"] = False
            else:
                row["status"] = "缺证据"
                row["abnormal"] = True
            row["pending"] = True
            updated.append(row)
        return updated

    def report_source_position(self, entry_id: int, earliest: Any) -> dict[str, Any]:
        """消息源上报入口：登记该分区源端现存最早位置（新分区即起始记录）。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"{self.ENTITY} {entry_id} 不存在或已归档"}
        value = _to_int(earliest)
        if value is None or value < 0:
            return {"ok": False, "message": "上报位置必须是非负整数"}
        entry["源端最早位置"] = str(value)
        return {"ok": True, "message": f"源端现存最早位置已登记为 {value}"}

    def evidence_for(self, partition: str) -> dict[str, Any]:
        """供续采策略查询：该分区当前是否有核验通过的起点证据。"""
        target = partition.strip()
        for row in store.rows(self.MODULE):
            if str(row.get("分区标识", "")).strip() != target:
                continue
            if row.get("status") not in ("已核验", "续采中"):
                continue
            read_from = _to_int(row.get("计划读取起点"))
            if read_from is None:
                continue
            fetch_from = _to_int(row.get("实际开读位置"))
            return {
                "ok": True,
                "read_from": read_from,
                "fetch_from": fetch_from if fetch_from is not None else read_from,
                "unverified_range": str(row.get("未证实范围", "")),
                "evidence": str(row.get("起点证据类型", "")),
            }
        return {"ok": False, "reason": f"分区 {target} 尚无核验通过的起点证据"}

    def pending_partitions(self) -> dict[str, Any]:
        """待核分区明细：还没有可用起点证据、需要值班员处理的分区。"""
        items = []
        for row in store.rows(self.MODULE):
            if row.get("status") in ("已核验", "续采中"):
                continue
            items.append({
                "id": row.get("id"),
                "分区标识": row.get("分区标识", ""),
                "status": row.get("status", ""),
                "起点证据类型": row.get("起点证据类型", ""),
                "核验说明": row.get("核验说明", ""),
            })
        return {"total": len(items), "items": items}

    def domain_snapshot(self) -> dict[str, Any]:
        snap = super().domain_snapshot()
        snap["pending_partitions"] = self.pending_partitions()["items"]
        return snap

    # ---- 内部：证据链解析 ----

    def _resolve(self, entry: dict[str, Any]) -> dict[str, Any]:
        """按证据链重算核验单：已确认边界优先，其次源端上报；缺证据给明确原因。"""
        partition = str(entry.get("分区标识", "")).strip()
        checkpoints = [
            row for row in store.rows("record_checkpoint")
            if str(row.get("关联接入任务", "")).strip() == partition
        ]
        confirmed = self._checkpoint_values(checkpoints, "已确认")
        expired = self._checkpoint_values(checkpoints, "已过期")
        pending_count = sum(1 for row in checkpoints if row.get("status") == "待确认")
        source_earliest = _to_int(entry.get("源端最早位置"))
        trace = self._trace_leads(expired)
        entry["旧段线索"] = trace

        if confirmed:
            boundary = max(value for value, _ in confirmed)
            planned = boundary + 1
            fetch = max(planned, source_earliest) if source_earliest is not None else planned
            entry["已确认边界"] = str(boundary)
            entry["起点证据类型"] = "已确认检查点"
            entry["计划读取起点"] = str(planned)
            entry["实际开读位置"] = str(fetch)
            entry["最早可读位置"] = str(fetch)
            entry["未证实范围"] = f"{planned}-{fetch - 1}" if fetch > planned else ""
            note = f"已确认边界 {boundary}，计划从 {planned} 续读"
            if fetch > planned:
                note += f"；源端现存最早 {source_earliest}，{planned}-{fetch - 1} 交付情况未证实，实际开读 {fetch}"
            if trace:
                note += f"；旧段线索：{trace}"
            if pending_count:
                note += f"；另有 {pending_count} 条待确认检查点"
            entry["核验说明"] = note
            return {"ok": True, "read_from": planned, "fetch_from": fetch}

        if not checkpoints:
            # 全新分区：只能采用消息源给出的起始记录。
            if source_earliest is None:
                return self._mark_no_evidence(
                    entry, "全新分区无任何检查点，且消息源未上报起始记录：找不到合法起点，不能按零恢复")
            entry["起点证据类型"] = "源端起始记录"
            entry["计划读取起点"] = str(source_earliest)
            entry["实际开读位置"] = str(source_earliest)
            entry["最早可读位置"] = str(source_earliest)
            entry["未证实范围"] = ""
            entry["核验说明"] = f"全新分区，采用消息源给出的起始记录 {source_earliest} 作为接入起点"
            return {"ok": True, "read_from": source_earliest, "fetch_from": source_earliest}

        # 老分区：断点丢失，只剩过期或待确认检查点，保留能查到的历史范围。
        if source_earliest is None:
            return self._mark_no_evidence(
                entry, "无已确认检查点且消息源未上报现存最早位置：找不到合法起点，不能按零恢复")
        entry["起点证据类型"] = "源端现存最早位置"
        entry["计划读取起点"] = str(source_earliest)
        entry["实际开读位置"] = str(source_earliest)
        entry["最早可读位置"] = str(source_earliest)
        entry["未证实范围"] = f"0-{source_earliest - 1}" if source_earliest > 0 else ""
        note = f"断点已丢失，消息源上报现存最早位置 {source_earliest}，值班员可决定是否先读 {source_earliest} 之后的数据"
        if entry["未证实范围"]:
            note += f"；{entry['未证实范围']} 是否已交付暂时查不出"
        if len({value for value, _ in expired}) > 1:
            note += "；历史记录之间存在冲突"
        if trace:
            note += f"；旧段留线索追查：{trace}"
        if pending_count:
            note += f"；另有 {pending_count} 条待确认检查点，确认后可补充有效边界"
        entry["核验说明"] = note
        return {"ok": True, "read_from": source_earliest, "fetch_from": source_earliest}

    @staticmethod
    def _checkpoint_values(
        checkpoints: list[dict[str, Any]], status: str
    ) -> list[tuple[int, dict[str, Any]]]:
        values = []
        for row in checkpoints:
            if row.get("status") != status:
                continue
            value = _to_int(row.get("检查点值"))
            if value is None:
                continue
            values.append((value, row))
        return values

    @staticmethod
    def _trace_leads(expired: list[tuple[int, dict[str, Any]]]) -> str:
        """过期检查点留作追查旧段的线索，记录冲突时一并标注。"""
        if not expired:
            return ""
        ordered = sorted(expired, key=lambda item: str(item[1].get("创建时间", "")))
        parts = [f"过期检查点#{row.get('id')}={value}" for value, row in ordered]
        conflict = len({value for value, _ in expired}) > 1
        return "、".join(parts) + ("（记录冲突）" if conflict else "")

    @staticmethod
    def _mark_no_evidence(entry: dict[str, Any], reason: str) -> dict[str, Any]:
        """缺证据时只记录明确原因，绝不把分区标成已从零恢复。"""
        entry["起点证据类型"] = "无证据"
        entry["计划读取起点"] = ""
        entry["实际开读位置"] = ""
        entry["最早可读位置"] = ""
        entry["未证实范围"] = ""
        entry["核验说明"] = reason
        return {"ok": False, "reason": reason}

    def _audit_resume(self, plan: dict[str, Any]) -> None:
        """把每次开读计划写进流数据处理审计，未证实范围一并留痕。"""
        audit_rows = store.rows("stream_audit")
        aid = max((int(row.get("id", 0)) for row in audit_rows), default=0) + 1
        now = datetime.now(timezone.utc).isoformat()
        unverified = plan.get("未证实范围", "")
        audit_rows.append({
            "id": aid, "处理时间": now,
            "数据源": f"start_verify:{plan.get('分区标识', '')}",
            "消息总数": "1", "成功数": "1",
            "失败原因分布": f"未证实范围{unverified}" if unverified else "",
            "status": "偏差超标" if unverified else "正常",
            "pending": True, "abnormal": bool(unverified),
        })
