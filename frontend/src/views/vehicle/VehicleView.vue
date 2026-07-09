<template>
  <section class="page-grid">
    <div class="panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">车辆状态</p>
          <h2>实时车辆运行情况</h2>
        </div>
        <select v-model="selectedLine" class="compact-input">
          <option>全部线路</option>
          <option v-for="line in lines" :key="line.id">{{ line.name }}</option>
        </select>
      </div>

      <div class="detail-grid">
        <div class="map-placeholder">
          <span>车辆地图预留区</span>
          <p>后续接入地图 API 后，可展示车辆实时位置和行驶方向。</p>
        </div>
        <div class="card-list compact">
          <article v-for="vehicle in filteredVehicles" :key="vehicle.id" class="vehicle-row">
            <div>
              <strong>{{ vehicle.id }}</strong>
              <p>{{ vehicle.line }} · {{ vehicle.position }}</p>
              <span>下一站 {{ vehicle.next }} · ETA {{ vehicle.eta }} 分钟</span>
            </div>
            <div class="card-actions">
              <span>{{ vehicle.passengers }}/{{ vehicle.capacity }} 人</span>
              <span class="level-tag" :class="crowdClass(vehicle.crowd)">{{ vehicle.crowd }}</span>
            </div>
          </article>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { lines, vehicles } from '@/utils/mockData'
import { crowdClass } from '@/utils/format'

const selectedLine = ref('全部线路')
const filteredVehicles = computed(() => {
  if (selectedLine.value === '全部线路') return vehicles
  return vehicles.filter((item) => item.line === selectedLine.value)
})
</script>
