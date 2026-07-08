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
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>

    <main class="main-panel">
      <header class="topbar">
        <div>
          <p class="eyebrow">乘客端</p>
          <h1>{{ currentTitle }}</h1>
        </div>
        <RouterLink class="ghost-button" to="/login">退出登录</RouterLink>
      </header>
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { path: '/home', label: '首页' },
  { path: '/ai', label: 'AI 助手' }
]

const currentTitle = computed(() => route.meta.title || '智行公交')
</script>
