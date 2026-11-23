"""领域服务注册表：通用资源路由按模块 key 分派到独立业务服务。"""
from __future__ import annotations

from app.services.base import BaseModuleService
from app.services.api_connector import ApiConnectorService
from app.services.stream_source import StreamSourceService
from app.services.offset_manager import OffsetManagerService
from app.services.api_scheduler import ApiSchedulerService
from app.services.record_checkpoint import RecordCheckpointService
from app.services.start_verify import StartVerifyService
from app.services.message_parser import MessageParserService
from app.services.dedup_center import DedupCenterService
from app.services.watermark_tracker import WatermarkTrackerService
from app.services.rate_guard import RateGuardService
from app.services.failure_isolation import FailureIsolationService
from app.services.stream_audit import StreamAuditService
from app.services.batch_replay import BatchReplayService
from app.services.field_transform import FieldTransformService
from app.services.api_logger import ApiLoggerService
from app.services.data_sink import DataSinkService
from app.services.schema_registry import SchemaRegistryService
from app.services.stream_export import StreamExportService
from app.services.resume_policy import ResumePolicyService
from app.services.payload_store import PayloadStoreService
from app.services.throughput_alarm import ThroughputAlarmService

SERVICES: dict[str, BaseModuleService] = {
    "api_connector": ApiConnectorService(),
    "stream_source": StreamSourceService(),
    "offset_manager": OffsetManagerService(),
    "api_scheduler": ApiSchedulerService(),
    "record_checkpoint": RecordCheckpointService(),
    "start_verify": StartVerifyService(),
    "message_parser": MessageParserService(),
    "dedup_center": DedupCenterService(),
    "watermark_tracker": WatermarkTrackerService(),
    "rate_guard": RateGuardService(),
    "failure_isolation": FailureIsolationService(),
    "stream_audit": StreamAuditService(),
    "batch_replay": BatchReplayService(),
    "field_transform": FieldTransformService(),
    "api_logger": ApiLoggerService(),
    "data_sink": DataSinkService(),
    "schema_registry": SchemaRegistryService(),
    "stream_export": StreamExportService(),
    "resume_policy": ResumePolicyService(),
    "payload_store": PayloadStoreService(),
    "throughput_alarm": ThroughputAlarmService(),
}


def service_for(module: str) -> BaseModuleService | None:
    return SERVICES.get(module)
