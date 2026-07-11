<template>
  <section class="home-map-layout fullscreen-map-layout">
    <section class="home-map-panel real-map-panel fullscreen-map-panel">
      <BusMap ref="busMapRef" @select-stop="selectMapStop" @select-route="selectMapRoute" />

      <button
        class="map-current-locate-button"
        type="button"
        title="定位到当前位置"
        @click="focusMapToCurrentLocation"
      >
        ▲
      </button>

      <Transition name="dock-pop" mode="out-in">
        <button
          v-if="!isInfoPanelOpen"
          class="map-mini-toggle"
          type="button"
          @click="isInfoPanelOpen = true"
        >
          <strong>{{ selectedInfo.name || '目的地检索' }}</strong>
          <span>{{ panelSubtitle }}</span>
        </button>

        <aside v-else :class="['map-info-dock', `weather-${weatherTone}`]">
          <button
            v-if="panelMode === 'search'"
            class="dock-text-action dock-collapse-action"
            type="button"
            @click="isInfoPanelOpen = false"
          >
            收起
          </button>

          <div v-if="panelMode !== 'search'" class="section-title map-detail-title">
            <div>
              <p class="eyebrow">{{ panelLabel }}</p>
              <h1>{{ panelTitle }}</h1>
            </div>
            <button class="dock-text-action compact-ghost" type="button" @click="isInfoPanelOpen = false">
              收起
            </button>
          </div>

          <template v-if="panelMode === 'search'">
            <form class="destination-search floating-search" @submit.prevent="searchRoutes">
              <label class="search-header-line current-location-row">
                <span>当前位置</span>
                <input v-model="query.start" placeholder="输入当前位置" />
                <button class="locate-current-button" type="button" @click="getCurrentLocation">
                  定位
                </button>
              </label>
              <label class="search-box-row">
                <span>目标地点</span>
                <input v-model="query.end" placeholder="搜索地点、公交站、线路" />
                <button class="search-submit-chip" type="submit">检索</button>
              </label>
              <p v-if="notice" class="form-tip">{{ notice }}</p>
            </form>

            <Transition name="card-pop">
              <article v-if="recommendation" class="recommend-preview">
                <p class="eyebrow">推荐结果</p>
                <h3>{{ recommendation.title }}</h3>
                <div class="recommend-meta">
                  <span>ETA {{ recommendation.eta }} 分钟</span>
                  <span>体验分 {{ recommendation.score }}</span>
                  <span>{{ recommendation.load }}</span>
                </div>
                <button class="primary-button" type="button" @click="applyRecommendedRoute(recommendation)">
                  查看推荐路线
                </button>
              </article>
            </Transition>

            <div class="home-waterfall-cards">
              <article
                v-for="item in localTips"
                :key="item.label"
                :class="['life-card', item.tone]"
              >
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
                <p>{{ item.tip }}</p>
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
      </Transition>

      <Transition name="side-card">
        <article v-if="panelMode !== 'search'" :class="['map-chart-card', `chart-${chartTone}`]">
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
      </Transition>

      <Transition name="side-card">
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

          <Transition name="card-pop">
            <div v-if="aiRecommendation" class="ai-route-result">
              <div>
                <p class="eyebrow">推荐路线</p>
                <h4>{{ aiRecommendation.title }}</h4>
              </div>
              <div class="recommend-meta compact-meta">
                <span>{{ aiRecommendation.eta }} 分钟</span>
                <span>{{ aiRecommendation.load }}</span>
                <span>{{ aiRecommendation.score }} 分</span>
              </div>
              <button class="primary-button" type="button" @click="applyRecommendedRoute(aiRecommendation)">
                地图查看
              </button>
            </div>
          </Transition>

          <form class="map-ai-input" @submit.prevent="sendAiMessage">
            <input v-model="aiInput" placeholder="例如：去滨海湾，想少走路" />
            <button class="primary-button" type="submit">发送</button>
          </form>
        </section>
      </Transition>
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
import { askAiTravel } from '@/api/ai'
import { mockRoutes } from '@/map/mock-bus-data'

const busMapRef = ref(null)
const query = reactive({ start: '乌节站', end: '滨海湾' })
const notice = ref('')
const recommendation = ref(null)
const panelMode = ref('search')
const isInfoPanelOpen = ref(true)
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
const dragState = reactive({
  dragging: false,
  moved: false,
  offsetX: 0,
  offsetY: 0,
  startX: 0,
  startY: 0
})

const localTips = [
  { label: '天气', value: '29°C 多云', tip: '体感偏热，候车注意补水。', tone: 'weather' },
  { label: '穿衣', value: '轻薄短袖', tip: '车厢空调较足，可带薄外套。', tone: 'wear' },
  { label: '出行', value: '建议提前 8 分钟', tip: '乌节方向当前等待较短。', tone: 'travel' },
  { label: '客流', value: '适中', tip: '避开 18:00 后中心区高峰。', tone: 'flow' }
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

const weatherTone = computed(() => {
  const weather = localTips.find((item) => item.label === '天气')?.value || ''
  if (weather.includes('雨')) return 'rainy'
  if (weather.includes('晴')) return 'sunny'
  if (weather.includes('云')) return 'cloudy'
  return 'mild'
})

const chartTone = computed(() => {
  const crowdText = `${selectedInfo.crowd} ${selectedInfo.status}`
  if (crowdText.includes('拥挤') || crowdText.includes('较高')) return 'heavy'
  if (crowdText.includes('适中') || crowdText.includes('可站立') || crowdText.includes('建议关注')) return 'medium'
  return 'light'
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
    title: query.end ? `${query.start || '当前位置'} → ${query.end}` : matchedRoute.title,
    reason: `已根据“${query.end || '目的地'}”生成本地演示路线，后续可替换为后端推荐接口。`
  }
  notice.value = `已检索目的地：${query.end || '未填写'}`
}

const getCurrentLocation = () => {
  query.start = '乌节站'
  notice.value = '已获取当前位置：乌节站'
}

const focusMapToCurrentLocation = () => {
  const focusedStop = busMapRef.value?.focusStopByName(query.start)
  if (!focusedStop) {
    notice.value = `请输入明确站点名称：${query.start || '未填写'}`
    return
  }

  notice.value = `地图已定位到：${focusedStop.stop_name}`
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
  selectedInfo.crowd = stop.crowd_level ? loadLevelText(stop.crowd_level) : '暂无实时客流'
  selectedInfo.status = stop.crowd_level ? (stop.crowd_level === 'high' ? '较高' : '正常') : '站点数据已接入'
  selectedInfo.eta = Number.isFinite(Number(stop.eta_minutes)) ? `约 ${stop.eta_minutes} 分钟` : '暂无实时到站'
  selectedInfo.routes = stop.passing_routes?.join(' / ') || '暂无线路关联'
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

const sendAiMessage = async () => {
  const text = aiInput.value.trim()
  if (!text) return

  aiMessages.value.push({ id: Date.now(), role: 'user', content: text })
  const replyId = Date.now() + 1

  aiMessages.value.push({
    id: replyId,
    role: 'assistant',
    content: '正在请求 DeepSeek 出行助手...'
  })
  aiInput.value = ''

  try {
    const response = await askAiTravel({
      mode: 'qa',
      question: text,
      context: {
        current_location: query.start,
        destination: query.end,
        visible_routes: mockRouteOptions.slice(0, 4)
      }
    })
    const target = aiMessages.value.find((message) => message.id === replyId)
    if (target) {
      target.content = response.data?.answer || '后端未返回回答。'
    }
    const matchedRoute = findRouteForDestination(text)
    aiRecommendation.value = {
      ...matchedRoute,
      title: text.includes('舒适') ? `舒适优先：${matchedRoute.title}` : `综合推荐：${matchedRoute.title}`,
      reason: response.data?.answer || matchedRoute.reason
    }
  } catch (error) {
    const target = aiMessages.value.find((message) => message.id === replyId)
    if (target) {
      target.content = error?.response?.data?.message || '后端 AI 接口暂不可用，请确认后端已启动且 DEEPSEEK_API_KEY 已配置。'
    }
  }
}

const startFloatDrag = (event) => {
  dragState.dragging = true
  dragState.moved = false
  dragState.startX = event.clientX
  dragState.startY = event.clientY
  dragState.offsetX = event.clientX - floatPosition.x
  dragState.offsetY = event.clientY - floatPosition.y
  window.addEventListener('mousemove', onFloatDrag)
  window.addEventListener('mouseup', stopFloatDrag)
}

const onFloatDrag = (event) => {
  if (!dragState.dragging) return
  const moveDistance = Math.hypot(event.clientX - dragState.startX, event.clientY - dragState.startY)
  if (moveDistance < 6) return
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
