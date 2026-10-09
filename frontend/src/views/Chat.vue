<template>
  <div class="page-container">
    <!-- 顶部标题和按钮区域 -->
    <div class="header-container">
      <div class="header-text">
        <div class="title">会话管理</div>
        <div class="subtitle">浏览群组与好友，选择要导出的聊天记录</div>
      </div>
      <div class="header-buttons">
        <button class="button-style-a" @click="refreshList">刷新列表</button>
      </div>
    </div>
    
    <!-- 30像素间距 -->
    <div class="spacing"></div>
    
    <!-- 分割线 -->
    <div class="divider"></div>
    
    <!-- 内容区域 -->
    <div class="content-container">
      <!-- 左侧群组列表 -->
      <div class="left-section">
        <div class="section-title">群组（{{ groupCount }}）</div>
        <div class="item-list">
          <div v-for="group in groups" :key="group.group_code" class="item-card">
            <div class="item-avatar">
              <img src="https://via.placeholder.com/40" alt="群头像" />
            </div>
            <div class="item-info">
              <div class="item-name">{{ group.group_name }}</div>
              <div class="item-id">{{ group.group_code }}</div>
            </div>
            <div class="item-actions">
              <button class="button-style-b" @click="exportChat('group', group.group_code)">导出</button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 右侧好友列表 -->
      <div class="right-section">
        <div class="section-title">好友（{{ friendCount }}）</div>
        <div class="item-list">
          <div v-for="friend in friends" :key="friend.uin" class="item-card">
            <div class="item-avatar">
              <img src="https://via.placeholder.com/40" alt="好友头像" />
            </div>
            <div class="item-info">
              <div class="item-name">{{ friend.nick }}</div>
              <div class="item-id">{{ friend.uin }}</div>
            </div>
            <div class="item-actions">
              <button class="button-style-b" @click="exportChat('friend', friend.uin)">导出</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { getGroups, getFriends } from '../services/api'

const router = useRouter()
const authStore = useAuthStore()

// 群组和好友数据
const groups = ref([])
const friends = ref([])
const groupCount = ref(0)
const friendCount = ref(0)

// 刷新列表
const refreshList = async () => {
  try {
    const groupResponse = await getGroups()
    if (groupResponse.data.status === 'success') {
      groups.value = groupResponse.data.groups || []
      groupCount.value = groups.value.length
    }
    
    const friendResponse = await getFriends()
    if (friendResponse.data.status === 'success') {
      friends.value = friendResponse.data.friends || []
      friendCount.value = friends.value.length
    }
  } catch (error) {
    console.error('刷新列表失败:', error)
  }
}

// 导出聊天记录
const exportChat = (type, id) => {
  const chatType = type === 'group' ? 2 : 1
  router.push({
    path: '/create-new-task',
    query: {
      type: chatType,
      id: id
    }
  })
}

// 组件挂载时获取数据
onMounted(() => {
  if (authStore.isConnected) {
    refreshList()
  }
})
</script>

<style scoped>
.page-container {
  width: 100%;
  padding: 20px 0;
  display: flex;
  flex-direction: column;
}

.header-container {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.header-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.title {
  font-size: 24px;
  font-weight: bold;
  color: black;
  margin-bottom: 5px;
}

.subtitle {
  font-size: 16px;
  color: black;
}

.header-buttons {
  display: flex;
  gap: 10px;
}

.spacing {
  height: 30px;
}

.divider {
  width: 100%;
  height: 1px;
  background-color: #eee;
  margin-bottom: 20px;
}

.content-container {
  display: flex;
  justify-content: space-between;
  width: 100%;
}

.left-section, .right-section {
  width: 48%;
}

.section-title {
  font-size: 14px;
  color: black;
  margin-bottom: 15px;
}

.item-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.item-card {
  display: flex;
  align-items: center;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: white;
}

.item-avatar {
  width: 40px;
  height: 40px;
  margin-right: 5px;
}

.item-avatar img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
}

.item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.item-name {
  font-weight: bold;
  margin-bottom: 2px;
}

.item-id {
  font-size: 12px;
  color: #666;
}

.item-actions {
  display: flex;
  gap: 5px;
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