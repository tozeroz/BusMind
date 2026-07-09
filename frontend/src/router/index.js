import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layout/MainLayout.vue'
import LoginView from '@/views/login/LoginView.vue'
import RegisterView from '@/views/login/RegisterView.vue'
import HomeView from '@/views/home/HomeView.vue'
import AdminView from '@/views/admin/AdminView.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: LoginView },
  { path: '/register', component: RegisterView },
  { path: '/admin', component: AdminView },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: 'home', component: HomeView, meta: { title: '首页' } }
    ]
  }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
