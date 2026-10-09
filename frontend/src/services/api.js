import axios from 'axios'
import { useAuthStore } from '../stores/auth'

// 创建axios实例
const api = axios.create({
  baseURL: 'http://localhost:5000',
  timeout: 10000
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 检查是否为需要连接状态的API
    const requiresConnection = [
      '/api/qq/groups',
      '/api/qq/friends',
      '/api/qq/tasks',
      '/api/qq/export',
      '/api/qq/batch_export',
      '/api/analyze'
    ]
    
    // 如果请求需要连接状态，检查是否已连接
    if (requiresConnection.some(path => config.url.includes(path))) {
      const authStore = useAuthStore()
      if (!authStore.isConnected) {
        // 如果未连接，取消请求
        return Promise.reject(new Error('NapCat服务未连接，请先登录'))
      }
    }
    
    return config
  },
  error => {
    // 对请求错误做些什么
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    // 对响应数据做点什么
    return response
  },
  error => {
    // 对响应错误做点什么
    console.error('API请求错误:', error)
    return Promise.reject(error)
  }
)

// 获取二维码
export const getQrcode = () => {
  return api.get('/api/qrcode', {
    responseType: 'blob'
  })
}

// 启动napcat服务
export const startNapcat = () => {
  return api.post('/api/napcat/start')
}

// 获取napcat状态
export const getNapcatStatus = () => {
  return api.get('/api/napcat/status')
}

// 获取群聊列表
export const getGroups = () => {
  return api.get('/api/qq/groups')
}

// 获取好友列表
export const getFriends = () => {
  return api.get('/api/qq/friends')
}

// 获取任务列表
export const getTasks = () => {
  return api.get('/api/qq/tasks')
}

// 删除任务
export const deleteTask = (taskId) => {
  return api.delete(`/api/qq/tasks/${taskId}`)
}

// 打开文件所在位置
export const openFileLocation = (filePath) => {
  return api.post('/api/qq/tasks/open-file', { file_path: filePath })
}

// 导出聊天记录
export const exportChat = (data) => {
  return api.post('/api/qq/export', data)
}

// 批量导出聊天记录
export const batchExport = (data) => {
  return api.post('/api/qq/batch_export', data)
}

// 获取导出文件内容（用于预览）
export const getExportFile = (path) => {
  return api.get('/api/qq/export/file', {
    params: { path }
  })
}

// 分析导出任务（分析可能耗时较长，不设置超时）
export const analyzeTask = (taskId) => {
  return api.post('/api/analyze', { task_id: taskId }, {
    timeout: 0  // 0 表示无超时限制
  })
}

// 获取分析日志
export const getAnalyzeLogs = () => {
  return api.get('/api/analyze/logs')
}

// 清空分析日志
export const clearAnalyzeLogs = () => {
  return api.get('/api/analyze/logs/clear')
}

export default api