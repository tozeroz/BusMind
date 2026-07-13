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
        <p class="eyebrow">当前站点</p>
        <h3>{{ station.name || '公交站点' }}</h3>
        <span>站点编号 {{ station.id || '—' }}</span>
      </div>
      <button class="ghost-button compact-ghost" type="button" @click="emit('close')">
        关闭
      </button>
    </header>

    <div class="selected-route-detail-grid selected-station-detail-grid">
      <p><span>实时到站</span><strong>{{ station.eta || '暂无实时到站' }}</strong></p>
      <p><span>客流状态</span><strong>{{ station.crowd || '暂无客流数据' }}</strong></p>
      <p class="station-flow-summary"><span>客流摘要</span><strong>{{ station.status || '数据接入中' }}</strong></p>
    </div>

    <section class="selected-route-reason selected-station-routes">
      <span>经过线路</span>
      <p>{{ station.routes || '暂无线路关联' }}</p>
    </section>

    <div class="station-action-buttons">
      <button
        class="station-action-button primary-action-button"
        type="button"
        @click="emit('show-routes')"
      >
        <span class="action-icon">🚌</span>
        <span>公交线路图</span>
      </button>
      <button
        class="station-action-button secondary-action-button"
        type="button"
        @click="emit('show-eta')"
      >
        <span class="action-icon">⏱️</span>
        <span>巴士抵达时间</span>
      </button>
    </div>

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
            :key="route.line_id || route.id"
            class="route-item"
            @click="emit('select-route', route)"
          >
            <span class="route-color-dot" :style="{ backgroundColor: route.color || '#4f8fc0' }"></span>
            <span class="route-name">{{ route.line_name || route.title || '线路' + (route.line_id || route.id) }}</span>
            <span class="route-direction">{{ route.start_station }} → {{ route.end_station }}</span>
          </li>
        </ul>
        <p v-else class="routes-empty">暂无线路数据</p>
      </section>
    </Transition>

    <p v-if="station.flowSummary" class="selected-station-source">
      {{ station.flowSummary }}
    </p>
  </article>
</template>

<script setup>
const emit = defineEmits(['close', 'show-routes', 'show-eta', 'close-routes', 'select-route'])

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
</script>

<style scoped>
.station-action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.station-action-button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 12px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.primary-action-button {
  background: #e11d2e;
  color: #ffffff;
}

.primary-action-button:hover {
  background: #c91927;
}

.secondary-action-button {
  background: #f3f4f6;
  color: #374151;
}

.secondary-action-button:hover {
  background: #e5e7eb;
}

.action-icon {
  font-size: 14px;
}

.station-routes-expanded {
  margin-top: 16px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
}

.routes-expanded-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.routes-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 200px;
  overflow-y: auto;
}

.route-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  margin-bottom: 4px;
  background: #ffffff;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.route-item:hover {
  background: #f3f4f6;
}

.route-item:last-child {
  margin-bottom: 0;
}

.route-color-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.route-name {
  font-weight: 600;
  font-size: 14px;
  color: #1f2937;
  min-width: 60px;
}

.route-direction {
  font-size: 11px;
  color: #6b7280;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.routes-empty {
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
  padding: 20px;
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
</style>
