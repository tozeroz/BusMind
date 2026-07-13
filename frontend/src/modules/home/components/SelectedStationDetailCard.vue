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

    <p v-if="station.flowSummary" class="selected-station-source">
      {{ station.flowSummary }}
    </p>
  </article>
</template>

<script setup>
const emit = defineEmits(['close'])

defineProps({
  station: {
    type: Object,
    required: true
  }
})
</script>
