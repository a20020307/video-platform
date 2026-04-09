<template>
  <el-card class="video-card" shadow="hover" @click="router.push(`/videos/${video.id}`)">
    <div class="video-thumb">
      <el-icon :size="48" color="#909399"><VideoPlay /></el-icon>
    </div>
    <div class="video-info">
      <div class="video-title" :title="video.title">{{ video.title }}</div>
      <div class="video-meta">
        <el-tag size="small" :type="statusType">{{ statusLabel }}</el-tag>
        <span class="video-size">{{ formatBytes(video.file_size) }}</span>
      </div>
      <div class="video-uploader">{{ video.uploader?.email }}</div>
    </div>
    <div class="video-actions" @click.stop>
      <el-popconfirm
        v-if="canDelete"
        title="确认删除这个视频？"
        confirm-button-text="删除"
        cancel-button-text="取消"
        @confirm="handleDelete"
      >
        <template #reference>
          <el-button type="danger" text :icon="Delete" size="small" />
        </template>
      </el-popconfirm>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth.js'
import { videoApi } from '../api/videos.js'

const props = defineProps({ video: Object })
const emit = defineEmits(['deleted'])
const router = useRouter()
const auth = useAuthStore()

const canDelete = computed(() =>
  auth.isAdmin || (auth.isUploader && props.video.uploader?.id === auth.user?.id)
)

const statusType = computed(() => {
  const map = { ready: 'success', uploading: 'warning', processing: 'info', failed: 'danger', deleted: 'info' }
  return map[props.video.status] || 'info'
})

const statusLabel = computed(() => {
  const map = { ready: '可播放', uploading: '上传中', processing: '处理中', failed: '失败', deleted: '已删除' }
  return map[props.video.status] || props.video.status
})

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
}

async function handleDelete() {
  try {
    await videoApi.delete(props.video.id)
    ElMessage.success('删除成功')
    emit('deleted')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '删除失败')
  }
}
</script>

<style scoped>
.video-card { cursor: pointer; position: relative; }
.video-thumb {
  height: 140px;
  background: #f0f2f5;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  margin-bottom: 12px;
}
.video-title {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 6px;
}
.video-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.video-size { color: #909399; font-size: 12px; }
.video-uploader { color: #909399; font-size: 12px; }
.video-actions { position: absolute; top: 8px; right: 8px; }
</style>
