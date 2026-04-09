<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <template #header><h2>注册</h2></template>

      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px" @submit.prevent="submit">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" type="email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="至少8位" show-password />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="观看者" value="viewer" />
            <el-option label="上传者" value="uploader" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">
            注册
          </el-button>
        </el-form-item>
      </el-form>

      <div class="auth-link">
        已有账户？<router-link to="/login">立即登录</router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()
const router = useRouter()
const formRef = ref()
const loading = ref(false)
const form = ref({ email: '', password: '', role: 'viewer' })

const rules = {
  email: [{ required: true, type: 'email', message: '请输入有效邮箱', trigger: 'blur' }],
  password: [{ required: true, min: 8, message: '密码至少8位', trigger: 'blur' }],
  role: [{ required: true }]
}

async function submit() {
  await formRef.value.validate()
  loading.value = true
  try {
    await auth.register(form.value.email, form.value.password, form.value.role)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page { display: flex; justify-content: center; align-items: center; min-height: 100vh; }
.auth-card { width: 420px; }
.auth-link { text-align: center; margin-top: 12px; }
h2 { text-align: center; }
</style>
