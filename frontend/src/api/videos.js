import client from './client.js'

export const videoApi = {
  list: (params) => client.get('/videos', { params }),
  get: (id) => client.get(`/videos/${id}`),
  delete: (id) => client.delete(`/videos/${id}`)
}
