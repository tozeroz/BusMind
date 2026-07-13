<!--
  文件：src/modules/profile/components/ProfileHero.vue
  用途：展示个人中心顶部身份与出行偏好摘要。
  存放内容：头像、用户名称、角色、常用通勤和今日偏好。
  实现功能：建立页面首要信息层级，并向父组件发出刷新操作。
-->
<template>
  <section class="profile-hero">
    <div class="profile-identity">
      <div class="profile-avatar" aria-hidden="true">{{ avatarText }}</div>
      <div>
        <p class="profile-kicker">个人中心</p>
        <h1>{{ displayName }}</h1>
      </div>
    </div>
    <aside class="today-preference">
      <span>今日出行偏好</span>
      <strong>舒适优先</strong>
      <p>系统会优先推荐客流较低、步行较少的路线。</p>
    </aside>
  </section>
</template>
<script setup>
defineProps({ displayName: { type: String, required: true }, avatarText: { type: String, required: true }, roleText: { type: String, required: true } })
</script>