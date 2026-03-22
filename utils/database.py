"""
数据库连接工具

提供 MySQL 数据库连接和查询功能。
"""


# 通过 @contextmanager 装饰器将生成器函数变成了一个上下文管理器。
# 这样，调用者必须使用 with 语句来使用它
from contextlib import contextmanager
from typing import Any, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseConnection:
    """
    MySQL 数据库连接管理器
    
    提供安全的数据库连接和查询执行功能。
    """
    
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
    ) -> None:
        self._host = host or settings.mysql_host
        self._port = port or settings.mysql_port
        self._user = user or settings.mysql_user
        self._password = password or settings.mysql_password
        self._database = database or settings.mysql_database
        self._engine: Engine | None = None
    
    @property
    def engine(self) -> Engine:
        """获取数据库引擎"""
        if self._engine is None:
            dsn = f"mysql+pymysql://{self._user}:{self._password}@{self._host}:{self._port}/{self._database}"
            self._engine = create_engine(
                dsn,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False,
            )
        return self._engine
    
    @contextmanager
    def get_connection(self) -> Generator[Connection, None, None]:
        """获取数据库连接（上下文管理器）"""
        conn = self.engine.connect()
        try:
            yield conn
        finally:
            conn.close()
    
    def connect(self) -> bool:
        """测试连接"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(f"MySQL 连接成功: {self._host}:{self._port}/{self._database}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"MySQL 连接失败: {e}")
            return False
    
    def execute_query(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        执行查询 SQL
        
        Args:
            sql: SQL 查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        with self.get_connection() as conn:
            result = conn.execute(text(sql), params or {})
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
    
    def get_status_variables(self) -> dict[str, Any]:
        """获取 MySQL 状态变量"""
        results = self.execute_query("SHOW GLOBAL STATUS")
        return {row["Variable_name"]: row["Value"] for row in results}
    
    def get_system_variables(self) -> dict[str, Any]:
        """获取 MySQL 系统变量"""
        results = self.execute_query("SHOW GLOBAL VARIABLES")
        return {row["Variable_name"]: row["Value"] for row in results}
    
    def get_process_list(self) -> list[dict[str, Any]]:
        """获取当前连接列表"""
        return self.execute_query("SHOW PROCESSLIST")
    
    def get_table_sizes(self, database: str | None = None) -> list[dict[str, Any]]:
        """获取表大小信息"""
        db = database or self._database
        sql = """
        SELECT 
            TABLE_NAME as table_name,
            TABLE_ROWS as table_rows,
            DATA_LENGTH as data_length,
            INDEX_LENGTH as index_length,
            DATA_FREE as data_free
        FROM information_schema.TABLES 
        WHERE TABLE_SCHEMA = :db
        ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC
        LIMIT 20
        """
        return self.execute_query(sql, {"db": db})
    
    def close(self) -> None:
        """关闭连接"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            logger.info("MySQL 连接已关闭")


_db: DatabaseConnection | None = None


def get_database() -> DatabaseConnection:
    """获取数据库连接实例（单例）"""
    global _db
    if _db is None:
        _db = DatabaseConnection()
    return _db
