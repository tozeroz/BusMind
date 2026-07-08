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
        <RouterLink class="ghost-button" to="/login">退出登录</RouterLink>
      </nav>
    </aside>

    <main class="main-panel">
      <RouterView />
    </main>
  </div>
</template>
