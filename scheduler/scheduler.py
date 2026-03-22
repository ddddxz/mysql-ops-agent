"""
定时任务调度器

基于 APScheduler 实现定时任务管理。
"""

from datetime import datetime
from typing import Callable
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from utils import get_logger

logger = get_logger(__name__)


class SchedulerManager:
    """
    定时任务调度管理器
    
    支持定时任务：
    - 定时健康检查
    - 定时报表生成
    - 告警检查
    """
    
    def __init__(self):
        self._scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            executors={"default": ThreadPoolExecutor(max_workers=3)},
            timezone="Asia/Shanghai",
        )
        self._jobs: dict[str, dict] = {}
    
    def start(self) -> None:
        """启动调度器"""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("定时任务调度器已启动")
    
    def stop(self) -> None:
        """停止调度器"""
        if self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("定时任务调度器已停止")
    
    def add_cron_job(
        self,
        job_id: str,
        func: Callable,
        cron_expr: str,
        **kwargs,
    ) -> bool:
        """
        添加 Cron 定时任务
        
        Args:
            job_id: 任务 ID
            func: 任务函数
            cron_expr: Cron 表达式 (如 "0 9 * * *" 表示每天 9:00)
            **kwargs: 传递给任务函数的参数
            
        Returns:
            是否添加成功
        """
        try:
            parts = cron_expr.split()
            if len(parts) != 5:
                raise ValueError(f"无效的 Cron 表达式: {cron_expr}")
            
            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
            )
            
            self._scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                kwargs=kwargs,
                replace_existing=True,
            )
            
            self._jobs[job_id] = {
                "type": "cron",
                "expression": cron_expr,
                "func": func.__name__,
                "created_at": datetime.now(),
            }
            
            logger.info(f"添加 Cron 任务: {job_id} ({cron_expr})")
            return True
            
        except Exception as e:
            logger.error(f"添加 Cron 任务失败: {job_id} - {e}")
            return False
    
    def add_interval_job(
        self,
        job_id: str,
        func: Callable,
        minutes: int = 0,
        hours: int = 0,
        **kwargs,
    ) -> bool:
        """
        添加间隔任务
        
        Args:
            job_id: 任务 ID
            func: 任务函数
            minutes: 间隔分钟数
            hours: 间隔小时数
            **kwargs: 传递给任务函数的参数
            
        Returns:
            是否添加成功
        """
        try:
            trigger = IntervalTrigger(hours=hours, minutes=minutes)
            
            self._scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                kwargs=kwargs,
                replace_existing=True,
            )
            
            self._jobs[job_id] = {
                "type": "interval",
                "hours": hours,
                "minutes": minutes,
                "func": func.__name__,
                "created_at": datetime.now(),
            }
            
            logger.info(f"添加间隔任务: {job_id} (每 {hours}h {minutes}m)")
            return True
            
        except Exception as e:
            logger.error(f"添加间隔任务失败: {job_id} - {e}")
            return False
    
    def remove_job(self, job_id: str) -> bool:
        """
        移除任务
        
        Args:
            job_id: 任务 ID
            
        Returns:
            是否移除成功
        """
        try:
            self._scheduler.remove_job(job_id)
            if job_id in self._jobs:
                del self._jobs[job_id]
            logger.info(f"移除任务: {job_id}")
            return True
        except Exception as e:
            logger.error(f"移除任务失败: {job_id} - {e}")
            return False
    
    def pause_job(self, job_id: str) -> bool:
        """暂停任务"""
        try:
            self._scheduler.pause_job(job_id)
            logger.info(f"暂停任务: {job_id}")
            return True
        except Exception as e:
            logger.error(f"暂停任务失败: {job_id} - {e}")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """恢复任务"""
        try:
            self._scheduler.resume_job(job_id)
            logger.info(f"恢复任务: {job_id}")
            return True
        except Exception as e:
            logger.error(f"恢复任务失败: {job_id} - {e}")
            return False
    
    def get_jobs(self) -> list[dict]:
        """获取所有任务列表"""
        jobs = []
        for job_id, info in self._jobs.items():
            job = self._scheduler.get_job(job_id)
            jobs.append({
                "job_id": job_id,
                "next_run_time": job.next_run_time if job else None,
                **info,
            })
        return jobs
    
    def get_job(self, job_id: str) -> dict | None:
        """获取单个任务信息"""
        if job_id not in self._jobs:
            return None
        
        job = self._scheduler.get_job(job_id)
        return {
            "job_id": job_id,
            "next_run_time": job.next_run_time if job else None,
            **self._jobs[job_id],
        }
    
    def trigger_job(self, job_id: str) -> bool:
        """立即触发任务"""
        try:
            self._scheduler.get_job(job_id).modify(next_run_time=datetime.now())
            logger.info(f"立即触发任务: {job_id}")
            return True
        except Exception as e:
            logger.error(f"触发任务失败: {job_id} - {e}")
            return False


_scheduler_manager: SchedulerManager | None = None


def get_scheduler() -> SchedulerManager:
    """获取调度器实例（单例）"""
    global _scheduler_manager
    if _scheduler_manager is None:
        _scheduler_manager = SchedulerManager()
    return _scheduler_manager
