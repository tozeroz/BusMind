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
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}

.station-action-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-width: 0;
  min-height: 42px;
  padding: 8px 10px;
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 8px;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.2;
  backdrop-filter: blur(14px);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12);
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease, border-color 0.18s ease;
}

.primary-action-button {
  background: linear-gradient(135deg, rgba(45, 104, 151, 0.62), rgba(45, 145, 137, 0.5));
}

.primary-action-button:hover {
  border-color: rgba(255, 255, 255, 0.42);
  background: linear-gradient(135deg, rgba(45, 104, 151, 0.78), rgba(45, 145, 137, 0.66));
  transform: translateY(-1px);
}

.secondary-action-button {
  background: rgba(255, 255, 255, 0.11);
}

.secondary-action-button:hover {
  border-color: rgba(255, 255, 255, 0.42);
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-1px);
}

.action-icon {
  display: grid;
  flex: 0 0 24px;
  width: 24px;
  height: 24px;
  place-items: center;
  border-radius: 7px;
  font-size: 13px;
  background: rgba(255, 255, 255, 0.14);
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
  .station-action-buttons {
    grid-template-columns: 1fr;
  }
}
</style>
