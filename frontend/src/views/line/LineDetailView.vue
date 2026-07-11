<template>
  <section class="page-grid line-detail-page">
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
        <div class="panel-soft line-summary">
          <h3>线路信息</h3>
          <dl class="line-facts">
            <div><dt>线路编号</dt><dd>{{ line.line_code || '--' }}</dd></div>
            <div><dt>服务号</dt><dd>{{ line.service_no || '--' }}</dd></div>
            <div><dt>运营商</dt><dd>{{ line.operator || '--' }}</dd></div>
            <div><dt>运行状态</dt><dd>{{ line.status || '--' }}</dd></div>
            <div><dt>线路方向</dt><dd>{{ line.direction || '--' }}</dd></div>
            <div><dt>站点数量</dt><dd>{{ line.total_stations || stations.length }}</dd></div>
            <div><dt>线路距离</dt><dd>{{ formatDistance(line.distance_km) }}</dd></div>
            <div><dt>发车间隔</dt><dd>{{ formatInterval(line.interval_minutes) }}</dd></div>
            <div><dt>首班时间</dt><dd>{{ formatTime(line.first_departure_time) }}</dd></div>
            <div><dt>末班时间</dt><dd>{{ formatTime(line.last_departure_time) }}</dd></div>
            <div><dt>早高峰频率</dt><dd>{{ line.am_peak_freq || '--' }}</dd></div>
            <div><dt>晚高峰频率</dt><dd>{{ line.pm_peak_freq || '--' }}</dd></div>
          </dl>
        </div>
        <div class="panel-soft station-panel">
          <h3>真实站点顺序</h3>
          <ol class="station-list station-scroll">
            <li v-for="item in stations" :key="item.id || item.station_id">
              <span>
                <strong>{{ item.station?.station_name || '未知站点' }}</strong>
                <small>{{ item.station?.road_name || item.station?.address || '' }}</small>
              </span>
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

const formatTime = (value) => value ? String(value).slice(0, 5) : '--'
const formatDistance = (value) => Number.isFinite(Number(value)) ? `${Number(value).toFixed(1)} km` : '--'
const formatInterval = (value) => Number(value) > 0 ? `${value} 分钟` : '--'

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

<style scoped>
.line-detail-page {
  height: 100%;
  min-height: 0;
}

.line-detail-page > .panel {
  min-height: 0;
}

.line-summary,
.station-panel {
  min-height: 0;
}

.line-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 18px 0 0;
}

.line-facts div {
  border-bottom: 1px solid var(--line);
  padding-bottom: 10px;
}

.line-facts dt {
  margin-bottom: 4px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
}

.line-facts dd {
  margin: 0;
  font-weight: 600;
}

.station-scroll {
  max-height: calc(100vh - 250px);
  overflow-y: auto;
  padding-right: 8px;
}

.station-scroll li > span {
  display: grid;
  gap: 3px;
}

@media (max-width: 760px) {
  .line-detail-page {
    height: auto;
  }

  .line-facts {
    grid-template-columns: 1fr;
  }

  .station-scroll {
    max-height: 55vh;
  }
}
</style>
