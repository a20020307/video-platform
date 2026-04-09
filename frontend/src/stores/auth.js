import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth.js'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || null)
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isUploader = computed(() => ['uploader', 'admin'].includes(user.value?.role))

  function setAuth(data) {
    token.value = data.access_token
    user.value = data.user
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))
  }

  function clearAuth() {
    token.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
  }

  async function login(email, password) {
    const res = await authApi.login({ email, password })
    setAuth(res.data)
    return res.data
  }

  async function register(email, password, role = 'viewer') {
    const res = await authApi.register({ email, password, role })
    return res.data
  }

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      clearAuth()
    }
  }

  return { token, user, isLoggedIn, isAdmin, isUploader, login, register, logout, clearAuth }
})
