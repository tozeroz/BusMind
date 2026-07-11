import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layout/MainLayout.vue'
import LoginView from '@/views/login/LoginView.vue'
import RegisterView from '@/views/login/RegisterView.vue'
import HomeView from '@/views/home/HomeView.vue'
import AdminView from '@/views/admin/AdminView.vue'
import AiAssistantView from '@/views/ai-assistant/AiAssistantView.vue'
import LineListView from '@/views/line/LineListView.vue'
import LineDetailView from '@/views/line/LineDetailView.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: LoginView },
  { path: '/register', component: RegisterView },
  { path: '/admin', component: AdminView },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: 'home', component: HomeView, meta: { title: '首页' } },
      { path: 'ai', component: AiAssistantView, meta: { title: 'AI 出行助手' } },
      { path: 'lines', component: LineListView, meta: { title: '公交线路' } },
      { path: 'lines/:id', component: LineDetailView, meta: { title: '线路详情' } }
    ]
  }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
