<template>
  <div class="navbar">
    <div class="nav-left">
      <button 
        v-for="item in leftNavItems" 
        :key="item.name"
        class="nav-button"
        :class="{ active: currentRoute === item.path }"
        @click="navigateTo(item.path)"
      >
        {{ item.name }}
      </button>
    </div>
    <div class="nav-right">
      <div v-if="isLoggedIn" class="online-indicator">
        <div class="online-dot"></div>
        <span>在线</span>
      </div>
      <button 
        v-else
        class="nav-button"
        :class="{ active: currentRoute === '/login' }"
        @click="navigateTo('/login')"
      >
        登录
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// 左侧导航项
const leftNavItems = [
  { name: '概览', path: '/' },
  { name: '会话', path: '/chat' },
  { name: '任务', path: '/task' },
  { name: '简报', path: '/brief-report' },
  { name: '关于', path: '/about' }
]

// 当前路由路径
const currentRoute = computed(() => route.path)

// 登录状态
const isLoggedIn = computed(() => authStore.isConnected)

// 导航到指定路径
const navigateTo = (path) => {
  if (path !== route.path) {
    router.push(path)
  }
}
</script>

<style scoped>
/* 组件特定样式可以在这里添加 */
.online-indicator {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #52c41a;
  font-weight: 500;
}

.online-dot {
  width: 8px;
  height: 8px;
  background-color: #52c41a;
  border-radius: 50%;
}
</style>