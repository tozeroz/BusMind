<!--
  文件：src/modules/admin/components/AdminPage.vue
  用途：实现 admin 业务模块中的页面容器或业务组件。
  存放内容：该业务领域专属的界面结构、响应式状态和业务协调代码。
  实现功能：集中承载模块业务功能，并与路由入口、公共层和 API 层保持职责分离。
-->
<template>
  <main class="admin-shell">
    <aside class="admin-sidebar">
      <div class="brand">
        <span class="brand-mark">A</span>
        <div><strong>管理后台</strong><small>BusMind Admin</small></div>
      </div>
      <nav class="nav-list">
        <button v-for="item in sections" :key="item.key" class="ghost-button" :class="{ 'router-link-active': activeSection === item.key }" type="button" @click="activeSection = item.key">
          {{ item.label }}
        </button>
      </nav>
      <RouterLink class="admin-exit" to="/login" @click="clearAuthToken">退出管理端</RouterLink>
    </aside>

    <section class="admin-main page-grid">
      <header class="topbar">
        <div><p class="eyebrow">管理员端</p><h1>基础数据与接口管理</h1></div>
        <span class="status-dot">{{ healthText }}</span>
      </header>

      <template v-if="activeSection === 'overview'">
        <div class="stats-row">
          <article v-for="item in adminStats" :key="item.label" class="stat-card"><span>{{ item.label }}</span><strong>{{ item.value }}</strong></article>
        </div>

        <div class="detail-grid">
          <section class="panel">
            <h3>LTA 实时到站刷新</h3>
            <div class="admin-form-grid">
              <input v-model="arrivalForm.bus_stop_code" maxlength="5" placeholder="5 位站点编号" />
              <input v-model="arrivalForm.service_no" placeholder="服务号（可选）" />
              <label class="checkbox-row"><input v-model="arrivalForm.sync_to_db" type="checkbox" />同步数据库</label>
              <button class="primary-button" type="button" :disabled="arrivalLoading" @click="refreshArrival">{{ arrivalLoading ? '刷新中' : '刷新到站' }}</button>
            </div>
            <p v-if="arrivalMessage" class="form-tip">{{ arrivalMessage }}</p>
            <pre v-if="arrivalResult" class="result-json">{{ pretty(arrivalResult) }}</pre>
          </section>

          <section class="panel">
            <h3>LTA 路况速度带刷新</h3>
            <div class="admin-form-grid">
              <label class="checkbox-row"><input v-model="trafficForm.sync_to_db" type="checkbox" />同步数据库</label>
              <button class="primary-button" type="button" :disabled="trafficLoading" @click="refreshTrafficSpeedBands">{{ trafficLoading ? '刷新中' : '刷新路况' }}</button>
            </div>
            <p v-if="trafficMessage" class="form-tip">{{ trafficMessage }}</p>
            <pre v-if="trafficResult" class="result-json">{{ pretty(trafficResult) }}</pre>
          </section>
        </div>

        <section class="panel">
          <div class="section-title"><div><p class="eyebrow">运行数据</p><h3>最近车辆</h3></div><button class="ghost-button" type="button" @click="loadOverview">刷新概览</button></div>
          <div class="card-list compact">
            <article v-for="vehicle in recentVehicles" :key="vehicle.vehicle_id" class="vehicle-row">
              <div><strong>{{ vehicle.vehicle_code || `车辆 ${vehicle.vehicle_id}` }}</strong><p>{{ vehicle.line_name || `线路 ${vehicle.line_id}` }} · {{ vehicle.current_position_text || vehicle.current_station_name || '位置未知' }}</p></div>
              <span class="level-tag">{{ vehicle.status }}</span>
            </article>
            <p v-if="!recentVehicles.length" class="muted">暂无车辆数据。</p>
          </div>
        </section>
      </template>

      <section v-else-if="activeSection === 'lines'" class="panel">
        <div class="section-title"><div><p class="eyebrow">CRUD /lines</p><h2>线路维护</h2></div><button class="ghost-button" type="button" @click="resetLineForm">新建线路</button></div>
        <form class="admin-form-grid entity-form" @submit.prevent="saveLine">
          <input v-model="lineForm.line_name" required placeholder="线路名称" />
          <input v-model="lineForm.line_code" :disabled="Boolean(editingLineId)" required placeholder="线路编码/服务号" />
          <input v-model="lineForm.start_station" placeholder="起点" />
          <input v-model="lineForm.end_station" placeholder="终点" />
          <select v-model="lineForm.status"><option value="running">running</option><option value="suspended">suspended</option><option value="offline">offline</option></select>
          <button class="primary-button" type="submit">{{ editingLineId ? '保存修改' : '创建线路' }}</button>
        </form>
        <p v-if="entityMessage" class="form-tip">{{ entityMessage }}</p>
        <div class="table-scroll"><table class="admin-table"><thead><tr><th>ID</th><th>线路</th><th>起终点</th><th>状态</th><th>操作</th></tr></thead><tbody>
          <tr v-for="item in lineItems" :key="item.line_id"><td>{{ item.line_id }}</td><td>{{ item.line_name }}<small>{{ item.line_code }}</small></td><td>{{ item.start_station }} → {{ item.end_station }}</td><td>{{ item.status }}</td><td><button type="button" @click="editLine(item)">编辑</button><button type="button" @click="removeLine(item)">删除</button><button type="button" @click="manageLineStations(item)">站序</button></td></tr>
        </tbody></table></div>

        <div v-if="relationLine" class="panel-soft relation-panel">
          <div class="section-title"><div><h3>{{ relationLine.line_name }} · 站序维护</h3><p class="muted">POST/PATCH/DELETE /lines/.../stations</p></div><button class="ghost-button" type="button" @click="relationLine = null">关闭</button></div>
          <form class="admin-form-grid" @submit.prevent="addRelation">
            <input v-model.number="relationForm.station_id" type="number" min="1" required placeholder="站点 ID" />
            <input v-model.number="relationForm.order_index" type="number" min="1" required placeholder="顺序" />
            <select v-model="relationForm.direction"><option value="forward">forward</option><option value="backward">backward</option></select>
            <button class="primary-button" type="submit">添加站点</button>
          </form>
          <div class="card-list compact">
            <article v-for="item in relationItems" :key="item.line_station_id || item.id" class="vehicle-row">
              <div><strong>#{{ item.order_index }} {{ item.station?.station_name || `站点 ${item.station_id}` }}</strong><p>{{ item.direction }}</p></div>
              <div class="card-actions"><button type="button" @click="moveRelation(item, -1)">上移</button><button type="button" @click="moveRelation(item, 1)">下移</button><button type="button" @click="removeRelation(item)">移除</button></div>
            </article>
          </div>
        </div>
      </section>

      <section v-else-if="activeSection === 'stations'" class="panel">
        <div class="section-title"><div><p class="eyebrow">CRUD /stations</p><h2>站点维护</h2></div><button class="ghost-button" type="button" @click="resetStationForm">新建站点</button></div>
        <form class="admin-form-grid entity-form" @submit.prevent="saveStation">
          <input v-model="stationForm.station_name" required placeholder="站点名称" />
          <input v-model="stationForm.station_code" placeholder="站点编码" />
          <input v-model.number="stationForm.latitude" type="number" step="0.000001" required placeholder="纬度" />
          <input v-model.number="stationForm.longitude" type="number" step="0.000001" required placeholder="经度" />
          <input v-model="stationForm.address" placeholder="地址/道路" />
          <button class="primary-button" type="submit">{{ editingStationId ? '保存修改' : '创建站点' }}</button>
        </form>
        <p v-if="entityMessage" class="form-tip">{{ entityMessage }}</p>
        <div class="table-scroll"><table class="admin-table"><thead><tr><th>ID</th><th>站点</th><th>坐标</th><th>状态</th><th>操作</th></tr></thead><tbody>
          <tr v-for="item in stationItems" :key="item.station_id"><td>{{ item.station_id }}</td><td>{{ item.station_name }}<small>{{ item.station_code }}</small></td><td>{{ item.latitude }}, {{ item.longitude }}</td><td>{{ item.status }}</td><td><button type="button" @click="editStation(item)">编辑</button><button type="button" @click="showStationLines(item)">经过线路</button><button type="button" @click="removeStation(item)">删除</button></td></tr>
        </tbody></table></div>
      </section>

      <section v-else class="panel">
        <div class="section-title"><div><p class="eyebrow">CRUD /vehicles</p><h2>车辆维护</h2></div><button class="ghost-button" type="button" @click="resetVehicleForm">新建车辆</button></div>
        <form class="admin-form-grid entity-form" @submit.prevent="saveVehicle">
          <input v-model="vehicleForm.vehicle_code" placeholder="车辆编码" />
          <input v-model.number="vehicleForm.line_id" type="number" min="1" :disabled="Boolean(editingVehicleId)" required placeholder="线路 ID" />
          <input v-model.number="vehicleForm.current_station_id" type="number" min="1" placeholder="当前站 ID" />
          <input v-model.number="vehicleForm.next_station_id" type="number" min="1" placeholder="下一站 ID" />
          <input v-model.number="vehicleForm.onboard_count" type="number" min="0" placeholder="车上人数" />
          <input v-model.number="vehicleForm.capacity" type="number" min="1" placeholder="容量" />
          <select v-model="vehicleForm.status"><option value="normal">normal</option><option value="delayed">delayed</option><option value="offline">offline</option></select>
          <button class="primary-button" type="submit">{{ editingVehicleId ? '保存修改' : '创建车辆' }}</button>
        </form>
        <p v-if="entityMessage" class="form-tip">{{ entityMessage }}</p>
        <div class="table-scroll"><table class="admin-table"><thead><tr><th>ID</th><th>车辆</th><th>线路</th><th>客载</th><th>状态</th><th>操作</th></tr></thead><tbody>
          <tr v-for="item in vehicleItems" :key="item.vehicle_id"><td>{{ item.vehicle_id }}</td><td>{{ item.vehicle_code || '--' }}</td><td>{{ item.line_id }}</td><td>{{ item.onboard_count }}/{{ item.capacity }}</td><td>{{ item.status }}</td><td><button type="button" @click="editVehicle(item)">编辑</button><button type="button" @click="removeVehicle(item)">删除</button></td></tr>
        </tbody></table></div>
      </section>
    </section>
  </main>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { refreshAdminLtaBusArrival, refreshAdminLtaTrafficSpeedBands } from '@/api/admin'
import {
  addStationToLine, createLine, createStation, deleteLine, deleteStation, getLineStations,
  getLines, getStationLines, getStations, removeStationFromLine, updateLine, updateLineStation, updateStation
} from '@/api/transit'
import { createVehicle, deleteVehicle, getVehicles, updateVehicle } from '@/api/vehicle'
import { getPassengerFlowTrend } from '@/api/history'
import { getApiHealth } from '@/api/health'
import { clearAuthToken } from '@/api/user'
import { getApiErrorMessage, unwrapList } from '@/api/response'

const sections = [
  { key: 'overview', label: '数据概览' }, { key: 'lines', label: '线路维护' },
  { key: 'stations', label: '站点维护' }, { key: 'vehicles', label: '车辆维护' }
]
const activeSection = ref('overview')
const healthText = ref('正在检查后端')
const adminStats = ref([{ label: '线路', value: '-' }, { label: '站点', value: '-' }, { label: '车辆', value: '-' }, { label: '客流', value: '-' }])
const recentVehicles = ref([])
const entityMessage = ref('')

const arrivalForm = reactive({ bus_stop_code: '01012', service_no: '', sync_to_db: false })
const arrivalLoading = ref(false)
const arrivalMessage = ref('')
const arrivalResult = ref(null)
const trafficForm = reactive({ sync_to_db: false })
const trafficLoading = ref(false)
const trafficMessage = ref('')
const trafficResult = ref(null)

const lineItems = ref([])
const stationItems = ref([])
const vehicleItems = ref([])
const editingLineId = ref(null)
const editingStationId = ref(null)
const editingVehicleId = ref(null)
const lineForm = reactive({ line_name: '', line_code: '', start_station: '', end_station: '', status: 'running' })
const stationForm = reactive({ station_name: '', station_code: '', latitude: 1.3521, longitude: 103.8198, address: '', status: 'active' })
const vehicleForm = reactive({ vehicle_code: '', line_id: null, current_station_id: null, next_station_id: null, onboard_count: 0, capacity: 60, status: 'normal' })

const relationLine = ref(null)
const relationItems = ref([])
const relationForm = reactive({ station_id: null, order_index: 1, direction: 'forward' })

const pretty = (value) => JSON.stringify(value, null, 2)
const cleanOptionalNumbers = (payload, keys) => {
  const result = { ...payload }
  keys.forEach((key) => { if (!Number.isFinite(Number(result[key]))) delete result[key]; else result[key] = Number(result[key]) })
  return result
}

async function checkHealth() {
  try { await getApiHealth(); healthText.value = '后端 /api/v1 正常' }
  catch { healthText.value = '后端连接异常' }
}

async function loadOverview() {
  try {
    const [lineResponse, stationResponse, vehicleResponse, flowResponse] = await Promise.all([
      getLines({ page: 1, limit: 1 }), getStations({ page: 1, limit: 1 }),
      getVehicles({ page: 1, limit: 5 }), getPassengerFlowTrend({ granularity: 'hour' })
    ])
    const vehicles = unwrapList(vehicleResponse, 'vehicles')
    const flowSummary = flowResponse.data?.summary || {}
    recentVehicles.value = vehicles
    adminStats.value = [
      { label: '线路', value: lineResponse.data?.total ?? 0 }, { label: '站点', value: stationResponse.data?.total ?? 0 },
      { label: '车辆', value: vehicleResponse.data?.total ?? vehicles.length }, { label: '客流', value: flowSummary.total_flow ?? 0 }
    ]
  } catch (error) { arrivalMessage.value = getApiErrorMessage(error, '管理概览加载失败') }
}

async function refreshArrival() {
  const code = arrivalForm.bus_stop_code.trim()
  if (!/^\d{5}$/.test(code)) { arrivalMessage.value = '请输入 5 位公交站编号'; return }
  arrivalLoading.value = true; arrivalMessage.value = ''; arrivalResult.value = null
  try {
    const response = await refreshAdminLtaBusArrival({ bus_stop_code: code, service_no: arrivalForm.service_no.trim() || null, sync_to_db: arrivalForm.sync_to_db })
    arrivalResult.value = response.data; arrivalMessage.value = '刷新成功。'
  } catch (error) { arrivalMessage.value = getApiErrorMessage(error, '刷新失败，请确认 LTA Key 和数据库连接。') }
  finally { arrivalLoading.value = false }
}

async function refreshTrafficSpeedBands() {
  trafficLoading.value = true; trafficMessage.value = ''; trafficResult.value = null
  try { const response = await refreshAdminLtaTrafficSpeedBands({ sync_to_db: trafficForm.sync_to_db }); trafficResult.value = response.data; trafficMessage.value = '刷新成功。' }
  catch (error) { trafficMessage.value = getApiErrorMessage(error, '刷新失败，请确认 LTA Key 和数据库连接。') }
  finally { trafficLoading.value = false }
}

async function loadLinesAdmin() { lineItems.value = unwrapList(await getLines({ page: 1, limit: 100 }), 'lines') }
async function loadStationsAdmin() { stationItems.value = unwrapList(await getStations({ page: 1, limit: 100 }), 'stations') }
async function loadVehiclesAdmin() { vehicleItems.value = unwrapList(await getVehicles({ page: 1, limit: 100 }), 'vehicles') }

function resetLineForm() { editingLineId.value = null; Object.assign(lineForm, { line_name: '', line_code: '', start_station: '', end_station: '', status: 'running' }) }
function editLine(item) { editingLineId.value = item.line_id; Object.assign(lineForm, { line_name: item.line_name || '', line_code: item.line_code || '', start_station: item.start_station || '', end_station: item.end_station || '', status: item.status || 'running' }) }
async function saveLine() {
  try {
    const payload = { ...lineForm }
    if (editingLineId.value) { delete payload.line_code; await updateLine(editingLineId.value, payload) } else await createLine(payload)
    entityMessage.value = editingLineId.value ? '线路已更新' : '线路已创建'; resetLineForm(); await loadLinesAdmin()
  } catch (error) { entityMessage.value = getApiErrorMessage(error, '线路保存失败') }
}
async function removeLine(item) { if (!window.confirm(`确认删除线路“${item.line_name}”？`)) return; try { await deleteLine(item.line_id); await loadLinesAdmin(); entityMessage.value = '线路已删除' } catch (error) { entityMessage.value = getApiErrorMessage(error, '线路删除失败') } }

function resetStationForm() { editingStationId.value = null; Object.assign(stationForm, { station_name: '', station_code: '', latitude: 1.3521, longitude: 103.8198, address: '', status: 'active' }) }
function editStation(item) { editingStationId.value = item.station_id; Object.assign(stationForm, { station_name: item.station_name || '', station_code: item.station_code || '', latitude: item.latitude, longitude: item.longitude, address: item.address || item.road_name || '', status: item.status || 'active' }) }
async function saveStation() { try { const payload = { ...stationForm, road_name: stationForm.address }; if (editingStationId.value) await updateStation(editingStationId.value, payload); else await createStation(payload); entityMessage.value = editingStationId.value ? '站点已更新' : '站点已创建'; resetStationForm(); await loadStationsAdmin() } catch (error) { entityMessage.value = getApiErrorMessage(error, '站点保存失败') } }
async function removeStation(item) { if (!window.confirm(`确认删除站点“${item.station_name}”？`)) return; try { await deleteStation(item.station_id); await loadStationsAdmin(); entityMessage.value = '站点已删除' } catch (error) { entityMessage.value = getApiErrorMessage(error, '站点删除失败') } }
async function showStationLines(item) { try { const response = await getStationLines(item.station_id); const lines = unwrapList(response, 'lines'); entityMessage.value = lines.length ? `${item.station_name}：${lines.map((line) => line.line_name || line.line_code).join('、')}` : `${item.station_name} 暂无经过线路` } catch (error) { entityMessage.value = getApiErrorMessage(error, '经过线路查询失败') } }

function resetVehicleForm() { editingVehicleId.value = null; Object.assign(vehicleForm, { vehicle_code: '', line_id: null, current_station_id: null, next_station_id: null, onboard_count: 0, capacity: 60, status: 'normal' }) }
function editVehicle(item) { editingVehicleId.value = item.vehicle_id; Object.assign(vehicleForm, { vehicle_code: item.vehicle_code || '', line_id: item.line_id, current_station_id: item.current_station_id, next_station_id: item.next_station_id, onboard_count: item.onboard_count || 0, capacity: item.capacity || 60, status: item.status || 'normal' }) }
async function saveVehicle() {
  try {
    let payload = cleanOptionalNumbers(vehicleForm, ['line_id', 'current_station_id', 'next_station_id', 'onboard_count', 'capacity'])
    if (editingVehicleId.value) { delete payload.line_id; delete payload.vehicle_code; await updateVehicle(editingVehicleId.value, payload) } else await createVehicle(payload)
    entityMessage.value = editingVehicleId.value ? '车辆已更新' : '车辆已创建'; resetVehicleForm(); await loadVehiclesAdmin()
  } catch (error) { entityMessage.value = getApiErrorMessage(error, '车辆保存失败') }
}
async function removeVehicle(item) { if (!window.confirm(`确认删除车辆“${item.vehicle_code || item.vehicle_id}”？`)) return; try { await deleteVehicle(item.vehicle_id); await loadVehiclesAdmin(); entityMessage.value = '车辆已删除' } catch (error) { entityMessage.value = getApiErrorMessage(error, '车辆删除失败') } }

async function manageLineStations(item) { relationLine.value = item; relationForm.order_index = 1; try { relationItems.value = unwrapList(await getLineStations(item.line_id), 'stations'); relationForm.order_index = relationItems.value.length + 1 } catch (error) { entityMessage.value = getApiErrorMessage(error, '站序加载失败') } }
async function addRelation() { try { await addStationToLine(relationLine.value.line_id, { line_id: relationLine.value.line_id, station_id: Number(relationForm.station_id), order_index: Number(relationForm.order_index), direction: relationForm.direction }); await manageLineStations(relationLine.value); entityMessage.value = '站点已加入线路' } catch (error) { entityMessage.value = getApiErrorMessage(error, '添加线路站点失败') } }
async function moveRelation(item, offset) { const next = Math.max(1, Number(item.order_index) + offset); try { await updateLineStation(item.line_station_id || item.id, { order_index: next, direction: item.direction }); await manageLineStations(relationLine.value) } catch (error) { entityMessage.value = getApiErrorMessage(error, '调整站序失败') } }
async function removeRelation(item) { try { await removeStationFromLine(item.line_station_id || item.id); await manageLineStations(relationLine.value); entityMessage.value = '站点已移除' } catch (error) { entityMessage.value = getApiErrorMessage(error, '移除站点失败') } }

watch(activeSection, async (section) => {
  entityMessage.value = ''
  try {
    if (section === 'lines') await loadLinesAdmin()
    if (section === 'stations') await loadStationsAdmin()
    if (section === 'vehicles') await loadVehiclesAdmin()
  } catch (error) { entityMessage.value = getApiErrorMessage(error, '管理数据加载失败') }
})

onMounted(async () => { await Promise.all([checkHealth(), loadOverview()]) })
</script>

<style scoped>
.admin-sidebar button { width: 100%; text-align: left; }
.admin-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin: 16px 0; }
.entity-form { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.checkbox-row { display: flex; align-items: center; gap: 8px; }
.result-json { max-height: 260px; overflow: auto; border-radius: 10px; padding: 12px; background: rgba(15, 23, 42, .06); white-space: pre-wrap; }
.table-scroll { overflow: auto; }
.admin-table { width: 100%; border-collapse: collapse; }
.admin-table th, .admin-table td { border-bottom: 1px solid rgba(148, 163, 184, .28); padding: 10px; text-align: left; vertical-align: top; }
.admin-table small { display: block; color: #64748b; }
.admin-table button { margin: 0 6px 6px 0; }
.relation-panel { margin-top: 20px; }
@media (max-width: 900px) { .admin-form-grid, .entity-form { grid-template-columns: 1fr; } }
</style>
