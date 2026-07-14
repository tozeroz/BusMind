<template>
  <article class="map-chart-card chart-light selected-route-detail-card selected-line-detail-card">
    <header class="selected-route-detail-header">
      <div>
        <p class="eyebrow">当前线路</p>
        <h3>{{ line.line_name || line.title || '公交线路' }}</h3>
        <span>{{ line.line_code || '—' }}<template v-if="line.service_no"> · {{ line.service_no }}</template></span>
      </div>
      <button class="ghost-button compact-ghost" type="button" @click="emit('close')">关闭</button>
    </header>

    <div class="line-basic-grid">
      <p class="line-basic-wide"><span>起点 → 终点</span><strong>{{ line.start_station || '—' }} → {{ line.end_station || '—' }}</strong></p>
      <p><span>运营商 / 方向</span><strong>{{ line.operator || '—' }} · {{ directionLabel(line.direction) }}</strong></p>
      <p><span>总站数 / 距离</span><strong>{{ valueOrDash(line.total_stations) }} 站 · {{ distanceLabel(line.distance_km) }}</strong></p>
      <p class="line-basic-wide"><span>首班 / 末班</span><strong>{{ line.first_departure_time || '—' }} / {{ line.last_departure_time || '—' }}</strong></p>
      <p><span>发车间隔</span><strong>{{ intervalLabel(line.interval_minutes) }}</strong></p>
      <p><span>运行状态</span><strong :class="['line-status', `is-${line.status || 'unknown'}`]">{{ statusLabel(line.status) }}</strong></p>
    </div>

    <section class="line-load-section">
      <header>
        <div>
          <span>选中站点客载</span>
          <strong>{{ stationName || `站点 ${stationId || '—'}` }}</strong>
        </div>
        <small>{{ loads.length }} 辆车</small>
      </header>

      <p v-if="loading" class="line-load-message">正在读取当前线路车辆客载…</p>
      <p v-else-if="error" class="line-load-message is-error">{{ error }}</p>
      <ul v-else-if="loads.length" class="line-load-list">
        <li v-for="item in loads" :key="item.vehicle_id || item.vehicle_code">
          <div class="line-load-vehicle">
            <strong>{{ item.vehicle_code || `车辆 ${item.vehicle_id}` }}</strong>
            <span>{{ loadLevelLabel(item.load_level) }}</span>
          </div>
          <div class="line-load-metrics">
            <p><span>人数 / 容量</span><strong>{{ valueOrDash(item.onboard_count) }} / {{ valueOrDash(item.capacity) }}</strong></p>
            <p><span>客载率</span><strong>{{ percentLabel(item.load_rate) }}</strong></p>
            <p><span>客载分</span><strong>{{ numberLabel(item.load_score) }}</strong></p>
            <p><span>置信度</span><strong>{{ percentLabel(item.confidence) }}</strong></p>
          </div>
        </li>
      </ul>
      <p v-else class="line-load-message">该线路暂无可用车辆客载数据。</p>
    </section>
  </article>
</template>

<script setup>
const emit = defineEmits(['close'])

defineProps({
  line: { type: Object, required: true },
  stationId: { type: [Number, String], default: null },
  stationName: { type: String, default: '' },
  loads: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' }
})

const valueOrDash = (value) => value === 0 || value ? value : '—'
const numberLabel = (value) => Number.isFinite(Number(value)) ? Number(value).toFixed(0) : '—'
const percentLabel = (value) => Number.isFinite(Number(value)) ? `${Math.round(Number(value) * 100)}%` : '—'
const distanceLabel = (value) => Number.isFinite(Number(value)) ? `${Number(value).toFixed(1)} km` : '—'
const intervalLabel = (value) => Number.isFinite(Number(value)) && Number(value) > 0 ? `${Number(value)} 分钟` : '—'
const directionLabel = (value) => value === 1 || value === '1' ? '正向' : value === 2 || value === '2' ? '反向' : value || '—'
const statusLabel = (value) => ({ running: '正常运行', active: '正常运行', inactive: '暂停服务', offline: '暂停服务' }[value] || value || '状态未知')
const loadLevelLabel = (value) => ({
  seats_available: '有座位',
  standing_available: '可站立',
  limited_standing: '较拥挤',
  overcrowded: '过度拥挤',
  SEA: '有座位',
  SDA: '可站立',
  LSD: '较拥挤'
}[value] || value || '未知客载')
</script>

<style scoped>
.selected-line-detail-card {
  max-height: min(78vh, 720px);
  overflow: hidden;
}

.line-basic-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 7px;
  margin-top: 10px;
}

.line-basic-grid p {
  display: grid;
  gap: 3px;
  min-width: 0;
  margin: 0;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 7px;
  padding: 7px 9px;
  background: rgba(255, 255, 255, 0.07);
}

.line-basic-grid span,
.line-load-metrics span {
  color: rgba(255, 255, 255, 0.56);
  font-size: 9px;
  letter-spacing: 0.04em;
}

.line-basic-grid strong {
  overflow: hidden;
  color: #fff;
  font-size: 11px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.line-basic-wide {
  grid-column: 1 / -1;
}

.line-status {
  width: fit-content;
  border-radius: 999px;
  padding: 1px 7px;
  color: #bff7df !important;
  background: rgba(34, 197, 94, 0.18);
}

.line-status.is-inactive,
.line-status.is-offline {
  color: #ffd1c7 !important;
  background: rgba(239, 68, 68, 0.18);
}

.line-load-section {
  min-height: 0;
  margin-top: 10px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 8px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.08);
}

.line-load-section > header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.line-load-section > header div {
  display: grid;
  gap: 2px;
}

.line-load-section > header span,
.line-load-section > header small {
  color: rgba(255, 255, 255, 0.58);
  font-size: 10px;
}

.line-load-section > header strong {
  color: #fff;
  font-size: 12px;
}

.line-load-list {
  display: grid;
  gap: 7px;
  max-height: 260px;
  margin: 0;
  padding: 0 3px 0 0;
  overflow-y: auto;
  list-style: none;
  scrollbar-color: rgba(255, 255, 255, 0.45) rgba(255, 255, 255, 0.08);
}

.line-load-list > li {
  display: grid;
  gap: 7px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 7px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.07);
}

.line-load-vehicle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.line-load-vehicle strong {
  color: #fff;
  font-size: 11px;
}

.line-load-vehicle span {
  border-radius: 999px;
  padding: 2px 7px;
  color: #c9f5e7;
  font-size: 9px;
  background: rgba(45, 145, 137, 0.24);
}

.line-load-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 5px;
}

.line-load-metrics p {
  display: grid;
  gap: 2px;
  min-width: 0;
  margin: 0;
}

.line-load-metrics strong {
  color: #fff;
  font-size: 10px;
}

.line-load-message {
  margin: 0;
  padding: 18px 8px;
  color: rgba(255, 255, 255, 0.68);
  font-size: 11px;
  text-align: center;
}

.line-load-message.is-error {
  color: #ffd1c7;
}

@media (max-width: 520px) {
  .line-load-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
