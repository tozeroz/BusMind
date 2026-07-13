<!--
  文件：src/layouts/MainLayout.vue
  用途：定义应用级页面布局。
  存放内容：导航、整体页面框架和嵌套路由出口。
  实现功能：提供统一页面结构，不实现某个页面专属的业务逻辑。
-->
<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark">B</span>
        <div>
          <strong>智行公交</strong>
          <small>BusMind</small>
        </div>
      </div>
      <nav class="nav-list">
        <RouterLink class="ghost-button" to="/home">首页</RouterLink>
        <RouterLink class="ghost-button" to="/lines">公交线路</RouterLink>
        <RouterLink class="ghost-button" to="/vehicles">车辆状态</RouterLink>
        <RouterLink class="ghost-button" to="/passenger-flow">客流趋势</RouterLink>
        <RouterLink class="ghost-button" to="/ai">AI 助手</RouterLink>
        <RouterLink class="ghost-button" to="/profile">个人中心</RouterLink>
        <RouterLink class="ghost-button" to="/login" @click="clearAuthToken">退出登录</RouterLink>
      </nav>
    </aside>

    <main class="main-panel">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { clearAuthToken } from '@/api/user'
</script>
