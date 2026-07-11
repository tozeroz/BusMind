<template>
  <section class="page-grid">
    <div class="panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">线路详情</p>
          <h2>{{ line.line_name || line.service_no || '线路加载中' }}</h2>
          <p v-if="line.line_id">
            {{ line.start_station || '起点待补充' }} → {{ line.end_station || '终点待补充' }}
            · 方向 {{ line.direction }}
          </p>
        </div>
        <RouterLink class="ghost-button" to="/lines">返回列表</RouterLink>
      </div>

      <p v-if="loading" class="muted">正在加载线路和站点...</p>
      <p v-else-if="errorMessage" class="muted">{{ errorMessage }}</p>

      <div class="detail-grid">
        <div class="map-placeholder">
          <span>地图预留区</span>
          <p>{{ line.operator || '运营商未知' }} · 共 {{ line.total_stations || stations.length }} 个站点</p>
        </div>
        <div class="panel-soft">
          <h3>真实站点顺序</h3>
          <ol class="station-list">
            <li v-for="item in stations" :key="item.id || item.station_id">
              <span>{{ item.station?.station_name || '未知站点' }}</span>
              <small>第 {{ item.stop_sequence || item.order_index }} 站 · {{ item.station?.station_code || '' }}</small>
            </li>
          </ol>
          <p v-if="!loading && !errorMessage && stations.length === 0" class="muted">该线路暂时没有站点数据。</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getLineDetail } from '@/api/transit'

const route = useRoute()
const line = ref({})
const loading = ref(true)
const errorMessage = ref('')
const stations = computed(() => line.value.stations || [])

onMounted(async () => {
  try {
    const response = await getLineDetail(route.params.id)
    line.value = response?.data || {}
  } catch (error) {
    errorMessage.value = error?.response?.data?.message || '线路详情加载失败，请检查后端和数据库连接。'
  } finally {
    loading.value = false
  }
})
</script>
