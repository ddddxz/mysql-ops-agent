<template>
    <div class="sessions-container">
        <el-card>
            <template #header>
                <div class="card-header">
                    <span>会话历史</span>
                    <el-button type="primary" size="small" @click="createSession">
                        新建会话
                    </el-button>
                </div>
            </template>
            
            <el-table :data="sessions" v-loading="loading">
                <el-table-column prop="session_id" label="会话 ID" width="280">
                    <template #default="{ row }">
                        <el-link type="primary" @click="viewSession(row.session_id)">
                            {{ row.session_id }}
                        </el-link>
                    </template>
                </el-table-column>
                <el-table-column prop="user_id" label="用户" width="120" />
                <el-table-column prop="message_count" label="消息数" width="100">
                    <template #default="{ row }">
                        <el-tag>{{ row.message_count }}</el-tag>
                    </template>
                </el-table-column>
                <el-table-column prop="created_at" label="创建时间" width="180">
                    <template #default="{ row }">
                        {{ formatTime(row.created_at) }}
                    </template>
                </el-table-column>
                <el-table-column prop="updated_at" label="更新时间" width="180">
                    <template #default="{ row }">
                        {{ formatTime(row.updated_at) }}
                    </template>
                </el-table-column>
                <el-table-column label="操作" width="150">
                    <template #default="{ row }">
                        <el-button size="small" @click="viewSession(row.session_id)">
                            查看
                        </el-button>
                        <el-button size="small" type="danger" @click="deleteSession(row.session_id)">
                            删除
                        </el-button>
                    </template>
                </el-table-column>
            </el-table>
        </el-card>
        
        <el-dialog v-model="dialogVisible" title="会话详情" width="700px">
            <div class="session-detail" v-if="sessionDetail">
                <div class="session-info">
                    <span>会话 ID: {{ sessionDetail.session_id }}</span>
                    <span>用户: {{ sessionDetail.user_id }}</span>
                    <span>消息数: {{ sessionDetail.message_count }}</span>
                </div>
                
                <el-divider />
                
                <div class="messages-list">
                    <div
                        v-for="(msg, index) in sessionMessages"
                        :key="index"
                        :class="['message-item', msg.role]"
                    >
                        <div class="message-role">
                            <el-tag :type="msg.role === 'user' ? 'primary' : 'success'" size="small">
                                {{ msg.role === 'user' ? '用户' : '助手' }}
                            </el-tag>
                        </div>
                        <div class="message-content">{{ msg.content }}</div>
                    </div>
                </div>
            </div>
        </el-dialog>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/utils/api'

const sessions = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const sessionDetail = ref(null)
const sessionMessages = ref([])

const fetchSessions = async () => {
    loading.value = true
    try {
        const res = await api.get('/chat/sessions')
        sessions.value = res || []
    } finally {
        loading.value = false
    }
}

const createSession = async () => {
    try {
        const res = await api.post('/chat/session?user_id=web_user')
        ElMessage.success(`会话创建成功: ${res.session_id}`)
        fetchSessions()
    } catch (error) {
        console.error(error)
    }
}

const viewSession = async (sessionId) => {
    try {
        const res = await api.get(`/chat/session/${sessionId}/history`)
        sessionDetail.value = {
            session_id: sessionId,
            user_id: res.user_id,
            message_count: res.message_count
        }
        sessionMessages.value = res.messages || []
        dialogVisible.value = true
    } catch (error) {
        console.error(error)
    }
}

const deleteSession = async (sessionId) => {
    try {
        await ElMessageBox.confirm('确定要删除该会话吗？', '提示', {
            type: 'warning'
        })
        await api.delete(`/chat/session/${sessionId}`)
        ElMessage.success('会话已删除')
        fetchSessions()
    } catch (error) {
        if (error !== 'cancel') {
            console.error(error)
        }
    }
}

const formatTime = (time) => {
    if (!time) return '-'
    return new Date(time).toLocaleString('zh-CN')
}

onMounted(() => {
    fetchSessions()
})
</script>

<style lang="scss" scoped>
.sessions-container {
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .session-detail {
        .session-info {
            display: flex;
            gap: 30px;
            color: #606266;
        }
        
        .messages-list {
            max-height: 400px;
            overflow-y: auto;
            
            .message-item {
                margin-bottom: 15px;
                padding: 10px;
                border-radius: 8px;
                background: #f5f7fa;
                
                &.user {
                    background: #ecf5ff;
                }
                
                &.assistant {
                    background: #f0f9eb;
                }
                
                .message-role {
                    margin-bottom: 8px;
                }
                
                .message-content {
                    line-height: 1.6;
                    white-space: pre-wrap;
                    word-break: break-word;
                }
            }
        }
    }
}
</style>
