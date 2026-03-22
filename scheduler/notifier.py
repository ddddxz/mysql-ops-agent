"""
告警通知模块

支持多种通知方式：
- QQ 邮件通知
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Any
from dotenv import load_dotenv

from utils import get_logger

load_dotenv()

logger = get_logger(__name__)


class EmailNotifier:
    """
    邮件通知器
    
    使用 QQ 邮箱发送告警通知。
    """
    
    def __init__(
        self,
        smtp_server: str = "smtp.qq.com",
        smtp_port: int = 465,
        sender_email: str | None = None,
        sender_password: str | None = None,
        receiver_emails: list[str] | None = None,
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email or os.getenv("QQ_EMAIL")
        self.sender_password = sender_password or os.getenv("QQ_EMAIL_PASSWORD")
        self.receiver_emails = receiver_emails or self._get_default_receivers()
    
    def _get_default_receivers(self) -> list[str]:
        """获取默认接收者列表"""
        receivers = os.getenv("ALERT_EMAIL_RECEIVERS", "")
        if receivers:
            return [r.strip() for r in receivers.split(",") if r.strip()]
        return []
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.sender_email and self.sender_password and self.receiver_emails)
    
    async def send_email(
        self,
        subject: str,
        content: str,
        html_content: str | None = None,
    ) -> bool:
        """
        发送邮件
        
        Args:
            subject: 邮件主题
            content: 纯文本内容
            html_content: HTML 内容（可选）
            
        Returns:
            是否发送成功
        """
        if not self.is_configured():
            logger.warning("邮件通知未配置，跳过发送")
            return False
        
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = ", ".join(self.receiver_emails)
            
            message.attach(MIMEText(content, "plain", "utf-8"))
            
            if html_content:
                message.attach(MIMEText(html_content, "html", "utf-8"))
            
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.sender_email, self.sender_password)
                server.sendmail(
                    self.sender_email,
                    self.receiver_emails,
                    message.as_string(),
                )
            
            logger.info(f"邮件发送成功: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    async def send_health_alert(self, result: dict[str, Any]) -> bool:
        """
        发送健康检查告警邮件
        
        Args:
            result: 健康检查结果
            
        Returns:
            是否发送成功
        """
        status = result.get("status", "unknown")
        issues = result.get("issues", [])
        timestamp = result.get("timestamp", datetime.now().isoformat())
        
        status_emoji = {"healthy": "✅", "warning": "⚠️", "error": "❌"}.get(status, "❓")
        
        subject = f"【MySQL 告警】{status_emoji} 健康检查发现 {len(issues)} 个问题"
        
        text_content = f"""
MySQL 健康检查告警通知

检查时间: {timestamp}
检查状态: {status.upper()}
发现问题: {len(issues)} 个

问题详情:
{chr(10).join(f"- {issue}" for issue in issues)}

检查项目详情:
{self._format_checks_text(result.get("checks", {}))}

---
此邮件由 MySQL 智能运维系统自动发送
""".strip()
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
        .status {{ padding: 10px 20px; border-radius: 5px; font-weight: bold; display: inline-block; margin: 10px 0; }}
        .status-error {{ background: #fee; color: #c00; }}
        .status-warning {{ background: #ffe; color: #c80; }}
        .status-healthy {{ background: #efe; color: #0a0; }}
        .issue-list {{ background: white; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        .issue-item {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
        .check-item {{ background: white; padding: 10px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #667eea; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🏥 MySQL 健康检查告警</h2>
            <p>检查时间: {timestamp}</p>
        </div>
        <div class="content">
            <div class="status status-{status}">
                状态: {status.upper()} - 发现 {len(issues)} 个问题
            </div>
            
            <h3>⚠️ 问题列表</h3>
            <div class="issue-list">
                {"".join(f'<div class="issue-item">• {issue}</div>' for issue in issues)}
            </div>
            
            <h3>📊 检查详情</h3>
            {self._format_checks_html(result.get("checks", {}))}
        </div>
        <div class="footer">
            此邮件由 MySQL 智能运维系统自动发送<br>
            请勿直接回复
        </div>
    </div>
</body>
</html>
""".strip()
        
        return await self.send_email(subject, text_content, html_content)
    
    def _format_checks_text(self, checks: dict) -> str:
        """格式化检查结果（文本）"""
        lines = []
        for name, data in checks.items():
            status = data.get("status", "unknown")
            lines.append(f"\n[{name}] 状态: {status}")
            for key, value in data.items():
                if key != "status" and key != "issues":
                    lines.append(f"  - {key}: {value}")
        return "\n".join(lines)
    
    def _format_checks_html(self, checks: dict) -> str:
        """格式化检查结果（HTML）"""
        html = ""
        for name, data in checks.items():
            status = data.get("status", "unknown")
            status_class = f"status-{status}"
            
            details = ""
            for key, value in data.items():
                if key != "status" and key != "issues":
                    details += f"<div><strong>{key}:</strong> {value}</div>"
            
            html += f"""
            <div class="check-item">
                <div class="status {status_class}" style="font-size: 12px;">{name}: {status}</div>
                {details}
            </div>
            """
        return html


class Notifier:
    """
    统一通知管理器
    
    支持多种通知渠道。
    """
    
    def __init__(self):
        self._email = EmailNotifier()
    
    @property
    def email(self) -> EmailNotifier:
        """获取邮件通知器"""
        return self._email
    
    async def send_health_alert(self, result: dict[str, Any]) -> dict[str, bool]:
        """
        发送健康检查告警（所有渠道）
        
        Args:
            result: 健康检查结果
            
        Returns:
            各渠道发送结果
        """
        results = {}
        
        if self._email.is_configured():
            results["email"] = await self._email.send_health_alert(result)
        else:
            logger.warning("邮件通知未配置")
            results["email"] = False
        
        return results


_notifier: Notifier | None = None


def get_notifier() -> Notifier:
    """获取通知器实例（单例）"""
    global _notifier
    if _notifier is None:
        _notifier = Notifier()
    return _notifier
