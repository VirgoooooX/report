import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'

const routes = [
  { path: '/', name: 'dashboard', component: Dashboard },
  {
    path: '/category/:name',
    name: 'category',
    component: () => import('@/views/CategoryDetail.vue')
  },
  {
    path: '/sn',
    name: 'sn',
    component: () => import('@/views/QueryCenter.vue')
  },
  {
    path: '/predictions',
    name: 'predictions',
    component: () => import('@/views/PredictionsView.vue')
  },
  {
    path: '/schedule',
    name: 'schedule',
    component: () => import('@/views/ScheduleView.vue')
  },
  {
    path: '/test-summary',
    name: 'test-summary',
    component: () => import('@/views/TestSummaryView.vue')
  },
  {
    path: '/failure-analysis',
    name: 'failure-analysis',
    component: () => import('@/views/FailureMatrixPage.vue')
  },
  {
    path: '/export',
    name: 'export',
    component: () => import('@/views/ExportView.vue')
  },
  {
    path: '/daily-update',
    name: 'daily-update',
    component: () => import('@/views/DailyUpdateView.vue')
  },
]

export default createRouter({
  history: createWebHistory(),
  routes
})
