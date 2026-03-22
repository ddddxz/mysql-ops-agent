import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

export const useChatStore = defineStore('chat', () => {
    const messages = ref([])
    const sessionId = ref(null)
    const deepThinkMode = ref(false)
    const loading = ref(false)
    const streamingContent = ref('')
    const currentThinking = ref([])
    let abortController = null

    const scrollToBottom = (messagesRef) => {
        if (messagesRef) {
            messagesRef.scrollTop = messagesRef.scrollHeight
        }
    }

    const formatMessage = (content) => {
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>')
            .replace(/- (.*?)(?=<br>|$)/g, '<li>$1</li>')
    }

    const sendMessage = async (message, messagesRef) => {
        if (!message || loading.value) return
        
        messages.value.push({ role: 'user', content: message })
        loading.value = true
        streamingContent.value = ''
        currentThinking.value = []
        scrollToBottom(messagesRef)
        
        abortController = new AbortController()
        
        try {
            const token = localStorage.getItem('token')
            const params = new URLSearchParams({
                message,
                user_id: 'web_user',
                deep_think: deepThinkMode.value
            })
            
            if (sessionId.value) {
                params.append('session_id', sessionId.value)
            }
            
            const response = await fetch(`/api/stream/chat?${params.toString()}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                signal: abortController.signal
            })
            
            if (!response.ok) {
                throw new Error('请求失败')
            }
            
            const reader = response.body.getReader()
            const decoder = new TextDecoder()
            let buffer = ''
            let thinkingList = []
            let fullContent = ''
            
            while (true) {
                const { done, value } = await reader.read()
                if (done) break
                
                buffer += decoder.decode(value, { stream: true })
                const lines = buffer.split('\n')
                buffer = lines.pop() || ''
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6))
                            
                            switch (data.type) {
                                case 'session':
                                    sessionId.value = data.session_id
                                    break
                                case 'think_start':
                                    currentThinking.value = []
                                    break
                                case 'thinking':
                                    currentThinking.value.push(data.content)
                                    scrollToBottom(messagesRef)
                                    break
                                case 'think_end':
                                    thinkingList = [...currentThinking.value]
                                    currentThinking.value = []
                                    break
                                case 'response_start':
                                    streamingContent.value = ''
                                    break
                                case 'chunk':
                                    streamingContent.value += data.content
                                    fullContent += data.content
                                    scrollToBottom(messagesRef)
                                    break
                                case 'done':
                                    sessionId.value = data.session_id
                                    break
                                case 'error':
                                    ElMessage.error(data.message)
                                    break
                            }
                        } catch (e) {
                            console.error('解析数据失败:', e)
                        }
                    }
                }
            }
            
            messages.value.push({
                role: 'assistant',
                content: fullContent || streamingContent.value,
                thinking: thinkingList,
                showThinking: false
            })
            
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('请求已取消')
            } else {
                console.error(error)
                messages.value.push({
                    role: 'assistant',
                    content: '抱歉，处理您的请求时出现错误，请稍后重试。'
                })
            }
        } finally {
            loading.value = false
            streamingContent.value = ''
            currentThinking.value = []
            abortController = null
            scrollToBottom(messagesRef)
        }
    }

    const cancelRequest = () => {
        if (abortController) {
            abortController.abort()
        }
    }

    const clearHistory = async () => {
        try {
            const token = localStorage.getItem('token')
            await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    message: '',
                    user_id: 'web_user',
                    clear_history: true
                })
            })
            messages.value = []
            sessionId.value = null
            ElMessage.success('对话已清空')
        } catch (error) {
            console.error(error)
        }
    }

    const initWelcome = () => {
        if (messages.value.length === 0) {
            messages.value.push({
                role: 'assistant',
                content: '你好！我是 MySQL 智能运维助手，可以帮助你：\n\n- 检查 MySQL 健康状态\n- 分析慢查询\n- 优化 SQL 语句\n- 诊断性能问题\n\n请问有什么可以帮助你的？'
            })
        }
    }

    return {
        messages,
        sessionId,
        deepThinkMode,
        loading,
        streamingContent,
        currentThinking,
        sendMessage,
        cancelRequest,
        clearHistory,
        initWelcome,
        scrollToBottom,
        formatMessage
    }
})
