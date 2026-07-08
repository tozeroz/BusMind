<template>
  <section class="page-grid">
    <div class="navigation-page">
      <div class="map-stage">
        <div class="map-toolbar">
          <strong>地图预留区</strong>
          <span>后续接入地图 API 后展示可移动地图、站点、线路和车辆位置</span>
        </div>
        <div class="map-road horizontal"></div>
        <div class="map-road vertical"></div>
        <div class="map-pin start">起</div>
        <div class="map-pin end">终</div>
      </div>

      <form class="route-search-panel" @submit.prevent="searchRoutes">
        <p class="eyebrow">路线规划</p>
        <h2>你要去哪里？</h2>
        <label>
          出发地
          <input v-model="query.start" placeholder="如：宿舍区" />
        </label>
        <label>
          目的地
          <input v-model="query.end" placeholder="如：教学楼" />
        </label>
        <button class="primary-button" type="submit">询问 AI 出行助手</button>
        <p v-if="notice" class="form-tip">{{ notice }}</p>
      </form>
    </div>

    <div class="stats-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </div>

    <div class="panel">
      <div class="section-title">
        <h3>功能入口</h3>
        <p>乘客端保留地图首页和 AI 出行助手，路线、车辆、客流数据归入管理员端。</p>
      </div>
      <div class="feature-grid">
        <RouterLink v-for="item in features" :key="item.path" class="feature-card" :to="item.path">
          <strong>{{ item.title }}</strong>
          <span>{{ item.desc }}</span>
        </RouterLink>
      </div>
    </div>
  </section>
</template>

<script setup>
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ref } from 'vue'

const router = useRouter()
const query = reactive({ start: '宿舍区', end: '教学楼' })
const notice = ref('')

const searchRoutes = () => {
  notice.value = `已带入：${query.start} → ${query.end}`
  router.push('/ai')
}

const stats = [
  { label: '运行线路', value: '3 条' },
  { label: '在线车辆', value: '12 辆' },
  { label: '平均等待', value: '7 分钟' },
  { label: '当前客流', value: '适中' }
]

const features = [
  { title: 'AI 出行助手', desc: '用自然语言获取出行建议', path: '/ai' },
  { title: '地图预览', desc: '后续展示可移动地图和实时位置', path: '/home' }
]
</script>
