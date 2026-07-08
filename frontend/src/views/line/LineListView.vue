<template>
  <section class="page-grid">
    <div class="panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">路线查询</p>
          <h2>{{ start }} 到 {{ end }} 的推荐路线</h2>
          <p class="muted">当前使用模拟数据展示，后续由 FastAPI 返回真实推荐结果。</p>
        </div>
        <input v-model="keyword" class="compact-input" placeholder="搜索线路或站点" />
      </div>

      <div class="card-list">
        <article v-for="line in filteredLines" :key="line.id" class="line-card">
          <div>
            <h3>{{ line.name }}</h3>
            <p>{{ line.start }} → {{ line.end }}</p>
            <span class="muted">预计等待 {{ line.wait }} 分钟 · 当前车辆 {{ line.vehicles }} 辆 · 首末班 {{ line.time }}</span>
          </div>
          <div class="card-actions">
            <span class="level-tag" :class="crowdClass(line.crowd)">{{ line.crowd }}</span>
            <RouterLink class="ghost-button" :to="`/lines/${line.id}`">路线信息</RouterLink>
            <RouterLink class="ghost-button" to="/vehicles">车辆信息</RouterLink>
            <RouterLink class="ghost-button" to="/recommend">客流数据</RouterLink>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { lines } from '@/utils/mockData'
import { crowdClass } from '@/utils/format'

const route = useRoute()
const keyword = ref('')
const start = computed(() => route.query.start || '出发地')
const end = computed(() => route.query.end || '目的地')
const filteredLines = computed(() => {
  const text = keyword.value.trim()
  if (!text) return lines
  return lines.filter((line) => `${line.name}${line.start}${line.end}${line.stations.join('')}`.includes(text))
})
</script>
