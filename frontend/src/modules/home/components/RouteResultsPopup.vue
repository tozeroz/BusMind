<!--
  文件：src/modules/home/components/RouteResultsPopup.vue
  用途：展示首页路线检索返回的综合推荐列表。
  存放内容：最多六条候选路线的排名、核心指标和地图查看操作。
  实现功能：将路线结果从左侧信息栏中独立出来，并向首页派发选择与关闭事件。
-->
<template>
  <aside class="route-results-popup" aria-live="polite">
    <header class="route-results-header">
      <div>
        <p class="eyebrow">检索结果</p>
        <strong>综合推荐路线</strong>
      </div>
      <button class="route-results-close" type="button" aria-label="关闭检索结果" @click="emit('close')">
        ×
      </button>
    </header>

    <div class="route-results-list">
      <article v-for="(route, index) in routes.slice(0, 6)" :key="route.routeId || route.id || index" class="route-result-item">
        <span class="route-result-rank">{{ index + 1 }}</span>
        <div class="route-result-content">
          <strong :title="route.title">{{ route.title }}</strong>
          <div class="route-result-meta">
            <span>ETA {{ route.eta }} 分钟</span>
            <span>{{ route.score }} 分</span>
            <span>{{ route.load }}</span>
          </div>
        </div>
        <button class="route-result-action" type="button" @click="emit('select', route)">
          查看
        </button>
      </article>
    </div>
  </aside>
</template>

<script setup>
const emit = defineEmits(['select', 'close'])

defineProps({
  routes: {
    type: Array,
    default: () => []
  }
})
</script>