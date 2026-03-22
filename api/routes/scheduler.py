"""
定时任务管理接口

提供定时任务的 CRUD 操作。
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from scheduler import get_scheduler, HealthCheckTask, ReportTask
from utils import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/scheduler", tags=["定时任务"])

_health_task = HealthCheckTask()
_report_task = ReportTask()


class CreateJobRequest(BaseModel):
    """创建任务请求"""
    job_type: str
    cron_expression: Optional[str] = None
    interval_minutes: Optional[int] = None
    interval_hours: Optional[int] = None


class JobResponse(BaseModel):
    """任务响应"""
    job_id: str
    status: str
    message: str


@router.get("/jobs", summary="获取所有定时任务")
async def list_jobs() -> list[dict]:
    """获取所有定时任务列表"""
    scheduler = get_scheduler()
    return scheduler.get_jobs()


@router.get("/job/{job_id}", summary="获取任务详情")
async def get_job(job_id: str) -> dict:
    """获取单个任务详情"""
    scheduler = get_scheduler()
    job = scheduler.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "任务不存在", "details": f"Job {job_id} not found"}
        )
    
    return job


@router.post("/job/health-check", summary="创建健康检查任务")
async def create_health_check_job(
    cron_expression: str = Query("0 9 * * *", description="Cron 表达式，默认每天 9:00"),
) -> JobResponse:
    """
    创建定时健康检查任务
    
    Cron 表达式格式: 分 时 日 月 周
    - "0 9 * * *" - 每天 9:00
    - "0 */2 * * *" - 每 2 小时
    - "30 8 * * 1-5" - 周一到周五 8:30
    """
    scheduler = get_scheduler()
    
    success = scheduler.add_cron_job(
        job_id="health_check",
        func=_health_task.run,
        cron_expr=cron_expression,
        notify_on_warning=True,
        notify_on_error=True,
    )
    
    if success:
        return JobResponse(
            job_id="health_check",
            status="created",
            message=f"健康检查任务已创建，执行时间: {cron_expression}",
        )
    else:
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "message": "创建任务失败"}
        )


@router.post("/job/report", summary="创建报表生成任务")
async def create_report_job(
    report_type: str = Query("daily", description="报表类型: daily/weekly/monthly"),
    cron_expression: str = Query("0 18 * * *", description="Cron 表达式，默认每天 18:00"),
) -> JobResponse:
    """
    创建定时报表生成任务
    
    报表类型:
    - daily: 日报表
    - weekly: 周报表
    - monthly: 月报表
    """
    scheduler = get_scheduler()
    
    job_id = f"report_{report_type}"
    
    success = scheduler.add_cron_job(
        job_id=job_id,
        func=_report_task.run,
        cron_expr=cron_expression,
        report_type=report_type,
    )
    
    if success:
        return JobResponse(
            job_id=job_id,
            status="created",
            message=f"报表生成任务已创建，类型: {report_type}，执行时间: {cron_expression}",
        )
    else:
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "message": "创建任务失败"}
        )


@router.post("/job/interval", summary="创建间隔任务")
async def create_interval_job(
    job_type: str = Query(..., description="任务类型: health_check/report"),
    minutes: int = Query(0, ge=0, description="间隔分钟数"),
    hours: int = Query(0, ge=0, description="间隔小时数"),
) -> JobResponse:
    """创建间隔执行任务"""
    if minutes == 0 and hours == 0:
        raise HTTPException(
            status_code=400,
            detail={"code": 400, "message": "必须指定间隔时间"}
        )
    
    scheduler = get_scheduler()
    
    job_id = f"{job_type}_interval"
    
    if job_type == "health_check":
        func = _health_task.run
    elif job_type == "report":
        func = _report_task.run
    else:
        raise HTTPException(
            status_code=400,
            detail={"code": 400, "message": "不支持的任务类型"}
        )
    
    success = scheduler.add_interval_job(
        job_id=job_id,
        func=func,
        minutes=minutes,
        hours=hours,
    )
    
    if success:
        return JobResponse(
            job_id=job_id,
            status="created",
            message=f"间隔任务已创建，每 {hours}h {minutes}m 执行一次",
        )
    else:
        raise HTTPException(
            status_code=500,
            detail={"code": 500, "message": "创建任务失败"}
        )


@router.delete("/job/{job_id}", summary="删除任务")
async def delete_job(job_id: str) -> JobResponse:
    """删除定时任务"""
    scheduler = get_scheduler()
    
    success = scheduler.remove_job(job_id)
    
    if success:
        return JobResponse(
            job_id=job_id,
            status="deleted",
            message="任务已删除",
        )
    else:
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "任务不存在"}
        )


@router.post("/job/{job_id}/pause", summary="暂停任务")
async def pause_job(job_id: str) -> JobResponse:
    """暂停定时任务"""
    scheduler = get_scheduler()
    
    success = scheduler.pause_job(job_id)
    
    if success:
        return JobResponse(
            job_id=job_id,
            status="paused",
            message="任务已暂停",
        )
    else:
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "任务不存在"}
        )


@router.post("/job/{job_id}/resume", summary="恢复任务")
async def resume_job(job_id: str) -> JobResponse:
    """恢复定时任务"""
    scheduler = get_scheduler()
    
    success = scheduler.resume_job(job_id)
    
    if success:
        return JobResponse(
            job_id=job_id,
            status="resumed",
            message="任务已恢复",
        )
    else:
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "任务不存在"}
        )


@router.post("/job/{job_id}/trigger", summary="立即执行任务")
async def trigger_job(job_id: str) -> JobResponse:
    """立即触发任务执行"""
    scheduler = get_scheduler()
    
    success = scheduler.trigger_job(job_id)
    
    if success:
        return JobResponse(
            job_id=job_id,
            status="triggered",
            message="任务已触发执行",
        )
    else:
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "任务不存在"}
        )


@router.post("/health-check/run", summary="立即执行健康检查")
async def run_health_check() -> dict:
    """立即执行一次健康检查"""
    result = await _health_task.run(
        notify_on_warning=True,
        notify_on_error=True,
    )
    return result


@router.get("/health-check/history", summary="获取健康检查历史")
async def get_health_check_history(limit: int = Query(10, ge=1, le=100)) -> list[dict]:
    """获取健康检查历史记录"""
    return _health_task.get_history(limit)


@router.post("/report/generate", summary="立即生成报表")
async def generate_report(report_type: str = Query("daily", description="报表类型")) -> dict:
    """立即生成一份报表"""
    result = await _report_task.run(report_type)
    return result


@router.get("/report/list", summary="获取报表列表")
async def list_reports(limit: int = Query(20, ge=1, le=100)) -> list[dict]:
    """获取报表文件列表"""
    return _report_task.list_reports(limit)


@router.get("/report/{report_id}", summary="获取报表内容")
async def get_report(report_id: int) -> dict:
    """获取指定报表的内容"""
    report = _report_task.get_report(report_id)
    
    if not report:
        raise HTTPException(
            status_code=404,
            detail={"code": 404, "message": "报表不存在"}
        )
    
    return report
