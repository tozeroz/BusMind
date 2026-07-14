<template>
  <section class="frequency-chart-card">
    <header>
      <div>
        <p>&#x73ED;&#x6B21;&#x9891;&#x7387;</p>
        <h3>&#x9AD8;&#x5CF0;&#x4E0E;&#x975E;&#x9AD8;&#x5CF0;&#x5BF9;&#x6BD4;</h3>
      </div>
      <span>&#x5355;&#x4F4D;&#xFF1A;&#x5206;&#x949F;</span>
    </header>
    <canvas ref="canvasRef" aria-label="Line service frequency chart"></canvas>
    <div class="frequency-legend">
      <span v-for="point in points" :key="point.label"><i></i>{{ point.label }} {{ point.value || '--' }}</span>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({ line: { type: Object, default: null } })
const canvasRef = ref(null)
let resizeObserver = null

const averageFrequency = (value) => {
  const numbers = String(value ?? '').match(/\d+(?:\.\d+)?/g)?.map(Number) || []
  if (!numbers.length) return 0
  return numbers.reduce((sum, item) => sum + item, 0) / numbers.length
}

const points = computed(() => [
  { label: 'AM Peak', value: averageFrequency(props.line?.am_peak_freq) },
  { label: 'AM Off-peak', value: averageFrequency(props.line?.am_offpeak_freq) },
  { label: 'PM Peak', value: averageFrequency(props.line?.pm_peak_freq) },
  { label: 'PM Off-peak', value: averageFrequency(props.line?.pm_offpeak_freq) }
])

function drawChart() {
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const ratio = window.devicePixelRatio || 1
  canvas.width = Math.max(1, rect.width * ratio)
  canvas.height = Math.max(1, rect.height * ratio)
  const context = canvas.getContext('2d')
  context.scale(ratio, ratio)
  context.clearRect(0, 0, rect.width, rect.height)
  const padding = { top: 22, right: 18, bottom: 34, left: 36 }
  const width = rect.width - padding.left - padding.right
  const height = rect.height - padding.top - padding.bottom
  const values = points.value.map((point) => point.value)
  const max = Math.max(20, ...values) * 1.15
  context.font = '11px sans-serif'
  context.fillStyle = 'rgba(255,255,255,.62)'
  context.strokeStyle = 'rgba(255,255,255,.14)'
  context.lineWidth = 1
  for (let step = 0; step <= 4; step += 1) {
    const y = padding.top + (height / 4) * step
    context.beginPath(); context.moveTo(padding.left, y); context.lineTo(rect.width - padding.right, y); context.stroke()
    context.fillText(String(Math.round(max - (max / 4) * step)), 4, y + 4)
  }
  const coordinates = values.map((value, index) => ({
    x: padding.left + (width / Math.max(1, values.length - 1)) * index,
    y: padding.top + height - (value / max) * height
  }))
  context.strokeStyle = '#69e1c2'; context.lineWidth = 3; context.lineJoin = 'round'
  context.beginPath(); coordinates.forEach((point, index) => index ? context.lineTo(point.x, point.y) : context.moveTo(point.x, point.y)); context.stroke()
  coordinates.forEach((point) => {
    context.fillStyle = '#f7fbff'; context.beginPath(); context.arc(point.x, point.y, 4.5, 0, Math.PI * 2); context.fill()
    context.strokeStyle = '#35b99c'; context.lineWidth = 2; context.stroke()
  })
}

watch(points, () => nextTick(drawChart), { deep: true })
onMounted(() => {
  resizeObserver = new ResizeObserver(drawChart)
  if (canvasRef.value) resizeObserver.observe(canvasRef.value)
  nextTick(drawChart)
})
onBeforeUnmount(() => resizeObserver?.disconnect())
</script>

<style scoped>
.frequency-chart-card { width:100%; height:360px; min-height:360px; max-height:360px; display:grid; grid-template-rows:auto 220px auto; gap:12px; overflow:hidden; border:1px solid rgba(255,255,255,.2); border-radius:10px; padding:16px 18px; background:rgba(255,255,255,.08); }
header { display:flex; justify-content:space-between; gap:16px; }
header p,header h3 { margin:0; } header p,header span { color:rgba(255,255,255,.64); font-size:12px; } header h3 { margin-top:5px; font-size:18px; }
canvas { display:block; width:100%; height:220px; min-height:0; max-height:220px; }
.frequency-legend { display:flex; flex-wrap:wrap; gap:10px 14px; color:rgba(255,255,255,.72); font-size:11px; }
.frequency-legend span { display:flex; align-items:center; gap:6px; }.frequency-legend i { width:7px; height:7px; border-radius:50%; background:#69e1c2; }
</style>
