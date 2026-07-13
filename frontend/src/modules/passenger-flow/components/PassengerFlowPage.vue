<!--
  文件：src/modules/passenger-flow/components/PassengerFlowPage.vue
  用途：实现 passenger-flow 业务模块中的页面容器或业务组件。
  存放内容：该业务领域专属的界面结构、响应式状态和业务协调代码。
  实现功能：集中承载模块业务功能，并与路由入口、公共层和 API 层保持职责分离。
-->
<template>
  <section class="page-grid">
    <div class="panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">客流数据</p>
          <h2>历史客流趋势</h2>
          <p class="muted">Passenger Flow 表示站点或线路上下车客流，不等同于车辆客载。</p>
        </div>
        <div class="card-actions">
          <select v-model="granularity" class="compact-input" @change="loadFlow">
            <option value="hour">按小时</option>
            <option value="day">按天</option>
            <option value="week">按周</option>
          </select>
          <button class="ghost-button" type="button" :disabled="loading" @click="loadFlow">
            {{ loading ? '加载中' : '刷新' }}
          </button>
        </div>
      </div>

      <p v-if="errorMessage" class="form-tip">{{ errorMessage }}</p>

      <div class="stats-row">
        <article class="stat-card"><span>进站总量</span><strong>{{ summary.total_tap_in }}</strong></article>
        <article class="stat-card"><span>出站总量</span><strong>{{ summary.total_tap_out }}</strong></article>
        <article class="stat-card"><span>客流总量</span><strong>{{ summary.total_flow }}</strong></article>
        <article class="stat-card"><span>主要等级</span><strong>{{ levelText(summary.dominant_flow_level) }}</strong></article>
      </div>
    </div>

    <div class="panel chart-grid">
      <section>
        <h3>客流趋势</h3>
        <div v-if="trendItems.length" class="bar-chart">
          <div v-for="item in trendItems.slice(0, 12)" :key="item.flow_record_id" class="bar-row">
            <span>{{ timeLabel(item.record_time) }}</span>
            <div class="bar-track"><i :style="{ width: `${flowWidth(item.total_flow)}%` }"></i></div>
            <strong>{{ item.total_flow }}</strong>
          </div>
        </div>
        <div v-else class="empty-board admin-empty">
          <strong>暂无历史客流</strong>
          <p>接口调用成功但当前筛选条件没有数据。</p>
        </div>
      </section>

      <section>
        <h3>接口口径</h3>
        <div class="empty-board admin-empty">
          <strong>第一阶段仅展示历史 Passenger Flow</strong>
          <p>客流预测接口保留为历史/兼容能力，按项目文档暂不在页面调用，避免把历史分析误写成预测模型。</p>
        </div>
      </section>
    </div>

    <div class="panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">线路客载</p>
          <h3>线路车辆客载预测</h3>
          <p class="muted">Passenger Load 表示车辆内客载状态，与站点/线路客流 (Passenger Flow) 不同。</p>
        </div>
        <select v-model="loadLineId" class="compact-input" @change="loadLoadPredictions">
          <option value="">全部线路</option>
          <option v-for="line in lines" :key="line.line_id" :value="String(line.line_id)">
            {{ line.line_name || line.service_no || `线路 ${line.line_id}` }}
          </option>
        </select>
      </div>

      <p v-if="loadErrorMessage" class="form-tip">{{ loadErrorMessage }}</p>

      <div class="card-list compact">
        <article v-for="item in loadPredictionItems.slice(0, 12)" :key="item.load_prediction_id || `${item.vehicle_id}-${item.station_id}`" class="vehicle-card">
          <strong>{{ item.line_id ? `线路 ${item.line_id}` : '线路未指定' }}</strong>
          <p>
            车辆 {{ item.vehicle_id || '—' }}
            <template v-if="item.station_id"> · 站点 {{ item.station_id }}</template>
            <template v-if="item.predicted_onboard_count != null"> · 预计 {{ item.predicted_onboard_count }} / {{ item.capacity || '?' }} 人</template>
          </p>
          <span class="level-tag" :class="crowdClass(loadLevelText(item.predicted_load_level))">{{ loadLevelText(item.predicted_load_level) }}</span>
          <span v-if="item.predicted_load_rate != null" class="muted">客载率 {{ formatPercent(item.predicted_load_rate) }}</span>
        </article>
        <p v-if="!loadPredictionItems.length" class="muted">暂无客载预测记录。</p>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getPassengerFlowTrend, getLoadPredictionsByLine, getLoadPrediction } from '@/api/history'
import { getLines } from '@/api/transit'
import { crowdClass } from '@/utils/format'

const granularity = ref('hour')
const trendItems = ref([])
const summary = ref({ total_tap_in: 0, total_tap_out: 0, total_flow: 0, dominant_flow_level: null })
const loading = ref(false)
const errorMessage = ref('')

const lines = ref([])
const loadLineId = ref('')
const loadPredictionItems = ref([])
const loadErrorMessage = ref('')

const maxFlow = computed(() => Math.max(1, ...trendItems.value.map((item) => Number(item.total_flow) || 0)))
const flowWidth = (value) => Math.max(4, Math.round((Number(value || 0) / maxFlow.value) * 100))

const levelText = (value) => ({ low: '舒适', medium: '适中', high: '拥挤' }[value] || value || '未知')
const loadLevelText = (value) => ({
  seats_available: '有座位',
  standing_available: '可站立',
  limited_standing: '站立空间有限',
  SEA: '有座位',
  SDA: '可站立',
  LSD: '站立空间有限',
  UNKNOWN: '未知'
}[value] || value || '未知')
const timeLabel = (value) => value ? new Date(value).toLocaleString([], { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '未知时间'
const formatPercent = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? `${(num * 100).toFixed(0)}%` : '--'
}

const unwrapList = (response, key) => {
  const data = response?.data
  if (Array.isArray(data)) return data
  return data?.[key] || data?.items || []
}

const loadLines = async () => {
  try {
    const response = await getLines({ page: 1, limit: 100 })
    lines.value = unwrapList(response, 'lines')
  } catch (error) {
    // 线路列表加载失败时静默处理，仅影响客载筛选
    lines.value = []
  }
}

const loadLoadPredictions = async () => {
  loadErrorMessage.value = ''
  if (!loadLineId.value) {
    loadPredictionItems.value = []
    return
  }
  try {
    const response = await getLoadPredictionsByLine(Number(loadLineId.value))
    const items = unwrapList(response, 'items')
    if (!items.length) {
      const latest = await getLoadPrediction(Number(loadLineId.value))
      const single = latest?.data
      loadPredictionItems.value = single ? [single] : []
    } else {
      loadPredictionItems.value = items
    }
  } catch (error) {
    loadPredictionItems.value = []
    loadErrorMessage.value = error?.response?.data?.message || '线路客载预测加载失败'
  }
}

const loadFlow = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const trendResponse = await getPassengerFlowTrend({ granularity: granularity.value })
    const trend = trendResponse.data || {}
    trendItems.value = trend.items || []
    summary.value = trend.summary || summary.value
  } catch (error) {
    trendItems.value = []
    errorMessage.value = error?.response?.data?.message || '客流数据加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadFlow()
  await loadLines()
})
</script>
