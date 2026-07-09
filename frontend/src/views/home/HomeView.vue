<template>
  <section class="home-map-layout">
    <aside class="destination-panel">
      <div class="side-scroll">
        <template v-if="panelMode === 'search'">
          <p class="eyebrow">乘客端</p>
          <h1>首页</h1>

          <form class="destination-search" @submit.prevent="searchRoutes">
            <p class="eyebrow">目的地检索</p>
            <h2>你要去哪里？</h2>
            <div class="location-line">
              <span>当前位置</span>
              <strong>定位获取</strong>
            </div>
            <label>
              目的地
              <input v-model="query.end" placeholder="如：教学楼" />
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
          <p class="eyebrow">站点信息</p>
          <h1>{{ selectedInfo.name }}</h1>
          <div class="info-list">
            <p><span>经过线路</span><strong>校园 1 号线 / 校园 2 号线</strong></p>
            <p><span>下一班车</span><strong>约 5 分钟</strong></p>
            <p><span>当前客流</span><strong>{{ selectedInfo.crowd }}</strong></p>
            <p><span>站点热度</span><strong>较高</strong></p>
          </div>
        </template>

        <template v-else>
          <button class="ghost-button back-side-button" type="button" @click="resetPanel">返回检索</button>
          <p class="eyebrow">线路信息</p>
          <h1>{{ selectedInfo.name }}</h1>
          <div class="info-list">
            <p><span>线路编号</span><strong>{{ selectedInfo.id }}</strong></p>
            <p><span>当前客流</span><strong>{{ selectedInfo.crowd }}</strong></p>
            <p><span>运行状态</span><strong>{{ selectedInfo.status }}</strong></p>
            <p><span>预计延误</span><strong>3 分钟</strong></p>
          </div>
        </template>
      </div>
    </aside>

    <section class="home-map-panel real-map-panel">
      <BusMap @select-stop="selectMapStop" @select-route="selectMapRoute" />

      <article v-if="panelMode !== 'search'" class="map-chart-card">
        <div class="section-title">
          <div>
            <p class="eyebrow">{{ panelMode === 'station' ? '站点图表' : '线路图表' }}</p>
            <h3>{{ selectedInfo.name }}</h3>
          </div>
          <button class="ghost-button" type="button" @click="resetPanel">关闭</button>
        </div>
        <div class="mini-chart">
          <span style="height: 42%"></span>
          <span style="height: 70%"></span>
          <span style="height: 56%"></span>
          <span style="height: 88%"></span>
          <span style="height: 64%"></span>
        </div>
        <p class="muted">后续接入客流数据后，这里展示真实统计图表。</p>
      </article>
    </section>

    <button
      class="ai-floating-button"
      type="button"
      :style="{ left: `${floatPosition.x}px`, top: `${floatPosition.y}px` }"
      @mousedown.stop="startFloatDrag"
      @click="openAi"
      title="AI 出行助手"
    >
      AI
    </button>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { recommendRoutes } from '@/api/bus'
import BusMap from '@/components/map/BusMap.vue'

const router = useRouter()
const query = reactive({ end: '教学楼' })
const notice = ref('')
const recommendation = ref(null)
const panelMode = ref('search')
const selectedInfo = reactive({ id: '', name: '', crowd: '', status: '' })
const floatPosition = reactive({ x: window.innerWidth - 112, y: window.innerHeight - 120 })
const dragState = reactive({ dragging: false, moved: false, offsetX: 0, offsetY: 0 })

const stats = [
  { label: '运行线路', value: '3 条' },
  { label: '在线车辆', value: '12 辆' },
  { label: '平均等待', value: '7 分钟' },
  { label: '当前客流', value: '适中' }
]

const stationIdByKeyword = (keyword) => {
  if (keyword.includes('图书')) return 2
  if (keyword.includes('教学')) return 3
  if (keyword.includes('南门')) return 4
  if (keyword.includes('西门')) return 5
  if (keyword.includes('创新')) return 12
  return 3
}

const loadLevelText = (level) => {
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

const searchRoutes = async () => {
  notice.value = '正在请求推荐路线...'
  const endStationId = stationIdByKeyword(query.end)
  try {
    const response = await recommendRoutes({
      start_station_id: 1,
      end_station_id: endStationId,
      preference: 'balanced'
    })
    const route = response.data?.items?.[0]
    if (!route) throw new Error('empty recommendation')
    const lineNames = route.segments.map((segment) => segment.line_name).join(' → ')
    recommendation.value = {
      title: lineNames || route.route_id,
      reason: route.reason,
      eta: route.predicted_eta_minutes,
      score: route.experience_score,
      load: loadLevelText(route.predicted_load?.predicted_load_level)
    }
    notice.value = `已检索目的地：${query.end}`
  } catch (error) {
    recommendation.value = {
      title: '校园 2 号线',
      reason: '后端暂未连接成功，当前显示本地演示推荐结果。',
      eta: 8,
      score: 86,
      load: '预计有座'
    }
    notice.value = '后端接口暂不可用，已显示演示数据'
  }
}

const resetPanel = () => {
  panelMode.value = 'search'
  selectedInfo.id = ''
  selectedInfo.name = ''
  selectedInfo.crowd = ''
  selectedInfo.status = ''
}

const selectStation = (name, crowd) => {
  panelMode.value = 'station'
  selectedInfo.id = ''
  selectedInfo.name = name
  selectedInfo.crowd = crowd
  selectedInfo.status = '正常停靠'
}

const selectMapStop = (stop) => {
  selectStation(stop.stop_name, loadLevelText(stop.crowd_level))
}

const selectRoad = (id, name, crowd) => {
  panelMode.value = 'road'
  selectedInfo.id = id
  selectedInfo.name = name
  selectedInfo.crowd = crowd
  selectedInfo.status = crowd === '拥挤' ? '建议关注' : '运行正常'
}

const selectMapRoute = (route) => {
  selectRoad(route.line_id, route.line_name, loadLevelText(route.crowd_level))
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

const openAi = () => {
  if (dragState.moved) return
  router.push('/ai')
}
</script>
