<template>
  <main class="admin-shell">
    <aside class="admin-sidebar">
      <div class="brand">
        <span class="brand-mark">A</span>
        <div>
          <strong>管理后台</strong>
          <small>BusMind Admin</small>
        </div>
      </div>
      <nav class="nav-list">
        <a class="router-link-active">数据概览</a>
      </nav>
      <RouterLink class="admin-exit" to="/login">退出管理端</RouterLink>
    </aside>

    <section class="admin-main page-grid">
      <header class="topbar">
        <div>
          <p class="eyebrow">管理员端</p>
          <h1>基础数据与运行状态概览</h1>
        </div>
        <span class="status-dot">数据每 5 分钟更新</span>
      </header>

      <div class="stats-row">
        <article v-for="item in adminStats" :key="item.label" class="stat-card">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </article>
      </div>

      <div class="panel">
        <div class="section-title">
          <div>
            <p class="eyebrow">管理模块</p>
            <h2>公交运行数据管理</h2>
          </div>
          <span class="muted">路线、车辆和客流数据仅管理员端可见</span>
        </div>
        <div class="admin-grid">
          <article class="panel-soft">
            <h3>路线查询管理</h3>
            <p>查看推荐路线、线路详情、站点顺序和路线查询结果。</p>
          </article>
          <article class="panel-soft">
            <h3>车辆状态管理</h3>
            <p>查看车辆编号、当前位置、下一站、ETA 和运行状态。</p>
          </article>
          <article class="panel-soft">
            <h3>客流数据管理</h3>
            <p>查看客流量、拥挤趋势、站点热度和预测结果。</p>
          </article>
          <article class="panel-soft">
            <h3>基础数据维护</h3>
            <p>维护线路、站点、车辆和后续接口联调所需基础数据。</p>
          </article>
        </div>
      </div>

      <div class="admin-data-board">
        <section class="panel">
          <h3>路线查询</h3>
          <div class="admin-form-row">
            <input value="宿舍区" readonly />
            <input value="教学楼" readonly />
            <button class="ghost-button" type="button">查询</button>
          </div>
          <p class="muted">后续对接推荐路线接口，展示系统计算出的路线方案。</p>
        </section>

        <section class="panel">
          <h3>车辆状态</h3>
          <div class="admin-table-like">
            <span>车辆 A102</span>
            <span>宿舍区 → 食堂</span>
            <span>ETA 4 分钟</span>
            <span>拥挤</span>
          </div>
        </section>

        <section class="panel">
          <h3>客流数据</h3>
          <div class="empty-board admin-empty">
            <strong>核心数据展示区</strong>
            <p>等待确定客流预测字段后添加图表。</p>
          </div>
        </section>
      </div>
    </section>
  </main>
</template>

<script setup>
import { adminStats } from '@/utils/mockData'
</script>
