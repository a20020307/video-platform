<template>
  <div class="page">
    <!-- Stats header -->
    <el-row :gutter="16" style="margin-bottom: 24px">
      <el-col :span="6">
        <el-card shadow="never">
          <div class="stat">
            <div class="stat-value">{{ total }}</div>
            <div class="stat-label">视频总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6" v-if="auth.isUploader">
        <el-card shadow="never">
          <div class="stat">
            <div class="stat-value">{{ formatBytes(auth.user?.storage_used || 0) }}</div>
            <div class="stat-label">已用存储</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Search & Upload button -->
    <el-row justify="space-between" style="margin-bottom: 16px">
      <el-col :span="12">
        <h2>视频列表</h2>
      </el-col>
      <el-col :span="4" style="text-align: right">
        <el-button v-if="auth.isUploader" type="primary" @click="router.push('/upload')">
          <el-icon><Upload /></el-icon> 上传视频
        </el-button>
      </el-col>
    </el-row>

    <!-- Video grid -->
    <el-row :gutter="16" v-loading="loading">
      <el-col :span="6" v-for="video in videos" :key="video.id" style="margin-bottom: 16px">
        <VideoCard :video="video" @deleted="loadVideos" />
      </el-col>
      <el-col :span="24" v-if="!loading && videos.length === 0">
        <el-empty description="暂无视频" />
      </el-col>
    </el-row>

    <!-- Pagination -->
    <el-pagination
      v-if="total > pageSize"
      v-model:current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      layout="prev, pager, next"
      @current-change="loadVideos"
      style="margin-top: 16px; justify-content: center"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth.js'
import { videoApi } from '../api/videos.js'
import VideoCard from '../components/VideoCard.vue'

const auth = useAuthStore()
const router = useRouter()

const videos = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const loading = ref(false)

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
}

async function loadVideos() {
  loading.value = true
  try {
    const res = await videoApi.list({ page: currentPage.value, size: pageSize.value })
    videos.value = res.data.items
    total.value = res.data.total
  } catch (err) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadVideos)
</script>

<style scoped>
.stat { text-align: center; padding: 8px 0; }
.stat-value { font-size: 28px; font-weight: bold; color: #409eff; }
.stat-label { color: #909399; font-size: 13px; }
</style>
