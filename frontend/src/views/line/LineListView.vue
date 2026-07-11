<template>
  <section class="page-grid">
    <div class="panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">路线查询</p>
          <h2>新加坡公交线路</h2>
          <p class="muted">当前展示数据库中的前 10 条线路，共 {{ total }} 条。</p>
        </div>
        <input v-model="keyword" class="compact-input" placeholder="搜索线路或站点" />
      </div>

      <p v-if="loading" class="muted">正在加载线路...</p>
      <p v-else-if="errorMessage" class="muted">{{ errorMessage }}</p>
      <p v-else-if="filteredLines.length === 0" class="muted">没有找到匹配的线路。</p>

      <div class="card-list">
        <article v-for="line in filteredLines" :key="line.line_id" class="line-card">
          <div>
            <h3>{{ line.line_name || line.service_no || line.line_code }}</h3>
            <p>{{ line.start_station || '起点待补充' }} → {{ line.end_station || '终点待补充' }}</p>
            <span class="muted">
              线路 {{ line.line_code }} · 方向 {{ line.direction }} · {{ line.total_stations }} 个站点
              <template v-if="line.first_departure_time || line.last_departure_time">
                · 首末班 {{ line.first_departure_time || '--' }} - {{ line.last_departure_time || '--' }}
              </template>
            </span>
          </div>
          <div class="card-actions">
            <span class="level-tag">{{ line.operator || '运营商未知' }}</span>
            <RouterLink class="ghost-button" :to="`/lines/${line.line_id}`">路线信息</RouterLink>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getLines } from '@/api/transit'

const keyword = ref('')
const lines = ref([])
const total = ref(0)
const loading = ref(true)
const errorMessage = ref('')

const filteredLines = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return lines.value
  return lines.value.filter((line) =>
    `${line.line_name}${line.line_code}${line.service_no}${line.start_station}${line.end_station}`
      .toLowerCase()
      .includes(text)
  )
})

onMounted(async () => {
  try {
    const response = await getLines({ page: 1, limit: 20 })
    const receivedLines = response?.data?.lines || []
    lines.value = receivedLines.filter(isDisplayableLine).slice(0, 10)
    total.value = Math.max((response?.data?.total || lines.value.length) - 1, lines.value.length)
  } catch (error) {
    errorMessage.value = error?.response?.data?.message || '真实线路加载失败，请检查后端和数据库连接。'
  } finally {
    loading.value = false
  }
})

function isDisplayableLine(line) {
  const code = String(line?.line_code || '').toLowerCase()
  const name = String(line?.line_name || '').toLowerCase()
  return !code.includes('{{') && !name.includes('postman test')
}
</script>
