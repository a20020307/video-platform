<template>
  <el-menu mode="horizontal" :ellipsis="false" class="nav-menu">
    <el-menu-item index="/" @click="router.push('/')">
      <el-icon><VideoPlay /></el-icon>
      <span>视频平台</span>
    </el-menu-item>

    <div class="flex-grow" />

    <el-menu-item v-if="auth.isUploader" index="/upload" @click="router.push('/upload')">
      <el-icon><Upload /></el-icon> 上传视频
    </el-menu-item>

    <el-menu-item v-if="auth.isAdmin" index="/admin" @click="router.push('/admin')">
      <el-icon><Setting /></el-icon> 管理后台
    </el-menu-item>

    <el-sub-menu index="user">
      <template #title>
        <el-icon><User /></el-icon>
        <span>{{ auth.user?.email }}</span>
        <el-tag size="small" class="role-tag" :type="roleTagType">{{ auth.user?.role }}</el-tag>
      </template>
      <el-menu-item @click="handleLogout">退出登录</el-menu-item>
    </el-sub-menu>
  </el-menu>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()
const router = useRouter()

const roleTagType = computed(() => {
  const map = { admin: 'danger', uploader: 'warning', viewer: 'info' }
  return map[auth.user?.role] || 'info'
})

async function handleLogout() {
  await auth.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.nav-menu { padding: 0 16px; }
.flex-grow { flex: 1; }
.role-tag { margin-left: 8px; }
</style>
