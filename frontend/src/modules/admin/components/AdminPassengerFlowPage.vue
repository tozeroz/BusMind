<template>
  <section class="admin-flow-page">
    <aside class="station-filter-panel">
      <header>
        <div>
          <p class="eyebrow">&#x7AD9;&#x70B9;&#x7B5B;&#x9009;</p>
          <h2>&#x5168;&#x90E8;&#x7AD9;&#x70B9;</h2>
        </div>
        <span>{{ filteredStations.length }} / {{ stations.length }}</span>
      </header>

      <label class="station-search">
        <span>&#x7AD9;&#x70B9;&#x540D;</span>
        <input v-model="filters.keyword" type="search" placeholder="Station name / code" />
      </label>

      <p v-if="errorMessage" class="form-tip">{{ errorMessage }}</p>

      <div class="station-list-scroll">
        <article
          v-for="station in filteredStations"
          :key="station.station_id"
          :class="['station-row', { 'is-selected': isSelected(station) }]"
        >
          <div>
            <strong>{{ station.station_name }}</strong>
            <span>{{ station.station_code || station.bus_stop_code || `Station ${station.station_id}` }}</span>
            <small>{{ station.road_name || station.address || station.zone || '--' }}</small>
          </div>
          <button class="ghost-button" type="button" :disabled="detailLoading" @click="selectStation(station)">
            {{ isSelected(station) ? '\u5df2\u9009\u62e9' : '\u8be6\u60c5' }}
          </button>
        </article>
        <p v-if="stationLoading" class="station-state">&#x6B63;&#x5728;&#x52A0;&#x8F7D;&#x7AD9;&#x70B9;...</p>
        <p v-else-if="!filteredStations.length" class="station-state">&#x6CA1;&#x6709;&#x5339;&#x914D;&#x7684;&#x7AD9;&#x70B9;</p>
      </div>
    </aside>

    <section class="flow-detail-workspace">
      <template v-if="selectedStation">
        <section class="history-flow-section">
          <header class="detail-heading">
            <div>
              <p class="eyebrow">&#x5386;&#x53F2;&#x5BA2;&#x6D41;&#x8D8B;&#x52BF;</p>
              <h2>{{ selectedStation.station_name }}</h2>
              <span>{{ selectedStation.station_code || selectedStation.bus_stop_code || `Station ${selectedStation.station_id}` }}</span>
            </div>
            <span v-if="detailLoading" class="loading-chip">&#x6B63;&#x5728;&#x8BFB;&#x53D6;&#x6570;&#x636E;</span>
          </header>

          <div class="flow-summary-grid">
            <article><span>&#x8FDB;&#x7AD9;&#x603B;&#x91CF;</span><strong>{{ formatNumber(summary.total_tap_in) }}</strong></article>
            <article><span>&#x51FA;&#x7AD9;&#x603B;&#x91CF;</span><strong>{{ formatNumber(summary.total_tap_out) }}</strong></article>
            <article><span>&#x5BA2;&#x6D41;&#x603B;&#x91CF;</span><strong>{{ formatNumber(summary.total_flow) }}</strong></article>
            <article><span>&#x8212;&#x9002;&#x7B49;&#x7EA7;</span><strong :class="['comfort-level', comfortClass]">{{ comfortText }}</strong></article>
          </div>

          <PassengerFlowChart
            eyebrow="Historical Passenger Flow"
            title="&#x8FDB;&#x7AD9;&#x4E0E;&#x51FA;&#x7AD9;&#x8D8B;&#x52BF;"
            :points="trendItems"
            :series="historySeries"
            time-key="record_time"
            empty-title="&#x6682;&#x65E0;&#x5386;&#x53F2;&#x5BA2;&#x6D41;"
            empty-description="&#x8BE5;&#x7AD9;&#x70B9;&#x5F53;&#x524D;&#x6CA1;&#x6709;&#x53EF;&#x7528;&#x7684;&#x8FDB;&#x51FA;&#x7AD9;&#x805A;&#x5408;&#x6570;&#x636E;&#x3002;"
          />
        </section>

        <section class="prediction-flow-section">
          <div class="prediction-note">
            <div>
              <p class="eyebrow">&#x5BA2;&#x6D41;&#x8D8B;&#x52BF;&#x9884;&#x6D4B;</p>
              <h2>&#x672A;&#x6765;&#x5BA2;&#x6D41;&#x53D8;&#x5316;</h2>
            </div>
            <span>&#x5B9E;&#x9A8C;&#x6027;&#x517C;&#x5BB9;&#x63A5;&#x53E3;</span>
          </div>
          <div v-if="predictionItems.length" class="prediction-meta">
            <span>{{ predictionRange }}</span>
            <span>{{ predictionModel }}</span>
            <span>{{ predictionConfidence }}</span>
          </div>
          <PassengerFlowChart
            eyebrow="Passenger Flow Prediction"
            title="&#x9884;&#x6D4B;&#x5BA2;&#x6D41;&#x66F2;&#x7EBF;"
            :points="predictionItems"
            :series="predictionSeries"
            time-key="predict_time"
            empty-title="&#x6682;&#x65E0;&#x5BA2;&#x6D41;&#x9884;&#x6D4B;"
            empty-description="&#x9884;&#x6D4B;&#x63A5;&#x53E3;&#x5DF2;&#x8C03;&#x7528;&#xFF0C;&#x4F46;&#x8BE5;&#x7AD9;&#x70B9;&#x5F53;&#x524D;&#x6CA1;&#x6709;&#x5B9E;&#x9A8C;&#x9884;&#x6D4B;&#x8BB0;&#x5F55;&#x3002;"
          />
        </section>
      </template>

      <div v-else class="flow-detail-empty">
        <div class="empty-mark">FLOW</div>
        <h2>&#x9009;&#x62E9;&#x7AD9;&#x70B9;&#x67E5;&#x770B;&#x5BA2;&#x6D41;&#x8D8B;&#x52BF;</h2>
        <p>&#x5386;&#x53F2;&#x8FDB;&#x51FA;&#x7AD9;&#x6570;&#x636E;&#x3001;&#x5BA2;&#x6D41;&#x7B49;&#x7EA7;&#x4E0E;&#x5B9E;&#x9A8C;&#x9884;&#x6D4B;&#x5C06;&#x663E;&#x793A;&#x5728;&#x8FD9;&#x91CC;&#x3002;</p>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import PassengerFlowChart from '@/modules/admin/components/PassengerFlowChart.vue'
import { useAdminPassengerFlow } from '@/modules/admin/composables/useAdminPassengerFlow'

const {
  filters,
  stations,
  filteredStations,
  selectedStation,
  trendItems,
  predictionItems,
  summary,
  stationLoading,
  detailLoading,
  errorMessage,
  selectStation
} = useAdminPassengerFlow()

const historySeries = [
  { key: 'tap_in_volume', label: '\u8fdb\u7ad9', color: '#69e1c2' },
  { key: 'tap_out_volume', label: '\u51fa\u7ad9', color: '#75a9ff' }
]
const predictionSeries = [
  { key: 'predicted_flow', label: '\u9884\u6d4b\u5ba2\u6d41', color: '#ffd09c' }
]

const formatNumber = (value) => new Intl.NumberFormat('zh-CN').format(Number(value) || 0)
const formatPredictionTime = (value) => {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '--' : date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit' })
}
const predictionRange = computed(() => {
  if (!predictionItems.value.length) return ''
  return `${formatPredictionTime(predictionItems.value[0]?.predict_time)} - ${formatPredictionTime(predictionItems.value.at(-1)?.predict_time)}`
})
const predictionModel = computed(() => {
  const model = predictionItems.value.find((item) => item?.model_version)?.model_version
  return model ? `模型 ${model}` : '预测模型未标注'
})
const predictionConfidence = computed(() => {
  const values = predictionItems.value.map((item) => Number(item?.confidence)).filter(Number.isFinite)
  if (!values.length) return '置信度未标注'
  const average = values.reduce((sum, value) => sum + value, 0) / values.length
  return `平均置信度 ${Math.round(average * 100)}%`
})
const normalizedLevel = computed(() => String(summary.value.dominant_flow_level || '').toLowerCase())
const comfortText = computed(() => ({
  low: '\u8212\u9002',
  medium: '\u9002\u4e2d',
  high: '\u62e5\u6324'
})[normalizedLevel.value] || '\u672a\u77e5')
const comfortClass = computed(() => ({ low: 'is-low', medium: 'is-medium', high: 'is-high' }[normalizedLevel.value] || 'is-unknown'))
const isSelected = (station) => String(selectedStation.value?.station_id) === String(station.station_id)
</script>

<style scoped>
.admin-flow-page { min-height:0; display:grid; grid-template-columns:minmax(260px,310px) minmax(0,1fr); gap:18px; overflow:hidden; }
.station-filter-panel,.history-flow-section,.prediction-flow-section,.flow-detail-empty { border:1px solid rgba(255,255,255,.2); border-radius:10px; background:linear-gradient(145deg,rgba(255,255,255,.11),rgba(69,107,147,.26)); box-shadow:inset 0 1px rgba(255,255,255,.11),0 18px 42px rgba(9,28,49,.14); backdrop-filter:blur(18px) saturate(125%); -webkit-backdrop-filter:blur(18px) saturate(125%); }
.station-filter-panel { min-height:0; display:grid; grid-template-rows:auto auto auto minmax(0,1fr); gap:14px; padding:18px; overflow:hidden; }
.station-filter-panel>header,.detail-heading,.prediction-note { display:flex; align-items:flex-start; justify-content:space-between; gap:14px; }.station-filter-panel p,.station-filter-panel h2,.detail-heading p,.detail-heading h2,.prediction-note p,.prediction-note h2 { margin:0; }.station-filter-panel h2 { margin-top:4px; font-size:21px; }.station-filter-panel>header>span { color:rgba(255,255,255,.58); font-size:11px; }
.station-search { display:grid; gap:7px; }.station-search span { color:rgba(255,255,255,.7); font-size:12px; }.station-search input { width:100%; border:1px solid rgba(255,255,255,.18); border-radius:8px; padding:11px 12px; color:#fff; background:rgba(9,33,55,.34); outline:none; }.station-search input:focus { border-color:#8de4ce; box-shadow:0 0 0 3px rgba(141,228,206,.12); }
.form-tip { margin:0; color:#ffd4bd; font-size:12px; }.station-list-scroll { min-height:0; display:grid; align-content:start; gap:9px; overflow-y:auto; padding-right:5px; scrollbar-width:thin; scrollbar-color:rgba(141,228,206,.7) rgba(255,255,255,.06); }
.station-row { display:flex; align-items:center; justify-content:space-between; gap:10px; border:1px solid rgba(255,255,255,.1); border-radius:8px; padding:11px; background:rgba(9,33,55,.18); }.station-row.is-selected { border-color:#8de4ce; background:rgba(83,190,164,.16); }.station-row>div { min-width:0; display:grid; gap:3px; }.station-row strong,.station-row span,.station-row small { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.station-row span { color:#aee9dc; font-size:11px; }.station-row small { color:rgba(255,255,255,.5); font-size:10px; }.station-row button { flex:0 0 auto; padding:7px 10px; font-size:11px; }.station-state { padding:24px 8px; text-align:center; color:rgba(255,255,255,.58); }
.flow-detail-workspace { min-width:0; min-height:0; overflow-y:auto; padding-right:3px; scrollbar-width:thin; scrollbar-color:rgba(141,228,206,.7) rgba(255,255,255,.06); }.history-flow-section,.prediction-flow-section { display:grid; gap:16px; padding:18px; }.prediction-flow-section { margin-top:18px; }
.detail-heading h2,.prediction-note h2 { margin-top:4px; font-size:24px; }.detail-heading div>span { display:block; margin-top:5px; color:rgba(255,255,255,.58); font-size:12px; }.loading-chip,.prediction-note>span { border-radius:999px; padding:7px 11px; color:#17334a; font-size:10px; font-weight:700; background:#aef0de; }.prediction-note>span { color:#6a4420; background:#ffd09c; }
.prediction-meta { display:flex; flex-wrap:wrap; gap:8px; }.prediction-meta span { border:1px solid rgba(255,255,255,.14); border-radius:999px; padding:6px 10px; color:rgba(255,255,255,.72); font-size:10px; background:rgba(8,32,54,.22); }
.flow-summary-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }.flow-summary-grid article { border:1px solid rgba(255,255,255,.14); border-radius:8px; padding:13px 15px; background:linear-gradient(145deg,rgba(255,255,255,.08),rgba(8,32,54,.18)); backdrop-filter:blur(12px); }.flow-summary-grid span { display:block; color:rgba(255,255,255,.55); font-size:11px; }.flow-summary-grid strong { display:block; margin-top:6px; font-size:20px; }.comfort-level.is-low { color:#8de4ce; }.comfort-level.is-medium { color:#ffd09c; }.comfort-level.is-high { color:#ffad9f; }.comfort-level.is-unknown { color:rgba(255,255,255,.62); }
.flow-detail-empty { min-height:100%; display:grid; place-content:center; justify-items:center; padding:40px; text-align:center; }.empty-mark { border-radius:8px; padding:12px 15px; color:#17334a; font-size:12px; font-weight:900; letter-spacing:.12em; background:#aef0de; }.flow-detail-empty h2 { margin:18px 0 8px; }.flow-detail-empty p { max-width:480px; margin:0; color:rgba(255,255,255,.58); }
@media(max-width:900px){.admin-flow-page{grid-template-columns:1fr;overflow:visible}.station-filter-panel{max-height:480px;border-right:0;border-bottom:1px solid rgba(255,255,255,.16)}.flow-detail-workspace{overflow:visible}}
@media(max-width:560px){.flow-summary-grid{grid-template-columns:1fr}.detail-heading,.prediction-note{flex-direction:column}}
</style>
