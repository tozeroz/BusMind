<template>
  <section class="admin-vehicles-page">
    <aside class="vehicle-list-panel">
      <header class="vehicle-list-heading">
        <div>
          <p class="eyebrow">&#x8F66;&#x8F86;&#x7B5B;&#x9009;</p>
          <h2>&#x5168;&#x90E8;&#x8F66;&#x8F86;</h2>
        </div>
        <span>{{ filteredVehicles.length }} / {{ vehicles.length }}</span>
      </header>

      <label class="vehicle-search">
        <span>&#x8F66;&#x8F86;&#x7F16;&#x53F7;</span>
        <input v-model="filters.keyword" type="search" placeholder="Vehicle code / ID" />
      </label>

      <p v-if="errorMessage" class="form-tip">{{ errorMessage }}</p>

      <div class="vehicle-list-scroll">
        <article
          v-for="vehicle in filteredVehicles"
          :key="vehicle.vehicle_id"
          :class="['vehicle-list-row', { 'is-selected': isSelected(vehicle) }]"
        >
          <div>
            <strong>{{ vehicle.vehicle_code || `Vehicle ${vehicle.vehicle_id}` }}</strong>
            <span>{{ vehicle.line_name || vehicle.service_no || `Line ${vehicle.line_id || '--'}` }}</span>
          </div>
          <button class="ghost-button" type="button" :disabled="detailLoading" @click="selectVehicle(vehicle)">
            {{ isSelected(vehicle) ? '\u5df2\u9009\u62e9' : '\u8be6\u60c5' }}
          </button>
        </article>

        <p v-if="loading" class="vehicle-state">&#x6B63;&#x5728;&#x52A0;&#x8F7D;&#x8F66;&#x8F86;...</p>
        <p v-else-if="!filteredVehicles.length" class="vehicle-state">&#x6CA1;&#x6709;&#x5339;&#x914D;&#x7684;&#x8F66;&#x8F86;</p>
      </div>
    </aside>

    <section class="vehicle-detail-workspace">
      <template v-if="selectedVehicle">
        <article class="vehicle-summary-card">
          <header class="vehicle-summary-heading">
            <div>
              <p class="eyebrow">&#x8F66;&#x8F86;&#x8BE6;&#x60C5;</p>
              <h2>{{ selectedVehicle.vehicle_code || `Vehicle ${selectedVehicle.vehicle_id}` }}</h2>
              <span>{{ selectedVehicle.line_name || selectedVehicle.service_no || `Line ${selectedVehicle.line_id || '--'}` }}</span>
            </div>
            <span :class="['vehicle-status', `is-${statusTone}`]">{{ statusText }}</span>
          </header>

          <div class="vehicle-metric-grid">
            <article>
              <span>&#x5F53;&#x524D;&#x7AD9;</span>
              <strong>{{ currentStation }}</strong>
            </article>
            <article>
              <span>&#x5EF6;&#x8BEF;&#x5206;&#x949F;</span>
              <strong>{{ numberValue(selectedVehicle.delay_minutes) }} <small>min</small></strong>
            </article>
            <article>
              <span>&#x4EBA;&#x6570; / &#x5BB9;&#x91CF;</span>
              <strong>{{ numberValue(selectedVehicle.onboard_count) }} / {{ numberValue(selectedVehicle.capacity) }}</strong>
            </article>
            <article class="load-rate-metric">
              <span>&#x5BA2;&#x8F7D;&#x7387;</span>
              <strong>{{ loadRate }}%</strong>
              <i><b :style="{ width: `${loadRate}%` }"></b></i>
            </article>
          </div>
        </article>

        <VehicleRouteStrip :vehicle="selectedVehicle" :stations="routeStations" />
      </template>

      <div v-else class="vehicle-detail-empty">
        <div class="empty-badge">BUS</div>
        <h2>&#x9009;&#x62E9;&#x4E00;&#x8F86;&#x8F66;&#x67E5;&#x770B;&#x8FD0;&#x884C;&#x8BE6;&#x60C5;</h2>
        <p>&#x8F66;&#x8F86;&#x5F53;&#x524D;&#x7AD9;&#x3001;&#x5EF6;&#x8BEF;&#x3001;&#x5BA2;&#x8F7D;&#x4E0E;&#x7EBF;&#x8DEF;&#x7AD9;&#x5E8F;&#x5C06;&#x663E;&#x793A;&#x5728;&#x8FD9;&#x91CC;&#x3002;</p>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import VehicleRouteStrip from '@/modules/admin/components/VehicleRouteStrip.vue'
import { useAdminVehicles } from '@/modules/admin/composables/useAdminVehicles'

const {
  filters, vehicles, filteredVehicles, selectedVehicle, routeStations,
  loading, detailLoading, errorMessage, selectVehicle
} = useAdminVehicles()

const numberValue = (value) => Number.isFinite(Number(value)) ? Number(value) : '--'

const currentStation = computed(() => selectedVehicle.value?.current_station_name
  || selectedVehicle.value?.current_position_text
  || selectedVehicle.value?.current_station_id
  || '--')

const loadRate = computed(() => {
  const vehicle = selectedVehicle.value || {}
  let rate = Number(vehicle.load_percent)
  if (!Number.isFinite(rate)) {
    rate = Number(vehicle.load_rate)
    if (Number.isFinite(rate) && rate <= 2) rate *= 100
  }
  if (!Number.isFinite(rate) && Number(vehicle.capacity) > 0) {
    rate = Number(vehicle.onboard_count || 0) / Number(vehicle.capacity) * 100
  }
  return Math.max(0, Math.min(100, Math.round(Number.isFinite(rate) ? rate : 0)))
})

const statusTone = computed(() => {
  const status = String(selectedVehicle.value?.status || '').toLowerCase()
  if (status.includes('delay')) return 'warning'
  if (status.includes('offline') || status.includes('inactive')) return 'muted'
  return 'normal'
})

const statusText = computed(() => ({
  normal: '\u6b63\u5e38\u8fd0\u884c',
  warning: '\u5ef6\u8bef',
  muted: '\u79bb\u7ebf'
})[statusTone.value])

const isSelected = (vehicle) => String(selectedVehicle.value?.vehicle_id) === String(vehicle.vehicle_id)
</script>

<style scoped>
.admin-vehicles-page {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(260px, 310px) minmax(0, 1fr);
  gap: 18px;
  overflow: hidden;
}

.vehicle-list-panel,
.vehicle-summary-card,
.vehicle-detail-empty {
  border: 1px solid rgba(255, 255, 255, .2);
  border-radius: 10px;
  background: linear-gradient(145deg, rgba(255,255,255,.11), rgba(69,107,147,.26));
  box-shadow: inset 0 1px rgba(255,255,255,.11), 0 18px 42px rgba(9, 28, 49, .14);
  backdrop-filter: blur(18px) saturate(125%);
  -webkit-backdrop-filter: blur(18px) saturate(125%);
}

.vehicle-list-panel {
  min-height: 0;
  padding: 18px;
  display: grid;
  grid-template-rows: auto auto auto minmax(0, 1fr);
  gap: 14px;
  overflow: hidden;
}

.vehicle-list-heading,
.vehicle-summary-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.vehicle-list-heading p,
.vehicle-list-heading h2,
.vehicle-summary-heading p,
.vehicle-summary-heading h2 { margin: 0; }
.vehicle-list-heading h2 { margin-top: 4px; font-size: 21px; }
.vehicle-list-heading > span { color: rgba(255,255,255,.62); font-size: 12px; }

.vehicle-search { display: grid; gap: 7px; }
.vehicle-search span { color: rgba(255,255,255,.7); font-size: 12px; }
.vehicle-search input {
  width: 100%;
  border: 1px solid rgba(255,255,255,.18);
  border-radius: 8px;
  padding: 11px 12px;
  color: #fff;
  background: rgba(9, 33, 55, .34);
  outline: none;
}
.vehicle-search input:focus { border-color: #8de4ce; box-shadow: 0 0 0 3px rgba(141,228,206,.12); }

.vehicle-list-scroll {
  min-height: 0;
  display: grid;
  align-content: start;
  gap: 9px;
  overflow-y: auto;
  padding-right: 5px;
  scrollbar-width: thin;
  scrollbar-color: rgba(141,228,206,.7) rgba(255,255,255,.06);
}

.vehicle-list-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border: 1px solid rgba(255,255,255,.1);
  border-radius: 8px;
  padding: 11px;
  background: rgba(9, 33, 55, .18);
}
.vehicle-list-row.is-selected { border-color: #8de4ce; background: rgba(83, 190, 164, .16); }
.vehicle-list-row > div { min-width: 0; display: grid; gap: 4px; }
.vehicle-list-row strong,
.vehicle-list-row span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.vehicle-list-row span { color: rgba(255,255,255,.58); font-size: 11px; }
.vehicle-list-row button { flex: 0 0 auto; padding: 7px 10px; font-size: 11px; }
.vehicle-state { padding: 24px 8px; text-align: center; color: rgba(255,255,255,.58); }
.form-tip { margin: 0; color: #ffd4bd; font-size: 12px; }

.vehicle-detail-workspace {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 18px;
  overflow-y: auto;
  padding-right: 3px;
}

.vehicle-summary-card { padding: 20px; }
.vehicle-summary-heading h2 { margin-top: 4px; font-size: 28px; }
.vehicle-summary-heading div > span { display: block; margin-top: 6px; color: rgba(255,255,255,.6); }
.vehicle-status { border-radius: 999px; padding: 8px 12px; font-size: 12px; font-weight: 700; }
.vehicle-status.is-normal { color: #17334a; background: #aef0de; }
.vehicle-status.is-warning { color: #5a321f; background: #ffd1b9; }
.vehicle-status.is-muted { color: rgba(255,255,255,.7); background: rgba(255,255,255,.12); }

.vehicle-metric-grid { display: grid; grid-template-columns: 1.35fr repeat(3, 1fr); gap: 12px; margin-top: 18px; }
.vehicle-metric-grid article { min-width: 0; border: 1px solid rgba(255,255,255,.14); border-radius: 8px; padding: 14px; background: linear-gradient(145deg,rgba(255,255,255,.08),rgba(8,32,54,.18)); backdrop-filter: blur(12px); }
.vehicle-metric-grid article > span { display: block; color: rgba(255,255,255,.56); font-size: 11px; }
.vehicle-metric-grid strong { display: block; margin-top: 7px; overflow: hidden; color: #fff; font-size: 18px; text-overflow: ellipsis; white-space: nowrap; }
.vehicle-metric-grid small { color: rgba(255,255,255,.5); font-size: 11px; font-weight: 500; }
.load-rate-metric i { display: block; height: 5px; margin-top: 10px; overflow: hidden; border-radius: 999px; background: rgba(255,255,255,.1); }
.load-rate-metric b { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #62cdb3, #b8f0e3); }

.vehicle-detail-empty { min-height: 420px; display: grid; place-content: center; justify-items: center; padding: 40px; text-align: center; }
.empty-badge { border-radius: 8px; padding: 12px 15px; color: #17334a; font-size: 13px; font-weight: 900; letter-spacing: .12em; background: #aef0de; }
.vehicle-detail-empty h2 { margin: 18px 0 8px; }
.vehicle-detail-empty p { max-width: 480px; margin: 0; color: rgba(255,255,255,.58); }

@media (max-width: 1100px) {
  .vehicle-metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 820px) {
  .admin-vehicles-page { grid-template-columns: 1fr; overflow: visible; }
  .vehicle-list-panel { max-height: 460px; }
  .vehicle-detail-workspace { overflow: visible; }
}

@media (max-width: 560px) {
  .vehicle-metric-grid { grid-template-columns: 1fr; }
  .vehicle-summary-heading { flex-direction: column; }
}
</style>
