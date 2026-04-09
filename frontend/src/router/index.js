import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const routes = [
  { path: '/login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
  { path: '/register', component: () => import('../views/RegisterView.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('../views/HomeView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/upload',
    component: () => import('../views/UploadView.vue'),
    meta: { requiresAuth: true, roles: ['uploader', 'admin'] }
  },
  {
    path: '/videos/:id',
    component: () => import('../views/VideoDetailView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    component: () => import('../views/AdminView.vue'),
    meta: { requiresAuth: true, roles: ['admin'] }
  },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()

  if (to.meta.public) {
    if (auth.isLoggedIn && (to.path === '/login' || to.path === '/register')) {
      return next('/')
    }
    return next()
  }

  if (!auth.isLoggedIn) {
    return next('/login')
  }

  if (to.meta.roles && !to.meta.roles.includes(auth.user?.role)) {
    return next('/')
  }

  next()
})

export default router
