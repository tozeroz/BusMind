<template>
  <section class="page-grid">
    <div class="panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">线路详情</p>
          <h2>{{ line.name }}</h2>
          <p>{{ line.start }} → {{ line.end }} · 首末班 {{ line.time }}</p>
        </div>
        <RouterLink class="ghost-button" to="/lines">返回列表</RouterLink>
      </div>

      <div class="detail-grid">
        <div class="map-placeholder">
          <span>地图预留区</span>
          <p>后续接入地图 API 后展示线路、站点和车辆位置。</p>
        </div>
        <div class="panel-soft">
          <h3>站点与 ETA</h3>
          <ol class="station-list">
            <li v-for="(station, index) in line.stations" :key="station">
              <span>{{ station }}</span>
              <small>{{ index + 2 }} 分钟后到达</small>
            </li>
          </ol>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="section-title">
        <h3>当前车辆</h3>
        <span class="level-tag" :class="crowdClass(line.crowd)">线路整体 {{ line.crowd }}</span>
      </div>
      <div class="vehicle-grid">
        <article v-for="vehicle in relatedVehicles" :key="vehicle.id" class="vehicle-card">
          <strong>{{ vehicle.id }}</strong>
          <p>{{ vehicle.position }}</p>
          <span>下一站：{{ vehicle.next }} · ETA {{ vehicle.eta }} 分钟</span>
          <span class="level-tag" :class="crowdClass(vehicle.crowd)">{{ vehicle.crowd }}</span>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { lines, vehicles } from '@/utils/mockData'
import { crowdClass } from '@/utils/format'

const route = useRoute()
const line = computed(() => lines.find((item) => item.id === route.params.id) || lines[0])
const relatedVehicles = computed(() => vehicles.filter((item) => item.line === line.value.name))
</script>
