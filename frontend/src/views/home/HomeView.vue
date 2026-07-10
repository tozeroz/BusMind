<template>
  <section class="home-map-layout fullscreen-map-layout">
    <section class="home-map-panel real-map-panel fullscreen-map-panel">
      <BusMap ref="busMapRef" @select-stop="selectMapStop" @select-route="selectMapRoute" />

      <button
        v-if="!isInfoPanelOpen"
        class="map-mini-toggle"
        type="button"
        @click="isInfoPanelOpen = true"
      >
        <strong>{{ selectedInfo.name || '目的地检索' }}</strong>
        <span>{{ panelSubtitle }}</span>
      </button>

      <aside v-else class="map-info-dock">
        <div class="section-title">
          <div>
            <p class="eyebrow">{{ panelLabel }}</p>
            <h1>{{ panelTitle }}</h1>
          </div>
          <button class="ghost-button compact-ghost" type="button" @click="isInfoPanelOpen = false">
            收起
          </button>
        </div>

        <template v-if="panelMode === 'search'">
          <form class="destination-search floating-search" @submit.prevent="searchRoutes">
            <p class="eyebrow">目的地检索</p>
            <h2>你要去哪里？</h2>
            <div class="location-line">
              <span>当前位置</span>
              <strong>乌节站附近</strong>
            </div>
            <label>
              目的地
              <input v-model="query.end" placeholder="如：滨海湾 / 市政厅 / 莱佛士坊" />
            </label>
            <button class="primary-button" type="submit">开始检索</button>
            <p v-if="notice" class="form-tip">{{ notice }}</p>
          </form>

          <article v-if="recommendation" class="recommend-preview">
            <p class="eyebrow">推荐结果</p>
            <h3>{{ recommendation.title }}</h3>
            <p>{{ recommendation.reason }}</p>
            <div class="recommend-meta">
              <span>ETA {{ recommendation.eta }} 分钟</span>
              <span>体验分 {{ recommendation.score }}</span>
              <span>{{ recommendation.load }}</span>
            </div>
            <button class="primary-button" type="button" @click="applyRecommendedRoute(recommendation)">
              查看推荐路线
            </button>
          </article>

          <div class="home-side-stats">
            <article v-for="item in stats" :key="item.label" class="stat-card">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </article>
          </div>
        </template>

        <template v-else-if="panelMode === 'station'">
          <button class="ghost-button back-side-button" type="button" @click="resetPanel">返回检索</button>
          <div class="info-list">
            <p><span>经过线路</span><strong>{{ selectedInfo.routes }}</strong></p>
            <p><span>下一班车</span><strong>{{ selectedInfo.eta }}</strong></p>
            <p><span>当前客流</span><strong>{{ selectedInfo.crowd }}</strong></p>
            <p><span>站点热度</span><strong>{{ selectedInfo.status }}</strong></p>
          </div>
        </template>

        <template v-else>
          <button class="ghost-button back-side-button" type="button" @click="resetPanel">返回检索</button>
          <div class="info-list">
            <p><span>路线编号</span><strong>{{ selectedInfo.id }}</strong></p>
            <p><span>当前客流</span><strong>{{ selectedInfo.crowd }}</strong></p>
            <p><span>预计到达</span><strong>{{ selectedInfo.eta }}</strong></p>
            <p><span>运行状态</span><strong>{{ selectedInfo.status }}</strong></p>
          </div>
        </template>
      </aside>

      <article v-if="panelMode !== 'search'" class="map-chart-card">
        <div class="section-title">
          <div>
            <p class="eyebrow">{{ panelMode === 'station' ? '站点图表' : '路线图表' }}</p>
            <h3>{{ selectedInfo.name }}</h3>
          </div>
          <button class="ghost-button compact-ghost" type="button" @click="resetPanel">关闭</button>
        </div>
        <div class="mini-chart">
          <span v-for="(item, index) in selectedInfo.chart" :key="`${item}-${index}`" :style="{ height: `${item}%` }"></span>
        </div>
        <p class="muted">当前为本地模拟数据，后续可接入后端展示实时客流统计。</p>
      </article>

      <section v-if="isAiChatOpen" class="map-ai-card">
        <div class="section-title">
          <div>
            <p class="eyebrow">AI 出行助手</p>
            <h3>路线建议</h3>
          </div>
          <button class="ghost-button compact-ghost" type="button" @click="isAiChatOpen = false">
            关闭
          </button>
        </div>

        <div class="map-ai-messages">
          <article v-for="message in aiMessages" :key="message.id" :class="['mini-message', message.role]">
            <p>{{ message.content }}</p>
          </article>
        </div>

        <div v-if="aiRecommendation" class="ai-route-result">
          <p class="eyebrow">推荐路线</p>
          <h4>{{ aiRecommendation.title }}</h4>
          <p>{{ aiRecommendation.reason }}</p>
          <button class="primary-button" type="button" @click="applyRecommendedRoute(aiRecommendation)">
            在地图中查看
          </button>
        </div>

        <form class="map-ai-input" @submit.prevent="sendAiMessage">
          <input v-model="aiInput" placeholder="例如：去滨海湾，想少走路" />
          <button class="primary-button" type="submit">发送</button>
        </form>
      </section>
    </section>

    <button
      class="ai-floating-button"
      type="button"
      :style="{ left: `${floatPosition.x}px`, top: `${floatPosition.y}px` }"
      @mousedown.stop="startFloatDrag"
      @click="toggleAiChat"
      title="AI 出行助手"
    >
      AI
    </button>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import BusMap from '@/components/map/BusMap.vue'
import { mockRoutes } from '@/map/mock-bus-data'

const busMapRef = ref(null)
const query = reactive({ end: '滨海湾' })
const notice = ref('')
const recommendation = ref(null)
const panelMode = ref('search')
const isInfoPanelOpen = ref(false)
const isAiChatOpen = ref(false)
const aiInput = ref('去滨海湾，想坐最舒适的路线')
const aiRecommendation = ref(null)
const selectedInfo = reactive({
  id: '',
  name: '',
  crowd: '',
  status: '',
  eta: '',
  routes: '',
  chart: [42, 70, 56, 88, 64]
})
const floatPosition = reactive({ x: window.innerWidth - 112, y: window.innerHeight - 120 })
const dragState = reactive({ dragging: false, moved: false, offsetX: 0, offsetY: 0 })

const stats = [
  { label: '运行路线', value: '4 条' },
  { label: '在线车辆', value: '12 辆' },
  { label: '平均等待', value: '7 分钟' },
  { label: '当前客流', value: '适中' }
]

const routeReasons = [
  '途经乌节、索美塞、多美歌和市政厅，适合作为市中心通勤的综合推荐。',
  '沿乌节路和滨海方向行驶，当前客流压力较低，适合去滨海湾一带。',
  '覆盖莱佛士坊到市政厅方向，晚高峰客流较高，适合急需到达时选择。',
  '经索美塞、多美歌到克拉码头，步行距离短，乘坐舒适度更好。'
]

const mockRouteOptions = mockRoutes.map((route, index) => ({
  id: route.line_id,
  title: route.line_name,
  reason: routeReasons[index],
  eta: route.eta_minutes,
  score: [86, 91, 72, 89][index],
  load: loadLevelText(route.crowd_level),
  status: route.status,
  chart: route.chart
}))

const aiMessages = ref([
  {
    id: 1,
    role: 'assistant',
    content: '你好，我可以根据目的地、舒适度和等待时间给出路线建议。'
  }
])

const panelLabel = computed(() => {
  if (panelMode.value === 'station') return '站点信息'
  if (panelMode.value === 'road') return '路线详情'
  return '乘客端'
})

const panelTitle = computed(() => selectedInfo.name || '首页')

const panelSubtitle = computed(() => {
  if (panelMode.value === 'station') return '查看站点客流'
  if (panelMode.value === 'road') return '查看路线详情'
  return '点击展开搜索'
})

function loadLevelText(level) {
  const map = {
    seats_available: '预计有座',
    standing_available: '可站立',
    limited_standing: '较拥挤',
    low: '舒适',
    medium: '适中',
    high: '拥挤'
  }
  return map[level] || level || '未知客流'
}

const normalizeChart = (chart) => {
  if (Array.isArray(chart)) return chart
  if (typeof chart === 'string') {
    return chart.split(',').map((item) => Number(item)).filter(Boolean)
  }
  return [44, 62, 78, 66, 58]
}

const findRouteForDestination = (text) => {
  if (text.includes('滨海') || text.includes('莱佛士')) return mockRouteOptions[1]
  if (text.includes('市政厅') || text.includes('高峰')) return mockRouteOptions[2]
  if (text.includes('克拉') || text.includes('舒适') || text.includes('少走路')) return mockRouteOptions[3]
  return mockRouteOptions[0]
}

const searchRoutes = () => {
  busMapRef.value?.clearSelection()
  const matchedRoute = findRouteForDestination(query.end)

  recommendation.value = {
    ...matchedRoute,
    title: query.end ? `乌节站 → ${query.end}` : matchedRoute.title,
    reason: `已根据“${query.end || '目的地'}”生成本地演示路线，后续可替换为后端推荐接口。`
  }
  notice.value = `已检索目的地：${query.end || '未填写'}`
}

const resetPanel = () => {
  busMapRef.value?.clearSelection()
  panelMode.value = 'search'
  isInfoPanelOpen.value = true
  selectedInfo.id = ''
  selectedInfo.name = ''
  selectedInfo.crowd = ''
  selectedInfo.status = ''
  selectedInfo.eta = ''
  selectedInfo.routes = ''
  selectedInfo.chart = [42, 70, 56, 88, 64]
}

const openChartPanel = (mode) => {
  panelMode.value = mode
  isInfoPanelOpen.value = true
  isAiChatOpen.value = false
}

const selectStation = (stop) => {
  openChartPanel('station')
  selectedInfo.id = stop.stop_id
  selectedInfo.name = stop.stop_name
  selectedInfo.crowd = loadLevelText(stop.crowd_level)
  selectedInfo.status = stop.crowd_level === 'high' ? '较高' : '正常'
  selectedInfo.eta = `约 ${stop.eta_minutes} 分钟`
  selectedInfo.routes = stop.passing_routes?.join(' / ') || '市中心环线'
  selectedInfo.chart = stop.crowd_level === 'high' ? [68, 74, 82, 90, 76] : [34, 48, 56, 52, 44]
}

const selectMapStop = (stop) => {
  selectStation(stop)
}

const selectRoad = (route) => {
  openChartPanel('road')
  selectedInfo.id = route.line_id || route.id
  selectedInfo.name = route.line_name || route.title
  selectedInfo.crowd = route.load || loadLevelText(route.crowd_level)
  selectedInfo.status = route.status || (selectedInfo.crowd === '拥挤' ? '建议关注' : '运行正常')
  selectedInfo.eta = route.eta || route.eta_minutes ? `约 ${route.eta || route.eta_minutes} 分钟` : '约 8 分钟'
  selectedInfo.routes = ''
  selectedInfo.chart = normalizeChart(route.chart)
}

const selectMapRoute = (route) => {
  selectRoad(route)
}

const applyRecommendedRoute = (route) => {
  const focusedRoute = busMapRef.value?.focusRouteById(route.id || route.line_id)
  selectRoad({
    ...route,
    ...(focusedRoute || {}),
    id: route.id || focusedRoute?.line_id,
    line_name: route.title || focusedRoute?.line_name
  })
}

const sendAiMessage = () => {
  const text = aiInput.value.trim()
  if (!text) return

  aiMessages.value.push({ id: Date.now(), role: 'user', content: text })
  const matchedRoute = findRouteForDestination(text)

  aiRecommendation.value = {
    ...matchedRoute,
    title: text.includes('舒适') ? `舒适优先：${matchedRoute.title}` : `综合推荐：${matchedRoute.title}`,
    reason: '根据你的自然语言需求，模拟推荐一条可在地图中高亮查看的公交路线。'
  }
  aiMessages.value.push({
    id: Date.now() + 1,
    role: 'assistant',
    content: '已生成一条可查看的推荐路线，点击下方按钮可在地图中高亮。'
  })
  aiInput.value = ''
}

const startFloatDrag = (event) => {
  dragState.dragging = true
  dragState.moved = false
  dragState.offsetX = event.clientX - floatPosition.x
  dragState.offsetY = event.clientY - floatPosition.y
  window.addEventListener('mousemove', onFloatDrag)
  window.addEventListener('mouseup', stopFloatDrag)
}

const onFloatDrag = (event) => {
  if (!dragState.dragging) return
  dragState.moved = true
  floatPosition.x = Math.min(Math.max(16, event.clientX - dragState.offsetX), window.innerWidth - 72)
  floatPosition.y = Math.min(Math.max(76, event.clientY - dragState.offsetY), window.innerHeight - 72)
}

const stopFloatDrag = () => {
  dragState.dragging = false
  window.removeEventListener('mousemove', onFloatDrag)
  window.removeEventListener('mouseup', stopFloatDrag)
}

const toggleAiChat = () => {
  if (dragState.moved) return
  const shouldOpen = !isAiChatOpen.value
  isAiChatOpen.value = shouldOpen
  if (shouldOpen && panelMode.value !== 'search') {
    resetPanel()
  }
}
</script>
