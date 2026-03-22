<template>
    <div class="login-container">
        <div class="login-card">
            <div class="login-header">
                <h1>MySQL 智能运维</h1>
                <p>智能运维管理平台</p>
            </div>
            
            <el-form
                ref="loginFormRef"
                :model="loginForm"
                :rules="loginRules"
                class="login-form"
                @submit.prevent="handleLogin"
            >
                <el-form-item prop="username">
                    <el-input
                        v-model="loginForm.username"
                        placeholder="请输入用户名"
                        prefix-icon="User"
                        size="large"
                    />
                </el-form-item>
                
                <el-form-item prop="password">
                    <el-input
                        v-model="loginForm.password"
                        type="password"
                        placeholder="请输入密码"
                        prefix-icon="Lock"
                        size="large"
                        show-password
                        @keyup.enter="handleLogin"
                    />
                </el-form-item>
                
                <el-form-item>
                    <el-button
                        type="primary"
                        size="large"
                        class="login-button"
                        :loading="loading"
                        @click="handleLogin"
                    >
                        登 录
                    </el-button>
                </el-form-item>
            </el-form>
            
            <div class="login-footer">
                <el-divider>
                    <span class="demo-hint">演示账号</span>
                </el-divider>
                <div class="demo-accounts">
                    <el-tag
                        v-for="account in demoAccounts"
                        :key="account.username"
                        class="account-tag"
                        @click="fillAccount(account)"
                    >
                        {{ account.username }} ({{ account.role }})
                    </el-tag>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

const router = useRouter()
const loginFormRef = ref()
const loading = ref(false)

const loginForm = reactive({
    username: '',
    password: ''
})

const loginRules = {
    username: [
        { required: true, message: '请输入用户名', trigger: 'blur' }
    ],
    password: [
        { required: true, message: '请输入密码', trigger: 'blur' },
        { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
    ]
}

const demoAccounts = [
    { username: 'root', password: '123456', role: '管理员' },
    { username: 'admin', password: 'admin123', role: '管理员' },
    { username: 'operator', password: 'oper123', role: '运维员' },
    { username: 'viewer', password: 'view123', role: '观察员' }
]

const fillAccount = (account) => {
    loginForm.username = account.username
    loginForm.password = account.password
}

const handleLogin = async () => {
    if (!loginFormRef.value) return
    
    await loginFormRef.value.validate(async (valid) => {
        if (!valid) return
        
        loading.value = true
        
        try {
            const res = await api.post('/auth/login', {
                username: loginForm.username,
                password: loginForm.password
            })
            
            localStorage.setItem('token', res.access_token)
            localStorage.setItem('user', JSON.stringify(res.user))
            
            ElMessage.success(`欢迎回来，${res.user.username}！`)
            router.push('/chat')
        } catch (error) {
            console.error('登录失败:', error)
        } finally {
            loading.value = false
        }
    })
}
</script>

<style lang="scss" scoped>
.login-container {
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    
    .login-card {
        width: 400px;
        padding: 40px;
        background: #fff;
        border-radius: 12px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        
        .login-header {
            text-align: center;
            margin-bottom: 30px;
            
            h1 {
                font-size: 28px;
                color: #303133;
                margin-bottom: 8px;
            }
            
            p {
                color: #909399;
                font-size: 14px;
            }
        }
        
        .login-form {
            .login-button {
                width: 100%;
                margin-top: 10px;
            }
        }
        
        .login-footer {
            margin-top: 20px;
            
            .demo-hint {
                color: #909399;
                font-size: 12px;
            }
            
            .demo-accounts {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                justify-content: center;
                margin-top: 10px;
                
                .account-tag {
                    cursor: pointer;
                    transition: all 0.3s;
                    
                    &:hover {
                        transform: scale(1.05);
                    }
                }
            }
        }
    }
}
</style>
