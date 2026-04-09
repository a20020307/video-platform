import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ChunkedUploader } from '../api/upload.js'

export const useUploadStore = defineStore('upload', () => {
  // Map of taskId → { file, uploader, status, progress, error, videoId }
  const tasks = ref(new Map())

  function addTask(file, options = {}) {
    const taskId = `${Date.now()}-${Math.random().toString(36).slice(2)}`
    const uploader = new ChunkedUploader(file, {
      ...options,
      onProgress: ({ percent, uploadedChunks, totalChunks }) => {
        const task = tasks.value.get(taskId)
        if (task) {
          task.progress = percent
          task.uploadedChunks = uploadedChunks
          task.totalChunks = totalChunks
        }
      }
    })

    tasks.value.set(taskId, {
      taskId,
      file,
      uploader,
      status: 'pending',   // pending | uploading | completed | error | aborted
      progress: 0,
      uploadedChunks: 0,
      totalChunks: 0,
      error: null,
      videoId: null
    })

    return taskId
  }

  async function startTask(taskId) {
    const task = tasks.value.get(taskId)
    if (!task) return

    task.status = 'uploading'
    try {
      const result = await task.uploader.upload()
      task.status = 'completed'
      task.progress = 100
      task.videoId = result.videoId
    } catch (err) {
      if (task.status !== 'aborted') {
        task.status = 'error'
        task.error = err.response?.data?.detail || err.message
      }
    }
  }

  async function abortTask(taskId) {
    const task = tasks.value.get(taskId)
    if (!task) return
    task.status = 'aborted'
    await task.uploader.abort()
  }

  function removeTask(taskId) {
    tasks.value.delete(taskId)
  }

  return { tasks, addTask, startTask, abortTask, removeTask }
})
