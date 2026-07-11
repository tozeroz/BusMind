<template>
  <main class="admin-shell">
    <aside class="admin-sidebar">
      <div class="brand">
        <span class="brand-mark">A</span>
        <div>
          <strong>管理后台</strong>
          <small>BusMind Admin</small>
        </div>
      </div>
      <nav class="nav-list">
        <a class="router-link-active">数据概览</a>
      </nav>
      <RouterLink class="admin-exit" to="/login">退出管理端</RouterLink>
    </aside>

    <section class="admin-main page-grid">
      <header class="topbar">
        <div>
          <p class="eyebrow">管理员端</p>
          <h1>基础数据与运行状态概览</h1>
        </div>
        <span class="status-dot">数据每 5 分钟更新</span>
      </header>

      <div class="stats-row">
        <article v-for="item in adminStats" :key="item.label" class="stat-card">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </article>
      </div>

      <div class="panel">
        <div class="section-title">
          <div>
            <p class="eyebrow">管理模块</p>
            <h2>公交运行数据管理</h2>
          </div>
          <span class="muted">路线、车辆和客流数据仅管理员端可见</span>
        </div>
        <div class="admin-grid">
          <article class="panel-soft">
            <h3>路线查询管理</h3>
            <p>查看推荐路线、线路详情、站点顺序和路线查询结果。</p>
          </article>
          <article class="panel-soft">
            <h3>车辆状态管理</h3>
            <p>查看车辆编号、当前位置、下一站、ETA 和运行状态。</p>
          </article>
          <article class="panel-soft">
            <h3>客流数据管理</h3>
            <p>查看客流量、拥挤趋势、站点热度和预测结果。</p>
          </article>
          <article class="panel-soft">
            <h3>基础数据维护</h3>
            <p>维护线路、站点、车辆和后续接口联调所需基础数据。</p>
          </article>
        </div>
      </div>

      <div class="admin-data-board">
        <section class="panel">
          <h3>LTA 实时到站刷新</h3>
          <div class="admin-form-row">
            <input v-model="arrivalForm.bus_stop_code" maxlength="5" placeholder="站点编号，例如 01012" />
            <input v-model="arrivalForm.service_no" placeholder="线路号，可选" />
            <label class="admin-check">
              <input v-model="arrivalForm.sync_to_db" type="checkbox" />
              写入数据库
            </label>
            <button class="ghost-button" type="button" :disabled="arrivalLoading" @click="refreshArrival">
              {{ arrivalLoading ? '刷新中' : '刷新' }}
            </button>
          </div>
          <p v-if="arrivalMessage" class="muted">{{ arrivalMessage }}</p>
          <div v-if="arrivalResult" class="admin-table-like">
            <span>{{ arrivalResult.dataset }}</span>
            <span>采集 {{ arrivalResult.collected }} 条</span>
            <span>同步 {{ arrivalResult.synced }} 条</span>
            <span>{{ formatRefreshTime(arrivalResult.refreshed_at) }}</span>
          </div>
        </section>

        <section class="panel">
          <h3>LTA 路况速度带刷新</h3>
          <div class="admin-form-row">
            <label class="admin-check">
              <input v-model="trafficForm.sync_to_db" type="checkbox" />
              写入数据库
            </label>
            <button class="ghost-button" type="button" :disabled="trafficLoading" @click="refreshTrafficSpeedBands">
              {{ trafficLoading ? '刷新中' : '刷新' }}
            </button>
          </div>
          <p v-if="trafficMessage" class="muted">{{ trafficMessage }}</p>
          <div v-if="trafficResult" class="admin-table-like">
            <span>{{ trafficResult.dataset }}</span>
            <span>采集 {{ trafficResult.collected }} 条</span>
            <span>同步 {{ trafficResult.synced }} 条</span>
            <span>{{ formatRefreshTime(trafficResult.refreshed_at) }}</span>
          </div>
        </section>

        <section class="panel">
          <h3>车辆状态</h3>
          <div v-for="vehicle in recentVehicles" :key="vehicle.vehicle_id" class="admin-table-like">
            <span>{{ vehicle.vehicle_code || `车辆 ${vehicle.vehicle_id}` }}</span>
            <span>{{ vehicle.line_name || `线路 ${vehicle.line_id}` }}</span>
            <span>{{ vehicle.current_position_text || vehicle.current_station_name || '位置未知' }}</span>
            <span>{{ vehicle.status }}</span>
          </div>
          <p v-if="!recentVehicles.length" class="muted">暂无车辆数据。</p>
        </section>

        <section class="panel">
          <h3>客流数据</h3>
          <div class="empty-board admin-empty">
            <strong>总客流 {{ flowSummary.total_flow || 0 }}</strong>
            <p>进站 {{ flowSummary.total_tap_in || 0 }} · 出站 {{ flowSummary.total_tap_out || 0 }} · {{ flowSummary.dominant_flow_level || '暂无等级' }}</p>
          </div>
        </section>
      </div>
    </section>
  </main>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { refreshAdminLtaBusArrival, refreshAdminLtaTrafficSpeedBands } from '@/api/admin'
import { getLines, getStations } from '@/api/transit'
import { getVehicles } from '@/api/vehicle'
import { getPassengerFlowTrend } from '@/api/history'

const adminStats = ref([
  { label: '线路', value: '-' },
  { label: '站点', value: '-' },
  { label: '车辆', value: '-' },
  { label: '客流', value: '-' }
])
const recentVehicles = ref([])
const flowSummary = ref({})

const arrivalForm = reactive({
  bus_stop_code: '01012',
  service_no: '',
  sync_to_db: false
})
const arrivalLoading = ref(false)
const arrivalMessage = ref('')
const arrivalResult = ref(null)

const trafficForm = reactive({ sync_to_db: false })
const trafficLoading = ref(false)
const trafficMessage = ref('')
const trafficResult = ref(null)

const refreshArrival = async () => {
  const busStopCode = arrivalForm.bus_stop_code.trim()
  if (!/^\d{5}$/.test(busStopCode)) {
    arrivalMessage.value = '请输入 5 位公交站编号'
    return
  }

  arrivalLoading.value = true
  arrivalMessage.value = ''
  arrivalResult.value = null

  try {
    const response = await refreshAdminLtaBusArrival({
      bus_stop_code: busStopCode,
      service_no: arrivalForm.service_no.trim() || null,
      sync_to_db: arrivalForm.sync_to_db
    })
    arrivalResult.value = response.data
    arrivalMessage.value = '刷新成功，已从 LTA 获取最新到站数据。'
  } catch (error) {
    arrivalMessage.value = error?.response?.data?.message || '刷新失败，请确认后端、LTA Key 和数据库连接状态。'
  } finally {
    arrivalLoading.value = false
  }
}

const refreshTrafficSpeedBands = async () => {
  trafficLoading.value = true
  trafficMessage.value = ''
  trafficResult.value = null
  try {
    const response = await refreshAdminLtaTrafficSpeedBands({
      sync_to_db: trafficForm.sync_to_db
    })
    trafficResult.value = response.data
    trafficMessage.value = '刷新成功，已从 LTA 获取最新路况速度带。'
  } catch (error) {
    trafficMessage.value = error?.response?.data?.message || '刷新失败，请确认后端、LTA Key 和数据库连接状态。'
  } finally {
    trafficLoading.value = false
  }
}

const formatRefreshTime = (value) => {
  if (!value) return '刚刚'
  return new Date(value).toLocaleString()
}

const loadOverview = async () => {
  try {
    const [lineResponse, stationResponse, vehicleResponse, flowResponse] = await Promise.all([
      getLines({ page: 1, limit: 1 }),
      getStations({ page: 1, limit: 1 }),
      getVehicles({ page: 1, limit: 5 }),
      getPassengerFlowTrend({ granularity: 'hour' })
    ])
    const vehicles = vehicleResponse.data?.vehicles || []
    flowSummary.value = flowResponse.data?.summary || {}
    recentVehicles.value = vehicles
    adminStats.value = [
      { label: '线路', value: lineResponse.data?.total ?? 0 },
      { label: '站点', value: stationResponse.data?.total ?? 0 },
      { label: '车辆', value: vehicleResponse.data?.total ?? vehicles.length },
      { label: '客流', value: flowSummary.value.total_flow ?? 0 }
    ]
  } catch (error) {
    arrivalMessage.value = error?.response?.data?.message || '管理概览加载失败'
  }
}

onMounted(loadOverview)
</script>
