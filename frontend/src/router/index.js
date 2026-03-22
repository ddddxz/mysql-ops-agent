import { createRouter, createWebHistory } from 'vue-router'

const routes = [
    {
        path: '/login',
        name: 'Login',
        component: () => import('@/views/Login.vue'),
        meta: { title: '登录', requiresAuth: false }
    },
    {
        path: '/',
        redirect: '/chat'
    },
    {
        path: '/chat',
        name: 'Chat',
        component: () => import('@/views/Chat.vue'),
        meta: { title: '对话助手', requiresAuth: true }
    },
    {
        path: '/scheduler',
        name: 'Scheduler',
        component: () => import('@/views/Scheduler.vue'),
        meta: { title: '定时任务', requiresAuth: true }
    },
    {
        path: '/reports',
        name: 'Reports',
        component: () => import('@/views/Reports.vue'),
        meta: { title: '健康报表', requiresAuth: true }
    },
    {
        path: '/sessions',
        name: 'Sessions',
        component: () => import('@/views/Sessions.vue'),
        meta: { title: '会话历史', requiresAuth: true }
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

router.beforeEach((to, from, next) => {
    document.title = `${to.meta.title} - MySQL 智能运维`
    
    const token = localStorage.getItem('token')
    const requiresAuth = to.meta.requiresAuth !== false
    
    if (requiresAuth && !token) {
        next('/login')
    } else if (to.path === '/login' && token) {
        next('/chat')
    } else {
        next()
    }
})

export default router
