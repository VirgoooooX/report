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
    component: () => import('@/views/SnLookup.vue')
  },
  {
    path: '/predictions',
    name: 'predictions',
    component: () => import('@/views/PredictionsView.vue')
  },
  {
    path: '/export',
    name: 'export',
    component: () => import('@/views/ExportView.vue')
  }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
