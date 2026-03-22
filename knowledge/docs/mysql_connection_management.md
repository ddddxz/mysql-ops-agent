# MySQL 连接管理指南

## 连接相关参数

### max_connections

最大并发连接数，默认 151。

```sql
-- 查看当前设置
SHOW VARIABLES LIKE 'max_connections';

-- 临时修改
SET GLOBAL max_connections = 500;

-- 永久修改（my.cnf）
[mysqld]
max_connections = 500
```

计算建议：
- 每个连接约占用 256KB-1MB 内存
- 公式：max_connections = (可用内存 - global_buffers) / per_thread_buffers

### wait_timeout 和 interactive_timeout

连接空闲超时时间，默认 8 小时。

```sql
SHOW VARIABLES LIKE 'wait_timeout';
SHOW VARIABLES LIKE 'interactive_timeout';

-- 建议设置为 30 分钟
SET GLOBAL wait_timeout = 1800;
SET GLOBAL interactive_timeout = 1800;
```

## 监控连接状态

```sql
-- 当前连接数
SHOW STATUS LIKE 'Threads_connected';

-- 历史最大连接数
SHOW STATUS LIKE 'Max_used_connections';

-- 连接错误统计
SHOW STATUS LIKE 'Connection_errors%';

-- 查看所有连接
SHOW PROCESSLIST;

-- 详细连接信息
SELECT * FROM information_schema.PROCESSLIST;
```

## 连接池最佳实践

### 应用端配置

```python
# Python 连接池示例
import aiomysql

pool = await aiomysql.create_pool(
    host='localhost',
    port=3306,
    user='root',
    password='password',
    db='mydb',
    minsize=5,      # 最小连接数
    maxsize=20,     # 最大连接数
    pool_recycle=3600,  # 连接回收时间
    autocommit=True,
)
```

### 推荐配置

- **minsize**: 设置为预期并发数的 20-30%
- **maxsize**: 设置为预期并发数的 1.5-2 倍
- **pool_recycle**: 设置小于 wait_timeout

## 常见问题

### Too many connections

错误原因：连接数超过 max_connections

解决方案：
1. 临时增加 max_connections
2. 检查连接泄漏
3. 优化连接池配置

```sql
-- 查看连接来源
SELECT USER, HOST, COUNT(*) as count
FROM information_schema.PROCESSLIST
GROUP BY USER, HOST
ORDER BY count DESC;

-- 终止空闲连接
SELECT CONCAT('KILL ', id, ';') 
FROM information_schema.PROCESSLIST 
WHERE Command = 'Sleep' AND Time > 600;
```

### 连接超时

检查网络和防火墙设置：

```sql
-- 查看连接超时相关参数
SHOW VARIABLES LIKE 'connect_timeout';
SHOW VARIABLES LIKE 'net_read_timeout';
SHOW VARIABLES LIKE 'net_write_timeout';
```
