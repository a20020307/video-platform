<template>
  <div class="page">
    <h2 style="margin-bottom: 24px">管理后台 — 用户管理</h2>

    <el-table :data="users" v-loading="loading" border stripe>
      <el-table-column prop="email" label="邮箱" min-width="200" />
      <el-table-column prop="role" label="角色" width="120">
        <template #default="{ row }">
          <el-tag :type="roleType(row.role)">{{ row.role }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="已用存储" width="120">
        <template #default="{ row }">{{ formatBytes(row.storage_used) }}</template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'">{{ row.is_active ? '正常' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="注册时间" width="170">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-select
            :model-value="row.role"
            size="small"
            @change="(role) => updateRole(row.id, role)"
            style="width: 100%"
          >
            <el-option label="观看者" value="viewer" />
            <el-option label="上传者" value="uploader" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > pageSize"
      v-model:current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      layout="prev, pager, next"
      @current-change="loadUsers"
      style="margin-top: 16px; justify-content: center"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import client from '../api/client.js'

const users = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const loading = ref(false)

async function loadUsers() {
  loading.value = true
  try {
    const res = await client.get('/admin/users', { params: { page: currentPage.value, size: pageSize.value } })
    users.value = res.data.items
    total.value = res.data.total
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function updateRole(userId, role) {
  try {
    await client.patch(`/admin/users/${userId}/role`, { role })
    ElMessage.success('角色已更新')
    await loadUsers()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '更新失败')
  }
}

function roleType(role) {
  return { admin: 'danger', uploader: 'warning', viewer: 'info' }[role] || 'info'
}

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
}

function formatDate(d) {
  return d ? new Date(d).toLocaleString('zh-CN') : ''
}

onMounted(loadUsers)
</script>
