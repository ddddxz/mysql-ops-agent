"""
MCP 服务器

使用 MCP 原生协议，定义 MySQL 运维工具。
支持 stdio 传输，可被任何 MCP 客户端调用。

安装: pip install "mcp[cli]"
运行: python -m agent.mcp_server
"""

import os
os.environ["MCP_SERVER_MODE"] = "1"

from typing import Any

from mcp.server.fastmcp import FastMCP

from utils import get_database, get_logger

logger = get_logger(__name__)

mcp = FastMCP("MySQL运维助手")


@mcp.tool()
def collect_metrics(metric_type: str = "all") -> dict[str, Any]:
    """
    收集 MySQL 服务器指标，包括连接数、QPS、缓冲池命中率等。
    
    Args:
        metric_type: 指标类型 (all, connections, buffer, queries)
    
    Returns:
        指标数据字典
    """
    db = get_database()
    status = db.get_status_variables()
    variables = db.get_system_variables()
    
    metrics = {}
    
    if metric_type in ["all", "connections"]:
        threads_connected = int(status.get("Threads_connected", 0))
        max_connections = int(variables.get("max_connections", 0))
        metrics["connections"] = {
            "Threads_connected": threads_connected,
            "max_connections": max_connections,
            "usage_percent": round(threads_connected / max_connections * 100, 2) if max_connections > 0 else 0,
        }
    
    if metric_type in ["all", "buffer"]:
        read_requests = int(status.get("Innodb_buffer_pool_read_requests", 0))
        reads = int(status.get("Innodb_buffer_pool_reads", 0))
        hit_rate = (1 - reads / read_requests) * 100 if read_requests > 0 else 0
        metrics["buffer_pool"] = {"hit_rate_percent": round(hit_rate, 2)}
    
    if metric_type in ["all", "queries"]:
        questions = int(status.get("Questions", 0))
        uptime = int(status.get("Uptime", 1))
        metrics["queries"] = {
            "QPS": round(questions / uptime, 2) if uptime > 0 else 0,
            "Slow_queries": int(status.get("Slow_queries", 0)),
        }
    
    return metrics


@mcp.tool()
def health_check() -> dict[str, Any]:
    """
    检查 MySQL 服务器健康状态。
    
    Returns:
        健康状态信息，包括连接使用率、缓冲池命中率、问题列表
    """
    db = get_database()
    status = db.get_status_variables()
    variables = db.get_system_variables()
    
    threads_connected = int(status.get("Threads_connected", 0))
    max_connections = int(variables.get("max_connections", 0))
    
    read_requests = int(status.get("Innodb_buffer_pool_read_requests", 0))
    reads = int(status.get("Innodb_buffer_pool_reads", 0))
    hit_rate = (1 - reads / read_requests) * 100 if read_requests > 0 else 0
    
    issues = []
    if max_connections > 0 and threads_connected / max_connections > 0.8:
        issues.append("连接数使用率过高")
    if hit_rate < 99:
        issues.append("缓冲池命中率过低")
    
    return {
        "connection_usage": f"{threads_connected}/{max_connections}",
        "buffer_pool_hit_rate": round(hit_rate, 2),
        "issues": issues,
        "status": "健康" if not issues else "需要关注",
    }


@mcp.tool()
def explain_query(sql: str) -> dict[str, Any]:
    """
    分析 SQL 查询的执行计划，提供优化建议。
    
    Args:
        sql: 要分析的 SELECT SQL 语句
    
    Returns:
        执行计划和分析建议
    """
    if not sql.strip().lower().startswith("select"):
        return {"error": "仅支持 SELECT 查询"}
    
    db = get_database()
    result = db.execute_query(f"EXPLAIN {sql}")
    
    analysis = []
    if result:
        row = result[0]
        if row.get("type") == "ALL":
            analysis.append("全表扫描，建议添加索引")
        if not row.get("key"):
            analysis.append("未使用索引")
        if int(row.get("rows", 0)) > 1000:
            analysis.append(f"扫描行数较多: {row.get('rows')}")
    
    return {"explain_result": result, "analysis": analysis}


@mcp.tool()
def analyze_config() -> dict[str, Any]:
    """
    分析 MySQL 配置参数，返回关键配置信息。
    
    Returns:
        配置参数信息
    """
    db = get_database()
    variables = db.get_system_variables()
    status = db.get_status_variables()
    
    buffer_pool_size = int(variables.get("innodb_buffer_pool_size", 0))
    
    return {
        "innodb_buffer_pool_size": f"{buffer_pool_size // 1024 // 1024}M",
        "innodb_log_file_size": f"{int(variables.get('innodb_log_file_size', 0)) // 1024 // 1024}M",
        "max_connections": int(variables.get("max_connections", 0)),
        "current_connections": int(status.get("Threads_connected", 0)),
        "thread_cache_size": int(variables.get("thread_cache_size", 0)),
    }


@mcp.tool()
def get_table_sizes(database: str | None = None) -> list[dict[str, Any]]:
    """
    获取数据库表大小信息。
    
    Args:
        database: 数据库名，默认当前数据库
    
    Returns:
        表大小列表
    """
    db = get_database()
    return db.get_table_sizes(database)


@mcp.tool()
def get_process_list() -> list[dict[str, Any]]:
    """
    获取当前 MySQL 连接列表。
    
    Returns:
        连接列表
    """
    db = get_database()
    return db.get_process_list()


@mcp.tool()
def get_status() -> dict[str, Any]:
    """
    获取 MySQL 状态变量。
    
    Returns:
        状态变量字典
    """
    db = get_database()
    return db.get_status_variables()


@mcp.tool()
def get_variables() -> dict[str, Any]:
    """
    获取 MySQL 系统变量。
    
    Returns:
        系统变量字典
    """
    db = get_database()
    return db.get_system_variables()


@mcp.tool()
def execute_query(sql: str) -> list[dict[str, Any]]:
    """
    执行 SQL 查询语句（仅支持 SELECT, SHOW, EXPLAIN）。
    
    Args:
        sql: SQL 查询语句
    
    Returns:
        查询结果列表
    """
    sql_lower = sql.strip().lower()
    if not any(sql_lower.startswith(kw) for kw in ["select", "show", "explain"]):
        return [{"error": "仅支持 SELECT, SHOW, EXPLAIN 查询，不允许执行修改操作"}]
    
    db = get_database()
    try:
        result = db.execute_query(sql)
        return result if result else [{"result": "查询成功，无返回数据"}]
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
def kill_connection(process_id: int) -> dict[str, Any]:
    """
    终止指定的 MySQL 连接。
    
    Args:
        process_id: 进程 ID（从 SHOW PROCESSLIST 获取）
    
    Returns:
        执行结果
    """
    db = get_database()
    try:
        db.execute_query(f"KILL {process_id}")
        return {"success": True, "message": f"已终止连接 {process_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def configure_slow_query_log(enable: bool = True, long_query_time: float = 1.0) -> dict[str, Any]:
    """
    配置慢查询日志设置。
    
    Args:
        enable: 是否启用慢查询日志
        long_query_time: 慢查询阈值（秒）
    
    Returns:
        配置结果
    """
    db = get_database()
    result = {
        "success": False,
        "current_status": {},
        "changes_made": [],
        "errors": [],
        "suggestions": [],
    }
    
    try:
        current_vars = db.get_system_variables()
        result["current_status"] = {
            "slow_query_log": current_vars.get("slow_query_log", "UNKNOWN"),
            "long_query_time": current_vars.get("long_query_time", "UNKNOWN"),
        }
    except Exception as e:
        result["errors"].append(f"无法获取当前配置: {str(e)}")
        return result
    
    if enable:
        try:
            db.execute_query("SET GLOBAL slow_query_log = 'ON'")
            result["changes_made"].append("已启用 slow_query_log")
        except Exception as e:
            error_msg = str(e).lower()
            if "access denied" in error_msg or "permission" in error_msg:
                result["errors"].append("权限不足：需要 SUPER 或 SYSTEM_VARIABLES_ADMIN 权限")
                result["suggestions"].append("请联系数据库管理员授权，或手动修改 my.cnf 配置文件")
            elif "read-only" in error_msg:
                result["errors"].append("MySQL 运行在只读模式或云数据库限制")
                result["suggestions"].append("请联系云服务商或修改配置文件后重启 MySQL")
            else:
                result["errors"].append(f"启用慢查询日志失败: {str(e)}")
        
        try:
            db.execute_query(f"SET GLOBAL long_query_time = {long_query_time}")
            result["changes_made"].append(f"已设置 long_query_time = {long_query_time} 秒")
        except Exception as e:
            error_msg = str(e).lower()
            if "access denied" in error_msg or "permission" in error_msg:
                result["errors"].append("权限不足：无法修改 long_query_time")
            else:
                result["errors"].append(f"设置慢查询阈值失败: {str(e)}")
    else:
        try:
            db.execute_query("SET GLOBAL slow_query_log = 'OFF'")
            result["changes_made"].append("已禁用 slow_query_log")
        except Exception as e:
            result["errors"].append(f"禁用慢查询日志失败: {str(e)}")
    
    result["success"] = len(result["errors"]) == 0
    
    if result["success"]:
        result["message"] = f"配置成功: {', '.join(result['changes_made'])}"
    else:
        result["message"] = f"配置部分失败，请查看 errors 和 suggestions"
    
    return result


@mcp.tool()
def analyze_slow_queries(limit: int = 10) -> dict[str, Any]:
    """
    分析慢查询，返回慢查询统计信息。
    
    需要先启用慢查询日志：
    SET GLOBAL slow_query_log = 'ON';
    SET GLOBAL long_query_time = 1;
    
    Args:
        limit: 返回的慢查询数量限制
    
    Returns:
        慢查询统计信息
    """
    db = get_database()
    variables = db.get_system_variables()
    status = db.get_status_variables()
    
    slow_query_log = variables.get("slow_query_log", "OFF")
    long_query_time = float(variables.get("long_query_time", 10))
    slow_queries_count = int(status.get("Slow_queries", 0))
    
    result = {
        "slow_query_log_status": slow_query_log.upper(),
        "long_query_time": f"{long_query_time}秒",
        "total_slow_queries": slow_queries_count,
        "recommendations": [],
    }
    
    if slow_query_log.lower() == "off":
        result["recommendations"].append({
            "level": "warning",
            "message": "慢查询日志未启用",
            "action": "执行 SET GLOBAL slow_query_log = 'ON'; 启用"
        })
    
    if long_query_time > 2:
        result["recommendations"].append({
            "level": "info",
            "message": f"慢查询阈值({long_query_time}秒)可能过高",
            "action": "建议设置为 1-2 秒: SET GLOBAL long_query_time = 1;"
        })
    
    if slow_queries_count > 100:
        result["recommendations"].append({
            "level": "warning",
            "message": f"累计慢查询数量较多({slow_queries_count})",
            "action": "建议分析慢查询日志，优化高频慢查询"
        })
    
    try:
        query_stats = db.execute_query("""
            SELECT 
                DIGEST_TEXT as query_pattern,
                COUNT_STAR as exec_count,
                AVG_TIMER_WAIT/1000000000 as avg_time_sec,
                SUM_ROWS_EXAMINED as rows_examined,
                SUM_ROWS_SENT as rows_sent
            FROM performance_schema.events_statements_summary_by_digest
            WHERE AVG_TIMER_WAIT > 1000000000
            ORDER BY AVG_TIMER_WAIT DESC
            LIMIT {}
        """.format(limit))
        
        if query_stats:
            result["top_slow_queries"] = query_stats
    except Exception:
        result["top_slow_queries"] = []
        result["note"] = "performance_schema 未启用或无数据"
    
    return result


@mcp.tool()
def analyze_locks() -> dict[str, Any]:
    """
    分析当前锁等待和锁冲突情况。
    
    Returns:
        锁分析结果，包括锁等待、死锁信息
    """
    db = get_database()
    status = db.get_status_variables()
    
    result = {
        "lock_statistics": {
            "table_locks_immediate": int(status.get("Table_locks_immediate", 0)),
            "table_locks_waited": int(status.get("Table_locks_waited", 0)),
            "innodb_row_lock_waits": int(status.get("Innodb_row_lock_waits", 0)),
            "innodb_row_lock_time_avg": f"{int(status.get('Innodb_row_lock_time_avg', 0)) / 1000:.2f}ms",
        },
        "lock_wait_ratio": "0%",
        "current_locks": [],
        "deadlock_info": None,
        "recommendations": [],
    }
    
    immediate = int(status.get("Table_locks_immediate", 0))
    waited = int(status.get("Table_locks_waited", 0))
    if immediate + waited > 0:
        ratio = waited / (immediate + waited) * 100
        result["lock_wait_ratio"] = f"{ratio:.2f}%"
        if ratio > 1:
            result["recommendations"].append({
                "level": "warning",
                "message": f"锁等待比例较高({ratio:.2f}%)",
                "action": "检查是否有长事务或热点表"
            })
    
    try:
        lock_waits = db.execute_query("""
            SELECT 
                r.trx_id as waiting_trx_id,
                r.trx_mysql_thread_id as waiting_thread,
                r.trx_query as waiting_query,
                b.trx_id as blocking_trx_id,
                b.trx_mysql_thread_id as blocking_thread,
                b.trx_query as blocking_query
            FROM information_schema.INNODB_LOCK_WAITS w
            JOIN information_schema.INNODB_TRX b ON b.trx_id = w.blocking_trx_id
            JOIN information_schema.INNODB_TRX r ON r.trx_id = w.requesting_trx_id
        """)
        if lock_waits:
            result["current_locks"] = lock_waits
            result["recommendations"].append({
                "level": "critical",
                "message": f"发现 {len(lock_waits)} 个锁等待",
                "action": "检查阻塞事务，必要时 KILL 阻塞线程"
            })
    except Exception:
        pass
    
    try:
        innodb_status = db.execute_query("SHOW ENGINE INNODB STATUS")
        if innodb_status:
            status_text = innodb_status[0].get("Status", "")
            deadlock_start = status_text.find("LATEST DETECTED DEADLOCK")
            if deadlock_start != -1:
                deadlock_end = status_text.find("TRANSACTIONS", deadlock_start)
                if deadlock_end == -1:
                    deadlock_end = len(status_text)
                result["deadlock_info"] = status_text[deadlock_start:deadlock_end][:500]
    except Exception:
        pass
    
    return result


@mcp.tool()
def analyze_transactions() -> dict[str, Any]:
    """
    分析当前事务状态，查找长事务和潜在问题。
    
    Returns:
        事务分析结果
    """
    db = get_database()
    
    result = {
        "active_transactions": [],
        "long_transactions": [],
        "recommendations": [],
    }
    
    try:
        transactions = db.execute_query("""
            SELECT 
                trx_id,
                trx_state,
                trx_started,
                TIMESTAMPDIFF(SECOND, trx_started, NOW()) as duration_sec,
                trx_mysql_thread_id as thread_id,
                trx_query as current_query,
                trx_rows_locked,
                trx_lock_structs
            FROM information_schema.INNODB_TRX
            ORDER BY trx_started ASC
        """)
        
        if transactions:
            result["active_transactions"] = transactions
            
            for trx in transactions:
                duration = int(trx.get("duration_sec", 0))
                if duration > 60:
                    result["long_transactions"].append({
                        "trx_id": trx.get("trx_id"),
                        "duration": f"{duration}秒",
                        "thread_id": trx.get("thread_id"),
                        "state": trx.get("trx_state"),
                        "rows_locked": trx.get("trx_rows_locked"),
                    })
            
            if result["long_transactions"]:
                result["recommendations"].append({
                    "level": "warning",
                    "message": f"发现 {len(result['long_transactions'])} 个长事务(>60秒)",
                    "action": "检查是否需要提交或回滚这些事务"
                })
    except Exception as e:
        result["error"] = str(e)
    
    return result


@mcp.tool()
def analyze_indexes(database: str | None = None) -> dict[str, Any]:
    """
    分析索引使用情况，找出未使用索引和冗余索引。
    
    Args:
        database: 数据库名，默认当前数据库
    
    Returns:
        索引分析结果
    """
    db = get_database()
    
    result = {
        "unused_indexes": [],
        "redundant_indexes": [],
        "missing_index_suggestions": [],
        "recommendations": [],
    }
    
    try:
        unused = db.execute_query("""
            SELECT 
                OBJECT_SCHEMA as database_name,
                OBJECT_NAME as table_name,
                INDEX_NAME as index_name
            FROM performance_schema.table_io_waits_summary_by_index_usage
            WHERE INDEX_NAME IS NOT NULL
            AND COUNT_STAR = 0
            AND INDEX_NAME != 'PRIMARY'
            AND OBJECT_SCHEMA = DATABASE()
            ORDER BY OBJECT_NAME, INDEX_NAME
        """)
        if unused:
            result["unused_indexes"] = unused
            result["recommendations"].append({
                "level": "info",
                "message": f"发现 {len(unused)} 个未使用的索引",
                "action": "考虑删除未使用的索引以减少写入开销"
            })
    except Exception:
        pass
    
    try:
        redundant = db.execute_query("""
            SELECT 
                TABLE_SCHEMA as database_name,
                TABLE_NAME as table_name,
                GROUP_CONCAT(INDEX_NAME) as indexes,
                GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as columns
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
            AND INDEX_NAME != 'PRIMARY'
            GROUP BY TABLE_SCHEMA, TABLE_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX)
            HAVING COUNT(*) > 1
        """)
        if redundant:
            result["redundant_indexes"] = redundant
            result["recommendations"].append({
                "level": "warning",
                "message": f"发现 {len(redundant)} 组可能的冗余索引",
                "action": "检查并删除冗余索引"
            })
    except Exception:
        pass
    
    try:
        missing = db.execute_query("""
            SELECT 
                OBJECT_SCHEMA as database_name,
                OBJECT_NAME as table_name,
                INDEX_NAME as suggested_index,
                ENGINE as engine
            FROM performance_schema.table_io_waits_summary_by_index_usage
            WHERE INDEX_NAME IS NULL
            AND COUNT_STAR > 100
            AND OBJECT_SCHEMA = DATABASE()
            ORDER BY COUNT_STAR DESC
            LIMIT 10
        """)
        if missing:
            result["missing_index_suggestions"] = missing
            result["recommendations"].append({
                "level": "info",
                "message": f"发现 {len(missing)} 个可能需要索引的表",
                "action": "分析这些表的查询模式，考虑添加合适的索引"
            })
    except Exception:
        pass
    
    return result


@mcp.tool()
def get_index_statistics(table_name: str, database: str | None = None) -> dict[str, Any]:
    """
    获取指定表的索引统计信息。
    
    Args:
        table_name: 表名
        database: 数据库名，默认当前数据库
    
    Returns:
        索引统计信息
    """
    db = get_database()
    
    result = {
        "table_name": table_name,
        "database": database,
        "indexes": [],
        "cardinality": {},
    }
    
    try:
        db_name = "DATABASE()" if database is None else f"'{database}'"
        indexes = db.execute_query(f"""
            SELECT 
                INDEX_NAME,
                COLUMN_NAME,
                SEQ_IN_INDEX,
                CARDINALITY,
                SUB_PART,
                NULLABLE,
                INDEX_TYPE
            FROM information_schema.STATISTICS
            WHERE TABLE_NAME = '{table_name}'
            AND TABLE_SCHEMA = {db_name}
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """)
        
        if indexes:
            result["indexes"] = indexes
            
            index_groups = {}
            for idx in indexes:
                idx_name = idx.get("INDEX_NAME")
                if idx_name not in index_groups:
                    index_groups[idx_name] = []
                index_groups[idx_name].append(idx.get("COLUMN_NAME"))
            
            result["index_structure"] = index_groups
    except Exception as e:
        result["error"] = str(e)
    
    return result


@mcp.tool()
def execute_batch_queries(queries: list[str]) -> dict[str, Any]:
    """
    批量执行 SQL 查询语句（仅支持 SELECT, SHOW, EXPLAIN）。
    
    Args:
        queries: SQL 查询语句列表
    
    Returns:
        批量执行结果，包含每个查询的结果和状态
    """
    db = get_database()
    results = []
    success_count = 0
    error_count = 0
    
    for i, sql in enumerate(queries):
        sql_lower = sql.strip().lower()
        
        if not any(sql_lower.startswith(kw) for kw in ["select", "show", "explain"]):
            results.append({
                "index": i,
                "sql": sql,
                "success": False,
                "error": "仅支持 SELECT, SHOW, EXPLAIN 查询"
            })
            error_count += 1
            continue
        
        try:
            result = db.execute_query(sql)
            results.append({
                "index": i,
                "sql": sql,
                "success": True,
                "data": result if result else [],
                "row_count": len(result) if result else 0
            })
            success_count += 1
        except Exception as e:
            results.append({
                "index": i,
                "sql": sql,
                "success": False,
                "error": str(e)
            })
            error_count += 1
    
    return {
        "total": len(queries),
        "success_count": success_count,
        "error_count": error_count,
        "results": results
    }


@mcp.tool()
def get_table_sizes(database: str | None = None) -> list[dict[str, Any]]:
    """
    获取数据库中所有表的大小信息。
    
    Args:
        database: 数据库名，不传则使用当前数据库
    
    Returns:
        表大小列表，包含表名、行数、数据大小、索引大小等
    """
    db = get_database()
    
    db_name = "DATABASE()" if database is None else f"'{database}'"
    
    tables = db.execute_query(f"""
        SELECT 
            TABLE_NAME as table_name,
            TABLE_ROWS as rows,
            ROUND(DATA_LENGTH / 1024 / 1024, 2) as data_size_mb,
            ROUND(INDEX_LENGTH / 1024 / 1024, 2) as index_size_mb,
            ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as total_size_mb,
            TABLE_COMMENT as comment
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = {db_name}
        AND TABLE_TYPE = 'BASE TABLE'
        ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC
    """)
    
    return tables if tables else []


@mcp.tool()
def get_database_overview(database: str | None = None) -> dict[str, Any]:
    """
    获取数据库概览信息，包括表数量、总大小、字符集等。
    
    Args:
        database: 数据库名，不传则使用当前数据库
    
    Returns:
        数据库概览信息
    """
    db = get_database()
    
    db_name = "DATABASE()" if database is None else f"'{database}'"
    
    tables = db.execute_query(f"""
        SELECT 
            COUNT(*) as table_count,
            SUM(TABLE_ROWS) as total_rows,
            ROUND(SUM(DATA_LENGTH) / 1024 / 1024, 2) as total_data_mb,
            ROUND(SUM(INDEX_LENGTH) / 1024 / 1024, 2) as total_index_mb,
            ROUND(SUM(DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as total_size_mb
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = {db_name}
        AND TABLE_TYPE = 'BASE TABLE'
    """)
    
    db_info = db.execute_query(f"""
        SELECT 
            DEFAULT_CHARACTER_SET_NAME as charset,
            DEFAULT_COLLATION_NAME as collation
        FROM information_schema.SCHEMATA
        WHERE SCHEMA_NAME = {db_name}
    """)
    
    result = {
        "database": database if database else "current",
        "tables": tables[0] if tables else {},
        "charset": db_info[0] if db_info else {}
    }
    
    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
