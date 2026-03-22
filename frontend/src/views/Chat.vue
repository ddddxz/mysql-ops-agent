<template>
    <div class="chat-container">
        <el-card class="chat-card">
            <template #header>
                <div class="chat-header">
                    <span>MySQL 智能助手</span>
                    <div class="header-actions">
                        <el-switch
                            v-model="chatStore.deepThinkMode"
                            active-text="深度思考"
                            inactive-text="简洁模式"
                            inline-prompt
                            class="mode-switch"
                        />
                        <el-button type="primary" size="small" @click="chatStore.clearHistory">
                            清空对话
                        </el-button>
                    </div>
                </div>
            </template>
            
            <div class="chat-messages" ref="messagesRef">
                <div
                    v-for="(msg, index) in chatStore.messages"
                    :key="index"
                    :class="['message', msg.role]"
                >
                    <div class="message-avatar">
                        <el-avatar v-if="msg.role === 'user'" :size="36">
                            <el-icon><User /></el-icon>
                        </el-avatar>
                        <el-avatar v-else :size="36" class="bot-avatar">
                            <el-icon><Monitor /></el-icon>
                        </el-avatar>
                    </div>
                    <div class="message-content">
                        <div v-if="msg.thinking && msg.thinking.length > 0" class="thinking-section">
                            <div class="thinking-header" @click="msg.showThinking = !msg.showThinking">
                                <el-icon><Cpu /></el-icon>
                                <span>思考过程</span>
                                <el-icon class="arrow" :class="{ 'is-active': msg.showThinking }">
                                    <ArrowDown />
                                </el-icon>
                            </div>
                            <el-collapse-transition>
                                <div v-show="msg.showThinking" class="thinking-content">
                                    <div v-for="(think, i) in msg.thinking" :key="i" class="think-item">
                                        {{ think }}
                                    </div>
                                </div>
                            </el-collapse-transition>
                        </div>
                        <div class="message-text" v-html="chatStore.formatMessage(msg.content)"></div>
                    </div>
                </div>
                
                <div v-if="chatStore.loading" class="message assistant">
                    <div class="message-avatar">
                        <el-avatar :size="36" class="bot-avatar">
                            <el-icon><Monitor /></el-icon>
                        </el-avatar>
                    </div>
                    <div class="message-content">
                        <div v-if="chatStore.currentThinking.length > 0" class="thinking-section active">
                            <div class="thinking-header">
                                <el-icon class="is-loading"><Loading /></el-icon>
                                <span>正在思考...</span>
                            </div>
                            <div class="thinking-content">
                                <div v-for="(think, i) in chatStore.currentThinking" :key="i" class="think-item">
                                    {{ think }}
                                </div>
                            </div>
                        </div>
                        <div v-else class="message-loading">
                            <el-icon class="is-loading"><Loading /></el-icon>
                            <span>思考中...</span>
                        </div>
                        <div v-if="chatStore.streamingContent" class="message-text streaming">
                            {{ chatStore.streamingContent }}<span class="cursor">|</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="chat-input">
                <el-input
                    v-model="inputMessage"
                    type="textarea"
                    :rows="3"
                    placeholder="输入你的问题，例如：检查 MySQL 健康状态"
                    @keydown.enter.ctrl="sendMessage"
                />
                <div class="input-actions">
                    <span class="tip">Ctrl + Enter 发送</span>
                    <el-button
                        type="primary"
                        :loading="chatStore.loading"
                        :disabled="!inputMessage.trim()"
                        @click="sendMessage"
                    >
                        发送
                    </el-button>
                </div>
            </div>
        </el-card>
    </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()
const inputMessage = ref('')
const messagesRef = ref(null)

const scrollToBottom = () => {
    nextTick(() => {
        chatStore.scrollToBottom(messagesRef.value)
    })
}

const sendMessage = async () => {
    const message = inputMessage.value.trim()
    if (!message || chatStore.loading) return
    
    inputMessage.value = ''
    await chatStore.sendMessage(message, messagesRef.value)
}

onMounted(() => {
    chatStore.initWelcome()
    scrollToBottom()
})
</script>

<style lang="scss" scoped>
.chat-container {
    height: calc(100vh - 40px);
    
    .chat-card {
        height: 100%;
        display: flex;
        flex-direction: column;
        
        :deep(.el-card__header) {
            padding: 15px 20px;
            border-bottom: 1px solid #ebeef5;
        }
        
        :deep(.el-card__body) {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 0;
            overflow: hidden;
        }
    }
    
    .chat-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 16px;
        font-weight: 500;
        
        .header-actions {
            display: flex;
            align-items: center;
            gap: 15px;
            
            .mode-switch {
                --el-switch-on-color: #67C23A;
            }
        }
    }
    
    .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 20px;
        
        .message {
            display: flex;
            margin-bottom: 20px;
            
            &.user {
                flex-direction: row-reverse;
                
                .message-content {
                    background-color: #409EFF;
                    color: #fff;
                }
            }
            
            &.assistant {
                .message-content {
                    background-color: #f4f4f5;
                    color: #303133;
                }
            }
            
            .message-avatar {
                flex-shrink: 0;
                margin: 0 10px;
                
                .bot-avatar {
                    background-color: #67C23A;
                }
            }
            
            .message-content {
                max-width: 70%;
                padding: 12px 16px;
                border-radius: 8px;
                line-height: 1.6;
                
                .thinking-section {
                    margin-bottom: 12px;
                    border: 1px solid #e4e7ed;
                    border-radius: 6px;
                    overflow: hidden;
                    
                    &.active {
                        border-color: #67C23A;
                        background-color: #f0f9eb;
                    }
                    
                    .thinking-header {
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        padding: 8px 12px;
                        background-color: #f5f7fa;
                        cursor: pointer;
                        user-select: none;
                        
                        &:hover {
                            background-color: #e9ecf0;
                        }
                        
                        .arrow {
                            margin-left: auto;
                            transition: transform 0.3s;
                            
                            &.is-active {
                                transform: rotate(180deg);
                            }
                        }
                    }
                    
                    .thinking-content {
                        padding: 12px;
                        background-color: #fafafa;
                        
                        .think-item {
                            padding: 4px 0;
                            color: #606266;
                            font-size: 13px;
                            
                            &::before {
                                content: '› ';
                                color: #67C23A;
                            }
                        }
                    }
                }
                
                .message-text {
                    li {
                        margin-left: 20px;
                    }
                    
                    &.streaming {
                        .cursor {
                            animation: blink 1s infinite;
                        }
                    }
                }
                
                .message-loading {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    color: #909399;
                }
            }
        }
    }
    
    .chat-input {
        padding: 15px;
        border-top: 1px solid #ebeef5;
        
        .input-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 10px;
            
            .tip {
                color: #909399;
                font-size: 12px;
            }
        }
    }
}

@keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}
</style>
