<template>
    <div class="scheduler-container">
        <el-row :gutter="20">
            <el-col :span="16">
                <el-card>
                    <template #header>
                        <div class="card-header">
                            <span>定时任务列表</span>
                            <el-button type="primary" size="small" @click="schedulerStore.runHealthCheck">
                                立即健康检查
                            </el-button>
                        </div>
                    </template>
                    
                    <el-table :data="schedulerStore.jobs" v-loading="schedulerStore.loading">
                        <el-table-column prop="job_id" label="任务 ID" width="150" />
                        <el-table-column prop="type" label="类型" width="100">
                            <template #default="{ row }">
                                <el-tag :type="row.type === 'cron' ? 'primary' : 'success'">
                                    {{ row.type }}
                                </el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column prop="expression" label="执行规则" width="150" />
                        <el-table-column prop="next_run_time" label="下次执行时间" width="180">
                            <template #default="{ row }">
                                {{ schedulerStore.formatTime(row.next_run_time) }}
                            </template>
                        </el-table-column>
                        <el-table-column label="操作" width="200">
                            <template #default="{ row }">
                                <el-button size="small" @click="schedulerStore.triggerJob(row.job_id)">
                                    立即执行
                                </el-button>
                                <el-button size="small" type="danger" @click="schedulerStore.deleteJob(row.job_id)">
                                    删除
                                </el-button>
                            </template>
                        </el-table-column>
                    </el-table>
                </el-card>
            </el-col>
            
            <el-col :span="8">
                <el-card>
                    <template #header>
                        <span>创建定时任务</span>
                    </template>
                    
                    <el-form :model="createForm" label-width="100px">
                        <el-form-item label="任务类型">
                            <el-select v-model="createForm.type" style="width: 100%">
                                <el-option label="健康检查" value="health-check" />
                                <el-option label="报表生成" value="report" />
                            </el-select>
                        </el-form-item>
                        
                        <el-form-item label="执行方式">
                            <el-radio-group v-model="createForm.mode">
                                <el-radio label="cron">Cron 表达式</el-radio>
                                <el-radio label="interval">间隔执行</el-radio>
                            </el-radio-group>
                        </el-form-item>
                        
                        <el-form-item v-if="createForm.mode === 'cron'" label="Cron 表达式">
                            <el-input v-model="createForm.cronExpression" placeholder="0 9 * * *" />
                            <div class="form-tip">格式：分 时 日 月 周（如 0 9 * * * 表示每天 9:00）</div>
                        </el-form-item>
                        
                        <el-form-item v-else label="间隔时间">
                            <el-row :gutter="10">
                                <el-col :span="12">
                                    <el-input-number v-model="createForm.intervalHours" :min="0" :max="23" />
                                    <span class="unit">小时</span>
                                </el-col>
                                <el-col :span="12">
                                    <el-input-number v-model="createForm.intervalMinutes" :min="0" :max="59" />
                                    <span class="unit">分钟</span>
                                </el-col>
                            </el-row>
                        </el-form-item>
                        
                        <el-form-item v-if="createForm.type === 'report'" label="报表类型">
                            <el-select v-model="createForm.reportType" style="width: 100%">
                                <el-option label="日报表" value="daily" />
                                <el-option label="周报表" value="weekly" />
                                <el-option label="月报表" value="monthly" />
                            </el-select>
                        </el-form-item>
                        
                        <el-form-item>
                            <el-button type="primary" @click="handleCreateJob" :loading="schedulerStore.creating">
                                创建任务
                            </el-button>
                        </el-form-item>
                    </el-form>
                </el-card>
                
                <el-card class="last-check-card">
                    <template #header>
                        <span>最近检查结果</span>
                    </template>
                    
                    <div v-if="schedulerStore.lastResult" class="check-result">
                        <div class="result-header">
                            <el-tag :type="schedulerStore.getStatusType(schedulerStore.lastResult.status)" size="large">
                                {{ schedulerStore.getStatusText(schedulerStore.lastResult.status) }}
                            </el-tag>
                            <span class="check-time">{{ schedulerStore.formatTime(schedulerStore.lastResult.timestamp) }}</span>
                        </div>
                        
                        <div class="issues-list" v-if="schedulerStore.lastResult.issues && schedulerStore.lastResult.issues.length">
                            <div class="issues-title">发现问题：</div>
                            <ul>
                                <li v-for="(issue, index) in schedulerStore.lastResult.issues" :key="index">
                                    {{ issue }}
                                </li>
                            </ul>
                        </div>
                        
                        <div v-else class="no-issues">
                            <el-icon color="#67C23A" size="20"><CircleCheck /></el-icon>
                            <span>系统运行正常</span>
                        </div>
                    </div>
                    
                    <el-empty v-else description="暂无检查记录" />
                </el-card>
            </el-col>
        </el-row>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useSchedulerStore } from '@/stores/scheduler'

const schedulerStore = useSchedulerStore()

const createForm = ref({
    type: 'health-check',
    mode: 'cron',
    cronExpression: '0 9 * * *',
    intervalHours: 0,
    intervalMinutes: 30,
    reportType: 'daily'
})

const handleCreateJob = () => {
    schedulerStore.createJob(createForm.value)
}

onMounted(() => {
    schedulerStore.fetchJobs()
})
</script>

<style lang="scss" scoped>
.scheduler-container {
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .form-tip {
        font-size: 12px;
        color: #909399;
        margin-top: 5px;
    }
    
    .unit {
        margin-left: 5px;
        color: #606266;
    }
    
    .last-check-card {
        margin-top: 20px;
    }
    
    .check-result {
        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            
            .check-time {
                font-size: 12px;
                color: #909399;
            }
        }
        
        .issues-list {
            .issues-title {
                font-weight: 500;
                margin-bottom: 10px;
            }
            
            ul {
                padding-left: 20px;
                color: #E6A23C;
                
                li {
                    margin-bottom: 5px;
                }
            }
        }
        
        .no-issues {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #67C23A;
        }
    }
}
</style>
