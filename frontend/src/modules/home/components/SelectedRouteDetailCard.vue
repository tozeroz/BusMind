<!--
  文件：src/modules/home/components/SelectedRouteDetailCard.vue
  用途：展示用户从检索结果中选中的公交路线详情。
  存放内容：路线名称、行程、线路编号、到达时间、体验分、客流状态、运行状态和推荐理由。
  实现功能：在地图右侧集中呈现当前路线信息，并向首页派发关闭事件。
-->
<template>
  <article class="map-chart-card chart-light selected-route-detail-card">
    <header class="selected-route-detail-header">
      <div>
        <p class="eyebrow">当前路线</p>
        <h3>{{ route.title || '推荐路线' }}</h3>
        <span>{{ route.journeyTitle || '已选择路线' }}</span>
      </div>
      <button class="ghost-button compact-ghost" type="button" @click="emit('close')">
        关闭
      </button>
    </header>

    <div class="selected-route-detail-grid">
      <p><span>线路编号</span><strong>{{ route.id || route.routeId || '—' }}</strong></p>
      <p><span>预计到达</span><strong>约 {{ route.eta || '—' }} 分钟</strong></p>
      <p><span>体验评分</span><strong>{{ route.score || '—' }} 分</strong></p>
      <p><span>客流状态</span><strong>{{ route.load || '暂无数据' }}</strong></p>
      <p><span>运行状态</span><strong>{{ route.status || '可选路线' }}</strong></p>
    </div>

    <section class="selected-route-reason">
      <span>推荐说明</span>
      <p>{{ route.reason || '该路线根据预计到达时间、客流和出行体验综合计算得出。' }}</p>
    </section>
  </article>
</template>

<script setup>
const emit = defineEmits(['close'])

defineProps({
  route: {
    type: Object,
    required: true
  }
})
</script>
