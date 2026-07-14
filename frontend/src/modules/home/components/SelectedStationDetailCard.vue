<!--
  文件：src/modules/home/components/SelectedStationDetailCard.vue
  用途：展示用户在首页地图中选中的公交站点详情。
  存放内容：站点名称、编号、经过线路、实时到站、客流状态和客流摘要。
  实现功能：在地图右上角响应式展示站点信息，并向首页派发关闭事件。
-->
<template>
  <article class="map-chart-card chart-light selected-route-detail-card selected-station-detail-card">
    <header class="selected-route-detail-header">
      <div>
        <p class="eyebrow">站点详情</p>
        <h3>{{ station.name || '公交站点' }}</h3>
        <span>站点编号 {{ station.id || '—' }}</span>
      </div>
      <button class="ghost-button compact-ghost" type="button" @click="emit('close')">
        关闭
      </button>
    </header>

    <div class="station-basic-grid">
      <p><span>站点编码</span><strong>{{ station.stationCode || station.busStopCode || '—' }}</strong></p>
      <p><span>运行状态</span><strong :class="['station-status', `is-${station.stationStatus || 'unknown'}`]">{{ statusLabel(station.stationStatus) }}</strong></p>
    </div>

    <button
      v-if="!isRoutesExpanded"
      class="station-routes-reopen ghost-button"
      type="button"
      @click="emit('show-routes')"
    >查看经过线路</button>

    <Transition name="routes-expand">
      <section v-if="isRoutesExpanded" class="station-routes-expanded">
        <header class="routes-expanded-header">
          <span>连接该站点的公交线路</span>
          <button class="ghost-button compact-ghost" type="button" @click="emit('close-routes')">
            收起
          </button>
        </header>
        <ul v-if="station.routesList && station.routesList.length" class="routes-list">
          <li
            v-for="route in station.routesList"
            :key="`${route.line_id || route.id}-${route.direction || route.start_station}-${route.end_station}`"
            class="route-item"
            @click="emit('select-route', route)"
          >
            <span class="route-color-dot" :style="{ backgroundColor: route.color || '#4f8fc0' }"></span>
            <span class="route-name">{{ route.line_name || route.title || '线路' + (route.line_id || route.id) }}</span>
            <span class="route-direction">{{ route.start_station || '起点待定' }} → {{ route.end_station || '终点待定' }}</span>
          </li>
        </ul>
        <p v-else class="routes-empty">暂无线路数据</p>
      </section>
    </Transition>
  </article>
</template>

<script setup>
const emit = defineEmits(['close', 'show-routes', 'close-routes', 'select-route'])

defineProps({
  station: {
    type: Object,
    required: true
  },
  isRoutesExpanded: {
    type: Boolean,
    default: false
  }
})

const statusLabel = (status) => ({
  active: '正常服务',
  running: '正常服务',
  inactive: '暂停服务',
  offline: '暂停服务'
}[status] || status || '状态未知')
</script>

<style scoped>
.station-basic-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px;
  margin-top: 12px;
}

.station-basic-grid p {
  display: grid;
  gap: 5px;
  min-width: 0;
  margin: 0;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 8px;
  padding: 10px 11px;
  background: rgba(255, 255, 255, 0.08);
}

.station-basic-grid span {
  color: rgba(255, 255, 255, 0.58);
  font-size: 10px;
  letter-spacing: 0.05em;
}

.station-basic-grid strong {
  overflow: hidden;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.station-status {
  width: fit-content;
  border-radius: 999px;
  padding: 2px 8px;
  color: #bff7df !important;
  background: rgba(34, 197, 94, 0.18);
}

.station-status.is-inactive,
.station-status.is-offline {
  color: #ffd1c7 !important;
  background: rgba(239, 68, 68, 0.18);
}

.station-routes-reopen {
  width: 100%;
  margin-top: 12px;
}

.station-routes-expanded {
  margin-top: 12px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.09);
  backdrop-filter: blur(16px);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.routes-expanded-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  color: rgba(255, 255, 255, 0.78);
  font-size: 12px;
  font-weight: 700;
}

.routes-list {
  max-height: 200px;
  margin: 0;
  padding: 0 3px 0 0;
  overflow-y: auto;
  list-style: none;
  scrollbar-color: rgba(255, 255, 255, 0.48) rgba(255, 255, 255, 0.08);
}

.route-item {
  display: grid;
  grid-template-columns: 10px minmax(66px, auto) minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 6px;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.08);
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}

.route-item:hover {
  border-color: rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.16);
  transform: translateX(2px);
}

.route-item:last-child {
  margin-bottom: 0;
}

.route-color-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.12);
}

.route-name {
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}

.route-direction {
  min-width: 0;
  overflow: hidden;
  color: rgba(255, 255, 255, 0.68);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.routes-empty {
  padding: 20px;
  color: rgba(255, 255, 255, 0.68);
  font-size: 13px;
  text-align: center;
}

.routes-expand-enter-active,
.routes-expand-leave-active {
  transition: all 0.25s ease;
  overflow: hidden;
}

.routes-expand-enter-from,
.routes-expand-leave-to {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
  padding: 0 12px;
}

.routes-expand-enter-to,
.routes-expand-leave-from {
  opacity: 1;
  max-height: 300px;
}

@media (max-width: 520px) {
  .station-basic-grid {
    grid-template-columns: 1fr;
  }
}
</style>
