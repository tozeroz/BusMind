<template>
  <section class="passenger-flow-chart-card">
    <header>
      <div>
        <p>{{ eyebrow }}</p>
        <h3>{{ title }}</h3>
      </div>
      <span>{{ unit }}</span>
    </header>

    <div
      v-if="hasData"
      ref="viewportRef"
      class="chart-stage"
      @pointerdown="startDrag"
      @pointermove="dragChart"
      @pointerup="stopDrag"
      @pointercancel="stopDrag"
      @pointerleave="stopDrag"
    >
      <div class="chart-track" :style="trackStyle">
        <canvas ref="canvasRef" :aria-label="title"></canvas>
      </div>
    </div>
    <div v-else class="chart-empty">
      <strong>{{ emptyTitle }}</strong>
      <p>{{ emptyDescription }}</p>
    </div>

    <div v-if="hasData" class="chart-legend">
      <span v-for="seriesItem in normalizedSeries" :key="seriesItem.label">
        <i :style="{ background: seriesItem.color }"></i>{{ seriesItem.label }}
      </span>
      <span>{{ points.length }} &#x4E2A;&#x6570;&#x636E;&#x70B9;</span>
      <span class="drag-hint">&#x5DE6;&#x53F3;&#x62D6;&#x52A8;&#x67E5;&#x770B;&#x66F4;&#x591A;</span>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  eyebrow: { type: String, default: '' },
  title: { type: String, required: true },
  unit: { type: String, default: '\u5355\u4f4d\uff1a\u4eba\u6b21' },
  points: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
  timeKey: { type: String, default: 'record_time' },
  emptyTitle: { type: String, default: '\u6682\u65e0\u6570\u636e' },
  emptyDescription: { type: String, default: '\u5f53\u524d\u7ad9\u70b9\u6ca1\u6709\u53ef\u5c55\u793a\u7684\u8bb0\u5f55\u3002' }
})

const canvasRef = ref(null)
const viewportRef = ref(null)
let resizeObserver = null
const dragState = { active: false, startX: 0, scrollLeft: 0 }

const normalizedSeries = computed(() => props.series.map((item, index) => ({
  ...item,
  color: item.color || ['#69e1c2', '#75a9ff', '#ffd09c'][index % 3]
})))
const hasData = computed(() => props.points.length > 0 && normalizedSeries.value.length > 0)
const trackStyle = computed(() => ({ '--chart-width': `${Math.max(680, props.points.length * 20 + 78)}px` }))

function formatTime(value) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString([], { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function drawChart() {
  const canvas = canvasRef.value
  if (!canvas || !hasData.value) return
  const rect = canvas.getBoundingClientRect()
  const ratio = window.devicePixelRatio || 1
  canvas.width = Math.max(1, Math.round(rect.width * ratio))
  canvas.height = Math.max(1, Math.round(rect.height * ratio))
  const context = canvas.getContext('2d')
  context.setTransform(ratio, 0, 0, ratio, 0, 0)
  context.clearRect(0, 0, rect.width, rect.height)

  const padding = { top: 18, right: 20, bottom: 36, left: 48 }
  const width = Math.max(1, rect.width - padding.left - padding.right)
  const height = Math.max(1, rect.height - padding.top - padding.bottom)
  const values = normalizedSeries.value.flatMap((seriesItem) =>
    props.points.map((point) => Number(point?.[seriesItem.key]) || 0))
  const maxValue = Math.max(1, ...values) * 1.12

  context.font = '11px sans-serif'
  context.textBaseline = 'middle'
  for (let step = 0; step <= 4; step += 1) {
    const y = padding.top + height / 4 * step
    context.strokeStyle = 'rgba(255,255,255,.12)'
    context.lineWidth = 1
    context.beginPath()
    context.moveTo(padding.left, y)
    context.lineTo(rect.width - padding.right, y)
    context.stroke()
    context.fillStyle = 'rgba(255,255,255,.5)'
    context.fillText(String(Math.round(maxValue - maxValue / 4 * step)), 4, y)
  }

  const pointX = (index) => padding.left + width / Math.max(1, props.points.length - 1) * index
  normalizedSeries.value.forEach((seriesItem) => {
    const coordinates = props.points.map((point, index) => ({
      x: pointX(index),
      y: padding.top + height - (Number(point?.[seriesItem.key]) || 0) / maxValue * height
    }))
    context.strokeStyle = seriesItem.color
    context.lineWidth = 2.5
    context.lineJoin = 'round'
    context.lineCap = 'round'
    context.beginPath()
    coordinates.forEach((point, index) => index
      ? context.lineTo(point.x, point.y)
      : context.moveTo(point.x, point.y))
    context.stroke()
    if (coordinates.length <= 192) {
      coordinates.forEach((point) => {
        context.fillStyle = '#f6fbff'
        context.beginPath()
        context.arc(point.x, point.y, coordinates.length > 96 ? 2 : 3, 0, Math.PI * 2)
        context.fill()
        context.strokeStyle = seriesItem.color
        context.lineWidth = 1.5
        context.stroke()
      })
    }
  })

  const labelStep = Math.max(1, Math.ceil(props.points.length / Math.max(3, Math.floor(width / 120))))
  const labelIndexes = props.points
    .map((_, index) => index)
    .filter((index) => index === 0 || index === props.points.length - 1 || index % labelStep === 0)
  context.fillStyle = 'rgba(255,255,255,.5)'
  context.textBaseline = 'top'
  labelIndexes.forEach((index, labelIndex) => {
    context.textAlign = labelIndex === 0 ? 'left' : (labelIndex === labelIndexes.length - 1 ? 'right' : 'center')
    context.fillText(formatTime(props.points[index]?.[props.timeKey]), pointX(index), rect.height - 22)
  })
}

function startDrag(event) {
  if (event.button !== 0 || !viewportRef.value) return
  dragState.active = true
  dragState.startX = event.clientX
  dragState.scrollLeft = viewportRef.value.scrollLeft
  viewportRef.value.setPointerCapture?.(event.pointerId)
}

function dragChart(event) {
  if (!dragState.active || !viewportRef.value) return
  viewportRef.value.scrollLeft = dragState.scrollLeft - (event.clientX - dragState.startX)
}

function stopDrag(event) {
  if (!dragState.active) return
  dragState.active = false
  viewportRef.value?.releasePointerCapture?.(event.pointerId)
}

watch(() => [props.points, props.series], () => nextTick(drawChart), { deep: true })
onMounted(() => {
  resizeObserver = new ResizeObserver(drawChart)
  if (canvasRef.value) resizeObserver.observe(canvasRef.value)
  nextTick(drawChart)
})
onBeforeUnmount(() => resizeObserver?.disconnect())
</script>

<style scoped>
.passenger-flow-chart-card { height:340px; min-height:340px; max-height:340px; display:grid; grid-template-rows:auto 220px auto; gap:12px; overflow:hidden; border:1px solid rgba(255,255,255,.2); border-radius:10px; padding:17px 18px; background:linear-gradient(145deg,rgba(255,255,255,.11),rgba(69,107,147,.24)); box-shadow:inset 0 1px rgba(255,255,255,.11),0 18px 42px rgba(9,28,49,.14); backdrop-filter:blur(18px) saturate(125%); -webkit-backdrop-filter:blur(18px) saturate(125%); }
header { display:flex; align-items:flex-start; justify-content:space-between; gap:16px; }
header p,header h3 { margin:0; } header p,header>span { color:rgba(255,255,255,.6); font-size:11px; } header h3 { margin-top:4px; font-size:18px; }
.chart-stage { min-width:0; width:100%; height:220px; min-height:220px; max-height:220px; overflow-x:auto; overflow-y:hidden; overscroll-behavior-inline:contain; cursor:grab; scrollbar-width:thin; scrollbar-color:rgba(141,228,206,.75) rgba(255,255,255,.08); }.chart-stage:active { cursor:grabbing; }.chart-track { width:max(100%,var(--chart-width)); height:210px; min-height:210px; max-height:210px; }.chart-stage canvas { display:block; width:100%; height:210px; min-height:210px; max-height:210px; }
.chart-empty { min-height:210px; display:grid; place-content:center; justify-items:center; text-align:center; color:rgba(255,255,255,.62); }.chart-empty p { max-width:430px; margin:7px 0 0; font-size:12px; }
.chart-legend { display:flex; flex-wrap:wrap; gap:10px 16px; color:rgba(255,255,255,.64); font-size:11px; }.chart-legend span { display:flex; align-items:center; gap:6px; }.chart-legend i { width:8px; height:8px; border-radius:50%; }.chart-legend .drag-hint { margin-left:auto; color:#aee9dc; }
</style>
