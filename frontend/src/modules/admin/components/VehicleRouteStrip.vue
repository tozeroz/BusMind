<template>
  <section class="vehicle-route-card">
    <header>
      <div>
        <p class="eyebrow">&#x5F53;&#x524D;&#x7EBF;&#x8DEF;</p>
        <h3>{{ vehicle?.line_name || vehicle?.service_no || `Line ${vehicle?.line_id || '--'}` }}</h3>
      </div>
      <span>&#x6C34;&#x5E73;&#x62D6;&#x52A8;&#x67E5;&#x770B;&#x5176;&#x4ED6;&#x7AD9;&#x70B9;</span>
    </header>
    <div
      ref="viewportRef"
      class="route-strip-viewport"
      @pointerdown="startDrag"
      @pointermove="dragRoute"
      @pointerup="stopDrag"
      @pointercancel="stopDrag"
      @pointerleave="stopDrag"
    >
      <div v-if="stations.length" class="route-strip-track" :style="{ '--station-count': stations.length }">
        <article
          v-for="(station, index) in stations"
          :key="station.line_station_id || station.id || station.station_id"
          :class="['route-station', { 'is-current': index === currentIndex, 'is-passed': currentIndex >= 0 && index < currentIndex }]"
        >
          <div class="station-marker">
            <span v-if="index === currentIndex" class="vehicle-marker" aria-label="Current vehicle">BUS</span>
            <i></i>
          </div>
          <strong>{{ station.station_name || station.station_code || `Stop ${index + 1}` }}</strong>
          <small>{{ station.station_code || `#${index + 1}` }}</small>
        </article>
      </div>
      <p v-else class="route-empty">&#x8BE5;&#x7EBF;&#x8DEF;&#x6682;&#x65E0;&#x7AD9;&#x5E8F;&#x6570;&#x636E;</p>
    </div>
    <footer>
      <span>&#x524D;&#x4E24;&#x7AD9;</span>
      <strong>{{ currentStationName }}</strong>
      <span>&#x540E;&#x4E24;&#x7AD9;</span>
    </footer>
  </section>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  vehicle: { type: Object, default: null },
  stations: { type: Array, default: () => [] }
})
const viewportRef = ref(null)
const dragState = { active: false, startX: 0, scrollLeft: 0 }

const currentIndex = computed(() => {
  const currentId = props.vehicle?.current_station_id
  if (currentId !== null && currentId !== undefined) {
    const index = props.stations.findIndex((station) => String(station.station_id) === String(currentId))
    if (index >= 0) return index
  }
  const currentName = String(props.vehicle?.current_station_name || '').trim().toLowerCase()
  return currentName
    ? props.stations.findIndex((station) => String(station.station_name || '').trim().toLowerCase() === currentName)
    : -1
})

const currentStationName = computed(() => {
  const station = props.stations[currentIndex.value]
  return station?.station_name || props.vehicle?.current_station_name || '--'
})

function centerCurrentStation() {
  nextTick(() => {
    const viewport = viewportRef.value
    if (!viewport || currentIndex.value < 0) return
    const current = viewport.querySelector('.route-station.is-current')
    if (!current) return
    viewport.scrollTo({ left: current.offsetLeft - viewport.clientWidth / 2 + current.clientWidth / 2, behavior: 'smooth' })
  })
}

function startDrag(event) {
  const viewport = viewportRef.value
  if (!viewport) return
  dragState.active = true
  dragState.startX = event.clientX
  dragState.scrollLeft = viewport.scrollLeft
  viewport.setPointerCapture?.(event.pointerId)
}

function dragRoute(event) {
  if (!dragState.active || !viewportRef.value) return
  viewportRef.value.scrollLeft = dragState.scrollLeft - (event.clientX - dragState.startX)
}

function stopDrag(event) {
  dragState.active = false
  viewportRef.value?.releasePointerCapture?.(event.pointerId)
}

watch(() => [props.vehicle?.vehicle_id, props.stations.length], centerCurrentStation, { immediate: true })
</script>

<style scoped>
.vehicle-route-card { min-height:360px; display:grid; grid-template-rows:auto minmax(230px,1fr) auto; gap:16px; border:1px solid rgba(255,255,255,.2); border-radius:10px; padding:20px; overflow:hidden; background:rgba(255,255,255,.07); }
header,footer { display:flex; align-items:center; justify-content:space-between; gap:18px; } header p,header h3 { margin:0; } header h3 { margin-top:5px; font-size:22px; } header>span,footer { color:rgba(255,255,255,.62); font-size:12px; }
.route-strip-viewport { min-width:0; overflow-x:auto; overflow-y:hidden; overscroll-behavior-inline:contain; cursor:grab; scrollbar-color:rgba(141,228,206,.7) rgba(255,255,255,.08); scrollbar-width:thin; }.route-strip-viewport:active { cursor:grabbing; }
.route-strip-track { --item-width:150px; position:relative; display:grid; grid-template-columns:repeat(var(--station-count),var(--item-width)); width:max-content; min-width:100%; padding:58px 75px 28px; }.route-strip-track::before { content:''; position:absolute; top:93px; left:75px; right:75px; height:4px; border-radius:999px; background:linear-gradient(90deg,#5cc7ae,#9dded2); }
.route-station { position:relative; z-index:1; display:grid; justify-items:center; align-content:start; gap:8px; min-width:150px; text-align:center; }.station-marker { position:relative; width:100%; height:46px; display:grid; place-items:center; }.station-marker i { display:block; width:17px; height:17px; border:4px solid #8de4ce; border-radius:50%; background:#244567; box-shadow:0 0 0 5px rgba(141,228,206,.12); }.route-station.is-passed .station-marker i { background:#8de4ce; }.route-station.is-current .station-marker i { width:22px; height:22px; border-color:#fff; background:#51c9aa; }
.vehicle-marker { position:absolute; left:50%; bottom:34px; transform:translateX(-50%); min-width:48px; border-radius:7px 7px 4px 4px; padding:7px 8px; color:#17334a; font-size:10px; font-weight:900; letter-spacing:.08em; background:#f4fbff; box-shadow:0 8px 20px rgba(0,0,0,.22); }.vehicle-marker::after { content:''; position:absolute; left:50%; bottom:-6px; width:10px; height:10px; transform:translateX(-50%) rotate(45deg); background:#f4fbff; }
.route-station strong { max-width:130px; min-height:34px; color:#fff; font-size:12px; line-height:1.35; }.route-station small { color:rgba(255,255,255,.55); }.route-station.is-current strong { color:#aef0de; }
footer { justify-content:center; } footer strong { border-radius:999px; padding:7px 14px; color:#17334a; background:#aef0de; }.route-empty { display:grid; min-height:220px; place-items:center; color:rgba(255,255,255,.6); }
@media(max-width:720px){.route-strip-track{--item-width:130px;padding-inline:65px}.route-strip-track::before{left:65px;right:65px}.vehicle-route-card{padding:14px}header{align-items:flex-start;flex-direction:column}}
</style>
