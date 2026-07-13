<!--
  文件：src/modules/profile/components/ProfileAccountCard.vue
  用途：展示并编辑个人中心账户基础资料。
  存放内容：账号、手机号、邮箱、城市和昵称编辑表单。
  实现功能：通过事件将编辑、保存和取消操作交给页面容器处理。
-->
<template>
  <section class="profile-card account-card">
    <header class="profile-card-header">
      <div><p>账号信息</p><h2>基础资料</h2></div>
      <button class="profile-pill-button" type="button" @click="$emit(editing ? 'cancel' : 'edit')">{{ editing ? '取消' : '编辑' }}</button>
    </header>
    <form v-if="editing" class="profile-edit-form" @submit.prevent="$emit('save')">
      <label>昵称<input v-model="form.nickname" maxlength="32" /></label>
      <label>手机号<input :value="form.phone" disabled /></label>
      <label>邮箱<input :value="form.email" disabled /></label>
      <label>所在城市<input :value="form.city" disabled /></label>
      <button class="profile-primary-button" type="submit" :disabled="saving">{{ saving ? '保存中…' : '保存资料' }}</button>
    </form>
    <dl v-else class="profile-fact-list">
      <div><dt>账号</dt><dd>{{ user.username || 'demo_client' }}</dd></div>
      <div><dt>手机号</dt><dd>{{ form.phone }}</dd></div>
      <div><dt>邮箱</dt><dd>{{ form.email }}</dd></div>
      <div><dt>所在城市</dt><dd>{{ form.city }}</dd></div>
    </dl>
  </section>
</template>
<script setup>
defineProps({ user: { type: Object, required: true }, form: { type: Object, required: true }, editing: Boolean, saving: Boolean })
defineEmits(['edit', 'cancel', 'save'])
</script>