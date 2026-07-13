<!--
  文件：src/views/login/LoginView.vue
  用途：作为 BusMind 页面对应的轻量路由入口。
  存放内容：路由级组件组合以及对应业务模块页面容器的导入代码。
  实现功能：连接 Vue Router 与业务页面，不在路由入口中堆积具体业务实现。
-->
<template>
  <LoginPage />
</template>

<script setup>
import LoginPage from '@/modules/auth/components/LoginPage.vue'
</script>
