<template>
    <div class="reports-container">
        <el-row :gutter="20">
            <el-col :span="8">
                <el-card>
                    <template #header>
                        <div class="card-header">
                            <span>报表列表</span>
                            <el-button type="primary" size="small" @click="generateReport">
                                生成报表
                            </el-button>
                        </div>
                    </template>
                    
                    <el-table :data="reports" v-loading="loading" highlight-current-row @current-change="selectReport">
                        <el-table-column prop="title" label="报表标题" show-overflow-tooltip />
                        <el-table-column prop="report_type" label="类型" width="80">
                            <template #default="{ row }">
                                <el-tag size="small">{{ row.report_type }}</el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column prop="generated_at" label="生成时间" width="180">
                            <template #default="{ row }">
                                {{ formatTime(row.generated_at) }}
                            </template>
                        </el-table-column>
                    </el-table>
                </el-card>
            </el-col>
            
            <el-col :span="16">
                <el-card>
                    <template #header>
                        <span>报表详情</span>
                    </template>
                    
                    <div v-if="currentReport" class="report-detail">
                        <div class="report-header">
                            <h3>{{ currentReport.report_type }} 报表</h3>
                            <span class="report-time">生成时间：{{ formatTime(currentReport.generated_at) }}</span>
                        </div>
                        
                        <el-divider />
                        
                        <div class="server-info" v-if="currentReport.server_info">
                            <h4>服务器信息</h4>
                            <el-descriptions :column="2" border>
                                <el-descriptions-item label="版本">
                                    {{ currentReport.server_info.version }}
                                </el-descriptions-item>
                                <el-descriptions-item label="端口">
                                    {{ currentReport.server_info.port }}
                                </el-descriptions-item>
                                <el-descriptions-item label="主机名" :span="2">
                                    {{ currentReport.server_info.hostname }}
                                </el-descriptions-item>
                                <el-descriptions-item label="数据目录" :span="2">
                                    {{ currentReport.server_info.datadir }}
                                </el-descriptions-item>
                            </el-descriptions>
                        </div>
                        
                        <div class="status-summary" v-if="currentReport.status_variables">
                            <h4>状态摘要</h4>
                            <el-row :gutter="15">
                                <el-col :span="6" v-for="(value, key) in statusCards" :key="key">
                                    <el-statistic :title="value.label" :value="formatNumber(value.value)" />
                                </el-col>
                            </el-row>
                        </div>
                        
                        <div class="health-metrics" v-if="currentReport.health_metrics">
                            <h4>健康指标</h4>
                            <el-row :gutter="15">
                                <el-col :span="8">
                                    <div class="metric-card">
                                        <div class="metric-title">连接使用率</div>
                                        <div class="metric-value">
                                            {{ currentReport.health_metrics.connection_usage }}
                                        </div>
                                        <el-progress 
                                            :percentage="currentReport.health_metrics.connection_usage_percent"
                                            :status="getProgressStatus(currentReport.health_metrics.connection_usage_percent)"
                                        />
                                    </div>
                                </el-col>
                                <el-col :span="8">
                                    <div class="metric-card">
                                        <div class="metric-title">缓冲池命中率</div>
                                        <div class="metric-value">
                                            {{ currentReport.health_metrics.buffer_pool_hit_rate }}%
                                        </div>
                                        <el-progress 
                                            :percentage="currentReport.health_metrics.buffer_pool_hit_rate"
                                            :status="getProgressStatus(currentReport.health_metrics.buffer_pool_hit_rate, true)"
                                        />
                                    </div>
                                </el-col>
                                <el-col :span="8">
                                    <div class="metric-card">
                                        <div class="metric-title">锁等待</div>
                                        <div class="metric-value">
                                            {{ currentReport.health_metrics.innodb_row_lock_waits }}
                                        </div>
                                        <el-tag :type="currentReport.health_metrics.innodb_row_lock_waits > 100 ? 'warning' : 'success'">
                                            {{ currentReport.health_metrics.innodb_row_lock_waits > 100 ? '需要关注' : '正常' }}
                                        </el-tag>
                                    </div>
                                </el-col>
                            </el-row>
                        </div>
                    </div>
                    
                    <el-empty v-else description="请选择一份报表查看" />
                </el-card>
            </el-col>
        </el-row>
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

const reports = ref([])
const currentReport = ref(null)
const loading = ref(false)

const statusCards = computed(() => {
    if (!currentReport.value?.status_variables) return {}
    const s = currentReport.value.status_variables
    return {
        uptime: { label: '运行时间(秒)', value: s.uptime },
        queries: { label: '查询总数', value: s.queries },
        connections: { label: '连接总数', value: s.connections },
        slowQueries: { label: '慢查询数', value: s.slow_queries }
    }
})

const fetchReports = async () => {
    loading.value = true
    try {
        const res = await api.get('/scheduler/report/list')
        reports.value = res || []
    } finally {
        loading.value = false
    }
}

const selectReport = async (row) => {
    if (!row) return
    try {
        const res = await api.get(`/scheduler/report/${row.id}`)
        if (res && res.content) {
            currentReport.value = {
                ...res,
                ...res.content
            }
        } else {
            currentReport.value = res
        }
    } catch (error) {
        console.error(error)
    }
}

const generateReport = async () => {
    try {
        await api.post('/scheduler/report/generate?report_type=daily')
        ElMessage.success('报表生成成功')
        fetchReports()
    } catch (error) {
        console.error(error)
    }
}

const formatTime = (time) => {
    if (!time) return '-'
    return new Date(time).toLocaleString('zh-CN')
}

const formatNumber = (num) => {
    if (!num) return 0
    return parseInt(num).toLocaleString()
}

const getProgressStatus = (value, inverse = false) => {
    if (inverse) {
        if (value >= 99) return 'success'
        if (value >= 95) return 'warning'
        return 'exception'
    }
    if (value >= 90) return 'exception'
    if (value >= 80) return 'warning'
    return 'success'
}

onMounted(() => {
    fetchReports()
})
</script>

<style lang="scss" scoped>
.reports-container {
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .report-detail {
        .report-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            
            h3 {
                margin: 0;
            }
            
            .report-time {
                color: #909399;
                font-size: 14px;
            }
        }
        
        h4 {
            margin: 20px 0 15px;
            color: #303133;
        }
        
        .metric-card {
            background: #f5f7fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            
            .metric-title {
                font-size: 14px;
                color: #909399;
                margin-bottom: 10px;
            }
            
            .metric-value {
                font-size: 28px;
                font-weight: bold;
                color: #303133;
                margin-bottom: 15px;
            }
        }
    }
}
</style>
