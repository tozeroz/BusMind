<template>
  <div class="map-demo-page">
    <div class="map-header">
      <h2>新加坡公交地图演示</h2>
      <p>MapLibre GL JS + OneMap 底图 + 公交站点与线路可视化</p>
    </div>

    <div class="map-content">
      <BusMap @select-stop="selectedStop = $event" />
      <MapSidebar :stop="selectedStop" @close="selectedStop = null" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

import BusMap from '@/components/map/BusMap.vue'
import MapSidebar from '@/components/map/MapSidebar.vue'

const selectedStop = ref(null)
</script>

<style scoped>
.map-demo-page {
  width: 100%;
  height: 100vh;
  padding: 16px;
  box-sizing: border-box;
  background: #f5f7fa;
}

.map-header {
  margin-bottom: 12px;
}

.map-header h2 {
  margin: 0 0 6px;
}

.map-header p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.map-content {
  position: relative;
  height: calc(100vh - 100px);
  border-radius: 12px;
  overflow: hidden;
  background: #ffffff;
}
</style>
