<template>
  <main class="admin-shell">
    <aside class="admin-sidebar">
      <div class="brand">
        <span class="brand-mark">A</span>
        <div>
          <strong>管理后台</strong>
          <small>BusMind Admin</small>
        </div>
      </div>
      <nav class="nav-list">
        <a class="router-link-active">数据概览</a>
      </nav>
      <RouterLink class="admin-exit" to="/login">退出管理端</RouterLink>
    </aside>

    <section class="admin-main page-grid">
      <header class="topbar">
        <div>
          <p class="eyebrow">管理员端</p>
          <h1>基础数据与运行状态概览</h1>
        </div>
        <span class="status-dot">数据每 5 分钟更新</span>
      </header>

      <div class="stats-row">
        <article v-for="item in adminStats" :key="item.label" class="stat-card">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </article>
      </div>

      <div class="panel">
        <div class="section-title">
          <div>
            <p class="eyebrow">管理模块</p>
            <h2>公交运行数据管理</h2>
          </div>
          <span class="muted">路线、车辆和客流数据仅管理员端可见</span>
        </div>
        <div class="admin-grid">
          <article class="panel-soft">
            <h3>路线查询管理</h3>
            <p>查看推荐路线、线路详情、站点顺序和路线查询结果。</p>
          </article>
          <article class="panel-soft">
            <h3>车辆状态管理</h3>
            <p>查看车辆编号、当前位置、下一站、ETA 和运行状态。</p>
          </article>
          <article class="panel-soft">
            <h3>客流数据管理</h3>
            <p>查看客流量、拥挤趋势、站点热度和预测结果。</p>
          </article>
          <article class="panel-soft">
            <h3>基础数据维护</h3>
            <p>维护线路、站点、车辆和后续接口联调所需基础数据。</p>
          </article>
        </div>
      </div>

      <div class="admin-data-board">
        <section class="panel">
          <h3>LTA 实时到站刷新</h3>
          <div class="admin-form-row">
            <input v-model="arrivalForm.bus_stop_code" maxlength="5" placeholder="站点编号，例如 01012" />
            <input v-model="arrivalForm.service_no" placeholder="线路号，可选" />
            <label class="admin-check">
              <input v-model="arrivalForm.sync_to_db" type="checkbox" />
              写入数据库
            </label>
            <button class="ghost-button" type="button" :disabled="arrivalLoading" @click="refreshArrival">
              {{ arrivalLoading ? '刷新中' : '刷新' }}
            </button>
          </div>
          <p v-if="arrivalMessage" class="muted">{{ arrivalMessage }}</p>
          <div v-if="arrivalResult" class="admin-table-like">
            <span>{{ arrivalResult.dataset }}</span>
            <span>采集 {{ arrivalResult.collected }} 条</span>
            <span>同步 {{ arrivalResult.synced }} 条</span>
            <span>{{ formatRefreshTime(arrivalResult.refreshed_at) }}</span>
          </div>
        </section>

        <section class="panel">
          <h3>车辆状态</h3>
          <div class="admin-table-like">
            <span>车辆 A102</span>
            <span>宿舍区 → 食堂</span>
            <span>ETA 4 分钟</span>
            <span>拥挤</span>
          </div>
        </section>

        <section class="panel">
          <h3>客流数据</h3>
          <div class="empty-board admin-empty">
            <strong>核心数据展示区</strong>
            <p>等待确定客流预测字段后添加图表。</p>
          </div>
        </section>
      </div>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { refreshAdminLtaBusArrival } from '@/api/admin'
import { adminStats } from '@/utils/mockData'

const arrivalForm = reactive({
  bus_stop_code: '01012',
  service_no: '',
  sync_to_db: false
})
const arrivalLoading = ref(false)
const arrivalMessage = ref('')
const arrivalResult = ref(null)

const refreshArrival = async () => {
  const busStopCode = arrivalForm.bus_stop_code.trim()
  if (!/^\d{5}$/.test(busStopCode)) {
    arrivalMessage.value = '请输入 5 位公交站编号'
    return
  }

  arrivalLoading.value = true
  arrivalMessage.value = ''
  arrivalResult.value = null

  try {
    const response = await refreshAdminLtaBusArrival({
      bus_stop_code: busStopCode,
      service_no: arrivalForm.service_no.trim() || null,
      sync_to_db: arrivalForm.sync_to_db
    })
    arrivalResult.value = response.data
    arrivalMessage.value = '刷新成功，已从 LTA 获取最新到站数据。'
  } catch (error) {
    arrivalMessage.value = error?.response?.data?.message || '刷新失败，请确认后端、LTA Key 和数据库连接状态。'
  } finally {
    arrivalLoading.value = false
  }
}

const formatRefreshTime = (value) => {
  if (!value) return '刚刚'
  return new Date(value).toLocaleString()
}
</script>
