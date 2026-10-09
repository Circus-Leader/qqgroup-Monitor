<template>
  <div class="page-container">
    <!-- 顶部标题区域 -->
    <div class="header-section">
      <div class="header-content">
        <el-icon class="gear-icon"><Setting /></el-icon>
        <span class="header-title">创建导出任务</span>
      </div>
      <div class="header-divider"></div>
    </div>

    <!-- 主体内容区域 -->
    <div class="main-content">
      <!-- 左侧：选择导出目标 (40%) -->
      <div class="left-section">
        <div class="section-title">选择导出目标</div>
        <div class="section-subtitle">选择要导出聊天记录的群组或好友</div>

        <!-- 第一步内容 -->
        <div v-if="currentStep === 1" class="step-1-content">
          <div class="chat-type-label">选择聊天类型</div>
          <div class="chat-type-buttons">
            <button 
              class="chat-type-button" 
              :class="{ selected: selectedChatType === 'friend' }"
              @click="selectChatType('friend')"
            >
              好友聊天
            </button>
            <button 
              class="chat-type-button" 
              :class="{ selected: selectedChatType === 'group' }"
              @click="selectChatType('group')"
            >
              群组聊天
            </button>
          </div>

          <button class="load-button" @click="loadData">
            加载{{ selectedChatType === 'group' ? '群组' : '好友' }}
          </button>
          <span class="load-count">已加载{{ currentList.length }}个</span>

          <el-input
            v-model="searchQuery"
            class="search-input"
            placeholder="搜索群组/好友名称、群号/好友QQ号"
            clearable
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>

          <div class="item-list">
            <div 
              v-for="item in filteredList" 
              :key="item.group_code || item.uin"
              class="item-button"
              @click="selectItem(item)"
            >
              <img 
                :src="item.avatar_url ? `http://localhost:5000${item.avatar_url}` : item.default_avatar" 
                alt="头像" 
                class="item-avatar"
                @error="$event.target.src = item.default_avatar"
              />
              <span class="item-name">{{ item.group_name || item.nickname }}</span>
            </div>
          </div>
        </div>

        <!-- 第二步内容 -->
        <div v-else class="step-2-content">
          <div class="selected-info">已选择目标，请在右侧配置导出选项</div>
          <button class="reselect-button" @click="goBackToStep1">重新选择</button>
        </div>
      </div>

      <!-- 右侧：配置导出选项 (60%) -->
      <div class="right-section">
        <div class="section-title">配置导出选项</div>
        <div class="section-subtitle">设置导出格式和时间范围</div>

        <!-- 第一步：显示提示信息 -->
        <div v-if="currentStep === 1" class="step-1-hint">
          请先在左侧选择要导出的群组或好友
        </div>

        <!-- 第二步：显示配置选项 -->
        <div v-else class="step-2-content">
          <div class="selected-target-info">
            <div class="target-label">已选择 {{ selectedChatType === 'group' ? '群组' : '好友' }}</div>
            <div class="target-name">{{ selectedItem.group_name || selectedItem.nickname }}</div>
            <button class="change-button" @click="goBackToStep1">更换</button>
          </div>

          <div class="divider"></div>

          <div class="format-section">
            <div class="format-title">导出格式</div>
            <div class="format-subtitle">选择最适合您需求的格式</div>

            <div class="format-options">
              <button 
                class="format-button" 
                :class="{ selected: selectedFormat === 'JSON' }"
                @click="selectFormat('JSON')"
              >
                <div class="format-name">JSON</div>
                <div class="format-desc">结构化数据，保留完整信息，生成简报请使用这个</div>
              </button>

              <button 
                class="format-button" 
                :class="{ selected: selectedFormat === 'HTML' }"
                @click="selectFormat('HTML')"
              >
                <div class="format-name">HTML</div>
                <div class="format-desc">网页格式，适合直接查看和打印</div>
              </button>

              <button 
                class="format-button" 
                :class="{ selected: selectedFormat === 'TXT' }"
                @click="selectFormat('TXT')"
              >
                <div class="format-name">TXT</div>
                <div class="format-desc">纯文本，兼容性最好</div>
              </button>

              <button 
                class="format-button" 
                :class="{ selected: selectedFormat === 'EXCEL' }"
                @click="selectFormat('EXCEL')"
              >
                <div class="format-name">EXCEL</div>
                <div class="format-desc">Excel格式，便于数据分析</div>
              </button>
            </div>
          </div>

          <div class="time-section">
            <div class="time-title">时间范围</div>
            <div class="time-subtitle">留空则导出全部历史记录</div>

            <div class="time-picker-container">
              <span class="time-label">时间范围：</span>
              <el-date-picker
                v-model="startDate"
                type="date"
                placeholder="选择开始日期"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
              />
              <span class="time-separator">至</span>
              <el-date-picker
                v-model="endDate"
                type="date"
                placeholder="选择结束日期"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部按钮区域 -->
    <div class="footer-section">
      <div class="footer-buttons">
        <button class="cancel-button" @click="cancel">取消</button>
        <button 
          class="create-button" 
          :class="{ disabled: !canCreateTask }"
          :disabled="!canCreateTask"
          @click="createTask"
        >
          创建任务
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Setting, Search } from '@element-plus/icons-vue'
import { getGroups, getFriends, exportChat } from '../services/api'

const router = useRouter()
const route = useRoute()

const currentStep = ref(1)
const selectedChatType = ref('group')
const selectedFormat = ref('JSON')
const searchQuery = ref('')
const startDate = ref('')
const endDate = ref('')
const selectedItem = ref(null)

const groups = ref([])
const friends = ref([])

const currentList = computed(() => {
  return selectedChatType.value === 'group' ? groups.value : friends.value
})

const filteredList = computed(() => {
  if (!searchQuery.value) {
    return currentList.value
  }

  const query = searchQuery.value.toLowerCase()
  return currentList.value.filter(item => {
    const name = (item.group_name || item.nickname || '').toLowerCase()
    const id = (item.group_code || item.uin || '').toString()
    return name.includes(query) || id.includes(query)
  })
})

const canCreateTask = computed(() => {
  return currentStep.value === 2 && selectedItem.value !== null
})

const selectChatType = (type) => {
  selectedChatType.value = type
}

const loadData = async () => {
  try {
    const [groupsRes, friendsRes] = await Promise.all([
      getGroups(),
      getFriends()
    ])
    
    if (groupsRes.data.status === 'success') {
      groups.value = groupsRes.data.groups || []
    }
    
    if (friendsRes.data.status === 'success') {
      friends.value = friendsRes.data.friends || []
    }
  } catch (error) {
    console.error('加载数据失败:', error)
  }
}

const selectItem = (item) => {
  selectedItem.value = item
  currentStep.value = 2
}

const goBackToStep1 = () => {
  currentStep.value = 1
}

const selectFormat = (format) => {
  selectedFormat.value = format
}

const cancel = () => {
  router.push('/task')
}

const createTask = async () => {
  if (!canCreateTask.value) {
    return
  }

  try {
    const chatType = selectedChatType.value === 'group' ? 2 : 1
    const peerUid = selectedItem.value.group_code || selectedItem.value.uin

    const requestData = {
      chat_type: chatType,
      peer_uid: peerUid,
      format: selectedFormat.value
    }

    if (startDate.value && endDate.value) {
      requestData.filter = {
        start_time: startDate.value,
        end_time: endDate.value
      }
    }

    requestData.options = {
      include_resource_links: false,
      pretty_format: true
    }

    const response = await exportChat(requestData)

    if (response.data.status === 'success') {
      router.push('/task')
    } else {
      alert('创建任务失败，请重试')
    }
  } catch (error) {
    console.error('创建任务失败:', error)
    alert('创建任务失败，请重试')
  }
}

const initializeFromQuery = () => {
  const type = route.query.type
  const id = route.query.id

  if (type && id) {
    const chatType = type === '2' ? 'group' : 'friend'
    selectedChatType.value = chatType
    loadData().then(() => {
      const list = currentList.value
      const item = list.find(item => 
        (item.group_code && item.group_code.toString() === id.toString()) ||
        (item.uin && item.uin.toString() === id.toString())
      )
      
      if (item) {
        selectedItem.value = item
        currentStep.value = 2
      }
    })
  } else {
    loadData()
  }
}

onMounted(() => {
  initializeFromQuery()
})

watch(currentStep, (newStep) => {
  if (newStep === 1) {
    loadData()
  }
})
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100%;
  background-color: #ffffff;
  padding: 20px;
  box-sizing: border-box;
}

.header-section {
  height: 12.5%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.gear-icon {
  font-size: 32px;
  color: #000000;
}

.header-title {
  font-size: 28px;
  font-weight: bold;
  color: #000000;
}

.header-divider {
  height: 1px;
  background-color: #e0e0e0;
  margin-top: 20px;
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.left-section {
  width: 40%;
  height: 100%;
  padding: 20px 20px 20px 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e0e0e0;
}

.right-section {
  width: 60%;
  height: 100%;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.section-title {
  font-size: 18px;
  font-weight: 500;
  color: #000000;
  margin-bottom: 8px;
}

.section-subtitle {
  font-size: 14px;
  color: #666666;
  margin-bottom: 20px;
}

.step-1-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 15px;
  overflow: hidden;
}

.chat-type-label {
  font-size: 14px;
  color: #000000;
}

.chat-type-buttons {
  display: flex;
  gap: 10px;
}

.chat-type-button {
  flex: 1;
  padding: 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background-color: #ffffff;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.chat-type-button:hover {
  border-color: #409eff;
  color: #409eff;
}

.chat-type-button.selected {
  border-color: #409eff;
  color: #409eff;
  background-color: #ecf5ff;
}

.load-button {
  padding: 8px 16px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background-color: #ffffff;
  cursor: pointer;
  font-size: 14px;
  color: #000000;
  white-space: nowrap;
}

.load-button:hover {
  border-color: #409eff;
  color: #409eff;
}

.load-count {
  font-size: 14px;
  color: #666666;
  margin-left: 10px;
}

.search-input {
  width: 100%;
}

.item-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.item-button {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  height: 54px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background-color: #ffffff;
  cursor: pointer;
  transition: all 0.3s;
}

.item-button:hover {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.item-avatar {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  object-fit: cover;
}

.item-name {
  font-size: 14px;
  color: #000000;
}

.step-2-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 20px;
}

.selected-info {
  font-size: 16px;
  color: #000000;
  text-align: center;
}

.reselect-button {
  padding: 10px 20px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background-color: #ffffff;
  cursor: pointer;
  font-size: 14px;
  color: #000000;
}

.reselect-button:hover {
  border-color: #409eff;
  color: #409eff;
}

.step-1-hint {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: #999999;
}

.right-section .step-2-content {
  justify-content: flex-start;
  overflow-y: auto;
}

.selected-target-info {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background-color: #f5f5f5;
  border-radius: 4px;
}

.target-label {
  font-size: 14px;
  color: #666666;
}

.target-name {
  font-size: 16px;
  font-weight: 500;
  color: #000000;
  flex: 1;
}

.change-button {
  padding: 6px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background-color: #ffffff;
  cursor: pointer;
  font-size: 14px;
  color: #000000;
}

.change-button:hover {
  border-color: #409eff;
  color: #409eff;
}

.divider {
  height: 1px;
  background-color: #e0e0e0;
  margin: 20px 0;
}

.format-section,
.time-section {
  margin-bottom: 30px;
}

.format-title,
.time-title {
  font-size: 16px;
  font-weight: 500;
  color: #000000;
  margin-bottom: 8px;
}

.format-subtitle,
.time-subtitle {
  font-size: 14px;
  color: #666666;
  margin-bottom: 15px;
}

.format-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.format-button {
  padding: 15px 20px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background-color: #ffffff;
  cursor: pointer;
  text-align: left;
  transition: all 0.3s;
}

.format-button:hover {
  border-color: #409eff;
}

.format-button.selected {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.format-name {
  font-size: 16px;
  font-weight: 500;
  color: #000000;
  margin-bottom: 4px;
}

.format-desc {
  font-size: 14px;
  color: #666666;
}

.time-picker-container {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.time-label {
  font-size: 14px;
  color: #000000;
}

.time-separator {
  font-size: 14px;
  color: #666666;
}

.footer-section {
  height: 12.5%;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 40px;
  border-top: 1px solid #e0e0e0;
}

.footer-buttons {
  display: flex;
  gap: 15px;
}

.cancel-button,
.create-button {
  padding: 10px 30px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.cancel-button {
  background-color: #ffffff;
  border: 1px solid #d9d9d9;
  color: #000000;
}

.cancel-button:hover {
  border-color: #409eff;
  color: #409eff;
}

.create-button {
  background-color: #409eff;
  border: 1px solid #409eff;
  color: #ffffff;
}

.create-button:hover:not(.disabled) {
  background-color: #66b1ff;
  border-color: #66b1ff;
}

.create-button.disabled {
  background-color: #c0c4cc;
  border-color: #c0c4cc;
  cursor: not-allowed;
}
</style>
