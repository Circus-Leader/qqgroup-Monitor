import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory('/qcea-tool'),
  routes: [
    {
      path: '/',
      name: 'Overview',
      component: () => import('../views/Overview.vue')
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/Login.vue')
    },
    {
      path: '/chat',
      name: 'Chat',
      component: () => import('../views/Chat.vue')
    },
    {
      path: '/task',
      name: 'Task',
      component: () => import('../views/Task.vue')
    },
    {
      path: '/brief-report',
      name: 'BriefReport',
      component: () => import('../views/BriefReport.vue')
    },
    {
      path: '/about',
      name: 'About',
      component: () => import('../views/About.vue')
    },
    {
      path: '/create-new-task',
      name: 'CreateNewTask',
      component: () => import('../views/CreateNewTask.vue')
    }
  ]
})

export default router