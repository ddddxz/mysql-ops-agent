"""
定时任务定义

定义各种定时任务：
- 健康检查任务
- 报表生成任务
"""

import json
from datetime import datetime
from typing import Any, Optional

from utils import get_logger
from utils.database import get_database
from scheduler.notifier import get_notifier
from db import Report, HealthCheckLog, AlertRecord, JobLog, get_session_factory

logger = get_logger(__name__)


class HealthCheckTask:
    """
    健康检查任务
    
    定期检查 MySQL 健康状态，发现问题发送告警通知。
    """
    
    def __init__(self):
        self._last_result: dict | None = None
    
    async def run(
        self,
        notify_on_warning: bool = True,
        notify_on_error: bool = True,
    ) -> dict[str, Any]:
        """
        执行健康检查
        
        Args:
            notify_on_warning: 发现警告时是否通知
            notify_on_error: 发现错误时是否通知
            
        Returns:
            检查结果
        """
        logger.info("开始执行定时健康检查...")
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "checks": {},
            "issues": [],
        }
        
        try:
            db = get_database()
            
            connection_result = self._check_connections(db)
            result["checks"]["connection"] = connection_result
            if connection_result.get("status") != "ok":
                result["issues"].extend(connection_result.get("issues", []))
            
            buffer_result = self._check_buffer_pool(db)
            result["checks"]["buffer_pool"] = buffer_result
            if buffer_result.get("status") != "ok":
                result["issues"].extend(buffer_result.get("issues", []))
            
            slow_query_result = self._check_slow_queries(db)
            result["checks"]["slow_queries"] = slow_query_result
            if slow_query_result.get("status") != "ok":
                result["issues"].extend(slow_query_result.get("issues", []))
            
            lock_result = self._check_locks(db)
            result["checks"]["locks"] = lock_result
            if lock_result.get("status") != "ok":
                result["issues"].extend(lock_result.get("issues", []))
            
            replication_result = self._check_replication(db)
            result["checks"]["replication"] = replication_result
            if replication_result.get("status") != "ok":
                result["issues"].extend(replication_result.get("issues", []))
            
            if result["issues"]:
                if any("错误" in issue or "失败" in issue for issue in result["issues"]):
                    result["status"] = "error"
                else:
                    result["status"] = "warning"
            
            self._last_result = result
            
            self._save_check_result(result)
            
            if result["status"] != "healthy":
                if (result["status"] == "error" and notify_on_error) or \
                   (result["status"] == "warning" and notify_on_warning):
                    await self._send_notification(result)
            
            logger.info(f"健康检查完成: {result['status']}, 发现 {len(result['issues'])} 个问题")
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            result["issues"].append(f"健康检查执行失败: {e}")
            logger.error(f"健康检查执行失败: {e}")
            
            self._save_check_result(result)
            
            if notify_on_error:
                await self._send_notification(result)
        
        return result
    
    def _check_connections(self, db) -> dict:
        """检查连接状态"""
        try:
            status = db.get_status_variables()
            variables = db.get_system_variables()
            
            threads_connected = int(status.get("Threads_connected", 0))
            max_connections = int(variables.get("max_connections", 0))
            
            usage_percent = (threads_connected / max_connections * 100) if max_connections > 0 else 0
            
            issues = []
            status_text = "ok"
            
            if usage_percent > 90:
                issues.append(f"连接使用率过高: {usage_percent:.1f}% ({threads_connected}/{max_connections})")
                status_text = "error"
            elif usage_percent > 80:
                issues.append(f"连接使用率较高: {usage_percent:.1f}% ({threads_connected}/{max_connections})")
                status_text = "warning"
            
            return {
                "status": status_text,
                "threads_connected": threads_connected,
                "max_connections": max_connections,
                "usage_percent": round(usage_percent, 2),
                "issues": issues,
            }
        except Exception as e:
            return {"status": "error", "issues": [f"连接检查失败: {e}"]}
    
    def _check_buffer_pool(self, db) -> dict:
        """检查缓冲池状态"""
        try:
            status = db.get_status_variables()
            
            read_requests = int(status.get("Innodb_buffer_pool_read_requests", 0))
            reads = int(status.get("Innodb_buffer_pool_reads", 0))
            
            hit_rate = (1 - reads / read_requests) * 100 if read_requests > 0 else 100
            
            issues = []
            status_text = "ok"
            
            if hit_rate < 95:
                issues.append(f"缓冲池命中率过低: {hit_rate:.2f}%")
                status_text = "error"
            elif hit_rate < 99:
                issues.append(f"缓冲池命中率较低: {hit_rate:.2f}%")
                status_text = "warning"
            
            return {
                "status": status_text,
                "hit_rate": round(hit_rate, 2),
                "read_requests": read_requests,
                "reads": reads,
                "issues": issues,
            }
        except Exception as e:
            return {"status": "error", "issues": [f"缓冲池检查失败: {e}"]}
    
    def _check_slow_queries(self, db) -> dict:
        """检查慢查询"""
        try:
            status = db.get_status_variables()
            
            slow_queries = int(status.get("Slow_queries", 0))
            
            issues = []
            status_text = "ok"
            
            if slow_queries > 100:
                issues.append(f"慢查询数量过多: {slow_queries}")
                status_text = "warning"
            
            return {
                "status": status_text,
                "slow_queries": slow_queries,
                "issues": issues,
            }
        except Exception as e:
            return {"status": "error", "issues": [f"慢查询检查失败: {e}"]}
    
    def _check_locks(self, db) -> dict:
        """检查锁等待"""
        try:
            status = db.get_status_variables()
            
            table_locks_waited = int(status.get("Table_locks_waited", 0))
            innodb_row_lock_waits = int(status.get("Innodb_row_lock_waits", 0))
            
            issues = []
            status_text = "ok"
            
            if table_locks_waited > 100:
                issues.append(f"表锁等待过多: {table_locks_waited}")
                status_text = "warning"
            
            if innodb_row_lock_waits > 100:
                issues.append(f"行锁等待过多: {innodb_row_lock_waits}")
                status_text = "warning"
            
            return {
                "status": status_text,
                "table_locks_waited": table_locks_waited,
                "innodb_row_lock_waits": innodb_row_lock_waits,
                "issues": issues,
            }
        except Exception as e:
            return {"status": "error", "issues": [f"锁检查失败: {e}"]}
    
    def _check_replication(self, db) -> dict:
        """检查复制状态"""
        try:
            result = db.execute_query("SHOW SLAVE STATUS")
            
            if not result:
                return {
                    "status": "ok",
                    "replication_enabled": False,
                    "issues": [],
                }
            
            issues = []
            status_text = "ok"
            
            slave_io_running = result[0].get("Slave_IO_Running", "No")
            slave_sql_running = result[0].get("Slave_SQL_Running", "No")
            seconds_behind = int(result[0].get("Seconds_Behind_Master", 0) or 0)
            
            if slave_io_running != "Yes" or slave_sql_running != "Yes":
                issues.append(f"复制线程异常: IO={slave_io_running}, SQL={slave_sql_running}")
                status_text = "error"
            elif seconds_behind > 60:
                issues.append(f"复制延迟过高: {seconds_behind} 秒")
                status_text = "warning"
            
            return {
                "status": status_text,
                "replication_enabled": True,
                "slave_io_running": slave_io_running,
                "slave_sql_running": slave_sql_running,
                "seconds_behind": seconds_behind,
                "issues": issues,
            }
        except Exception as e:
            return {"status": "ok", "replication_enabled": False, "issues": []}
    
    def _save_check_result(self, result: dict) -> None:
        """保存检查结果到数据库"""
        factory = get_session_factory()
        session = factory()
        
        try:
            log = HealthCheckLog(
                status=result["status"],
                issues=json.dumps(result.get("issues", []), ensure_ascii=False),
                metrics=json.dumps(result.get("checks", {}), ensure_ascii=False),
            )
            session.add(log)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"保存健康检查结果失败: {e}")
        finally:
            session.close()
    
    async def _send_notification(self, result: dict) -> None:
        """发送告警通知"""
        try:
            self._save_alert(result)
            
            notifier = get_notifier()
            await notifier.send_health_alert(result)
        except Exception as e:
            logger.error(f"发送告警通知失败: {e}")
    
    def _save_alert(self, result: dict) -> None:
        """保存告警记录到数据库"""
        factory = get_session_factory()
        session = factory()
        
        try:
            level = "critical" if result["status"] == "error" else "warning"
            
            alert = AlertRecord(
                alert_type="health_check",
                level=level,
                title=f"MySQL健康检查告警: {result['status']}",
                content=json.dumps(result, ensure_ascii=False),
            )
            session.add(alert)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"保存告警记录失败: {e}")
        finally:
            session.close()
    
    def get_last_result(self) -> dict | None:
        """获取最后一次检查结果"""
        return self._last_result
    
    def get_history(self, limit: int = 10) -> list[dict]:
        """从数据库获取检查历史"""
        factory = get_session_factory()
        session = factory()
        
        try:
            logs = session.query(HealthCheckLog).order_by(
                HealthCheckLog.checked_at.desc()
            ).limit(limit).all()
            
            return [
                {
                    "timestamp": log.checked_at.isoformat() if log.checked_at else None,
                    "status": log.status,
                    "issues": json.loads(log.issues) if log.issues else [],
                    "checks": json.loads(log.metrics) if log.metrics else {},
                }
                for log in logs
            ]
        finally:
            session.close()


class ReportTask:
    """
    报表生成任务
    
    定期生成健康检查报表。
    """
    
    async def run(self, report_type: str = "daily") -> dict[str, Any]:
        """
        生成报表
        
        Args:
            report_type: 报表类型 (daily/weekly/monthly)
            
        Returns:
            报表信息
        """
        logger.info(f"开始生成{report_type}报表...")
        
        try:
            db = get_database()
            
            report_data = {
                "report_type": report_type,
                "generated_at": datetime.now().isoformat(),
                "server_info": self._get_server_info(db),
                "status_variables": self._get_status_summary(db),
                "health_metrics": await self._get_health_metrics(db),
            }
            
            title = f"MySQL运维报表 - {report_type} - {datetime.now().strftime('%Y-%m-%d')}"
            
            report_id = self._save_report(report_type, title, report_data)
            
            logger.info(f"报表生成完成: ID={report_id}")
            
            return {
                "status": "success",
                "report_id": report_id,
                "report_type": report_type,
                "title": title,
                "generated_at": report_data["generated_at"],
            }
            
        except Exception as e:
            logger.error(f"报表生成失败: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
    
    def _save_report(self, report_type: str, title: str, data: dict) -> int:
        """保存报表到数据库"""
        factory = get_session_factory()
        session = factory()
        
        try:
            report = Report(
                report_type=report_type,
                title=title,
                content=json.dumps(data, ensure_ascii=False),
            )
            session.add(report)
            session.commit()
            
            return report.id
        except Exception as e:
            session.rollback()
            logger.error(f"保存报表失败: {e}")
            raise
        finally:
            session.close()
    
    def _get_server_info(self, db) -> dict:
        """获取服务器信息"""
        try:
            result = db.execute_query("SELECT VERSION() as version")
            version = result[0]["version"] if result else "unknown"
            
            variables = db.get_system_variables()
            
            return {
                "version": version,
                "hostname": variables.get("hostname", "unknown"),
                "port": variables.get("port", "3306"),
                "datadir": variables.get("datadir", "unknown"),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_status_summary(self, db) -> dict:
        """获取状态摘要"""
        try:
            status = db.get_status_variables()
            
            return {
                "uptime": status.get("Uptime", "0"),
                "queries": status.get("Queries", "0"),
                "connections": status.get("Connections", "0"),
                "slow_queries": status.get("Slow_queries", "0"),
                "bytes_received": status.get("Bytes_received", "0"),
                "bytes_sent": status.get("Bytes_sent", "0"),
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_health_metrics(self, db) -> dict:
        """获取健康指标"""
        try:
            status = db.get_status_variables()
            variables = db.get_system_variables()
            
            threads_connected = int(status.get("Threads_connected", 0))
            max_connections = int(variables.get("max_connections", 0))
            
            read_requests = int(status.get("Innodb_buffer_pool_read_requests", 0))
            reads = int(status.get("Innodb_buffer_pool_reads", 0))
            hit_rate = (1 - reads / read_requests) * 100 if read_requests > 0 else 100
            
            return {
                "connection_usage": f"{threads_connected}/{max_connections}",
                "connection_usage_percent": round(threads_connected / max_connections * 100, 2) if max_connections > 0 else 0,
                "buffer_pool_hit_rate": round(hit_rate, 2),
                "table_locks_waited": int(status.get("Table_locks_waited", 0)),
                "innodb_row_lock_waits": int(status.get("Innodb_row_lock_waits", 0)),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def list_reports(self, limit: int = 20) -> list[dict]:
        """从数据库列出所有报表"""
        factory = get_session_factory()
        session = factory()
        
        try:
            reports = session.query(Report).order_by(
                Report.created_at.desc()
            ).limit(limit).all()
            
            return [
                {
                    "id": report.id,
                    "report_type": report.report_type,
                    "title": report.title,
                    "generated_at": report.created_at.isoformat() if report.created_at else None,
                }
                for report in reports
            ]
        finally:
            session.close()
    
    def get_report(self, report_id: int) -> dict | None:
        """从数据库获取报表内容"""
        factory = get_session_factory()
        session = factory()
        
        try:
            report = session.query(Report).filter(Report.id == report_id).first()
            
            if not report:
                return None
            
            return {
                "id": report.id,
                "report_type": report.report_type,
                "title": report.title,
                "generated_at": report.created_at.isoformat() if report.created_at else None,
                "content": json.loads(report.content) if report.content else {},
            }
        finally:
            session.close()


class JobLogManager:
    """任务日志管理器"""
    
    @staticmethod
    def log_job_start(job_id: str, job_type: str) -> None:
        """记录任务开始"""
        factory = get_session_factory()
        session = factory()
        
        try:
            log = JobLog(
                job_id=job_id,
                job_type=job_type,
                status="running",
                started_at=datetime.now(),
            )
            session.add(log)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"记录任务开始失败: {e}")
        finally:
            session.close()
    
    @staticmethod
    def log_job_finish(job_id: str, status: str, result: Optional[str] = None, error: Optional[str] = None) -> None:
        """记录任务完成"""
        factory = get_session_factory()
        session = factory()
        
        try:
            log = session.query(JobLog).filter(JobLog.job_id == job_id).order_by(
                JobLog.created_at.desc()
            ).first()
            
            if log:
                log.status = status
                log.result = result
                log.error_message = error
                log.finished_at = datetime.now()
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"记录任务完成失败: {e}")
        finally:
            session.close()
    
    @staticmethod
    def get_job_logs(job_type: Optional[str] = None, limit: int = 50) -> list[dict]:
        """获取任务日志"""
        factory = get_session_factory()
        session = factory()
        
        try:
            query = session.query(JobLog)
            
            if job_type:
                query = query.filter(JobLog.job_type == job_type)
            
            logs = query.order_by(JobLog.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": log.id,
                    "job_id": log.job_id,
                    "job_type": log.job_type,
                    "status": log.status,
                    "result": log.result,
                    "error_message": log.error_message,
                    "started_at": log.started_at.isoformat() if log.started_at else None,
                    "finished_at": log.finished_at.isoformat() if log.finished_at else None,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ]
        finally:
            session.close()
