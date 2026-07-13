/**
 * 文件：src/main.js
 * 用途：启动 Vue 3 前端应用。
 * 存放内容：应用创建、路由注册和全局样式加载代码。
 * 实现功能：将完成配置的 BusMind 应用挂载到浏览器页面。
 */
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './styles/index.css'

createApp(App).use(router).mount('#app')
