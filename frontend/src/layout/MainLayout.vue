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
