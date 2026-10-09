<template>
  <div class="page-container">
    <div class="login-box">
      <div class="login-title">登录</div>
      <div class="login-subtitle">使用手机QQ扫描下方二维码登录</div>
      
      <div class="qr-code-container">
        <!-- 加载中状态 -->
        <div v-if="qrCodeStatus === 'loading'" class="loading">
          <el-icon class="is-loading" :size="40">
            <Loading />
          </el-icon>
        </div>
        
        <!-- 错误状态 -->
        <div v-else-if="qrCodeStatus === 'error'" class="error-message">
          二维码获取失败，请尝试刷新页面重新登录
        </div>
        
        <!-- 显示二维码 -->
        <img v-else-if="qrCodeStatus === 'success'" :src="qrCodeUrl" alt="QQ登录二维码" />
      </div>
      
      <!-- 登录状态提示 -->
      <div v-if="isPolling" class="login-subtitle">
        <div v-if="napcatStatus === 'generating_qrcode'">
          正在生成二维码，请稍候...
        </div>
        <div v-else-if="napcatStatus === 'waiting_for_login'">
          请使用手机QQ扫描二维码登录...
        </div>
        <div v-else-if="napcatStatus === 'stopped'">
          服务已停止，正在尝试重新启动...
        </div>
        <div v-else-if="napcatStatus === 'error'">
          服务出错，正在尝试重新启动...
        </div>
        <div v-else>
          正在检查登录状态...
        </div>
        <div class="polling-info">
          检查间隔: {{ pollingIntervalSeconds }}秒
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElIcon } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import { getQrcode, startNapcat, getNapcatStatus } from '../services/api'

const router = useRouter()
const authStore = useAuthStore()

// 二维码状态: 'loading', 'error', 'success'
const qrCodeStatus = ref('loading')
// 二维码URL
const qrCodeUrl = ref('')
// 是否正在轮询
const isPolling = ref(false)
// napcat状态
const napcatStatus = ref('')
// 轮询间隔(秒)
const pollingIntervalSeconds = ref(2)
// 轮询定时器
let pollingTimer = null

// 获取二维码
const fetchQrcode = async () => {
  try {
    qrCodeStatus.value = 'loading'
    const response = await getQrcode()
    
    // 创建Blob URL
    const blob = new Blob([response.data], { type: 'image/png' })
    qrCodeUrl.value = URL.createObjectURL(blob)
    qrCodeStatus.value = 'success'
    
    // 获取二维码成功后，15秒后开始轮询检查登录状态
    // 临时修改为5s
    setTimeout(startPolling, 5000)
  } catch (error) {
    console.error('获取二维码失败:', error)
    qrCodeStatus.value = 'error'
  }
}

// 开始轮询检查登录状态
const startPolling = async () => {
  if (isPolling.value) return
  
  isPolling.value = true
  authStore.setPollingStatus(true)
  
  // 初始轮询间隔为2秒
  let pollingInterval = 2000
  // 最大轮询间隔为10秒
  const maxInterval = 10000
  
  // 设置轮询定时器
  const poll = async () => {
    try {
      // 一直向/api/napcat/start发请求
      const response = await startNapcat()
      const status = response.data.status
      napcatStatus.value = status
      
      // 如果状态为success，表示已连接成功
      if (status === 'success') {
        // 更新连接状态
        authStore.setConnectionStatus(true)
        // 清除轮询
        stopPolling()
        // 跳转到概览页
        router.push('/')
      }
      
      // 指数退避策略：每次失败后增加轮询间隔
      pollingInterval = Math.min(pollingInterval * 1.2, maxInterval)
      // 更新显示的轮询间隔
      pollingIntervalSeconds.value = Math.round(pollingInterval / 1000)
      
    } catch (error) {
      console.error('检查登录状态失败:', error)
      napcatStatus.value = 'error'
      // 网络错误时重置连接状态
      authStore.setConnectionStatus(false)
      // 网络错误时增加轮询间隔
      pollingInterval = Math.min(pollingInterval * 1.5, maxInterval)
      // 更新显示的轮询间隔
      pollingIntervalSeconds.value = Math.round(pollingInterval / 1000)
    }
    
    // 设置下一次轮询
    pollingTimer = setTimeout(poll, pollingInterval)
  }
  
  // 立即开始第一次轮询
  pollingTimer = setTimeout(poll, 0)
  
  // 设置2分钟后自动停止轮询
  authStore.setPollingTimer(
    setTimeout(() => {
      stopPolling()
      // 超时后重置连接状态
      authStore.setConnectionStatus(false)
    }, 120000)
  )
}

// 停止轮询
const stopPolling = () => {
  if (pollingTimer) {
    clearTimeout(pollingTimer)
    pollingTimer = null
  }
  
  // 清除超时定时器
  authStore.clearPollingTimer()
  
  isPolling.value = false
  authStore.setPollingStatus(false)
}

// 组件挂载时获取二维码
onMounted(() => {
  // 如果已经登录成功，直接跳转到概览页
  if (authStore.isConnected) {
    router.push('/')
    return
  }
  
  // 未登录，获取二维码
  fetchQrcode()
})

// 组件卸载时清理资源
onUnmounted(() => {
  stopPolling()
  
  // 释放Blob URL
  if (qrCodeUrl.value) {
    URL.revokeObjectURL(qrCodeUrl.value)
  }
})
</script>

<style scoped>
.page-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f5f5f5;
}

.login-box {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 30px;
  width: 350px;
  text-align: center;
}

.login-title {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 10px;
  color: #333;
}

.login-subtitle {
  font-size: 14px;
  color: #666;
  margin-bottom: 20px;
}

.qr-code-container {
  width: 300px;
  height: 300px;
  margin: 0 auto;
  display: flex;
  justify-content: center;
  align-items: center;
  border: 1px solid #eee;
  border-radius: 4px;
}

.qr-code-container img {
  max-width: 100%;
  max-height: 100%;
}

.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.error-message {
  color: #f56c6c;
  font-size: 14px;
}

.polling-info {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}
</style>