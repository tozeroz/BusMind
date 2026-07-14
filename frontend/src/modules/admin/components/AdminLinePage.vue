<template>
  <section class="admin-lines-page">
    <form class="line-filter-panel" @submit.prevent="applyFilters">
      <div class="filter-heading">
        <div>
          <p class="eyebrow">&#x7EBF;&#x8DEF;&#x7B5B;&#x9009;</p>
          <h2>&#x5FEB;&#x901F;&#x627E;&#x5230;&#x76EE;&#x6807;&#x7EBF;&#x8DEF;</h2>
        </div>
        <span>{{ filteredLines.length }} / {{ allLines.length }} &#x6761;&#x7EBF;&#x8DEF;</span>
      </div>
      <div class="filter-grid">
        <label>
          <span>&#x8FD0;&#x8425;&#x5546;</span>
          <select v-model="filters.operator">
            <option value="">&#x5168;&#x90E8;&#x8FD0;&#x8425;&#x5546;</option>
            <option v-for="operator in operators" :key="operator" :value="operator">{{ operator }}</option>
          </select>
        </label>
        <label>
          <span>&#x7ECF;&#x8FC7;&#x7AD9;&#x70B9;</span>
          <input v-model="filters.station" placeholder="Station name / code" />
        </label>
        <label>
          <span>&#x7EBF;&#x8DEF;&#x540D;&#x79F0; / &#x7F16;&#x7801;</span>
          <input v-model="filters.keyword" placeholder="Name / code / service no." />
        </label>
        <div class="filter-actions">
          <button class="ghost-button" type="button" @click="resetFilters">&#x91CD;&#x7F6E;</button>
          <button class="primary-button" type="submit" :disabled="filtering">
            {{ filtering ? '\u7b5b\u9009\u4e2d...' : '\u5e94\u7528\u7b5b\u9009' }}
          </button>
        </div>
      </div>
    </form>

    <p v-if="errorMessage" class="form-tip">{{ errorMessage }}</p>
    <div v-if="loading" class="line-page-state">&#x6B63;&#x5728;&#x52A0;&#x8F7D;&#x5168;&#x90E8;&#x7EBF;&#x8DEF;...</div>

    <section v-else class="line-workspace">
      <article v-if="selectedLine" class="selected-line-detail">
        <header class="selected-line-header">
          <div>
            <p class="eyebrow">&#x5F53;&#x524D;&#x7EBF;&#x8DEF;</p>
            <h2>{{ selectedLine.line_name || selectedLine.service_no }}</h2>
          </div>
          <span class="status-chip">{{ statusText(selectedLine.status) }}</span>
        </header>
        <div class="selected-line-grid">
          <div class="line-facts">
            <dl>
              <div><dt>&#x540D;&#x79F0; / &#x7F16;&#x7801; / &#x670D;&#x52A1;&#x53F7;</dt><dd>{{ value(selectedLine.line_name) }} / {{ value(selectedLine.line_code) }} / {{ value(selectedLine.service_no) }}</dd></div>
              <div><dt>&#x8FD0;&#x8425;&#x5546; / &#x65B9;&#x5411;</dt><dd>{{ value(selectedLine.operator) }} / {{ directionText(selectedLine.direction) }}</dd></div>
              <div><dt>&#x8D77;&#x70B9; / &#x7EC8;&#x70B9;</dt><dd>{{ value(selectedLine.start_station) }} &rarr; {{ value(selectedLine.end_station) }}</dd></div>
              <div><dt>&#x603B;&#x7AD9;&#x6570; / &#x8DDD;&#x79BB;</dt><dd>{{ numberValue(selectedLine.total_stations) }} / {{ numberValue(selectedLine.distance_km) }} km</dd></div>
              <div><dt>&#x9996;&#x73ED; / &#x672B;&#x73ED;</dt><dd>{{ value(selectedLine.first_departure_time) }} / {{ value(selectedLine.last_departure_time) }}</dd></div>
              <div><dt>&#x53D1;&#x8F66;&#x95F4;&#x9694; / &#x72B6;&#x6001;</dt><dd>{{ numberValue(selectedLine.interval_minutes) }} min / {{ statusText(selectedLine.status) }}</dd></div>
            </dl>
            <section class="station-sequence">
              <div><strong>&#x771F;&#x5B9E;&#x7AD9;&#x70B9;&#x987A;&#x5E8F;</strong><span>{{ selectedStations.length }} stops</span></div>
              <ol v-if="selectedStations.length">
                <li v-for="station in selectedStations.slice(0, 12)" :key="station.line_station_id || station.station_id">
                  {{ station.station_name || station.stop_name || station.station_code }}
                </li>
              </ol>
              <p v-else>&#x6682;&#x65E0;&#x7AD9;&#x70B9;&#x6570;&#x636E;</p>
            </section>
          </div>
          <LineFrequencyChart :line="selectedLine" />
        </div>
      </article>

      <div class="line-list-heading">
        <div><p class="eyebrow">&#x5168;&#x90E8;&#x7EBF;&#x8DEF;</p><h2>{{ selectedLine ? '\u5176\u4ed6\u7ebf\u8def' : '\u7ebf\u8def\u5217\u8868' }}</h2></div>
        <span v-if="detailLoading">&#x6B63;&#x5728;&#x8BFB;&#x53D6;&#x8BE6;&#x60C5;...</span>
      </div>
      <div class="admin-line-list">
        <article
          v-for="line in orderedLines"
          :key="line.line_id"
          :class="['admin-line-row', { 'is-selected': selectedLine && String(line.line_id) === String(selectedLine.line_id) }]"
        >
          <div class="line-primary">
            <strong>{{ line.line_name || line.service_no || line.line_code }}</strong>
            <span>{{ value(line.line_code) }} &middot; {{ value(line.service_no) }}</span>
          </div>
          <div class="line-secondary">
            <span>{{ value(line.operator) }}</span>
            <span>{{ value(line.start_station) }} &rarr; {{ value(line.end_station) }}</span>
          </div>
          <button class="ghost-button detail-button" type="button" :disabled="detailLoading" @click="selectLine(line)">
            {{ selectedLine && String(line.line_id) === String(selectedLine.line_id) ? '\u5df2\u7f6e\u9876' : '\u8be6\u60c5' }}
          </button>
        </article>
        <p v-if="!orderedLines.length" class="line-page-state">&#x6CA1;&#x6709;&#x627E;&#x5230;&#x5339;&#x914D;&#x7684;&#x7EBF;&#x8DEF;</p>
      </div>
    </section>
  </section>
</template>

<script setup>
import LineFrequencyChart from './LineFrequencyChart.vue'
import { useAdminLines } from '@/modules/admin/composables/useAdminLines'

const {
  filters, allLines, filteredLines, orderedLines, selectedLine, selectedStations,
  operators, loading, filtering, detailLoading, errorMessage,
  applyFilters, resetFilters, selectLine
} = useAdminLines()

const value = (input) => input || '--'
const numberValue = (input) => Number.isFinite(Number(input)) ? Number(input) : '--'
const directionText = (input) => input === 1 ? '\u53bb\u7a0b' : input === 2 ? '\u8fd4\u7a0b' : value(input)
const statusText = (input) => ({ running: '\u8fd0\u884c\u4e2d', active: '\u8fd0\u884c\u4e2d', suspended: '\u6682\u505c', inactive: '\u505c\u8fd0' }[input] || value(input))
</script>

<style scoped>
.admin-lines-page { min-height:0; height:calc(100% + 8px); margin-top:-8px; display:grid; grid-template-rows:auto auto minmax(0,1fr); gap:14px; overflow:hidden; color:#f7fbff; }
.line-filter-panel,.selected-line-detail,.line-workspace { border:1px solid rgba(255,255,255,.2); border-radius:10px; background:rgba(69,107,147,.4); backdrop-filter:blur(18px); }
.line-filter-panel { padding:16px 18px; }
.filter-heading,.selected-line-header,.line-list-heading { display:flex; align-items:flex-start; justify-content:space-between; gap:18px; }
.filter-heading h2,.filter-heading p,.selected-line-header h2,.selected-line-header p,.line-list-heading h2,.line-list-heading p { margin:0; }
.filter-heading h2,.line-list-heading h2 { margin-top:4px; font-size:20px; }.filter-heading>span,.line-list-heading>span { color:rgba(255,255,255,.65); font-size:12px; }
.filter-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)) auto; gap:12px; align-items:end; margin-top:14px; }
.filter-grid label { display:grid; gap:6px; color:rgba(255,255,255,.7); font-size:12px; }.filter-grid input,.filter-grid select { width:100%; min-height:40px; border:1px solid rgba(255,255,255,.24); border-radius:8px; padding:0 11px; color:#fff; background:rgba(17,45,76,.58); }.filter-grid option { color:#172c46; }
.filter-actions { display:flex; gap:8px; }.filter-actions button { min-height:40px; white-space:nowrap; }.primary-button { border:0; border-radius:8px; padding:0 15px; color:#143149; font-weight:800; background:#8de4ce; cursor:pointer; }
.line-workspace { min-height:0; display:flex; flex-direction:column; gap:14px; padding:16px; overflow:auto; scrollbar-gutter:stable; }
.selected-line-detail { flex:0 0 auto; padding:18px; background:rgba(52,92,132,.62); }.selected-line-header { align-items:center; margin-bottom:14px; }.selected-line-header h2 { margin-top:4px; font-size:24px; }.status-chip { border-radius:999px; padding:7px 12px; color:#b9f3de; background:rgba(60,186,150,.16); }
.selected-line-grid { display:grid; grid-template-columns:minmax(0,1.05fr) minmax(360px,.95fr); gap:16px; align-items:start; }.line-facts { min-width:0; }.line-facts dl { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:9px; margin:0; }.line-facts dl>div { min-height:68px; border:1px solid rgba(255,255,255,.14); border-radius:8px; padding:11px 13px; background:rgba(255,255,255,.06); }.line-facts dt { color:rgba(255,255,255,.58); font-size:11px; }.line-facts dd { margin:7px 0 0; font-size:13px; font-weight:750; line-height:1.4; }
.station-sequence { margin-top:10px; border:1px solid rgba(255,255,255,.14); border-radius:8px; padding:12px 14px; background:rgba(255,255,255,.05); }.station-sequence>div { display:flex; justify-content:space-between; gap:12px; }.station-sequence span,.station-sequence p { color:rgba(255,255,255,.6); font-size:11px; }.station-sequence ol { display:flex; flex-wrap:wrap; gap:7px; margin:10px 0 0; padding:0; list-style:none; }.station-sequence li { border-radius:999px; padding:5px 9px; color:rgba(255,255,255,.78); font-size:10px; background:rgba(255,255,255,.08); }
.line-list-heading { flex:0 0 auto; align-items:end; }.admin-line-list { display:grid; gap:8px; }.admin-line-row { display:grid; grid-template-columns:minmax(180px,.7fr) minmax(280px,1.3fr) auto; gap:16px; align-items:center; min-height:66px; border:1px solid rgba(255,255,255,.15); border-radius:9px; padding:10px 12px 10px 16px; background:rgba(255,255,255,.065); }.admin-line-row.is-selected { border-color:rgba(105,225,194,.62); background:rgba(72,170,151,.14); order:-1; }.line-primary,.line-secondary { display:grid; gap:5px; min-width:0; }.line-primary span,.line-secondary { color:rgba(255,255,255,.62); font-size:11px; }.line-secondary span { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.detail-button { min-width:76px; }
.line-page-state { display:grid; min-height:100px; place-items:center; color:rgba(255,255,255,.65); }.eyebrow { color:#9fe7d4; font-size:11px; font-weight:800; letter-spacing:.12em; }
@media(max-width:1100px){.filter-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.selected-line-grid{grid-template-columns:1fr}.admin-line-row{grid-template-columns:1fr auto}.line-secondary{grid-column:1/-1;grid-row:2}}
@media(max-width:720px){.filter-grid,.line-facts dl{grid-template-columns:1fr}.filter-actions{justify-content:flex-end}.admin-line-row{grid-template-columns:1fr auto}.selected-line-detail{padding:13px}}
</style>
