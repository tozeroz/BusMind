<!--
  文件：src/modules/home/components/HomePage.vue
  用途：实现 home 业务模块中的页面容器或业务组件。
  存放内容：该业务领域专属的界面结构、响应式状态和业务协调代码。
  实现功能：集中承载模块业务功能，并与路由入口、公共层和 API 层保持职责分离。
-->
<template>
  <section class="home-map-layout fullscreen-map-layout">
    <section class="home-map-panel real-map-panel fullscreen-map-panel">
      <BusMap
        ref="busMapRef"
        @select-stop="selectMapStop"
        @select-route="selectMapRoute"
        @load-error="notice = $event"
        @initial-data-loaded="refreshArrivals"
      />

      <button
        class="map-current-locate-button"
        type="button"
        title="定位到当前位置"
        @click="focusMapToCurrentLocation"
      >
        ▲
      </button>

      <button
        class="map-reload-button"
        type="button"
        title="重新加载地图数据"
        @click="reloadMapData"
      >
        ⟳
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
                <button class="search-submit-chip" type="submit" :disabled="isSearching">
                  {{ isSearching ? '检索中…' : '检索' }}
                </button>
              </label>
              <p v-if="notice" class="form-tip">{{ notice }}</p>
            </form>

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
            <div class="info-list info-list-station">
              <header class="info-list-header">
                <div class="info-list-header-line">
                  <strong class="info-list-line-code">{{ selectedInfo.id || '路线' }}</strong>
                </div>
                <div class="info-list-header-route">
                  <span class="info-list-route-label">目的地</span>
                  <span class="info-list-route-divider" aria-hidden="true"></span>
                  <span class="info-list-route-value">{{ selectedInfo.routes || '暂无线路关联' }}</span>
                </div>
              </header>
              <div class="info-list-rows">
                <p><span>始发站 · 末班车</span><strong>{{ selectedInfo.eta || '暂无末班信息' }}</strong></p>
                <p><span>客流状态</span><strong>{{ selectedInfo.crowd || '暂无客流' }}</strong></p>
                <p><span>发车间隔</span><strong>{{ selectedInfo.status || '数据接入中' }}</strong></p>
              </div>
            </div>
          </template>

          <template v-else>
            <button class="ghost-button back-side-button" type="button" @click="resetPanel">返回检索</button>
            <div class="info-list info-list-road">
              <header class="info-list-header">
                <div class="info-list-header-line">
                  <strong class="info-list-line-code">{{ selectedInfo.id || '路线' }}</strong>
                </div>
                <div class="info-list-header-route">
                  <span class="info-list-route-label">目的地</span>
                  <span class="info-list-route-divider" aria-hidden="true"></span>
                  <span class="info-list-route-value">{{ selectedInfo.name || '暂无目的地' }}</span>
                </div>
              </header>
              <div class="info-list-rows">
                <p><span>始发站 · 末班车</span><strong>{{ selectedInfo.eta || '暂无末班信息' }}</strong></p>
                <p><span>客流状态</span><strong>{{ selectedInfo.crowd || '暂无客流' }}</strong></p>
                <p><span>发车间隔</span><strong>{{ selectedInfo.status || '数据接入中' }}</strong></p>
              </div>
            </div>
          </template>

        </aside>
      </Transition>


      <Transition name="card-pop">
        <RouteResultsPopup
          v-if="panelMode === 'search' && recommendation && routeOptions.length"
          :routes="routeOptions"
          @select="applyRecommendedRoute"
          @close="recommendation = null"
        />
      </Transition>
      <Transition name="side-card">
        <aside v-if="isInfoPanelOpen" class="map-player-panel map-player-slot">
          <div>
            <p class="eyebrow">语音播报</p>
            <strong>{{ selectedInfo.name || '\u51fa\u884c\u64ad\u653e\u5668' }}</strong>
            <span>{{ panelMode === 'search' ? '\u5f85\u9009\u62e9\u7ad9\u70b9\u6216\u7ebf\u8def' : chartCaption }}</span>
          </div>
          <div class="player-control-row" aria-hidden="true">
            <i></i><b></b><i></i>
          </div>
        </aside>
      </Transition>
      <Transition name="side-card">
        <SelectedRouteDetailCard
          v-if="selectedRecommendedRoute"
          :route="selectedRecommendedRoute"
          @close="selectedRecommendedRoute = null"
        />
        <SelectedStationDetailCard
          v-else-if="isStationDetailOpen"
          :station="selectedInfo"
          :is-routes-expanded="isRoutesExpanded"
          @close="isStationDetailOpen = false"
          @show-routes="handleShowRoutes"
          @show-eta="handleShowEta"
          @close-routes="handleCloseRoutes"
          @select-route="handleSelectRoute"
        />
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
import BusMap from '@/modules/map/components/BusMap.vue'
import RouteResultsPopup from '@/modules/home/components/RouteResultsPopup.vue'
import SelectedRouteDetailCard from '@/modules/home/components/SelectedRouteDetailCard.vue'
import SelectedStationDetailCard from '@/modules/home/components/SelectedStationDetailCard.vue'
import { askAiTravel } from '@/api/ai'
import { getNearbyLocations, searchLocations } from '@/api/location'
import { getEta } from '@/api/intelligence'
import { getRouteRecommendations, RECOMMENDATION_PREFERENCES } from '@/api/recommendation'
import { getPassengerFlowTrend } from '@/api/history'
import { getRealtimeVehicles } from '@/api/vehicle'
import { getApiErrorMessage, unwrapList } from '@/api/response'
import { triggerArrivalRefresh } from '@/api/user'

const refreshArrivals = () => {
  triggerArrivalRefresh().catch(() => {})
}

const busMapRef = ref(null)
const query = reactive({ start: 'Aft Braddell Rd', end: 'New Tech Pk' })
const notice = ref('')
const recommendation = ref(null)
const isSearching = ref(false)
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
  chart: [42, 70, 56, 88, 64],
  flowSource: 'local',
  flowSummary: '',
  routesList: []
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

const routeOptions = ref([])
const selectedRecommendedRoute = ref(null)
const isStationDetailOpen = ref(false)
const isRoutesExpanded = ref(false)
const rawRouteOptions = ref([])
const resolvedJourney = reactive({ startStationId: null, endStationId: null })

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

const chartCaption = computed(() => {
  if (selectedInfo.flowSource === 'backend') {
    return `\u6570\u636e\u6765\u6e90\uff1a\u540e\u7aef\u5386\u53f2\u5ba2\u6d41\u63a5\u53e3${selectedInfo.flowSummary ? ` · ${selectedInfo.flowSummary}` : ''}`
  }
  return '\u6682\u65e0\u540e\u7aef\u5ba2\u6d41\u6570\u636e\uff0c\u5148\u663e\u793a\u5730\u56fe\u7ad9\u70b9\u4fe1\u606f\u3002'
})

const buildChartFromFlow = (items, maxValue) => {
  if (!Array.isArray(items) || !items.length) return null
  const peak = Math.max(maxValue || 1, ...items.map((item) => Number(item.total_flow) || 0))
  if (!peak) return null
  return items
    .slice(0, 6)
    .map((item) => Math.max(6, Math.round((Number(item.total_flow || 0) / peak) * 100)))
}

const loadStationFlowChart = async (station) => {
  const stationId = station?.station_id ?? station?.stop_id
  if (stationId === undefined || stationId === null) return
  try {
    const response = await getPassengerFlowTrend({ station_id: stationId, granularity: 'hour' })
    const data = response?.data || {}
    const items = Array.isArray(data) ? data : (data.items || [])
    const summary = data.summary || {}
    const chart = buildChartFromFlow(items, summary.total_flow)

    if (String(selectedInfo.id) !== String(stationId)) return

    if (chart && chart.length) selectedInfo.chart = chart
    selectedInfo.flowSource = 'backend'

    const totalFlow = summary.total_flow ?? items.reduce((sum, item) => sum + (Number(item.total_flow) || 0), 0)
    const dominantLevel = summary.dominant_flow_level || items.find((item) => item.flow_level)?.flow_level
    selectedInfo.crowd = dominantLevel ? loadLevelText(dominantLevel) : (totalFlow ? String(totalFlow) : selectedInfo.crowd)
    selectedInfo.status = totalFlow ? `\u603b\u5ba2\u6d41 ${totalFlow}` : '\u5386\u53f2\u5ba2\u6d41\u5df2\u63a5\u5165'
    selectedInfo.flowSummary = `\u603b\u5ba2\u6d41 ${totalFlow || '--'} · \u4e3b\u8981\u7b49\u7ea7 ${dominantLevel ? loadLevelText(dominantLevel) : '--'}`
  } catch (error) {
    selectedInfo.flowSource = 'local'
    selectedInfo.flowSummary = ''
  }
}
const loadStationRealtime = async (station) => {
  const stationId = Number(station?.station_id ?? station?.stop_id)
  const lineId = Number(station?.line_ids?.[0] ?? station?.line_id)
  if (!Number.isFinite(stationId) || !Number.isFinite(lineId)) return

  try {
    const vehicleResponse = await getRealtimeVehicles({ line_id: lineId })
    const vehicle = unwrapList(vehicleResponse, 'vehicles')[0]
    if (!vehicle?.vehicle_id) return

    const etaOutcome = await getEta({ vehicle_id: Number(vehicle.vehicle_id), target_station_id: stationId, line_id: lineId })
    if (String(selectedInfo.id) !== String(stationId)) return

    const eta = etaOutcome?.data?.predicted_eta_minutes
    if (Number.isFinite(Number(eta))) selectedInfo.eta = `\u7ea6 ${Number(eta).toFixed(1)} \u5206\u949f`
  } catch {
    // Keep station cards on map/history data when realtime ETA is unavailable.
  }
}

function loadLevelText(level) {
  const map = {
    seats_available: '预计有座',
    standing_available: '可站立',
    limited_standing: '较拥挤',
    overcrowded: '过度拥挤',
    SEA: '预计有座',
    SDA: '可站立',
    LSD: '较拥挤',
    UNKNOWN: '未知客流',
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

const normalizeRecommendation = (route) => ({
  id: route.line_ids?.[0] || route.route_id,
  routeId: route.route_id,
  title: route.segments?.map((item) => item.line_name).filter(Boolean).join(' → ') || `路线 ${route.route_id}`,
  reason: route.reason || '后端已生成推荐路线。',
  eta: Number(route.predicted_eta_minutes ?? route.total_time_minutes ?? 0).toFixed(1),
  score: Number(route.experience_score ?? 0).toFixed(1),
  load: loadLevelText(route.predicted_load?.predicted_load_level),
  status: route.recommend_types?.includes('best_experience') ? '综合推荐' : '可选路线',
  chart: [
    route.experience_score,
    Number(100 - (route.walk_time_minutes || 0)),
    route.predicted_load?.load_score,
    Number(100 - (route.transfer_count || 0) * 20),
    Number(100 - (route.total_time_minutes || 0))
  ].filter((value) => Number.isFinite(Number(value)))
})

const findRouteForDestination = () => routeOptions.value[0] || null

const searchStation = async (keyword) => {
  const response = await searchLocations({ keyword: keyword.trim(), page: 1, limit: 5 })
  const stations = response.data?.stations || response.data?.items || []
  return stations[0] || null
}

const searchRoutes = async () => {
  if (isSearching.value) return
  busMapRef.value?.clearSelection()
  recommendation.value = null
  selectedRecommendedRoute.value = null
  isStationDetailOpen.value = false
  routeOptions.value = []
  rawRouteOptions.value = []
  resolvedJourney.startStationId = null
  resolvedJourney.endStationId = null
  if (!query.start.trim() || !query.end.trim()) {
    notice.value = '请输入完整的起点和终点'
    return
  }

  notice.value = '正在搜索站点并生成推荐路线...'
  isSearching.value = true
  try {
    const [startStation, endStation] = await Promise.all([
      searchStation(query.start),
      searchStation(query.end)
    ])
    if (!startStation || !endStation) {
      notice.value = '没有找到匹配站点，请输入更准确的站点名称'
      return
    }
    if (startStation.station_id === endStation.station_id) {
      notice.value = '起点和终点不能是同一站点'
      return
    }

    const result = await getRouteRecommendations({
      startStationId: startStation.station_id,
      endStationId: endStation.station_id,
      preference: RECOMMENDATION_PREFERENCES.BALANCED,
      allowTransfer: true,
      maxTransferCount: 2
    })
    rawRouteOptions.value = result.items
    routeOptions.value = rawRouteOptions.value.map(normalizeRecommendation)
    resolvedJourney.startStationId = Number(startStation.station_id)
    resolvedJourney.endStationId = Number(endStation.station_id)
    const bestRoute = result.optimal.bestExperience || rawRouteOptions.value[0]
    const matchedRoute = bestRoute ? normalizeRecommendation(bestRoute) : null
    if (!matchedRoute) {
      notice.value = '后端没有返回可用路线'
      return
    }
    recommendation.value = {
      ...matchedRoute,
      title: `${startStation.station_name} → ${endStation.station_name}`
    }
    notice.value = `已找到 ${routeOptions.value.length} 条候选路线`
  } catch (error) {
    notice.value = getApiErrorMessage(error, '路线检索失败，请检查后端服务和站点数据')
  } finally {
    isSearching.value = false
  }
}

const getCurrentLocation = () => {
  if (!navigator.geolocation) {
    notice.value = '当前浏览器不支持定位'
    return
  }
  notice.value = '正在获取当前位置...'
  navigator.geolocation.getCurrentPosition(async ({ coords }) => {
    try {
      const response = await getNearbyLocations({
        latitude: coords.latitude,
        longitude: coords.longitude,
        radius_km: 2
      })
      const nearest = response.data?.stations?.[0]
      if (!nearest) {
        notice.value = '当前位置附近 2 公里内没有公交站'
        return
      }
      query.start = nearest.station_name
      notice.value = `已定位到最近站点：${nearest.station_name}`
      busMapRef.value?.focusStopByName(nearest.station_name)
    } catch (error) {
      notice.value = getApiErrorMessage(error, '附近站点查询失败')
    }
  }, () => {
    notice.value = '无法获取位置，请检查浏览器定位权限'
  }, { enableHighAccuracy: true, timeout: 10000 })
}

const focusMapToCurrentLocation = () => {
  const focusedStop = busMapRef.value?.focusStopByName(query.start)
  if (!focusedStop) {
    notice.value = `请输入明确站点名称：${query.start || '未填写'}`
    return
  }

  notice.value = `地图已定位到：${focusedStop.stop_name}`
}

const reloadMapData = async () => {
  notice.value = '正在重新加载地图数据...'
  try {
    await busMapRef.value?.reloadMapData()
    notice.value = '地图数据已重新加载'
  } catch (error) {
    notice.value = getApiErrorMessage(error, '地图数据重新加载失败')
  }
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
  selectedInfo.flowSource = 'local'
  selectedInfo.flowSummary = ''
  selectedInfo.routesList = []
  isStationDetailOpen.value = false
  isRoutesExpanded.value = false
  busMapRef.value?.hideRoutes()
}

const openChartPanel = (mode) => {
  panelMode.value = mode
  isInfoPanelOpen.value = true
  isAiChatOpen.value = false
}

const selectStation = (stop) => {
  panelMode.value = 'search'
  isInfoPanelOpen.value = true
  isAiChatOpen.value = false
  selectedRecommendedRoute.value = null
  isStationDetailOpen.value = true
  isRoutesExpanded.value = false
  selectedInfo.id = stop.stop_id
  selectedInfo.name = stop.stop_name
  selectedInfo.crowd = stop.crowd_level ? loadLevelText(stop.crowd_level) : '暂无实时客流'
  selectedInfo.status = '正在读取历史客流'
  selectedInfo.eta = stop.eta_minutes != null && Number.isFinite(Number(stop.eta_minutes))
    ? `约 ${Number(stop.eta_minutes).toFixed(1)} 分钟`
    : '暂无实时到站'
  selectedInfo.routes = stop.passing_routes?.join(' / ') || '暂无线路关联'
  selectedInfo.chart = stop.crowd_level === 'high' ? [68, 74, 82, 90, 76] : [34, 48, 56, 52, 44]
  selectedInfo.flowSource = 'local'
  selectedInfo.flowSummary = ''
  selectedInfo.routesList = stop.routesList || []
  loadStationFlowChart(stop)
  loadStationRealtime(stop)
}

const selectMapStop = (stop) => {
  selectStation(stop)
}

const selectRoad = (route) => {
  isStationDetailOpen.value = false
  selectedRecommendedRoute.value = null
  openChartPanel('road')
  selectedInfo.id = route.line_id || route.id
  selectedInfo.name = route.line_name || route.title
  selectedInfo.crowd = route.load || loadLevelText(route.crowd_level || route.load_code)
  selectedInfo.status = route.status || (selectedInfo.crowd === '拥挤' ? '建议关注' : '运行正常')
  selectedInfo.eta = route.eta || route.eta_minutes ? `约 ${route.eta || route.eta_minutes} 分钟` : '约 8 分钟'
  selectedInfo.routes = ''
  selectedInfo.chart = normalizeChart(route.chart)
}

const selectMapRoute = (route) => {
  selectRoad(route)
}

const handleShowRoutes = () => {
  if (!selectedInfo.id) return
  isRoutesExpanded.value = true
  const routes = busMapRef.value?.getStopRoutes(selectedInfo.id) || []
  selectedInfo.routesList = routes.map(route => ({
    ...route.properties,
    id: route.id,
    color: route.properties.color || route.properties.display_color
  }))
  busMapRef.value?.showStationRoutes({ stop_id: selectedInfo.id, stop_name: selectedInfo.name })
}

const handleCloseRoutes = () => {
  isRoutesExpanded.value = false
  busMapRef.value?.hideRoutes()
}

const handleShowEta = () => {
  notice.value = '正在获取实时到站信息...'
}

const handleSelectRoute = (route) => {
  busMapRef.value?.focusRouteById(route.line_id || route.id)
  selectMapRoute(route)
  isRoutesExpanded.value = false
}

const applyRecommendedRoute = (route) => {
  isStationDetailOpen.value = false
  const focusedRoute = busMapRef.value?.focusRouteById(route.id || route.line_id)
  selectedRecommendedRoute.value = {
    ...(focusedRoute || {}),
    ...route,
    id: route.id || focusedRoute?.line_id,
    title: route.title || focusedRoute?.line_name || '推荐路线',
    journeyTitle: `${query.start} → ${query.end}`
  }
  notice.value = `已在地图中定位：${selectedRecommendedRoute.value.title}`
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
    const hasStationPair = Number.isFinite(resolvedJourney.startStationId) && Number.isFinite(resolvedJourney.endStationId)
    const response = await askAiTravel({
      mode: hasStationPair ? 'suggest' : 'qa',
      question: text,
      ...(hasStationPair ? {
        start_station_id: resolvedJourney.startStationId,
        end_station_id: resolvedJourney.endStationId
      } : {}),
      preference: text.includes('舒适') || text.includes('不挤') ? 'low_load' : 'balanced',
      context: {
        current_location: query.start,
        destination: query.end,
        items: rawRouteOptions.value.slice(0, 4)
      }
    })
    const target = aiMessages.value.find((message) => message.id === replyId)
    if (target) {
      target.content = response.data?.answer || '后端未返回回答。'
    }
    const relatedRoute = response.data?.related_routes?.[0]
    const matchedRoute = relatedRoute ? normalizeRecommendation(relatedRoute) : findRouteForDestination()
    aiRecommendation.value = matchedRoute ? {
      ...matchedRoute,
      title: text.includes('舒适') ? `舒适优先：${matchedRoute.title}` : `综合推荐：${matchedRoute.title}`,
      reason: response.data?.answer || matchedRoute.reason
    } : null
  } catch (error) {
    const target = aiMessages.value.find((message) => message.id === replyId)
    if (target) {
      target.content = getApiErrorMessage(error, '后端 AI 接口暂不可用，请确认后端已启动。')
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
