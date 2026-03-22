<template>
    <el-config-provider :locale="zhCn">
        <template v-if="isLoginPage">
            <router-view />
        </template>
        <template v-else>
            <el-container class="app-container">
                <el-aside width="220px" class="app-aside">
                    <div class="logo">
                        <el-icon size="24"><Database /></el-icon>
                        <span>MySQL 智能运维</span>
                    </div>
                    <el-menu
                        :default-active="activeMenu"
                        router
                        background-color="#304156"
                        text-color="#bfcbd9"
                        active-text-color="#409EFF"
                    >
                        <el-menu-item index="/chat">
                            <el-icon><ChatDotRound /></el-icon>
                            <span>对话助手</span>
                        </el-menu-item>
                        <el-menu-item index="/scheduler">
                            <el-icon><Timer /></el-icon>
                            <span>定时任务</span>
                        </el-menu-item>
                        <el-menu-item index="/reports">
                            <el-icon><Document /></el-icon>
                            <span>健康报表</span>
                        </el-menu-item>
                        <el-menu-item index="/sessions">
                            <el-icon><ChatLineSquare /></el-icon>
                            <span>会话历史</span>
                        </el-menu-item>
                    </el-menu>
                </el-aside>
                <el-container>
                    <el-header class="app-header">
                        <div class="header-left">
                            <span class="page-title">{{ pageTitle }}</span>
                        </div>
                        <div class="header-right">
                            <el-dropdown @command="handleCommand">
                                <span class="user-info">
                                    <el-icon><User /></el-icon>
                                    <span>{{ userInfo.username }}</span>
                                    <el-tag size="small" type="success">{{ roleLabel }}</el-tag>
                                </span>
                                <template #dropdown>
                                    <el-dropdown-menu>
                                        <el-dropdown-item command="profile">
                                            <el-icon><User /></el-icon>
                                            个人信息
                                        </el-dropdown-item>
                                        <el-dropdown-item divided command="logout">
                                            <el-icon><SwitchButton /></el-icon>
                                            退出登录
                                        </el-dropdown-item>
                                    </el-dropdown-menu>
                                </template>
                            </el-dropdown>
                        </div>
                    </el-header>
                    <el-main class="app-main">
                        <router-view />
                    </el-main>
                </el-container>
            </el-container>
        </template>
    </el-config-provider>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

const route = useRoute()
const router = useRouter()
const activeMenu = computed(() => route.path)

const userInfo = ref({
    username: '',
    role: '',
    permissions: []
})

const isLoginPage = computed(() => route.path === '/login')

const pageTitle = computed(() => route.meta.title || 'MySQL 智能运维')

const roleLabel = computed(() => {
    const roleMap = {
        'admin': '管理员',
        'operator': '运维员',
        'viewer': '观察员'
    }
    return roleMap[userInfo.value.role] || userInfo.value.role
})

const loadUserInfo = () => {
    const userStr = localStorage.getItem('user')
    if (userStr) {
        try {
            userInfo.value = JSON.parse(userStr)
        } catch (e) {
            console.error('解析用户信息失败:', e)
        }
    }
}

const handleCommand = async (command) => {
    if (command === 'logout') {
        try {
            await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
                type: 'warning'
            })
            localStorage.removeItem('token')
            localStorage.removeItem('user')
            ElMessage.success('已退出登录')
            router.push('/login')
        } catch (e) {
            // 取消操作
        }
    } else if (command === 'profile') {
        ElMessage.info('个人信息功能开发中...')
    }
}

onMounted(() => {
    loadUserInfo()
})
</script>

<style lang="scss" scoped>
.app-container {
    height: 100vh;
}

.app-aside {
    background-color: #304156;
    
    .logo {
        height: 60px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        color: #fff;
        font-size: 16px;
        font-weight: bold;
        border-bottom: 1px solid #3a4a5e;
    }
    
    .el-menu {
        border-right: none;
    }
}

.app-header {
    background-color: #fff;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 20px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
    
    .header-left {
        .page-title {
            font-size: 18px;
            font-weight: 500;
            color: #303133;
        }
    }
    
    .header-right {
        .user-info {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            padding: 8px 12px;
            border-radius: 4px;
            transition: background-color 0.3s;
            
            &:hover {
                background-color: #f5f7fa;
            }
        }
    }
}

.app-main {
    background-color: #f0f2f5;
    padding: 20px;
}
</style>
