import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    isConnected: false,  // 标记是否已连接到NapCat服务
    isPolling: false,
    pollingTimer: null
  }),
  
  actions: {
    setConnectionStatus(status) {
      this.isConnected = status
    },
    
    setPollingStatus(status) {
      this.isPolling = status
    },
    
    setPollingTimer(timer) {
      this.pollingTimer = timer
    },
    
    clearPollingTimer() {
      if (this.pollingTimer) {
        clearInterval(this.pollingTimer)
        this.pollingTimer = null
      }
      this.isPolling = false
    }
  }
})