<template>
  <el-config-provider>
    <NavBar v-if="auth.isLoggedIn" />
    <router-view />
  </el-config-provider>
</template>

<script setup>
import { useAuthStore } from './stores/auth.js'
import NavBar from './components/NavBar.vue'

const auth = useAuthStore()
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Helvetica Neue', Arial, sans-serif; background: #f5f5f5; }
.page { max-width: 1200px; margin: 0 auto; padding: 24px 16px; }
</style>
