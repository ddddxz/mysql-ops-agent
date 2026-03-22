# InnoDB 性能调优指南

## 核心参数配置

### innodb_buffer_pool_size

最重要的 InnoDB 参数，用于缓存数据和索引。

```sql
-- 推荐设置为系统内存的 70-80%
-- 8GB 内存服务器
SET GLOBAL innodb_buffer_pool_size = 6442450944; -- 6GB

-- 查看当前设置
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
```

### innodb_log_file_size

控制重做日志文件大小，影响写入性能。

```sql
-- 推荐设置为 buffer pool 的 25%
-- 需要在配置文件中设置
[mysqld]
innodb_log_file_size = 1G
```

### innodb_flush_log_at_trx_commit

控制事务日志刷新策略：

- **1**: 每次提交都刷新（最安全，默认）
- **2**: 每秒刷新一次（性能较好，可能丢失 1 秒数据）
- **0**: 由操作系统决定（性能最好，最不安全）

```sql
SET GLOBAL innodb_flush_log_at_trx_commit = 2;
```

### innodb_io_capacity

设置 InnoDB 的 I/O 容量：

```sql
-- SSD 推荐 2000-5000
SET GLOBAL innodb_io_capacity = 2000;

-- HDD 推荐 200-500
SET GLOBAL innodb_io_capacity = 200;
```

## 监控 InnoDB 状态

```sql
-- 查看 InnoDB 整体状态
SHOW ENGINE INNODB STATUS\G

-- 查看缓冲池状态
SHOW STATUS LIKE 'Innodb_buffer_pool%';

-- 查看行锁等待
SELECT * FROM performance_schema.data_lock_waits;
```

## 常见问题排查

### 缓冲池命中率低

```sql
-- 计算命中率
SELECT 
    (1 - (Innodb_buffer_pool_reads / Innodb_buffer_pool_read_requests)) * 100 
    AS buffer_pool_hit_rate
FROM (
    SELECT variable_value AS Innodb_buffer_pool_reads
    FROM performance_schema.global_status
    WHERE variable_name = 'Innodb_buffer_pool_reads'
) r,
(
    SELECT variable_value AS Innodb_buffer_pool_read_requests
    FROM performance_schema.global_status
    WHERE variable_name = 'Innodb_buffer_pool_read_requests'
) rr;
```

命中率应该 > 99%，否则需要增加 buffer pool 大小。

### 日志写入瓶颈

检查日志写入相关状态：

```sql
SHOW STATUS LIKE 'Innodb_os_log%';
SHOW STATUS LIKE 'Innodb_log_waits';
```

如果 `Innodb_log_waits` 持续增长，考虑增加 `innodb_log_file_size`。
