<!-- Admin operations view reuses the client line, vehicle, and passenger-flow pages. -->
<template>
  <main class="admin-shell admin-client-shell">
    <aside class="admin-sidebar">
      <div class="brand">
        <span class="brand-mark">A</span>
        <div>
          <strong>&#x7BA1;&#x7406;&#x5458;&#x7AEF;</strong>
          <small>BusMind Admin</small>
        </div>
      </div>

      <nav class="nav-list" aria-label="Admin data navigation">
        <button
          v-for="item in sections"
          :key="item.key"
          class="ghost-button"
          :class="{ 'router-link-active': activeSection === item.key }"
          type="button"
          @click="activeSection = item.key"
        >
          {{ item.label }}
        </button>
      </nav>

      <RouterLink class="admin-exit" to="/login" @click="clearAuthToken">
        &#x9000;&#x51FA;&#x7BA1;&#x7406;&#x5458;&#x7AEF;
      </RouterLink>
    </aside>

    <section class="admin-main admin-client-main">
      <header class="topbar admin-client-topbar">
        <div>
          <p class="eyebrow">&#x7BA1;&#x7406;&#x5458;&#x8FD0;&#x8425;&#x89C6;&#x56FE;</p>
          <h1>{{ activeSectionMeta.title }}</h1>
          <p class="muted">{{ activeSectionMeta.description }}</p>
        </div>
        <span class="status-dot">&#x771F;&#x5B9E;&#x63A5;&#x53E3;&#x6570;&#x636E;</span>
      </header>

      <KeepAlive>
        <component :is="activeComponent" :key="activeSection" />
      </KeepAlive>
    </section>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import LineListPage from '@/modules/line/components/LineListPage.vue'
import VehiclePage from '@/modules/vehicle/components/VehiclePage.vue'
import PassengerFlowPage from '@/modules/passenger-flow/components/PassengerFlowPage.vue'
import { clearAuthToken } from '@/api/user'

const sections = [
  {
    key: 'lines',
    label: '\u516c\u4ea4\u7ebf\u8def',
    title: '\u516c\u4ea4\u7ebf\u8def',
    description: '\u67e5\u770b\u7ebf\u8def\u3001\u8d77\u7ec8\u70b9\u4e0e\u7ad9\u70b9\u8be6\u60c5\u3002'
  },
  {
    key: 'vehicles',
    label: '\u8f66\u8f86\u72b6\u6001',
    title: '\u8f66\u8f86\u72b6\u6001',
    description: '\u67e5\u770b\u5b9e\u65f6\u8f66\u8f86\u4f4d\u7f6e\u3001\u8fd0\u884c\u72b6\u6001\u3001ETA \u4e0e\u5ba2\u8f7d\u60c5\u51b5\u3002'
  },
  {
    key: 'passenger-flow',
    label: '\u5ba2\u6d41\u8d8b\u52bf',
    title: '\u5ba2\u6d41\u8d8b\u52bf',
    description: '\u67e5\u770b\u5386\u53f2\u5ba2\u6d41\u8d8b\u52bf\u548c\u7ebf\u8def\u8f66\u8f86\u5ba2\u8f7d\u9884\u6d4b\u3002'
  }
]

const componentMap = {
  lines: LineListPage,
  vehicles: VehiclePage,
  'passenger-flow': PassengerFlowPage
}

const activeSection = ref('lines')
const activeSectionMeta = computed(
  () => sections.find((item) => item.key === activeSection.value) || sections[0]
)
const activeComponent = computed(() => componentMap[activeSection.value] || LineListPage)
</script>

<style scoped>
.admin-client-shell {
  height: 100vh;
  min-height: 0;
  overflow: hidden;
}

.admin-client-main {
  height: 100vh;
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  align-content: start;
  gap: 18px;
  overflow: hidden;
}

.admin-client-topbar {
  flex: 0 0 auto;
}

.admin-client-topbar .muted {
  margin-top: 6px;
}

@media (max-width: 900px) {
  .admin-client-shell {
    height: 100vh;
    overflow-y: auto;
  }

  .admin-client-main {
    height: auto;
    min-height: auto;
    overflow: visible;
  }
}
</style>
