/**
 * Chunked upload service.
 *
 * Flow:
 *   1. initUpload()  → get session_id, total_chunks, uploaded_chunks (for resume)
 *   2. uploadChunk() for each pending chunk (parallel batches, with retry)
 *   3. completeUpload()
 *   4. abortUpload() on cancellation
 *
 * Retry strategy: exponential backoff with jitter
 *   delay = min(1000 * 2^attempt + random(0..1000), 30000) ms
 */
import client from './client.js'

const DEFAULT_CHUNK_SIZE = 10 * 1024 * 1024  // 10 MB
const MAX_CONCURRENT = 3
const MAX_RETRIES = 3

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function retryWithBackoff(fn, maxRetries = MAX_RETRIES) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn()
    } catch (err) {
      if (attempt === maxRetries - 1) throw err
      const delay = Math.min(1000 * Math.pow(2, attempt) + Math.random() * 1000, 30000)
      await sleep(delay)
    }
  }
}

export class ChunkedUploader {
  /**
   * @param {File} file
   * @param {object} options
   * @param {string} options.title
   * @param {string} [options.description]
   * @param {number} [options.chunkSize]
   * @param {number} [options.maxConcurrent]
   * @param {number} [options.maxRetries]
   * @param {(progress: {percent: number, uploadedChunks: number, totalChunks: number}) => void} [options.onProgress]
   * @param {string} [options.sessionId]  existing session_id for resume
   */
  constructor(file, options = {}) {
    this.file = file
    this.title = options.title || file.name
    this.description = options.description || ''
    this.chunkSize = options.chunkSize || DEFAULT_CHUNK_SIZE
    this.maxConcurrent = options.maxConcurrent || MAX_CONCURRENT
    this.maxRetries = options.maxRetries || MAX_RETRIES
    this.onProgress = options.onProgress || (() => {})

    this.sessionId = options.sessionId || null
    this.videoId = null
    this.totalChunks = 0
    this.uploadedChunks = new Set()
    this.aborted = false
  }

  async init() {
    const res = await client.post('/videos/upload/init', {
      title: this.title,
      description: this.description,
      filename: this.file.name,
      file_size: this.file.size,
      content_type: this.file.type || 'video/mp4',
      chunk_size: this.chunkSize
    })
    const data = res.data
    this.sessionId = data.session_id
    this.videoId = data.video_id
    this.totalChunks = data.total_chunks
    this.chunkSize = data.chunk_size  // server may adjust
    data.uploaded_chunks.forEach((n) => this.uploadedChunks.add(n))
    return data
  }

  _getChunkBlob(chunkNumber) {
    const start = (chunkNumber - 1) * this.chunkSize
    const end = Math.min(start + this.chunkSize, this.file.size)
    return this.file.slice(start, end)
  }

  async _uploadSingleChunk(chunkNumber) {
    const blob = this._getChunkBlob(chunkNumber)
    const res = await client.put(
      `/videos/upload/${this.sessionId}/chunk`,
      blob,
      {
        params: { chunk_number: chunkNumber },
        headers: { 'Content-Type': 'application/octet-stream' },
        // Don't use the global timeout for chunk uploads — large chunks take longer
        timeout: 0
      }
    )
    this.uploadedChunks.add(chunkNumber)
    const { uploaded_chunks, total_chunks, progress } = res.data
    this.onProgress({ percent: progress, uploadedChunks: uploaded_chunks, totalChunks: total_chunks })
    return res.data
  }

  async _uploadChunkWithRetry(chunkNumber) {
    return retryWithBackoff(() => this._uploadSingleChunk(chunkNumber), this.maxRetries)
  }

  async upload() {
    if (!this.sessionId) {
      await this.init()
    }

    // Determine which chunks still need uploading
    const pending = []
    for (let i = 1; i <= this.totalChunks; i++) {
      if (!this.uploadedChunks.has(i)) pending.push(i)
    }

    // Upload in batches of maxConcurrent
    for (let i = 0; i < pending.length; i += this.maxConcurrent) {
      if (this.aborted) throw new Error('Upload aborted')
      const batch = pending.slice(i, i + this.maxConcurrent)
      await Promise.all(batch.map((n) => this._uploadChunkWithRetry(n)))
    }

    if (this.aborted) throw new Error('Upload aborted')

    const res = await client.post(`/videos/upload/${this.sessionId}/complete`)
    return { videoId: this.videoId, ...res.data }
  }

  async abort() {
    this.aborted = true
    if (this.sessionId) {
      try {
        await client.delete(`/videos/upload/${this.sessionId}/abort`)
      } catch (e) {
        // best-effort
      }
    }
  }
}
