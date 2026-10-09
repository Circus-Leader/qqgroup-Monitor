<template>
  <div class="page-container">
    <div class="header-section">
      <div class="header-title">分析聊天记录并查看简报</div>
      <div class="divider"></div>
    </div>
    
    <div class="main-content">
      <div class="left-section">
        <div class="left-title">选择分析目标</div>
        <div class="left-subtitle">选择要分析的聊天记录</div>
        <div class="task-list">
          <button
            v-for="task in tasks"
            :key="task.id"
            :class="['task-item', { 'selected': selectedTask && selectedTask.id === task.id, 'disabled': isAnalyzing }]"
            @click="selectTask(task)"
            :disabled="isAnalyzing"
          >
            <img 
              :src="task.avatar_url ? `http://localhost:5000${task.avatar_url}` : task.default_avatar" 
              alt="头像" 
              class="task-avatar"
              @error="$event.target.src = task.default_avatar"
            />
            <div class="task-info">
              <div class="task-line-1">
                <span class="task-name">{{ task.session_name }}</span>
                <span class="task-file-type">{{ getFileType(task.file_name) }}</span>
              </div>
              <div class="task-line-2">
                <span>{{ task.message_count }}条消息</span>
                <span>{{ formatTime(task.created_at) }}</span>
              </div>
              <div class="task-line-3">
                <span>{{ task.peer.chat_type === 2 ? '群聊' : '私聊' }}</span>
                <span>{{ task.peer.peer_uid }}</span>
              </div>
            </div>
          </button>
        </div>
      </div>
      
      <div class="right-section">
        <div v-if="!selectedTask" class="right-placeholder">
          请先在左侧选择要分析的聊天记录
        </div>
        
        <div v-else-if="!isAnalyzing && !analysisResult" class="right-selected">
          <div v-if="selectedTask.peer.chat_type === 2 && isJsonFile(selectedTask.file_name)">
            已选择群聊 {{ selectedTask.session_name }}
          </div>
          <div v-else-if="selectedTask.peer.chat_type === 2 && !isJsonFile(selectedTask.file_name)">
            暂不支持分析除json格式外的文件，请选择或重新导出json格式
          </div>
          <div v-else>
            暂不支持分析私聊文件，请选择群聊文件
          </div>
        </div>
        
        <div v-else-if="isAnalyzing || analysisResult" class="right-analysis">
          <div class="analysis-header">
            当前分析群聊
            <img 
              :src="selectedTask.avatar_url ? `http://localhost:5000${selectedTask.avatar_url}` : selectedTask.default_avatar" 
              alt="头像" 
              class="analysis-avatar"
              @error="$event.target.src = selectedTask.default_avatar"
            />
            {{ selectedTask.session_name }}
          </div>
          <div class="analysis-logs-section">
            <div class="logs-title">当前日志：</div>
            <div class="logs-container">
              <div v-for="(log, index) in logs" :key="index" class="log-item">{{ log }}</div>
            </div>
          </div>
          <div class="analysis-result-section">
            <div class="result-title">分析结果</div>
            <div class="result-container">
              <div v-if="!analysisResult" class="result-placeholder">等待后端分析...</div>
              <div v-else class="result-content">
                <div v-for="(value, key) in analysisResult" :key="key" class="result-item">
                  <div class="result-key">{{ formatKey(key) }}</div>
                  <div class="result-value">{{ formatValue(value, key) }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="footer-section">
      <div class="footer-buttons">
        <button class="cancel-button" @click="cancel">取消</button>
        <button
          :class="['analyze-button', { 'disabled': !canAnalyze || isAnalyzing }]"
          @click="startAnalysis"
          :disabled="!canAnalyze || isAnalyzing"
        >
          开始分析
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { getTasks, analyzeTask, getAnalyzeLogs } from '../services/api'

const router = useRouter()

const tasks = ref([])
const selectedTask = ref(null)
const isAnalyzing = ref(false)
const logs = ref([])
const analysisResult = ref(null)
let logPollingInterval = null

const canAnalyze = computed(() => {
  return selectedTask.value &&
         selectedTask.value.peer.chat_type === 2 &&
         isJsonFile(selectedTask.value.file_name)
})

const getFileType = (fileName) => {
  if (!fileName) return '未知'
  const ext = fileName.split('.').pop().toUpperCase()
  return ext || '未知'
}

const formatTime = (timeStr) => {
  if (!timeStr) return '未知时间'
  try {
    const date = new Date(timeStr)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    })
  } catch {
    return timeStr
  }
}

const isJsonFile = (fileName) => {
  if (!fileName) return false
  return fileName.toLowerCase().endsWith('.json')
}

const formatKey = (key) => {
  const keyMap = {
    'chat_name': '群聊名',
    'total_messages': '总消息数',
    'date_range': '时间范围',
    'chat_topics': '聊天主题',
    'sensitive_count': '敏感内容出现次数',
    'participant_count': '参与人数',
    'sensitive_contexts': '敏感内容上下文'
  }
  return keyMap[key] || key
}

const formatValue = (value, key) => {
  if (key === 'sensitive_contexts' && Array.isArray(value)) {
    return value.map(context => {
      const word = context.word || '未知敏感词'
      const messages = context.messages || []
      let result = `敏感词: ${word}\n上下文聊天记录:\n`
      messages.forEach(msg => {
        const senderName = msg.sender?.name || '未知用户'
        const text = typeof msg.content === 'object' ? msg.content.text : msg.content
        result += `${senderName}: ${text}\n`
      })
      return result
    }).join('\n')
  }
  
  if (typeof value === 'object' && value !== null) {
    return JSON.stringify(value, null, 2)
  }
  return String(value)
}

const loadTasks = async () => {
  try {
    const response = await getTasks()
    if (response.data.status === 'success') {
      const rawTasks = response.data.tasks || []
      tasks.value = rawTasks.map(task => {
        const chatTypeValue = task.chat_type === '群聊' ? 2 : 1
        const fileName = task.file_path ? task.file_path.split('\\').pop().split('/').pop() : `export.${task.format.toLowerCase()}`
        return {
          id: task.id,
          session_name: task.name,
          peer: {
            chat_type: chatTypeValue,
            peer_uid: task.id_number
          },
          message_count: task.message_count,
          file_name: fileName,
          file_path: task.file_path,
          created_at: task.create_date,
          status: task.status,
          format: task.format,
          avatar_url: task.avatar_url,
          default_avatar: task.default_avatar
        }
      })
    }
  } catch (error) {
    console.error('加载任务列表失败:', error)
  }
}

const selectTask = (task) => {
  if (isAnalyzing.value) return
  selectedTask.value = task
}

const startAnalysis = async () => {
  if (!canAnalyze.value || isAnalyzing.value) return
  
  isAnalyzing.value = true
  logs.value = []
  analysisResult.value = null
  
  startLogPolling()
  
  try {
    const response = await analyzeTask(selectedTask.value.id)
    if (response.data.status === 'success') {
      analysisResult.value = response.data.brief_report
    } else {
      logs.value.push(`分析失败: ${response.data.message}`)
    }
  } catch (error) {
    console.error('分析失败:', error)
    logs.value.push(`分析失败: ${error.message}`)
  } finally {
    isAnalyzing.value = false
    stopLogPolling()
  }
}

const startLogPolling = () => {
  if (logPollingInterval) return
  
  logPollingInterval = setInterval(async () => {
    try {
      const response = await getAnalyzeLogs()
      if (response.data.status === 'success') {
        logs.value = response.data.logs || []
      }
    } catch (error) {
      console.error('获取日志失败:', error)
    }
  }, 2000)
}

const stopLogPolling = () => {
  if (logPollingInterval) {
    clearInterval(logPollingInterval)
    logPollingInterval = null
  }
}

const cancel = () => {
  stopLogPolling()
  router.push('/')
}

onMounted(() => {
  loadTasks()
})

onUnmounted(() => {
  stopLogPolling()
})
</script>

<style scoped>
.page-container {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #fff;
}

.header-section {
  height: 12.5%;
  display: flex;
  flex-direction: column;
  padding: 0 20px;
  box-sizing: border-box;
}

.header-title {
  font-size: 28px;
  font-weight: bold;
  color: #000;
  text-align: left;
}

.divider {
  height: 1px;
  background-color: #e0e0e0;
  margin-top: auto;
}

.main-content {
  flex: 1;
  display: flex;
  padding: 20px;
  box-sizing: border-box;
  gap: 20px;
}

.left-section {
  width: 40%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.left-title {
  font-size: 18px;
  font-weight: bold;
  color: #000;
  text-align: left;
}

.left-subtitle {
  font-size: 14px;
  color: #000;
  text-align: left;
}

.task-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.task-item {
  height: 72px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 15px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background-color: #fff;
  cursor: pointer;
  transition: all 0.2s;
}

.task-item:hover:not(.disabled) {
  background-color: #f5f5f5;
  border-color: #1890ff;
}

.task-item.selected {
  border-color: #1890ff;
  background-color: #e6f7ff;
}

.task-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.task-avatar {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  flex-shrink: 0;
}

.task-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
}

.task-line-1 {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: bold;
  color: #000;
}

.task-file-type {
  font-size: 12px;
  color: #666;
  background-color: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
}

.task-line-2,
.task-line-3 {
  display: flex;
  gap: 15px;
  font-size: 12px;
  color: #666;
}

.right-section {
  width: 60%;
  display: flex;
  flex-direction: column;
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 20px;
  box-sizing: border-box;
}

.right-placeholder,
.right-selected {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: #666;
}

.right-analysis {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.analysis-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: bold;
  color: #000;
}

.analysis-avatar {
  width: 40px;
  height: 40px;
  border-radius: 4px;
}

.analysis-logs-section {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.logs-title {
  font-size: 14px;
  font-weight: bold;
  color: #000;
}

.logs-container {
  height: 60px;
  overflow-y: auto;
  background-color: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 8px;
  font-size: 12px;
  color: #333;
}

.log-item {
  margin-bottom: 4px;
  line-height: 1.4;
}

.analysis-result-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 5px;
  overflow: hidden;
}

.result-title {
  font-size: 14px;
  font-weight: bold;
  color: #000;
}

.result-container {
  flex: 1;
  overflow-y: auto;
  background-color: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 15px;
}

.result-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  font-size: 14px;
  color: #999;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.result-item {
  padding: 10px;
  background-color: #f5f5f5;
  border-radius: 4px;
}

.result-key {
  font-size: 14px;
  font-weight: bold;
  color: #000;
  margin-bottom: 5px;
}

.result-value {
  font-size: 13px;
  color: #333;
  white-space: pre-wrap;
  word-break: break-all;
}

.footer-section {
  height: 12.5%;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 20px;
  box-sizing: border-box;
}

.footer-buttons {
  display: flex;
  gap: 15px;
}

.cancel-button,
.analyze-button {
  padding: 10px 30px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-button {
  background-color: #f0f0f0;
  border: 1px solid #ccc;
  color: #000;
}

.cancel-button:hover {
  background-color: #e0e0e0;
}

.analyze-button {
  background-color: #1890ff;
  border: none;
  color: #fff;
}

.analyze-button:hover:not(.disabled) {
  background-color: #40a9ff;
}

.analyze-button.disabled {
  background-color: #b3d9ff;
  cursor: not-allowed;
}
</style>
