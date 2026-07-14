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
          <strong>{{ $route.path === '/profile' ? '个人中心' : '智行公交' }}</strong>
          <small>{{ $route.path === '/profile' ? 'Profile' : 'BusMind' }}</small>
        </div>
      </div>
      <nav class="nav-list">
        <RouterLink
          class="ghost-button"
          :to="$route.path === '/profile' ? '/home' : '/profile'"
        >
          {{ $route.path === '/profile' ? '返回首页' : '个人中心' }}
        </RouterLink>
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
