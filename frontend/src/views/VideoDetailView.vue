<template>
  <div class="page">
    <el-button @click="router.back()" style="margin-bottom: 16px">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <div v-if="loading" v-loading="true" style="height: 400px" />

    <template v-else-if="video">
      <el-row :gutter="24">
        <el-col :span="16">
          <!-- Video player -->
          <div class="video-player-wrap">
            <video
              v-if="video.presigned_url"
              :src="video.presigned_url"
              controls
              class="video-player"
            />
            <div v-else class="video-placeholder">
              <el-icon :size="64" color="#909399"><VideoPlay /></el-icon>
              <p>{{ video.status === 'processing' ? '视频处理中，稍后可播放' : '视频暂不可播放' }}</p>
            </div>
          </div>
        </el-col>

        <el-col :span="8">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="标题">{{ video.title }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusType">{{ video.status }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="上传者">{{ video.uploader?.email }}</el-descriptions-item>
            <el-descriptions-item label="文件大小">{{ formatBytes(video.file_size) }}</el-descriptions-item>
            <el-descriptions-item label="格式">{{ video.content_type }}</el-descriptions-item>
            <el-descriptions-item label="播放次数">{{ video.view_count }}</el-descriptions-item>
            <el-descriptions-item label="上传时间">{{ formatDate(video.created_at) }}</el-descriptions-item>
          </el-descriptions>

          <div v-if="video.description" style="margin-top: 16px">
            <h4>描述</h4>
            <p style="color: #606266; margin-top: 8px">{{ video.description }}</p>
          </div>
        </el-col>
      </el-row>
    </template>

    <el-empty v-else description="视频不存在" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { videoApi } from '../api/videos.js'

const route = useRoute()
const router = useRouter()
const video = ref(null)
const loading = ref(true)

const statusType = computed(() => {
  const map = { ready: 'success', uploading: 'warning', processing: 'info', failed: 'danger' }
  return map[video.value?.status] || 'info'
})

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

onMounted(async () => {
  try {
    const res = await videoApi.get(route.params.id)
    video.value = res.data
  } catch (err) {
    if (err.response?.status !== 404) ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.video-player-wrap {
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  aspect-ratio: 16/9;
  display: flex;
  align-items: center;
  justify-content: center;
}
.video-player { width: 100%; height: 100%; }
.video-placeholder { text-align: center; color: #fff; }
</style>
