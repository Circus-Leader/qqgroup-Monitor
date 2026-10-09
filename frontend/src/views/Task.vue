<template>
  <div class="page-container">
    <!-- 顶部标题和按钮区域 -->
    <div class="header-container">
      <div class="header-text">
        <div class="title">导出任务</div>
        <div class="subtitle">查看与管理任务，下载完成文件</div>
        <div class="subtitle">如果消息数量为 0，请先尝试刷新</div>
      </div>
      <div class="header-buttons">
        <button class="button-style-a" @click="refreshTasks">刷新列表</button>
        <button class="button-style-b" @click="createNewTask">新建任务</button>
      </div>
    </div>
    
    <!-- 30像素间距 -->
    <div class="spacing"></div>
    
    <!-- 任务列表区域 -->
    <div class="task-list">
      <div v-for="task in tasks" :key="task.id" class="task-card">
        <div class="task-header">
          <div class="task-name">{{ task.name }}</div>
          <div :class="['task-status', task.status]">
            {{ task.status === 'completed' ? '已完成' : '导出中' }}
          </div>
        </div>
        <div class="task-info">
          <span>{{ task.id_number }}</span>
          <span>{{ task.create_date }}</span>
          <span>{{ task.message_count }}条消息</span>
          <span>{{ task.date_range }}</span>
        </div>
        <div class="task-actions">
          <button class="icon-button folder-icon" @click="viewFileLocation(task.file_path)">
            📁
          </button>
          <button class="icon-button delete-icon" @click="deleteTask(task.id)">
            ❌
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { getTasks, deleteTask as deleteTaskAPI, openFileLocation as openFileLocationAPI } from '../services/api'

const router = useRouter()
const authStore = useAuthStore()

// 任务数据
const tasks = ref([])

// 刷新任务列表
const refreshTasks = async () => {
  try {
    const response = await getTasks()
    if (response.data.status === 'success') {
      tasks.value = response.data.tasks
    }
  } catch (error) {
    console.error('刷新任务列表失败:', error)
  }
}

// 创建新任务
const createNewTask = () => {
  router.push('/create-new-task')
}

// 查看文件所在位置
const viewFileLocation = async (filePath) => {
  if (!filePath) {
    alert('文件路径不存在')
    return
  }
  
  try {
    await openFileLocationAPI(filePath)
    console.log('文件位置已打开:', filePath)
  } catch (error) {
    console.error('打开文件位置失败:', error)
    alert('打开文件位置失败，请重试')
  }
}

// 删除任务
const deleteTask = async (taskId) => {
  // 弹窗确认
  if (confirm('确定要删除该任务记录吗？')) {
    try {
      // 调用删除任务API
      await deleteTaskAPI(taskId)
      // 更新本地任务列表
      tasks.value = tasks.value.filter(task => task.id !== taskId)
      console.log('任务删除成功')
    } catch (error) {
      console.error('删除任务失败:', error)
      alert('删除任务失败，请重试')
    }
  }
}

// 组件挂载时获取数据
onMounted(() => {
  if (authStore.isConnected) {
    refreshTasks()
  }
})
</script>

<style scoped>
/* 页面容器 */
.page-container {
  width: 100%;
  padding: 20px 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

/* 顶部标题和按钮容器 */
.header-container {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
}

/* 标题文本区域 */
.header-text {
  flex: 1;
  min-width: 300px;
}

/* 主标题 */
.title {
  font-size: 24px;
  font-weight: bold;
  color: #000;
  margin-bottom: 5px;
}

/* 副标题 */
.subtitle {
  font-size: 16px;
  color: #000;
  margin-bottom: 5px;
}

/* 按钮区域 */
.header-buttons {
  display: flex;
  gap: 10px;
  margin-left: 20px;
}

/* 30像素间距 */
.spacing {
  width: 100%;
  height: 30px;
}

/* 任务列表 */
.task-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

/* 任务卡片 */
.task-card {
  width: 100%;
  max-width: 800px;
  background-color: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-sizing: border-box;
}

/* 任务头部 */
.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 任务名称 */
.task-name {
  font-weight: bold;
  font-size: 16px;
}

/* 任务状态 */
.task-status {
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}

/* 已完成状态 */
.task-status.completed {
  color: #2e7d32;
  background-color: #e8f5e9;
}

/* 导出中状态 */
.task-status.exporting {
  color: #f57c00;
  background-color: #fff3e0;
}

/* 任务信息 */
.task-info {
  display: flex;
  gap: 20px;
  font-size: 14px;
  color: #666;
}

/* 任务操作按钮 */
.task-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 图标按钮 */
.icon-button {
  width: 32px;
  height: 32px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background-color: #fff;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  font-size: 16px;
}

/* 文件夹图标按钮 */
.folder-icon:hover {
  background-color: #f5f5f5;
}

/* 删除图标按钮 */
.delete-icon:hover {
  background-color: #ffebee;
}

/* 按钮样式 */
.button-style-a {
  background-color: #f0f0f0;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 5px 10px;
  cursor: pointer;
  font-size: 12px;
}

.button-style-a:hover {
  background-color: #e0e0e0;
}

.button-style-b {
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 5px 10px;
  cursor: pointer;
  font-size: 12px;
}

.button-style-b:hover {
  background-color: #40a9ff;
}
</style>