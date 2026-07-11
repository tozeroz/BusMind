<template>
  <section class="page-grid line-detail-page">
    <div class="panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">线路详情</p>
          <h2>{{ line.line_name || line.service_no || '线路加载中' }}</h2>
          <p v-if="line.line_id">
            {{ line.start_station || '起点待补充' }} → {{ line.end_station || '终点待补充' }}
            · 方向 {{ line.direction }}
          </p>
        </div>
        <RouterLink class="ghost-button" to="/lines">返回列表</RouterLink>
      </div>

      <p v-if="loading" class="muted">正在加载线路和站点...</p>
      <p v-else-if="errorMessage" class="muted">{{ errorMessage }}</p>

      <div class="detail-grid detail-grid--three">
        <div class="panel-soft line-summary">
          <h3>线路信息</h3>
          <dl class="line-facts">
            <div><dt>线路编号</dt><dd>{{ line.line_code || '--' }}</dd></div>
            <div><dt>服务号</dt><dd>{{ line.service_no || '--' }}</dd></div>
            <div><dt>运营商</dt><dd>{{ line.operator || '--' }}</dd></div>
            <div><dt>运行状态</dt><dd>{{ line.status || '--' }}</dd></div>
            <div><dt>线路方向</dt><dd>{{ line.direction || '--' }}</dd></div>
            <div><dt>站点数量</dt><dd>{{ line.total_stations || stations.length }}</dd></div>
            <div><dt>线路距离</dt><dd>{{ formatDistance(line.distance_km) }}</dd></div>
            <div><dt>发车间隔</dt><dd>{{ formatInterval(line.interval_minutes) }}</dd></div>
            <div><dt>首班时间</dt><dd>{{ formatTime(line.first_departure_time) }}</dd></div>
            <div><dt>末班时间</dt><dd>{{ formatTime(line.last_departure_time) }}</dd></div>
            <div><dt>早高峰频率</dt><dd>{{ line.am_peak_freq || '--' }}</dd></div>
            <div><dt>晚高峰频率</dt><dd>{{ line.pm_peak_freq || '--' }}</dd></div>
          </dl>
        </div>
        <div class="panel-soft station-panel">
          <h3>真实站点顺序</h3>
          <ol class="station-list station-scroll">
            <li v-for="item in stations" :key="item.id || item.station_id">
              <span>
                <strong>{{ item.station?.station_name || '未知站点' }}</strong>
                <small>{{ item.station?.road_name || item.station?.address || '' }}</small>
              </span>
              <small>第 {{ item.stop_sequence || item.order_index }} 站 · {{ item.station?.station_code || '' }}</small>
            </li>
          </ol>
          <p v-if="!loading && !errorMessage && stations.length === 0" class="muted">该线路暂时没有站点数据。</p>
        </div>

        <div class="panel-soft eta-panel">
          <div class="eta-head">
            <h3>实时 ETA 预测</h3>
            <div class="eta-controls">
              <label>
                <span>车辆</span>
                <select v-model.number="selectedVehicleId" :disabled="realtimeVehicles.length === 0">
                  <option :value="null">-- 选择车辆 --</option>
                  <option v-for="v in realtimeVehicles" :key="v.vehicle_id" :value="v.vehicle_id">
                    {{ v.vehicle_code || v.vehicle_id }} · {{ v.status || '未知状态' }}
                  </option>
                </select>
              </label>
              <label>
                <span>目标站点</span>
                <select v-model.number="selectedStationId" :disabled="stations.length === 0">
                  <option :value="null">-- 选择站点 --</option>
                  <option
                    v-for="item in stations"
                    :key="item.station_id || item.id"
                    :value="item.station?.station_id || item.station_id"
                  >
                    {{ item.station?.station_name || '未知站点' }}
                  </option>
                </select>
              </label>
              <button
                class="ghost-button"
                type="button"
                :disabled="!canQueryEta || etaLoading"
                @click="refreshEta"
              >
                {{ etaLoading ? '查询中...' : '刷新 ETA' }}
              </button>
            </div>
          </div>

          <p v-if="etaEmptyVehicles" class="muted">
            当前线路暂无实时车辆数据，可先在 Admin 页触发 LTA 刷新或检查数据库。
          </p>
          <p v-else-if="!selectedVehicleId" class="muted">选择一辆车查看它到目标站点的预计到达时间。</p>
          <p v-else-if="!selectedStationId" class="muted">在右侧下拉里选一个目标站点。</p>

          <div v-if="etaResult" class="eta-card">
            <div class="eta-main">
              <span class="eta-minutes">{{ etaResult.predicted_eta_minutes }}<small>分钟</small></span>
              <span class="eta-arrival">预计到达 {{ formatClock(etaResult.arrival_time) }}</span>
            </div>
            <dl class="eta-factors">
              <div><dt>数据源</dt><dd>{{ etaResult.factors?.source || '--' }}</dd></div>
              <div><dt>模型版本</dt><dd>{{ etaResult.model_version || '--' }}</dd></div>
              <div><dt>置信度</dt><dd>{{ formatConfidence(etaResult.factors?.confidence) }}</dd></div>
              <div><dt>距离</dt><dd>{{ formatMeters(etaResult.factors?.distance_meters) }}</dd></div>
              <div><dt>速度</dt><dd>{{ formatSpeed(etaResult.factors?.speed_kph) }}</dd></div>
            </dl>
          </div>
          <p v-if="etaError" class="muted eta-error">{{ etaError }}</p>
        </div>
      </div>

      <div class="detail-grid detail-grid--three history-grid">
        <section class="panel-soft history-panel">
          <div class="eta-head">
            <h3>线路 ETA 历史</h3>
            <button class="ghost-button compact-ghost" type="button" :disabled="etaHistoryLoading" @click="loadEtaHistory">
              {{ etaHistoryLoading ? '加载中' : '刷新' }}
            </button>
          </div>
          <p v-if="etaHistoryError" class="muted eta-error">{{ etaHistoryError }}</p>
          <div v-if="etaHistoryItems.length" class="history-list">
            <article v-for="item in etaHistoryItems.slice(0, 8)" :key="item.eta_prediction_id || `${item.vehicle_id}-${item.target_station_id}`" class="history-row">
              <div>
                <strong>{{ formatEtaMinutes(item.predicted_eta_minutes) }} 分钟</strong>
                <span>车辆 {{ item.vehicle_id }} · 目标站 {{ item.target_station_id }}</span>
              </div>
              <div class="history-meta">
                <span>{{ formatClock(item.arrival_time) || '--' }}</span>
                <span v-if="item.confidence != null">置信度 {{ formatConfidence(item.confidence) }}</span>
                <span v-if="item.model_version">{{ item.model_version }}</span>
              </div>
            </article>
          </div>
          <p v-else-if="!etaHistoryLoading" class="muted">该线路暂无 ETA 历史记录。</p>
        </section>

        <section class="panel-soft history-panel">
          <div class="eta-head">
            <h3>线路客载历史</h3>
            <button class="ghost-button compact-ghost" type="button" :disabled="loadHistoryLoading" @click="loadLineLoadHistory">
              {{ loadHistoryLoading ? '加载中' : '刷新' }}
            </button>
          </div>
          <p v-if="loadHistoryError" class="muted eta-error">{{ loadHistoryError }}</p>
          <div v-if="loadHistoryItems.length" class="history-list">
            <article v-for="item in loadHistoryItems.slice(0, 8)" :key="item.load_prediction_id || `${item.vehicle_id}-${item.station_id}`" class="history-row">
              <div>
                <strong>{{ loadHistoryLevelText(item.predicted_load_level) }}</strong>
                <span>车辆 {{ item.vehicle_id }}<template v-if="item.station_id"> · 站点 {{ item.station_id }}</template></span>
              </div>
              <div class="history-meta">
                <span v-if="item.predicted_load_rate != null">客载率 {{ formatLoadRate(item.predicted_load_rate) }}</span>
                <span v-if="item.confidence != null">置信度 {{ formatConfidence(item.confidence) }}</span>
                <span v-if="item.model_version">{{ item.model_version }}</span>
              </div>
            </article>
          </div>
          <p v-else-if="!loadHistoryLoading" class="muted">该线路暂无客载历史记录。</p>
        </section>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getLineDetail } from '@/api/transit'
import { getRealtimeVehicles } from '@/api/vehicle'
import { getEta } from '@/api/intelligence'
import { getEtaPredictionsByLine, getLoadPredictionsByLine } from '@/api/history'

const route = useRoute()
const line = ref({})
const loading = ref(true)
const errorMessage = ref('')
const stations = computed(() => line.value.stations || [])

const realtimeVehicles = ref([])
const realtimeLoading = ref(false)
const realtimeErrorMessage = ref('')

const selectedVehicleId = ref(null)
const selectedStationId = ref(null)

const etaLoading = ref(false)
const etaResult = ref(null)
const etaError = ref('')

const etaHistoryItems = ref([])
const etaHistoryLoading = ref(false)
const etaHistoryError = ref('')

const loadHistoryItems = ref([])
const loadHistoryLoading = ref(false)
const loadHistoryError = ref('')

const etaEmptyVehicles = computed(
  () => !realtimeLoading.value && realtimeVehicles.value.length === 0 && !realtimeErrorMessage.value
)
const canQueryEta = computed(
  () => Number.isFinite(selectedVehicleId.value) && Number.isFinite(selectedStationId.value)
)

const formatTime = (value) => value ? String(value).slice(0, 5) : '--'
const formatDistance = (value) => Number.isFinite(Number(value)) ? `${Number(value).toFixed(1)} km` : '--'
const formatInterval = (value) => Number(value) > 0 ? `${value} 分钟` : '--'

const formatClock = (value) => {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
}
const formatConfidence = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? num.toFixed(2) : '--'
}
const formatMeters = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? `${(num / 1000).toFixed(2)} km` : '--'
}
const formatSpeed = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? `${num.toFixed(1)} km/h` : '--'
}

const formatEtaMinutes = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? num.toFixed(1) : '--'
}

const formatLoadRate = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? `${(num * 100).toFixed(0)}%` : '--'
}

const loadHistoryLevelText = (value) => ({
  seats_available: '有座位',
  standing_available: '可站立',
  limited_standing: '站立空间有限',
  SEA: '有座位',
  SDA: '可站立',
  LSD: '站立空间有限',
  UNKNOWN: '未知'
}[value] || value || '未知')

const unwrapHistoryList = (response) => {
  const data = response?.data
  if (Array.isArray(data)) return data
  return data?.items || []
}

const loadEtaHistory = async () => {
  const lineId = Number(route.params.id)
  if (!Number.isFinite(lineId)) return
  etaHistoryLoading.value = true
  etaHistoryError.value = ''
  try {
    const response = await getEtaPredictionsByLine(lineId)
    etaHistoryItems.value = unwrapHistoryList(response)
  } catch (error) {
    etaHistoryItems.value = []
    etaHistoryError.value = error?.response?.data?.message || '线路 ETA 历史加载失败'
  } finally {
    etaHistoryLoading.value = false
  }
}

const loadLineLoadHistory = async () => {
  const lineId = Number(route.params.id)
  if (!Number.isFinite(lineId)) return
  loadHistoryLoading.value = true
  loadHistoryError.value = ''
  try {
    const response = await getLoadPredictionsByLine(lineId)
    loadHistoryItems.value = unwrapHistoryList(response)
  } catch (error) {
    loadHistoryItems.value = []
    loadHistoryError.value = error?.response?.data?.message || '线路客载历史加载失败'
  } finally {
    loadHistoryLoading.value = false
  }
}

async function loadRealtimeVehicles(lineId) {
  realtimeLoading.value = true
  realtimeErrorMessage.value = ''
  realtimeVehicles.value = []
  try {
    const response = await getRealtimeVehicles({ line_id: lineId })
    const list = Array.isArray(response?.data)
      ? response.data
      : Array.isArray(response?.data?.items)
        ? response.data.items
        : []
    realtimeVehicles.value = list.filter((v) => v && Number.isFinite(Number(v.vehicle_id)))
  } catch (error) {
    realtimeErrorMessage.value = error?.response?.data?.message || '实时车辆加载失败。'
  } finally {
    realtimeLoading.value = false
  }
}

async function refreshEta() {
  if (!canQueryEta.value) return
  etaLoading.value = true
  etaError.value = ''
  etaResult.value = null
  try {
    const response = await getEta({
      vehicle_id: selectedVehicleId.value,
      target_station_id: selectedStationId.value,
      line_id: Number(route.params.id),
    })
    etaResult.value = response?.data || null
  } catch (error) {
    etaError.value = error?.response?.data?.message || 'ETA 查询失败，请稍后重试。'
  } finally {
    etaLoading.value = false
  }
}

watch(canQueryEta, (ready) => { if (ready) refreshEta() })

onMounted(async () => {
  try {
    const response = await getLineDetail(route.params.id)
    line.value = response?.data || {}
  } catch (error) {
    errorMessage.value = error?.response?.data?.message || '线路详情加载失败，请检查后端和数据库连接。'
  } finally {
    loading.value = false
  }
  await loadRealtimeVehicles(route.params.id)
  await Promise.all([loadEtaHistory(), loadLineLoadHistory()])
})
</script>

<style scoped>
.line-detail-page {
  height: 100%;
  min-height: 0;
}

.line-detail-page > .panel {
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.line-summary,
.station-panel,
.eta-panel {
  min-height: 0;
}

.detail-grid {
  display: grid;
  gap: 20px;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  flex: 1;
  min-height: 0;
}

.detail-grid--three {
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr) minmax(0, 1.1fr);
}

.detail-grid--three > .panel-soft {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.line-summary {
  overflow-y: auto;
}

.station-scroll {
  max-height: 100%;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 8px;
}

.eta-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.line-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 18px 0 0;
}

.line-facts div {
  border-bottom: 1px solid var(--line);
  padding-bottom: 10px;
}

.line-facts dt {
  margin-bottom: 4px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
}

.line-facts dd {
  margin: 0;
  font-weight: 600;
}

.station-scroll li > span {
  display: grid;
  gap: 3px;
}

@media (max-width: 1100px) {
  .detail-grid--three {
    grid-template-columns: 1fr;
  }

  .line-summary,
  .eta-panel {
    overflow-y: visible;
  }

  .station-scroll {
    max-height: 55vh;
  }
}

.eta-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.eta-head h3 {
  margin: 0;
}

.eta-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.eta-controls label {
  display: grid;
  gap: 4px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.eta-controls select {
  min-width: 180px;
  padding: 6px 8px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: var(--surface, #1d1d1d);
  color: inherit;
}

.eta-card {
  margin-top: 8px;
  padding: 18px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(36, 116, 230, 0.18), rgba(36, 116, 230, 0.04));
  display: grid;
  gap: 16px;
}

.eta-main {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 12px;
}

.eta-minutes {
  font-size: 40px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.eta-minutes small {
  font-size: 14px;
  font-weight: 500;
  margin-left: 4px;
  color: rgba(255, 255, 255, 0.7);
}

.eta-arrival {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
}

.eta-factors {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin: 0;
}

.eta-factors dt {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 4px;
}

.eta-factors dd {
  margin: 0;
  font-weight: 600;
}

.eta-error {
  margin-top: 10px;
  color: #ff7878;
}

.history-grid {
  margin-top: 18px;
}

.history-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.history-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
}

.history-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.history-row strong {
  display: block;
  font-size: 16px;
}

.history-row span {
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
}

.history-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

@media (max-width: 760px) {
  .line-detail-page {
    height: auto;
  }

  .line-facts {
    grid-template-columns: 1fr;
  }
}
</style>
