<template>
  <section class="page">
    <header class="page-head">
      <div>
        <h2>运营概览</h2>
        <p class="page-desc">汇总各业务模块的关键指标，先看总量再看异常。</p>
      </div>
    </header>
    <div class="stat-row">
      <article v-for="card in cards" :key="card.label" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
      </article>
    </div>
    <table class="data-table">
      <thead>
        <tr><th>业务模块</th><th>今日新增</th><th>待处理</th><th>异常量</th></tr>
      </thead>
      <tbody>
        <tr v-for="row in moduleRows" :key="row.name">
          <td>{{ row.name }}</td>
          <td>{{ row.created }}</td>
          <td>{{ row.pending }}</td>
          <td>{{ row.abnormal }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchJson } from '@/api/client'

type Overview = {
  cards: { label: string; value: number }[]
  modules: { name: string; created: number; pending: number; abnormal: number }[]
}

const cards = ref<Overview['cards']>([])
const moduleRows = ref<Overview['modules']>([])

onMounted(async () => {
  try {
    const payload = await fetchJson<Overview>('/api/overview')
    cards.value = payload.cards
    moduleRows.value = payload.modules
  } catch {
    cards.value = [{"label": "业务模块", "value": 0}, {"label": "今日新增", "value": 0}]
    moduleRows.value = [{"name": "API连接器", "created": 0, "pending": 0, "abnormal": 0}, {"name": "消息流源", "created": 0, "pending": 0, "abnormal": 0}, {"name": "偏移量管理", "created": 0, "pending": 0, "abnormal": 0}, {"name": "API调用调度", "created": 0, "pending": 0, "abnormal": 0}, {"name": "记录检查点", "created": 0, "pending": 0, "abnormal": 0}, {"name": "接入起点核验", "created": 0, "pending": 0, "abnormal": 0}, {"name": "消息解析器", "created": 0, "pending": 0, "abnormal": 0}, {"name": "去重中心", "created": 0, "pending": 0, "abnormal": 0}, {"name": "水位追踪", "created": 0, "pending": 0, "abnormal": 0}, {"name": "频控保护", "created": 0, "pending": 0, "abnormal": 0}, {"name": "失败隔离区", "created": 0, "pending": 0, "abnormal": 0}, {"name": "流数据处理审计", "created": 0, "pending": 0, "abnormal": 0}, {"name": "批量消息回放", "created": 0, "pending": 0, "abnormal": 0}, {"name": "字段转换器", "created": 0, "pending": 0, "abnormal": 0}, {"name": "API调用日志", "created": 0, "pending": 0, "abnormal": 0}, {"name": "数据落地配置", "created": 0, "pending": 0, "abnormal": 0}, {"name": "Schema注册中心", "created": 0, "pending": 0, "abnormal": 0}, {"name": "流式数据导出", "created": 0, "pending": 0, "abnormal": 0}, {"name": "续采策略", "created": 0, "pending": 0, "abnormal": 0}, {"name": "消息载荷存储", "created": 0, "pending": 0, "abnormal": 0}, {"name": "吞吐量告警", "created": 0, "pending": 0, "abnormal": 0}]
  }
})
</script>
