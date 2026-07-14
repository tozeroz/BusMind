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
        @select-stop-destination="selectMapDestination"
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
                <div class="station-autocomplete">
                  <input
                    v-model="query.start"
                    placeholder="输入当前位置"
                    autocomplete="off"
                    @input="handleStationInput('start')"
                    @focus="openStationSuggestions('start')"
                    @blur="closeStationSuggestions('start')"
                  />
                  <div v-if="stationSuggestionOpen.start" class="station-suggestion-list">
                    <button
                      v-for="station in stationSuggestions.start"
                      :key="station.station_id"
                      type="button"
                      @mousedown.prevent="chooseStationSuggestion('start', station)"
                    ><strong>{{ station.station_name }}</strong><small>{{ station.station_code || station.bus_stop_code || '' }}</small></button>
                    <p v-if="stationSuggestionLoading.start">&#x6B63;&#x5728;&#x641C;&#x7D22;&#x7AD9;&#x70B9;...</p>
                  </div>
                </div>
                <button class="locate-current-button" type="button" @click="getCurrentLocation">
                  定位
                </button>
              </label>
              <label class="search-box-row">
                <span>目标地点</span>
                <div class="station-autocomplete">
                  <input
                    v-model="query.end"
                    placeholder="搜索地点、公交站、线路"
                    autocomplete="off"
                    @input="handleStationInput('end')"
                    @focus="openStationSuggestions('end')"
                    @blur="closeStationSuggestions('end')"
                  />
                  <div v-if="stationSuggestionOpen.end" class="station-suggestion-list">
                    <button
                      v-for="station in stationSuggestions.end"
                      :key="station.station_id"
                      type="button"
                      @mousedown.prevent="chooseStationSuggestion('end', station)"
                    ><strong>{{ station.station_name }}</strong><small>{{ station.station_code || station.bus_stop_code || '' }}</small></button>
                    <p v-if="stationSuggestionLoading.end">&#x6B63;&#x5728;&#x641C;&#x7D22;&#x7AD9;&#x70B9;...</p>
                  </div>
                </div>
                <button class="search-submit-chip" type="submit" :disabled="isSearching">
                  {{ isSearching ? '检索中…' : '检索' }}
                </button>
              </label>
              <p v-if="notice" class="form-tip">{{ notice }}</p>
              <p class="muted map-selection-tip">
                &#x5730;&#x56FE;&#x5FEB;&#x6377;&#x64CD;&#x4F5C;&#xFF1A;&#x5DE6;&#x952E;&#x8BBE;&#x4E3A;&#x8D77;&#x70B9; &middot; &#x53F3;&#x952E;&#x8BBE;&#x4E3A;&#x76EE;&#x7684;&#x5730;
              </p>
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

          <p :class="['backend-listen-status', `is-${backendHealth.state}`]" role="status">
            <span class="backend-status-dot" aria-hidden="true"></span>
            {{ backendHealth.label }}
          </p>
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
        <SelectedLineDetailCard
          v-else-if="selectedLineDetail"
          :line="selectedLineDetail"
          :station-id="selectedLineStation.id"
          :station-name="selectedLineStation.name"
          :loads="selectedLineLoads"
          :loading="isSelectedLineLoading"
          :error="selectedLineLoadError"
          @close="closeSelectedLineDetail"
        />
        <SelectedStationDetailCard
          v-else-if="isStationDetailOpen"
          :station="selectedInfo"
          :is-routes-expanded="isRoutesExpanded"
          @close="closeStationDetail"
          @show-routes="handleShowRoutes"
          @close-routes="handleCloseRoutes"
          @select-route="handleSelectRoute"
        />
      </Transition>

      <Transition name="side-card">
        <AiAssistantPanel
          v-if="isAiChatOpen"
          :messages="aiMessages"
          :route="aiRecommendation"
          :loading="aiSending"
          :status="aiStatus"
          :missing-fields="aiMissingFields"
          :conversation-id="aiConversationId"
          @close="isAiChatOpen = false"
          @new-chat="newAiConversation"
          @send="sendAiMessage"
          @map="applyRecommendedRoute"
          @explain="explainAiRoute"
          @next="nextAiRoute"
        />
      </Transition>
    </section>

    <AiAssistantTrigger
      :style="{ left: `${floatPosition.x}px`, top: `${floatPosition.y}px` }"
      @drag-start="startFloatDrag"
      @toggle="toggleAiChat"
    />
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import BusMap from '@/modules/map/components/BusMap.vue'
import RouteResultsPopup from '@/modules/home/components/RouteResultsPopup.vue'
import SelectedRouteDetailCard from '@/modules/home/components/SelectedRouteDetailCard.vue'
import SelectedLineDetailCard from '@/modules/home/components/SelectedLineDetailCard.vue'
import SelectedStationDetailCard from '@/modules/home/components/SelectedStationDetailCard.vue'
import AiAssistantPanel from '@/modules/ai-assistant/components/AiAssistantPanel.vue'
import AiAssistantTrigger from '@/modules/ai-assistant/components/AiAssistantTrigger.vue'
import { useAiTravelConversation } from '@/modules/ai-assistant/composables/useAiTravelConversation'
import { searchLocations } from '@/api/location'
import { getEta, getRealtimePassengerLoad } from '@/api/intelligence'
import { getCachedBusArrival, getTrafficHeatmap } from '@/api/map'
import { getProgressiveRouteRecommendations, RECOMMENDATION_PREFERENCES } from '@/api/recommendation'
import { getPassengerFlowTrend } from '@/api/history'
import { getLineDetail, getStationDetail } from '@/api/transit'
import { getApiHealth } from '@/api/health'
import { getRealtimeVehicles } from '@/api/vehicle'
import { getApiErrorMessage, unwrapData, unwrapList } from '@/api/response'
import { triggerArrivalRefresh } from '@/api/user'

const refreshArrivals = () => {
  triggerArrivalRefresh().catch(() => {})
}

const busMapRef = ref(null)
const query = reactive({ start: 'Aft Braddell Rd', end: 'New Tech Pk' })
const selectedJourneyStations = reactive({ start: null, end: null })
const stationSuggestions = reactive({ start: [], end: [] })
const stationSuggestionOpen = reactive({ start: false, end: false })
const stationSuggestionLoading = reactive({ start: false, end: false })
const stationSuggestionSequence = { start: 0, end: 0 }
const stationSuggestionTimers = { start: null, end: null }
const notice = ref('')
const recommendation = ref(null)
const isSearching = ref(false)
const backendHealth = reactive({
  state: 'checking',
  label: '\u540e\u7aef\u76d1\u542c\uff1a\u68c0\u67e5\u4e2d',
  lastOnlineLabel: '',
  consecutiveFailures: 0
})
const backendHealthIntervalMs = 5000
const backendHealthTimeoutMs = 6000
const backendHealthOfflineThreshold = 2
let backendHealthRequestPending = false
let backendHealthTimer = null
const panelMode = ref('search')
const isInfoPanelOpen = ref(false)
const isAiChatOpen = ref(false)
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
  routesList: [],
  stationCode: '',
  busStopCode: '',
  stationStatus: ''
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
const selectedLineDetail = ref(null)
const selectedLineLoads = ref([])
const selectedLineStation = reactive({ id: null, name: '' })
const isSelectedLineLoading = ref(false)
const selectedLineLoadError = ref('')
let selectedLineRequestSequence = 0
const isStationDetailOpen = ref(false)
const isRoutesExpanded = ref(false)
const rawRouteOptions = ref([])
const resolvedJourney = reactive({ startStationId: null, endStationId: null })
const stationEtaRefreshIntervalMs = 30000
let stationEtaRefreshTimer = null
let stationEtaRefreshStop = null

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

const firstStationServiceNo = (station) => {
  const serviceNos = station?.service_nos
  if (Array.isArray(serviceNos)) return serviceNos.find(Boolean) || ''
  return String(serviceNos || '').split('|').map((item) => item.trim()).find(Boolean) || ''
}

const loadStationRealtime = async (station) => {
  const stationId = Number(station?.station_id ?? station?.stop_id)
  const lineId = Number(station?.line_ids?.[0] ?? station?.line_id)
  const busStopCode = String(station?.bus_stop_code || station?.station_code || '').trim()
  const serviceNo = firstStationServiceNo(station)

  try {
    if (busStopCode) {
      const arrivalResponse = await getCachedBusArrival({
        bus_stop_code: busStopCode,
        ...(serviceNo ? { service_no: serviceNo } : {})
      })
      if (String(selectedInfo.id) !== String(stationId)) return

      const arrival = unwrapData(arrivalResponse, {})?.next_arrival
      const eta = arrival?.eta_minutes
      if (Number.isFinite(Number(eta))) {
        selectedInfo.eta = `\u7ea6 ${Number(eta).toFixed(1)} \u5206\u949f`
        if (arrival?.load_code) selectedInfo.crowd = loadLevelText(arrival.load_code)
        return
      }
    }

    if (!Number.isFinite(stationId) || !Number.isFinite(lineId)) return
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

const clearStationEtaRefreshTimer = () => {
  if (stationEtaRefreshTimer) {
    window.clearInterval(stationEtaRefreshTimer)
    stationEtaRefreshTimer = null
  }
  stationEtaRefreshStop = null
}

const startStationEtaRefreshTimer = (station) => {
  clearStationEtaRefreshTimer()
  const stationId = station?.station_id ?? station?.stop_id
  if (stationId === undefined || stationId === null) return

  stationEtaRefreshStop = {
    ...station,
    line_ids: Array.isArray(station?.line_ids) ? [...station.line_ids] : station?.line_ids
  }
  stationEtaRefreshTimer = window.setInterval(() => {
    if (!isStationDetailOpen.value || String(selectedInfo.id) !== String(stationId)) {
      clearStationEtaRefreshTimer()
      return
    }
    loadStationRealtime(stationEtaRefreshStop)
  }, stationEtaRefreshIntervalMs)
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
  ...route,
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

const {
  messages: aiMessages,
  conversationId: aiConversationId,
  currentRoute: aiRecommendation,
  status: aiStatus,
  missingFields: aiMissingFields,
  isSending: aiSending,
  send: sendAiMessage,
  explainCurrentRoute: explainAiRoute,
  requestNextRoute: nextAiRoute,
  newConversation: newAiConversation
} = useAiTravelConversation({
  normalizeRoute: normalizeRecommendation,
  getJourneyContext: () => ({
    startStationId: resolvedJourney.startStationId,
    endStationId: resolvedJourney.endStationId,
    startName: query.start,
    endName: query.end,
    rawRoutes: rawRouteOptions.value.slice(0, 10)
  })
})

const findRouteForDestination = () => routeOptions.value[0] || null

const searchStation = async (keyword) => {
  const response = await searchLocations({
    keyword: keyword.trim(),
    page: 1,
    limit: 10,
    active_only: false
  })
  const stations = unwrapList(response, 'stations')
  const normalizedKeyword = keyword.trim().toLocaleLowerCase()
  return stations.find((station) =>
    String(station.station_name || '').trim().toLocaleLowerCase() === normalizedKeyword
    || String(station.station_code || station.bus_stop_code || '').trim().toLocaleLowerCase() === normalizedKeyword
  ) || stations[0] || null
}

const stationIdOf = (station) => {
  const stationId = Number(station?.station_id ?? station?.stop_id ?? station?.id)
  return Number.isInteger(stationId) && stationId > 0 ? stationId : null
}

const stationNameOf = (station) => String(station?.station_name || station?.stop_name || station?.name || '').trim()

const rememberJourneyStation = (type, station, { focus = true } = {}) => {
  const stationId = stationIdOf(station)
  const stationName = stationNameOf(station)
  if (!stationId || !stationName) return null

  const normalizedStation = { ...station, station_id: stationId, station_name: stationName }
  selectedJourneyStations[type] = normalizedStation
  query[type] = stationName
  resolvedJourney[type === 'start' ? 'startStationId' : 'endStationId'] = stationId
  stationSuggestions[type] = []
  stationSuggestionOpen[type] = false
  clearJourneyResults()
  if (focus) busMapRef.value?.focusStopByName(stationName)
  return normalizedStation
}

const loadStationSuggestions = async (type) => {
  const keyword = query[type].trim()
  const sequence = ++stationSuggestionSequence[type]
  if (!keyword) {
    stationSuggestions[type] = []
    stationSuggestionOpen[type] = false
    return
  }

  stationSuggestionLoading[type] = true
  try {
    const response = await searchLocations({ keyword, page: 1, limit: 8, active_only: false })
    if (sequence !== stationSuggestionSequence[type]) return
    stationSuggestions[type] = unwrapList(response, 'stations')
    stationSuggestionOpen[type] = true
  } catch {
    if (sequence === stationSuggestionSequence[type]) stationSuggestions[type] = []
  } finally {
    if (sequence === stationSuggestionSequence[type]) stationSuggestionLoading[type] = false
  }
}

const handleStationInput = (type) => {
  selectedJourneyStations[type] = null
  resolvedJourney[type === 'start' ? 'startStationId' : 'endStationId'] = null
  clearJourneyResults()
  if (stationSuggestionTimers[type]) window.clearTimeout(stationSuggestionTimers[type])
  stationSuggestionTimers[type] = window.setTimeout(() => loadStationSuggestions(type), 180)
}

const openStationSuggestions = (type) => {
  if (stationSuggestions[type].length) stationSuggestionOpen[type] = true
  else if (query[type].trim()) loadStationSuggestions(type)
}

const closeStationSuggestions = (type) => {
  window.setTimeout(() => { stationSuggestionOpen[type] = false }, 120)
}

const chooseStationSuggestion = (type, station) => {
  const selected = rememberJourneyStation(type, station)
  if (!selected) return
  notice.value = type === 'start'
    ? `\u5df2\u5c06 ${selected.station_name} \u8bbe\u4e3a\u8d77\u70b9`
    : `\u5df2\u5c06 ${selected.station_name} \u8bbe\u4e3a\u76ee\u7684\u5730`
}

const resolveJourneyStation = async (type) => {
  const remembered = selectedJourneyStations[type]
  if (remembered && stationIdOf(remembered) && stationNameOf(remembered) === query[type].trim()) return remembered

  const stationId = resolvedJourney[type === 'start' ? 'startStationId' : 'endStationId']
  if (stationId) return { station_id: stationId, station_name: query[type].trim() }

  const station = await searchStation(query[type])
  return station ? rememberJourneyStation(type, station, { focus: false }) : null
}

const searchRoutes = async () => {
  if (isSearching.value) return
  busMapRef.value?.clearSelection()
  recommendation.value = null
  selectedRecommendedRoute.value = null
  isStationDetailOpen.value = false
  clearStationEtaRefreshTimer()
  routeOptions.value = []
  rawRouteOptions.value = []
  if (!query.start.trim() || !query.end.trim()) {
    notice.value = '请输入完整的起点和终点'
    return
  }

  notice.value = '正在搜索站点并生成推荐路线...'
  isSearching.value = true
  backendHealth.state = backendHealth.lastOnlineLabel ? 'online' : 'checking'
  backendHealth.label = '\u540e\u7aef\u76d1\u542c\uff1a\u6b63\u5728\u5904\u7406\u68c0\u7d22'
  try {
    const [startStation, endStation] = await Promise.all([
      resolveJourneyStation('start'),
      resolveJourneyStation('end')
    ])
    if (!startStation || !endStation) {
      notice.value = '没有找到匹配站点，请输入更准确的站点名称'
      return
    }
    if (startStation.station_id === endStation.station_id) {
      notice.value = '起点和终点不能是同一站点'
      return
    }
    query.start = stationNameOf(startStation)
    query.end = stationNameOf(endStation)

    const { result } = await getProgressiveRouteRecommendations({
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
    checkBackendHealth()
  }
}

const checkBackendHealth = async () => {
  if (backendHealthRequestPending) return
  if (isSearching.value) {
    backendHealth.state = backendHealth.lastOnlineLabel ? 'online' : 'checking'
    backendHealth.label = '\u540e\u7aef\u76d1\u542c\uff1a\u6b63\u5728\u5904\u7406\u68c0\u7d22'
    return
  }
  backendHealthRequestPending = true
  try {
    const data = unwrapData(await getApiHealth({ timeout: backendHealthTimeoutMs }), {})
    if (data.status !== 'ok') throw new Error('Unexpected health status')
    backendHealth.state = 'online'
    backendHealth.label = `\u540e\u7aef\u76d1\u542c\uff1a\u6b63\u5e38${data.version ? ` \u00b7 ${data.version}` : ''}`
    backendHealth.lastOnlineLabel = backendHealth.label
    backendHealth.consecutiveFailures = 0
  } catch {
    if (isSearching.value) {
      backendHealth.state = backendHealth.lastOnlineLabel ? 'online' : 'checking'
      backendHealth.label = '\u540e\u7aef\u76d1\u542c\uff1a\u6b63\u5728\u5904\u7406\u68c0\u7d22'
      return
    }
    backendHealth.consecutiveFailures += 1
    if (backendHealth.consecutiveFailures >= backendHealthOfflineThreshold) {
      backendHealth.state = 'offline'
      backendHealth.label = '\u540e\u7aef\u76d1\u542c\uff1a\u672a\u8fde\u63a5'
    } else if (backendHealth.lastOnlineLabel) {
      backendHealth.state = 'online'
      backendHealth.label = backendHealth.lastOnlineLabel
    } else {
      backendHealth.state = 'checking'
      backendHealth.label = '\u540e\u7aef\u76d1\u542c\uff1a\u91cd\u8bd5\u4e2d'
    }
  } finally {
    backendHealthRequestPending = false
  }
}

const getCurrentLocation = async () => {
  const currentName = query.start.trim() || 'Aft Braddell Rd'
  query.start = currentName
  const remembered = selectedJourneyStations.start
  if (remembered && stationNameOf(remembered) === currentName) {
    busMapRef.value?.focusStopByName(currentName)
    notice.value = `\u5df2\u5b9a\u4f4d\u5230\u7ad9\u70b9\uff1a${currentName}`
    return
  }

  try {
    const focusedStop = busMapRef.value?.focusStopByName(currentName)
    const targetStation = focusedStop || await searchStation(currentName)
    if (!targetStation) {
      notice.value = `\u6ca1\u6709\u627e\u5230\u5339\u914d\u7ad9\u70b9\uff1a${currentName}`
      return
    }

    const selected = rememberJourneyStation('start', targetStation)
    notice.value = `\u5df2\u5b9a\u4f4d\u5230\u7ad9\u70b9\uff1a${selected.station_name}`
  } catch (error) {
    notice.value = getApiErrorMessage(error, `\u65e0\u6cd5\u5b9a\u4f4d\u5230\u7ad9\u70b9\uff1a${currentName}`)
  }
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

const loadSelectedStationDetail = async (stop) => {
  const stationId = stationIdOf(stop)
  if (!stationId) return

  try {
    const detail = unwrapData(await getStationDetail(stationId), {})
    if (String(selectedInfo.id) !== String(stationId)) return

    selectedInfo.name = detail.station_name || selectedInfo.name
    selectedInfo.stationCode = detail.station_code || detail.bus_stop_code || ''
    selectedInfo.busStopCode = detail.bus_stop_code || detail.station_code || ''
    selectedInfo.stationStatus = detail.status || ''
  } catch {
    if (String(selectedInfo.id) !== String(stationId)) return
    selectedInfo.stationStatus = '\u8be6\u60c5\u6682\u65f6\u4e0d\u53ef\u7528'
  }
}

const loadSelectedStationRoutes = () => {
  const routes = busMapRef.value?.getStopRoutes(selectedInfo.id) || []
  selectedInfo.routesList = routes.map(route => ({
    ...route.properties,
    id: route.id,
    color: route.properties.color || route.properties.display_color
  }))
  isRoutesExpanded.value = true
}

const resetPanel = () => {
  clearStationEtaRefreshTimer()
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
  selectedInfo.stationCode = ''
  selectedInfo.busStopCode = ''
  selectedInfo.stationStatus = ''
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
  clearStationEtaRefreshTimer()
  panelMode.value = 'search'
  isInfoPanelOpen.value = true
  isAiChatOpen.value = false
  selectedRecommendedRoute.value = null
  selectedLineDetail.value = null
  isStationDetailOpen.value = true
  isRoutesExpanded.value = true
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
  selectedInfo.routesList = []
  selectedInfo.stationCode = stop.station_code || stop.bus_stop_code || ''
  selectedInfo.busStopCode = stop.bus_stop_code || stop.station_code || ''
  selectedInfo.stationStatus = stop.status || 'active'
  loadSelectedStationDetail(stop)
  loadSelectedStationRoutes()
  loadStationFlowChart(stop)
  loadStationRealtime(stop)
  startStationEtaRefreshTimer(stop)
}

const clearJourneyResults = () => {
  selectedLineRequestSequence += 1
  recommendation.value = null
  selectedLineDetail.value = null
  selectedLineLoads.value = []
  selectedLineLoadError.value = ''
  isSelectedLineLoading.value = false
  busMapRef.value?.hideTrafficHeatmap()
  routeOptions.value = []
  rawRouteOptions.value = []
  selectedRecommendedRoute.value = null
}

const selectMapStop = (stop) => {
  const selected = rememberJourneyStation('start', stop, { focus: false })
  notice.value = selected ? `\u5df2\u5c06 ${selected.station_name} \u8bbe\u4e3a\u8d77\u70b9` : ''
  selectStation(stop)
}

const selectMapDestination = (stop) => {
  const selected = rememberJourneyStation('end', stop, { focus: false })
  if (!selected) return
  panelMode.value = 'search'
  isInfoPanelOpen.value = true
  isAiChatOpen.value = false
  isStationDetailOpen.value = false
  isRoutesExpanded.value = false
  clearStationEtaRefreshTimer()
  notice.value = `\u5df2\u5c06 ${selected.station_name} \u8bbe\u4e3a\u76ee\u7684\u5730\uff0c\u53ef\u76f4\u63a5\u70b9\u51fb\u68c0\u7d22`
}

const selectRoad = (route) => {
  clearStationEtaRefreshTimer()
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
  loadSelectedStationRoutes()
  busMapRef.value?.showStationRoutes({ stop_id: selectedInfo.id, stop_name: selectedInfo.name })
}

const handleCloseRoutes = () => {
  isRoutesExpanded.value = false
  busMapRef.value?.hideRoutes()
}

const handleShowEta = () => {
  notice.value = '正在获取实时到站信息...'
  if (stationEtaRefreshStop) loadStationRealtime(stationEtaRefreshStop)
}

const closeSelectedLineDetail = () => {
  selectedLineRequestSequence += 1
  selectedLineDetail.value = null
  selectedLineLoads.value = []
  busMapRef.value?.hideTrafficHeatmap()
  selectedLineLoadError.value = ''
  isSelectedLineLoading.value = false
}

const loadLineFromSelectedStation = async (route, stationId, stationName) => {
  const lineId = Number(route?.line_id ?? route?.id)
  if (!Number.isInteger(lineId) || lineId <= 0 || !stationId) return

  const sequence = ++selectedLineRequestSequence
  selectedLineDetail.value = { ...route, line_id: lineId }
  selectedLineStation.id = stationId
  selectedLineStation.name = stationName
  selectedLineLoads.value = []
  selectedLineLoadError.value = ''
  isSelectedLineLoading.value = true

  const [lineOutcome, vehiclesOutcome, heatmapOutcome] = await Promise.allSettled([
    getLineDetail(lineId),
    getRealtimeVehicles({ line_id: lineId }),
    getTrafficHeatmap({ line_id: lineId })
  ])
  if (sequence !== selectedLineRequestSequence) return

  if (lineOutcome.status === 'fulfilled') {
    selectedLineDetail.value = {
      ...route,
      ...unwrapData(lineOutcome.value, {}),
      line_id: lineId
    }
  } else {
    notice.value = getApiErrorMessage(lineOutcome.reason, '\u7ebf\u8def\u57fa\u7840\u4fe1\u606f\u6682\u65f6\u65e0\u6cd5\u8bfb\u53d6')
  }

  if (heatmapOutcome.status === 'fulfilled') {
    const heatmap = unwrapData(heatmapOutcome.value, {})
    const segmentCount = busMapRef.value?.showTrafficHeatmap(heatmap.traffic_segments || []) || 0
    notice.value = segmentCount
      ? `\u5df2\u52a0\u8f7d ${segmentCount} \u4e2a\u9053\u8def\u62e5\u5835\u70ed\u529b\u5206\u6bb5`
      : '\u5f53\u524d\u7ebf\u8def\u6682\u65e0\u53ef\u7528\u9053\u8def\u62e5\u5835\u70ed\u529b\u6570\u636e'
  } else {
    busMapRef.value?.hideTrafficHeatmap()
    notice.value = getApiErrorMessage(heatmapOutcome.reason, '\u9053\u8def\u62e5\u5835\u70ed\u529b\u6570\u636e\u6682\u65f6\u65e0\u6cd5\u8bfb\u53d6')
  }

  if (vehiclesOutcome.status !== 'fulfilled') {
    selectedLineLoadError.value = getApiErrorMessage(vehiclesOutcome.reason, '\u5f53\u524d\u7ebf\u8def\u8f66\u8f86\u6682\u65f6\u65e0\u6cd5\u8bfb\u53d6')
    isSelectedLineLoading.value = false
    return
  }

  const vehicles = unwrapList(vehiclesOutcome.value, 'vehicles').filter((vehicle) => vehicle.status !== 'offline')
  if (!vehicles.length) {
    isSelectedLineLoading.value = false
    return
  }

  const loadOutcomes = await Promise.allSettled(vehicles.map((vehicle) => getRealtimePassengerLoad({
    line_id: lineId,
    station_id: Number(stationId),
    vehicle_id: Number(vehicle.vehicle_id),
    current_onboard_count: Number(vehicle.onboard_count) || 0,
    capacity: Number(vehicle.capacity) || 60
  })))
  if (sequence !== selectedLineRequestSequence) return

  selectedLineLoads.value = loadOutcomes.flatMap((outcome, index) => {
    if (outcome.status !== 'fulfilled') return []
    const load = unwrapData(outcome.value, {})
    const vehicle = vehicles[index]
    return [{
      ...load,
      vehicle_id: load.vehicle_id || vehicle.vehicle_id,
      vehicle_code: vehicle.vehicle_code || '',
      current_station_name: vehicle.current_station_name || '',
      vehicle_status: vehicle.status || ''
    }]
  })
  if (!selectedLineLoads.value.length) {
    selectedLineLoadError.value = '\u5ba2\u8f7d\u63a5\u53e3\u6682\u65f6\u6ca1\u6709\u8fd4\u56de\u53ef\u7528\u6570\u636e'
  }
  isSelectedLineLoading.value = false
}

const handleSelectRoute = (route) => {
  const stationId = Number(selectedInfo.id)
  const stationName = selectedInfo.name
  if (!Number.isInteger(stationId) || stationId <= 0) return

  clearStationEtaRefreshTimer()
  selectedRecommendedRoute.value = null
  isStationDetailOpen.value = false
  isRoutesExpanded.value = false
  panelMode.value = 'search'
  isInfoPanelOpen.value = true
  isAiChatOpen.value = false
  busMapRef.value?.focusRouteById(route.line_id || route.id, { preserveStopId: stationId })
  busMapRef.value?.hideTrafficHeatmap()
  loadLineFromSelectedStation(route, stationId, stationName)
  notice.value = `\u6b63\u5728\u8bfb\u53d6 ${route.line_name || route.title || '\u5f53\u524d\u7ebf\u8def'} \u8be6\u60c5`
}

const applyRecommendedRoute = (route) => {
  clearStationEtaRefreshTimer()
  selectedLineDetail.value = null
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
  isAiChatOpen.value = !isAiChatOpen.value
}

const closeStationDetail = () => {
  isStationDetailOpen.value = false
  isRoutesExpanded.value = false
  clearStationEtaRefreshTimer()
}

onMounted(() => {
  checkBackendHealth()
  backendHealthTimer = window.setInterval(checkBackendHealth, backendHealthIntervalMs)
})

onBeforeUnmount(() => {
  clearStationEtaRefreshTimer()
  Object.values(stationSuggestionTimers).forEach((timer) => {
    if (timer) window.clearTimeout(timer)
  })
  if (backendHealthTimer) window.clearInterval(backendHealthTimer)
})
</script>
