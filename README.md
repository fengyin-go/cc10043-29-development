# API数据接入与消息流处理平台

面向第三方API和消息队列的数据接入、流式处理、水位管理和断点续采的采集治理平台

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。
两边各自独立启动，前端 dev server 已关掉自动打开页面，启动后按终端打印的地址手工打开。

## 目录结构

```text
.
├── frontend/                 Vue 3 + Vite + TypeScript 前端
│   ├── src/views/WorkbenchView.vue|tsx  全部模块共享工作台
│   ├── src/data/modules.ts              21个业务模块配置
│   ├── src/api/              统一请求封装
│   └── vite.config.ts        dev server 配置（open: false）
├── backend/                  FastAPI（Python） 后端
│   ├── app/routers/resource.py  通用查询/导出/登记/动作接口
│   ├── app/services/<key>.py    每个模块独立领域逻辑
│   ├── app/services/base.py     共享服务骨架
│   └── app/store.py          内存数据仓库与示例数据
├── .gitignore
└── docker-compose.yml
```

## 启动

### 后端

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./run.sh
```

健康检查：`curl http://127.0.0.1:8017/api/health`

### 前端

```bash
cd frontend
npm ci
npm run dev
```

前端默认监听 `http://127.0.0.1:5197/`，dev server 不会自动打开浏览器，
需要自己访问。`/api` 由 vite 代理到后端 `http://127.0.0.1:8017`。

## 业务模块

| 模块 | 目录 | 业务对象 | 主要字段 |
| --- | --- | --- | --- |
| API连接器 | `api_connector` | API连接器 | 连接器名称、API端点、认证方式 |
| 消息流源 | `stream_source` | 消息流源 | 源名称、中间件类型、Topic/Queue名 |
| 偏移量管理 | `offset_manager` | 偏移量记录 | 消费组、Topic/Queue、分区/分片 |
| API调用调度 | `api_scheduler` | 调用计划 | 计划名称、关联API、Cron表达式 |
| 记录检查点 | `record_checkpoint` | 检查点 | 关联接入任务、检查点类型、检查点值 |
| 接入起点核验 | `start_verify` | 核验单 | 分区标识、起点证据类型、最早可读位置 |
| 消息解析器 | `message_parser` | 解析模板 | 模板名称、消息格式、字段映射 |
| 去重中心 | `dedup_center` | 去重键 | 去重键名、关联数据源、去重窗口秒数 |
| 水位追踪 | `watermark_tracker` | 水位记录 | 数据源、水位字段、当前水位 |
| 频控保护 | `rate_guard` | 频控规则 | 规则名称、限流维度、每秒上限 |
| 失败隔离区 | `failure_isolation` | 隔离记录 | 失败消息ID、失败原因、原始Topic |
| 流数据处理审计 | `stream_audit` | 审计明细 | 处理时间、数据源、消息总数 |
| 批量消息回放 | `batch_replay` | 回放任务 | 回放范围、开始时间、结束时间 |
| 字段转换器 | `field_transform` | 转换规则 | 规则名称、源字段、目标字段 |
| API调用日志 | `api_logger` | 调用日志 | 调用时间、API名称、请求参数摘要 |
| 数据落地配置 | `data_sink` | 落地配置 | 配置名称、目标存储类型、写入模式 |
| Schema注册中心 | `schema_registry` | Schema版本 | Schema名称、版本号、字段定义 |
| 流式数据导出 | `stream_export` | 导出任务 | 任务名称、数据源、导出格式 |
| 续采策略 | `resume_policy` | 续采规则 | 规则名称、续采起点类型、续采步长 |
| 消息载荷存储 | `payload_store` | 原始载荷 | 采集批次、消息ID、原始载荷 |
| 吞吐量告警 | `throughput_alarm` | 告警规则 | 规则名称、监控数据源、吞吐量下限 |

## 约定

- 全部模块共享`frontend/src/views/WorkbenchView.vue|tsx`和一套资源路由。
- 每个模块仍保留独立`backend/app/services/<模块>.py`；纯前端保留
  `frontend/src/domain/<模块>.ts`，用于承载真实业务差异并维持36题位容量。
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。

领域：数据工程
子方向：数据采集、爬虫与RPA
