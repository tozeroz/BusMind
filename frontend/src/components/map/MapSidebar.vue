<template>
  <aside v-if="stop" class="map-sidebar">
    <button class="map-sidebar-close" type="button" aria-label="关闭站点详情" @click="$emit('close')">
      ×
    </button>

    <div class="sidebar-header">
      <span class="sidebar-kicker">Bus Stop</span>
      <h3>{{ stop.stop_name }}</h3>
      <strong>{{ stop.stop_id }}</strong>
    </div>

    <dl class="sidebar-facts">
      <div>
        <dt>预计到站</dt>
        <dd>{{ stop.eta_minutes }} 分钟</dd>
      </div>
      <div>
        <dt>拥挤程度</dt>
        <dd>
          <span class="crowd-pill" :class="crowdClass">{{ crowdText }}</span>
        </dd>
      </div>
    </dl>

    <section class="passing-routes">
      <h4>经过线路</h4>
      <div class="route-tags">
        <span v-for="route in stop.passing_routes" :key="route">{{ route }}</span>
      </div>
    </section>
  </aside>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stop: {
    type: Object,
    default: null
  }
})

defineEmits(['close'])

const crowdText = computed(() => {
  const labels = {
    low: '舒适',
    medium: '适中',
    high: '拥挤'
  }
  return labels[props.stop?.crowd_level] || '未知'
})

const crowdClass = computed(() => `crowd-${props.stop?.crowd_level || 'unknown'}`)
</script>

<style scoped>
.map-sidebar {
  position: absolute;
  top: 18px;
  right: 18px;
  z-index: 5;
  width: min(340px, calc(100% - 36px));
  border: 1px solid rgba(255, 255, 255, 0.42);
  border-radius: 8px;
  padding: 20px;
  color: #fff;
  background: rgba(28, 45, 68, 0.58);
  backdrop-filter: blur(24px);
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.2);
}

.map-sidebar-close {
  position: absolute;
  top: 10px;
  right: 10px;
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.32);
  border-radius: 999px;
  color: #fff;
  font-size: 22px;
  line-height: 1;
  background: rgba(255, 255, 255, 0.12);
}

.sidebar-header {
  display: grid;
  gap: 7px;
  padding-right: 36px;
}

.sidebar-kicker {
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.sidebar-header h3 {
  font-size: 22px;
  line-height: 1.25;
}

.sidebar-header strong {
  width: max-content;
  border-radius: 999px;
  padding: 6px 10px;
  color: #17324f;
  background: rgba(255, 255, 255, 0.92);
}

.sidebar-facts {
  display: grid;
  gap: 12px;
  margin: 20px 0;
}

.sidebar-facts div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 8px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.1);
}

.sidebar-facts dt {
  color: rgba(255, 255, 255, 0.74);
}

.sidebar-facts dd {
  margin: 0;
  font-weight: 800;
}

.crowd-pill {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  border-radius: 999px;
  padding: 0 10px;
}

.crowd-low {
  color: #dcfce7;
  background: rgba(22, 163, 74, 0.42);
}

.crowd-medium {
  color: #ffedd5;
  background: rgba(249, 115, 22, 0.44);
}

.crowd-high {
  color: #fee2e2;
  background: rgba(220, 38, 38, 0.46);
}

.crowd-unknown {
  color: #dbeafe;
  background: rgba(37, 99, 235, 0.4);
}

.passing-routes {
  display: grid;
  gap: 12px;
}

.passing-routes h4 {
  margin: 0;
}

.route-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.route-tags span {
  border: 1px solid rgba(255, 255, 255, 0.34);
  border-radius: 999px;
  padding: 7px 11px;
  color: #fff;
  font-weight: 800;
  background: rgba(255, 255, 255, 0.14);
}

@media (max-width: 720px) {
  .map-sidebar {
    top: auto;
    right: 12px;
    bottom: 12px;
    left: 12px;
    width: auto;
  }
}
</style>
