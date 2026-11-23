<template>
  <div class="app-shell">
    <aside class="app-side">
      <h1 class="app-title">API数据接入与消息流处理平台</h1>
      <nav class="nav-list">
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="nav-item">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>
    <main class="app-main">
      <header class="app-head">
        <span class="head-desc">面向第三方API和消息队列的数据接入、流式处理、水位管理和断点续采的采集治理平台</span>
        <span class="head-user">当前值班：数据工程组</span>
      </header>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
const navItems = [{ label: "运营概览", path: "/" }, { label: "API连接器", path: "/api_connector" }, { label: "消息流源", path: "/stream_source" }, { label: "偏移量管理", path: "/offset_manager" }, { label: "API调用调度", path: "/api_scheduler" }, { label: "记录检查点", path: "/record_checkpoint" }, { label: "接入起点核验", path: "/start_verify" }, { label: "消息解析器", path: "/message_parser" }, { label: "去重中心", path: "/dedup_center" }, { label: "水位追踪", path: "/watermark_tracker" }, { label: "频控保护", path: "/rate_guard" }, { label: "失败隔离区", path: "/failure_isolation" }, { label: "流数据处理审计", path: "/stream_audit" }, { label: "批量消息回放", path: "/batch_replay" }, { label: "字段转换器", path: "/field_transform" }, { label: "API调用日志", path: "/api_logger" }, { label: "数据落地配置", path: "/data_sink" }, { label: "Schema注册中心", path: "/schema_registry" }, { label: "流式数据导出", path: "/stream_export" }, { label: "续采策略", path: "/resume_policy" }, { label: "消息载荷存储", path: "/payload_store" }, { label: "吞吐量告警", path: "/throughput_alarm" }]
</script>
