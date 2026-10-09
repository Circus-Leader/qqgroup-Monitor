<template>
  <div class="page-container">
    <div class="overview-title">QQ聊天记录导出&分析工具</div>
    
    <!-- 按钮区域 -->
    <div class="button-container">
      <button class="button-style-a" @click="navigateToChat">浏览会话</button>
      <button class="button-style-b" @click="navigateToCreateTask">新建任务</button>
      <button class="button-style-a" @click="navigateToTask">查看任务</button>
    </div>
    
    <!-- 统计数据区域 -->
    <div class="stats-container">
      <div class="stat-box">
        <div class="stat-label">导出任务</div>
        <div class="stat-value">
          {{ taskStats.total_tasks }}
          <span class="stat-detail">进行中 {{ taskStats.running_tasks }} · 完成 {{ taskStats.completed_tasks }}</span>
        </div>
      </div>
      
      <div class="stat-box">
        <div class="stat-label">群组</div>
        <div class="stat-value">{{ groupCount }}</div>
      </div>
      
      <div class="stat-box">
        <div class="stat-label">好友</div>
        <div class="stat-value">{{ friendCount }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { getTasks, getGroups, getFriends } from '../services/api'

const router = useRouter()
const authStore = useAuthStore()

// 任务统计数据
const taskStats = ref({
  total_tasks: 0,
  running_tasks: 0,
  completed_tasks: 0
})

// 群组数量
const groupCount = ref(0)

// 好友数量
const friendCount = ref(0)

// 导航到会话页面
const navigateToChat = () => {
  router.push('/chat')
}

// 导航到新建任务页面
const navigateToCreateTask = () => {
  router.push('/create-new-task')
}

// 导航到任务页面
const navigateToTask = () => {
  router.push('/task')
}

// 获取任务统计数据
const fetchTaskStats = async () => {
  try {
    const response = await getTasks()
    if (response.data.status === 'success') {
      taskStats.value = {
        total_tasks: response.data.total_tasks,
        running_tasks: response.data.running_tasks,
        completed_tasks: response.data.completed_tasks
      }
    }
  } catch (error) {
    console.error('获取任务统计数据失败:', error)
  }
}

// 获取群组数量
const fetchGroupCount = async () => {
  try {
    const response = await getGroups()
    if (response.data.status === 'success') {
      groupCount.value = response.data.groups.length
    }
  } catch (error) {
    console.error('获取群组数量失败:', error)
  }
}

// 获取好友数量
const fetchFriendCount = async () => {
  try {
    const response = await getFriends()
    if (response.data.status === 'success') {
      friendCount.value = response.data.friends.length
    }
  } catch (error) {
    console.error('获取好友数量失败:', error)
  }
}

// 获取所有数据
const fetchData = async () => {
  // 只有在已连接状态下才发送API请求
  if (authStore.isConnected) {
    await Promise.all([
      fetchTaskStats(),
      fetchGroupCount(),
      fetchFriendCount()
    ])
  }
}

// 监听连接状态变化
watch(() => authStore.isConnected, (newValue) => {
  if (newValue) {
    fetchData()
  }
})

// 组件挂载时获取数据
onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.page-container {
  width: 100%;
  padding: 20px 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.overview-title {
  font-size: 24px;
  font-weight: bold;
  text-transform: uppercase;
  margin-bottom: 30px;
}

.button-container {
  display: flex;
  gap: 20px;
  margin-bottom: 30px;
}

.button-style-a {
  width: 90px;
  height: 36px;
  background-color: #ffffff;
  border: 1px solid #dcdcdc;
  border-radius: 4px;
  color: #333333;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.button-style-a:hover {
  background-color: #f5f5f5;
}

.button-style-b {
  width: 90px;
  height: 36px;
  background-color: #333333;
  border: 1px solid #333333;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.button-style-b:hover {
  background-color: #555555;
}

.stats-container {
  display: flex;
  width: 100%;
  gap: 10px;
}

.stat-box {
  flex: 1;
  background-color: #ffffff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.stat-label {
  font-size: 14px;
  color: #666666;
  margin-bottom: 10px;
  text-transform: lowercase;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  text-transform: uppercase;
}

.stat-detail {
  font-size: 14px;
  font-weight: normal;
  text-transform: lowercase;
  margin-left: 10px;
  color: #666666;
}
</style>