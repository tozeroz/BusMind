<!--
  文件：src/modules/profile/components/ProfilePage.vue
  用途：编排个人中心业务模块的完整页面。
  存放内容：页面顶部导航、身份横幅、三列内容布局和模块组件通信。
  实现功能：按参考图还原个人中心排布，同时保持数据逻辑与展示组件分离。
-->
<template>
  <div class="profile-page-shell">
<main class="profile-scroll-area">
      <div class="profile-content">
        <ProfileHero :display-name="displayName" :avatar-text="avatarText" :role-text="roleText" />
        <p v-if="message" class="profile-message" role="status">{{ message }}</p>
        <div v-if="loading" class="profile-loading">正在加载个人数据…</div>
        <div v-else class="profile-dashboard-grid">
          <div class="profile-column">
            <ProfileAccountCard :user="user" :form="profileForm" :editing="editing" :saving="saving" @edit="editing=true" @cancel="cancelEdit" @save="saveProfile" />
          </div>
          <div class="profile-column">
            <FavoriteRoutesCard :favorites="favorites" @remove="removeFavorite" />
          </div>
          <div class="profile-column">
            <RecentActivityCard :histories="histories" />
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { useProfilePage } from '@/modules/profile/composables/useProfilePage'
import ProfileHero from './ProfileHero.vue'
import ProfileAccountCard from './ProfileAccountCard.vue'
import FavoriteRoutesCard from './FavoriteRoutesCard.vue'
import RecentActivityCard from './RecentActivityCard.vue'

const {
  user, favorites, histories, loading, saving, editing, message, profileForm,
  displayName, avatarText, roleText,
  saveProfile, cancelEdit, removeFavorite
} = useProfilePage()
</script>

<style scoped>
.profile-page-shell {
  position: relative;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  color: #f7fbff;
}
.profile-scroll-area { height:100%; min-height:0; overflow-y:auto; scrollbar-gutter:stable; scrollbar-color:rgba(255,255,255,.76) rgba(15,39,67,.18); }
.profile-content { width:100%; margin:0 auto; padding:18px 22px 30px; }
.profile-dashboard-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:18px; align-items:stretch; }
.profile-column { display:grid; min-width:0; }
.profile-message,.profile-loading { margin:0 0 16px; border:1px solid rgba(255,255,255,.28); border-radius:10px; padding:12px 16px; background:rgba(52,91,130,.55); backdrop-filter:blur(16px); }
.profile-loading { min-height:180px; display:grid; place-items:center; font-weight:700; }
:deep(.profile-hero),:deep(.profile-card) { border:1px solid rgba(255,255,255,.25); border-radius:11px; background:rgba(106,145,187,.54); backdrop-filter:blur(20px); box-shadow:0 18px 46px rgba(12,38,70,.16); }
:deep(.profile-hero) { display:grid; grid-template-columns:minmax(0,1fr) minmax(280px,400px); align-items:center; gap:22px; min-height:124px; margin-bottom:18px; padding:14px 20px; background:rgba(106,145,187,.54); }
:deep(.profile-identity) { display:flex; align-items:center; gap:22px; min-width:0; }
:deep(.profile-avatar) { display:grid; flex:0 0 68px; width:68px; height:68px; aspect-ratio:1; place-items:center; border-radius:50%; color:#1b2c42; font-size:30px; font-weight:900; background:rgba(247,251,255,.94); box-shadow:0 12px 30px rgba(14,46,82,.15); }
:deep(.profile-kicker),:deep(.profile-card-header p) { margin:0 0 8px; color:rgba(255,255,255,.76); font-size:15px; font-weight:800; }
:deep(.profile-identity h1) { margin:0 0 8px; font-size:36px; line-height:1.08; }
:deep(.profile-identity p:last-child),:deep(.today-preference p) { margin:0; color:rgba(255,255,255,.7); font-size:17px; }
:deep(.today-preference) { display:grid; gap:5px; border:1px solid rgba(255,255,255,.22); border-radius:10px; padding:10px 14px; background:rgba(255,255,255,.12); }
:deep(.today-preference span) { color:rgba(255,255,255,.7); font-size:16px; }
:deep(.today-preference strong) { font-size:24px; }
:deep(.profile-column > .profile-card) { height:100%; }
:deep(.profile-card) { padding:26px 22px; }
:deep(.profile-card-header) { display:flex; align-items:flex-start; justify-content:space-between; gap:16px; margin-bottom:22px; }
:deep(.profile-card-header h2) { margin:0; font-size:27px; }
:deep(.profile-pill-button),:deep(.profile-primary-button) { display:inline-grid; min-height:44px; place-items:center; border:1px solid rgba(255,255,255,.24); border-radius:999px; padding:0 16px; color:#fff; font-size:14px; font-weight:700; text-decoration:none; background:rgba(255,255,255,.15); cursor:pointer; }
:deep(.profile-fact-list) { display:grid; gap:14px; margin:0; }
:deep(.profile-fact-list div) { display:grid; grid-template-columns:1fr auto; gap:16px; align-items:center; min-height:68px; border:1px solid rgba(255,255,255,.2); border-radius:9px; padding:0 16px; background:rgba(255,255,255,.1); }
:deep(.profile-fact-list dt) { color:rgba(255,255,255,.68); }
:deep(.profile-fact-list dd) { margin:0; font-size:16px; font-weight:800; text-align:right; }
:deep(.profile-edit-form) { display:grid; gap:12px; }
:deep(.profile-edit-form label) { display:grid; gap:6px; color:rgba(255,255,255,.76); font-size:13px; }
:deep(.profile-edit-form input) { min-height:46px; border:1px solid rgba(255,255,255,.3); border-radius:8px; padding:0 12px; color:#17304d; background:rgba(255,255,255,.9); }
:deep(.profile-stats-grid) { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
:deep(.profile-stats-grid article) { min-height:150px; display:grid; align-content:start; gap:8px; border:1px solid rgba(255,255,255,.2); border-radius:9px; padding:18px 16px; background:rgba(255,255,255,.09); }
:deep(.profile-stats-grid span),:deep(.profile-stats-grid small) { color:rgba(255,255,255,.66); }
:deep(.profile-stats-grid strong) { font-size:34px; }
:deep(.profile-stats-grid b) { font-size:15px; }
:deep(.profile-route-list),:deep(.activity-list) { display:grid; gap:14px; }
:deep(.profile-route-list article),:deep(.activity-list article) { position:relative; display:grid; gap:8px; border:1px solid rgba(255,255,255,.2); border-radius:9px; padding:18px 16px; background:rgba(255,255,255,.1); }
:deep(.profile-route-list article strong),:deep(.activity-list article strong) { font-size:16px; }
:deep(.profile-route-list article p),:deep(.activity-list article p) { margin:0; color:rgba(255,255,255,.68); line-height:1.55; }
:deep(.profile-route-list article>div) { display:flex; flex-wrap:wrap; gap:8px; margin-top:5px; }
:deep(.profile-route-list article span) { border:1px solid rgba(255,255,255,.2); border-radius:999px; padding:6px 10px; color:rgba(255,255,255,.8); background:rgba(255,255,255,.08); }
:deep(.route-remove) { position:absolute; top:10px; right:10px; border:0; color:rgba(255,255,255,.7); font-size:20px; background:transparent; cursor:pointer; }
:deep(.activity-list time) { color:rgba(255,255,255,.64); }
:deep(.preference-card label) { display:grid; grid-template-columns:66px 1fr 48px; align-items:center; gap:12px; margin:18px 0; }
:deep(.preference-card input) { width:100%; accent-color:#e8f2f8; }
:deep(.preference-card label strong) { text-align:right; }
@media(max-width:1100px){.profile-dashboard-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.profile-column:last-child{grid-column:1/-1}:deep(.activity-list){grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:760px){.profile-content{padding:14px}.profile-dashboard-grid{grid-template-columns:1fr}.profile-column:last-child{grid-column:auto}:deep(.profile-hero){grid-template-columns:1fr;padding:14px 16px}:deep(.profile-identity){align-items:center}:deep(.profile-avatar){flex-basis:62px;width:62px;height:62px;font-size:28px}:deep(.profile-identity h1){font-size:32px}:deep(.today-preference){padding:10px 14px}:deep(.activity-list){grid-template-columns:1fr}}
</style>