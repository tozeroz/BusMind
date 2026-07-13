<!--
  文件：src/modules/vehicle/components/VehiclePage.vue
  用途：实现 vehicle 业务模块中的页面容器或业务组件。
  存放内容：该业务领域专属的界面结构、响应式状态和业务协调代码。
  实现功能：集中承载模块业务功能，并与路由入口、公共层和 API 层保持职责分离。
-->
<template>
  <section class="page-grid">
    <div class="panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">车辆状态</p>
          <h2>实时车辆运行情况</h2>
          <p class="muted">数据来自实时车辆接口；点击车辆后补充 LTA ETA 与实时客载。</p>
        </div>
        <select v-model="selectedLineId" class="compact-input">
          <option value="">全部线路</option>
          <option v-for="line in lines" :key="line.line_id" :value="String(line.line_id)">
            {{ line.line_name || line.service_no || `线路 ${line.line_id}` }}
          </option>
        </select>
      </div>

      <p v-if="errorMessage" class="form-tip">{{ errorMessage }}</p>

      <div class="detail-grid">
        <div class="map-placeholder">
          <span>{{ loading ? '正在加载车辆...' : `${vehicles.length} 辆车辆` }}</span>
          <p>实时坐标已接入，可继续复用首页 MapLibre 地图进行可视化。</p>
        </div>
        <div class="card-list compact">
          <article
            v-for="vehicle in vehicles"
            :key="vehicle.vehicle_id"
            class="vehicle-row clickable"
            tabindex="0"
            @click="openDetail(vehicle)"
            @keyup.enter="openDetail(vehicle)"
          >
            <div>
              <strong>{{ vehicle.vehicle_code || `车辆 ${vehicle.vehicle_id}` }}</strong>
              <p>{{ vehicle.line_name || vehicle.service_no || `线路 ${vehicle.line_id}` }} · {{ positionText(vehicle) }}</p>
              <span>下一站 {{ vehicle.next_station_name || vehicle.next_station_id || '未知' }} · {{ speedText(vehicle) }}</span>
            </div>
            <div class="card-actions">
              <span>{{ vehicle.onboard_count || 0 }}/{{ vehicle.capacity || 0 }} 人</span>
              <span class="level-tag" :class="crowdClass(loadText(vehicle))">{{ loadText(vehicle) }}</span>
              <span>{{ vehicle.data_status === 'realtime' ? '实时' : '估算' }}</span>
            </div>
          </article>
          <div v-if="!loading && vehicles.length === 0" class="empty-board admin-empty">
            <strong>暂无车辆数据</strong>
            <p>请检查线路筛选或后端数据导入状态。</p>
          </div>
        </div>
      </div>
    </div>

    <Transition name="side-card">
      <aside v-if="detailVehicle" class="vehicle-detail-panel">
        <div class="section-title">
          <div>
            <p class="eyebrow">车辆详情</p>
            <h3>{{ detailVehicle.vehicle_code || `车辆 ${detailVehicle.vehicle_id}` }}</h3>
          </div>
          <button class="ghost-button compact-ghost" type="button" @click="closeDetail">关闭</button>
        </div>
        <p v-if="detailError" class="form-tip">{{ detailError }}</p>
        <dl class="vehicle-detail-facts">
          <div><dt>线路</dt><dd>{{ detailVehicle.line_name || `线路 ${detailVehicle.line_id}` }}</dd></div>
          <div><dt>状态</dt><dd>{{ detailVehicle.status || '--' }}</dd></div>
          <div><dt>当前站</dt><dd>{{ detailVehicle.current_station_name || detailVehicle.current_station_id || '--' }}</dd></div>
          <div><dt>下一站</dt><dd>{{ detailVehicle.next_station_name || detailVehicle.next_station_id || '--' }}</dd></div>
          <div><dt>位置</dt><dd>{{ positionText(detailVehicle) }}</dd></div>
          <div><dt>速度</dt><dd>{{ speedText(detailVehicle) }}</dd></div>
          <div><dt>车上人数</dt><dd>{{ detailVehicle.onboard_count ?? '--' }} / {{ detailVehicle.capacity ?? '--' }}</dd></div>
          <div><dt>客载等级</dt><dd>{{ loadText(detailVehicle) }}</dd></div>
          <div><dt>客载率</dt><dd>{{ formatPercent(detailVehicle.predicted_load_rate ?? detailVehicle.load_rate) }}</dd></div>
          <div><dt>下一站 ETA</dt><dd>{{ formatEta(detailVehicle.predicted_eta_minutes) }}</dd></div>
          <div><dt>客载来源</dt><dd>{{ detailVehicle.load_model_version || detailVehicle.data_status || '--' }}</dd></div>
          <div><dt>更新时间</dt><dd>{{ formatTime(detailVehicle.last_updated_at || detailVehicle.update_time) }}</dd></div>
        </dl>
      </aside>
    </Transition>
  </section>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { getLines } from '@/api/transit'
import { getRealtimeVehicles, getVehicleDetail, getVehicles } from '@/api/vehicle'
import { getEta, predictPassengerLoad } from '@/api/intelligence'
import { getApiErrorMessage, unwrapList } from '@/api/response'
import { crowdClass } from '@/utils/format'

const selectedLineId = ref('')
const lines = ref([])
const vehicles = ref([])
const loading = ref(false)
const errorMessage = ref('')

const detailVehicle = ref(null)
const detailError = ref('')

const loadLines = async () => {
  const response = await getLines({ page: 1, limit: 100 })
  lines.value = unwrapList(response, 'lines')
}

const loadVehicles = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const params = selectedLineId.value ? { line_id: Number(selectedLineId.value) } : {}
    let response = await getRealtimeVehicles(params)
    let items = unwrapList(response, 'vehicles')
    if (!items.length) {
      response = await getVehicles({ page: 1, limit: 100, ...params })
      items = unwrapList(response, 'vehicles')
    }
    vehicles.value = items
  } catch (error) {
    vehicles.value = []
    errorMessage.value = getApiErrorMessage(error, '车辆数据加载失败')
  } finally {
    loading.value = false
  }
}

const positionText = (vehicle) => vehicle.current_position_text
  || vehicle.current_station_name
  || (vehicle.latitude && vehicle.longitude ? `${Number(vehicle.latitude).toFixed(4)}, ${Number(vehicle.longitude).toFixed(4)}` : '位置未知')

const speedText = (vehicle) => `${Number(vehicle.speed_kph ?? vehicle.speed_kmh ?? vehicle.speed ?? 0).toFixed(0)} km/h`

const loadText = (vehicle) => {
  const level = vehicle.load_level || vehicle.load_code
  const map = {
    SEA: '舒适', SDA: '适中', LSD: '拥挤',
    seats_available: '舒适', standing_available: '适中', limited_standing: '拥挤'
  }
  return map[level] || (vehicle.load_percent >= 90 ? '拥挤' : vehicle.load_percent >= 60 ? '适中' : '舒适')
}

const formatPercent = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? `${(num * 100).toFixed(0)}%` : '--'
}

const formatTime = (value) => value ? new Date(value).toLocaleString() : '--'
const formatEta = (value) => Number.isFinite(Number(value)) ? `${Number(value).toFixed(1)} 分钟` : '--'

const closeDetail = () => {
  detailVehicle.value = null
  detailError.value = ''
}

const openDetail = async (vehicle) => {
  detailError.value = ''
  const listItem = vehicles.value.find((item) => item.vehicle_id === vehicle.vehicle_id) || vehicle
  detailVehicle.value = { ...listItem }
  if (!Number.isFinite(Number(listItem.vehicle_id))) return
  try {
    const response = await getVehicleDetail(listItem.vehicle_id)
    const detail = response?.data
    const merged = detail ? { ...listItem, ...detail } : { ...listItem }
    detailVehicle.value = merged

    const targetStationId = Number(merged.next_station_id || merged.current_station_id)
    const lineId = Number(merged.line_id)
    if (!Number.isFinite(targetStationId) || !Number.isFinite(lineId)) return

    const loadPayload = {
      line_id: lineId,
      station_id: targetStationId,
      vehicle_id: Number(merged.vehicle_id)
    }
    if (Number(merged.capacity) > 0) loadPayload.capacity = Number(merged.capacity)
    if (Number(merged.onboard_count) >= 0) loadPayload.current_onboard_count = Number(merged.onboard_count)

    const [etaOutcome, loadOutcome] = await Promise.allSettled([
      getEta({ vehicle_id: Number(merged.vehicle_id), target_station_id: targetStationId, line_id: lineId }),
      predictPassengerLoad(loadPayload)
    ])
    if (etaOutcome.status === 'fulfilled') {
      detailVehicle.value = { ...detailVehicle.value, ...etaOutcome.value?.data }
    }
    if (loadOutcome.status === 'fulfilled') {
      const load = loadOutcome.value?.data || {}
      detailVehicle.value = {
        ...detailVehicle.value,
        ...load,
        load_level: load.predicted_load_level || detailVehicle.value.load_level,
        load_model_version: load.model_version
      }
    }
    const failures = [etaOutcome, loadOutcome].filter((item) => item.status === 'rejected')
    if (failures.length) detailError.value = '基础详情已加载，部分 ETA/客载数据暂不可用。'
  } catch (error) {
    detailError.value = getApiErrorMessage(error, '车辆详情加载失败，已显示当前缓存数据。')
  }
}

watch(selectedLineId, loadVehicles)

onMounted(async () => {
  try {
    await loadLines()
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '线路列表加载失败')
  }
  await loadVehicles()
})
</script>

<style scoped>
.clickable {
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.clickable:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(36, 116, 230, 0.16);
}
.clickable:focus {
  outline: 2px solid rgba(36, 116, 230, 0.6);
  outline-offset: 2px;
}

.vehicle-detail-panel {
  position: fixed;
  top: 96px;
  right: 24px;
  width: min(360px, calc(100% - 48px));
  border-radius: 14px;
  padding: 18px 20px;
  background: rgba(28, 45, 68, 0.92);
  color: #fff;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.32);
  z-index: 20;
}

.vehicle-detail-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 16px 0 0;
}

.vehicle-detail-facts div {
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  padding-bottom: 8px;
}

.vehicle-detail-facts dt {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
  margin-bottom: 4px;
}

.vehicle-detail-facts dd {
  margin: 0;
  font-weight: 600;
}

.side-card-enter-active,
.side-card-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.side-card-enter-from,
.side-card-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
