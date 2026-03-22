import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/utils/api'

export const useSchedulerStore = defineStore('scheduler', () => {
    const jobs = ref([])
    const loading = ref(false)
    const creating = ref(false)
    const lastResult = ref(null)

    const fetchJobs = async () => {
        loading.value = true
        try {
            const res = await api.get('/scheduler/jobs')
            jobs.value = res || []
        } finally {
            loading.value = false
        }
    }

    const createJob = async (createForm) => {
        creating.value = true
        try {
            let url = ''
            if (createForm.type === 'health-check') {
                if (createForm.mode === 'cron') {
                    url = `/scheduler/job/health-check?cron_expression=${encodeURIComponent(createForm.cronExpression)}`
                } else {
                    url = `/scheduler/job/interval?job_type=health_check&hours=${createForm.intervalHours}&minutes=${createForm.intervalMinutes}`
                }
            } else {
                if (createForm.mode === 'cron') {
                    url = `/scheduler/job/report?report_type=${createForm.reportType}&cron_expression=${encodeURIComponent(createForm.cronExpression)}`
                } else {
                    url = `/scheduler/job/interval?job_type=report&hours=${createForm.intervalHours}&minutes=${createForm.intervalMinutes}`
                }
            }
            
            await api.post(url)
            ElMessage.success('任务创建成功')
            fetchJobs()
        } catch (error) {
            console.error(error)
        } finally {
            creating.value = false
        }
    }

    const triggerJob = async (jobId) => {
        try {
            await api.post(`/scheduler/job/${jobId}/trigger`)
            ElMessage.success('任务已触发执行')
        } catch (error) {
            console.error(error)
        }
    }

    const deleteJob = async (jobId) => {
        try {
            await ElMessageBox.confirm('确定要删除该任务吗？', '提示', {
                type: 'warning'
            })
            await api.delete(`/scheduler/job/${jobId}`)
            ElMessage.success('任务已删除')
            fetchJobs()
        } catch (error) {
            if (error !== 'cancel') {
                console.error(error)
            }
        }
    }

    const runHealthCheck = async () => {
        try {
            const res = await api.post('/scheduler/health-check/run')
            lastResult.value = res
            ElMessage.success('健康检查完成')
        } catch (error) {
            console.error(error)
        }
    }

    const formatTime = (time) => {
        if (!time) return '-'
        return new Date(time).toLocaleString('zh-CN')
    }

    const getStatusType = (status) => {
        const types = { healthy: 'success', warning: 'warning', error: 'danger' }
        return types[status] || 'info'
    }

    const getStatusText = (status) => {
        const texts = { healthy: '健康', warning: '警告', error: '错误' }
        return texts[status] || status
    }

    return {
        jobs,
        loading,
        creating,
        lastResult,
        fetchJobs,
        createJob,
        triggerJob,
        deleteJob,
        runHealthCheck,
        formatTime,
        getStatusType,
        getStatusText
    }
})
