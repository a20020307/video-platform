<template>
  <div class="page">
    <h2 style="margin-bottom: 24px">上传视频</h2>

    <!-- Drop zone -->
    <el-upload
      class="upload-zone"
      drag
      multiple
      :auto-upload="false"
      accept=".mp4,.mov,.avi,.mkv"
      :on-change="onFileChange"
      :show-file-list="false"
    >
      <el-icon :size="64" color="#409eff"><UploadFilled /></el-icon>
      <div class="el-upload__text">将视频文件拖拽至此，或 <em>点击上传</em></div>
      <template #tip>
        <div class="el-upload__tip">支持 MP4、MOV、AVI、MKV 格式，文件大小不限</div>
      </template>
    </el-upload>

    <!-- Upload queue -->
    <div v-if="uploadStore.tasks.size > 0" style="margin-top: 24px">
      <h3 style="margin-bottom: 12px">上传队列</h3>
      <el-card v-for="[taskId, task] in uploadStore.tasks" :key="taskId" style="margin-bottom: 12px">
        <div class="task-header">
          <div class="task-name">{{ task.file.name }}</div>
          <div class="task-actions">
            <el-tag :type="statusType(task.status)" size="small">{{ statusLabel(task.status) }}</el-tag>
            <el-button
              v-if="task.status === 'pending'"
              type="primary"
              size="small"
              @click="uploadStore.startTask(taskId)"
            >开始上传</el-button>
            <el-button
              v-if="task.status === 'uploading'"
              type="warning"
              size="small"
              @click="uploadStore.abortTask(taskId)"
            >取消</el-button>
            <el-button
              v-if="['completed', 'error', 'aborted'].includes(task.status)"
              size="small"
              @click="uploadStore.removeTask(taskId)"
            >移除</el-button>
          </div>
        </div>

        <el-progress
          v-if="['uploading', 'completed'].includes(task.status)"
          :percentage="task.progress"
          :status="task.status === 'completed' ? 'success' : ''"
          style="margin-top: 10px"
        />

        <div v-if="task.status === 'uploading'" class="task-detail">
          {{ task.uploadedChunks }} / {{ task.totalChunks }} 分片
        </div>

        <el-alert
          v-if="task.status === 'error'"
          :title="task.error"
          type="error"
          :closable="false"
          style="margin-top: 8px"
        />
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { useUploadStore } from '../stores/upload.js'

const uploadStore = useUploadStore()

function onFileChange(file) {
  const taskId = uploadStore.addTask(file.raw, { title: file.name })
  // Auto-start upload
  uploadStore.startTask(taskId)
}

function statusType(status) {
  const map = { pending: 'info', uploading: 'warning', completed: 'success', error: 'danger', aborted: 'info' }
  return map[status] || 'info'
}

function statusLabel(status) {
  const map = { pending: '等待', uploading: '上传中', completed: '完成', error: '失败', aborted: '已取消' }
  return map[status] || status
}
</script>

<style scoped>
.upload-zone { width: 100%; }
.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.task-name { font-weight: 500; flex: 1; margin-right: 16px; word-break: break-all; }
.task-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }
.task-detail { color: #909399; font-size: 12px; margin-top: 6px; }
</style>
