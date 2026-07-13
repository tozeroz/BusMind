<!--
  文件：src/modules/profile/components/TravelStatsCard.vue
  用途：展示用户本周出行统计摘要。
  存放内容：收藏数量、查询次数、平均等待和舒适推荐比例。
  实现功能：以四格统计卡呈现个人出行概览。
-->
<template>
  <section class="profile-card stats-card">
    <header class="profile-card-header"><div><p>出行统计</p><h2>本周概览</h2></div></header>
    <div class="profile-stats-grid">
      <article><span>收藏线路</span><strong>{{ favoriteCount }}</strong><small>常用路线持续更新</small></article>
      <article><span>本周查询</span><strong>{{ queryCount }}</strong><small>高峰时段查询更频繁</small></article>
      <article><span>平均等待</span><strong>{{ averageWait }}<b> 分</b></strong><small>相比上周更加稳定</small></article>
      <article><span>舒适推荐</span><strong>92%</strong><small>偏好匹配度较高</small></article>
    </div>
  </section>
</template>
<script setup>
defineProps({ favoriteCount: { type: Number, required: true }, queryCount: { type: Number, required: true }, averageWait: { type: String, required: true } })
</script>