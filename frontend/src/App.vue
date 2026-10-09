<template>
  <div class="app-container">
    <!-- 导航栏 -->
    <Navbar />
    
    <!-- 主体内容区域 -->
    <div class="main-content">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import Navbar from './components/Navbar.vue'
</script>

<style>
/* 全局样式已在style.css中定义 */
</style>