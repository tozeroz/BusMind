/**
 * 文件：src/router/index.js
 * 用途：定义应用路由和导航守卫。
 * 存放内容：路由记录、布局关系以及访问权限重定向规则。
 * 实现功能：将 URL 连接到轻量页面入口，并执行路由级身份和权限检查。
 */
import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import LoginView from '@/views/login/LoginView.vue'
import RegisterView from '@/views/login/RegisterView.vue'
import HomeView from '@/views/home/HomeView.vue'
import AdminView from '@/views/admin/AdminView.vue'
import ProfileView from '@/views/profile/ProfileView.vue'
import { getAuthToken, getStoredUser } from '@/api/user'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: LoginView, meta: { guestOnly: true } },
  { path: '/register', component: RegisterView, meta: { guestOnly: true } },
  { path: '/admin', component: AdminView, meta: { requiresAuth: true, requiresAdmin: true } },
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      { path: 'home', component: HomeView, meta: { title: '首页' } },
      { path: 'profile', component: ProfileView, meta: { title: '个人中心' } }
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/login' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const token = getAuthToken()
  const user = getStoredUser()

  if (to.matched.some((record) => record.meta.requiresAuth) && !token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.matched.some((record) => record.meta.requiresAdmin) && user?.role !== 'admin') {
    return '/home'
  }
  if (to.meta.guestOnly && token) {
    return user?.role === 'admin' ? '/admin' : '/home'
  }
  return true
})

export default router
