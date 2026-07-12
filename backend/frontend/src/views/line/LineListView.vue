<template>
  <section class="page-grid">
    <div class="panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">路线查询</p>
          <h2>新加坡公交线路</h2>
          <p class="muted">共 {{ total }} 条；当前第 {{ page }} 页。</p>
        </div>
        <input
          v-model="keyword"
          class="compact-input"
          placeholder="搜索线路名称或服务号"
          @input="scheduleSearch"
          @keydown.enter.prevent="loadLines(1)"
        />
      </div>

      <p v-if="loading" class="muted">正在加载线路...</p>
      <p v-else-if="errorMessage" class="form-tip">{{ errorMessage }}</p>
      <p v-else-if="lines.length === 0" class="muted">没有找到匹配的线路。</p>

      <div class="card-list">
        <article v-for="line in lines" :key="line.line_id" class="line-card">
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

      <div v-if="total > limit" class="card-actions pagination-actions">
        <button class="ghost-button" type="button" :disabled="page <= 1 || loading" @click="loadLines(page - 1)">上一页</button>
        <span class="muted">{{ page }} / {{ totalPages }}</span>
        <button class="ghost-button" type="button" :disabled="page >= totalPages || loading" @click="loadLines(page + 1)">下一页</button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getLines } from '@/api/transit'
import { getApiErrorMessage, unwrapList } from '@/api/response'

const keyword = ref('')
const lines = ref([])
const total = ref(0)
const page = ref(1)
const limit = 20
const loading = ref(false)
const errorMessage = ref('')
let searchTimer = null

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit)))

function isDisplayableLine(line) {
  const code = String(line?.line_code || '').toLowerCase()
  const name = String(line?.line_name || '').toLowerCase()
  return !code.includes('{{') && !name.includes('postman test')
}

async function loadLines(targetPage = page.value) {
  loading.value = true
  errorMessage.value = ''
  try {
    const params = { page: targetPage, limit }
    const text = keyword.value.trim()
    if (text) params.line_name = text
    const response = await getLines(params)
    lines.value = unwrapList(response, 'lines').filter(isDisplayableLine)
    total.value = Number(response?.data?.total ?? lines.value.length)
    page.value = targetPage
  } catch (error) {
    lines.value = []
    total.value = 0
    errorMessage.value = getApiErrorMessage(error, '真实线路加载失败，请检查后端和数据库连接。')
  } finally {
    loading.value = false
  }
}

function scheduleSearch() {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => loadLines(1), 350)
}

onMounted(() => loadLines(1))
onBeforeUnmount(() => window.clearTimeout(searchTimer))
</script>

<style scoped>
.pagination-actions {
  justify-content: center;
  margin-top: 18px;
}
</style>
