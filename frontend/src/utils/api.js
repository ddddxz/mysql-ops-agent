import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const api = axios.create({
    baseURL: '/api',
    timeout: 60000,
    headers: {
        'Content-Type': 'application/json'
    }
})

api.interceptors.request.use(
    config => {
        const token = localStorage.getItem('token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    error => {
        return Promise.reject(error)
    }
)

api.interceptors.response.use(
    response => response.data,
    error => {
        const isLoginRequest = error.config?.url?.includes('/auth/login')
        
        if (error.response?.status === 401) {
            if (isLoginRequest) {
                const message = error.response?.data?.detail || '用户名或密码错误'
                ElMessage.error(message)
            } else {
                localStorage.removeItem('token')
                localStorage.removeItem('user')
                ElMessage.error('登录已过期，请重新登录')
                router.push('/login')
            }
        } else {
            const message = error.response?.data?.detail || error.response?.data?.detail?.message || error.message || '请求失败'
            ElMessage.error(message)
        }
        return Promise.reject(error)
    }
)

export default api
