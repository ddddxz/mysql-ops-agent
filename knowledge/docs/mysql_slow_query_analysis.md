# MySQL 慢查询分析与优化

## 什么是慢查询

慢查询是指执行时间超过 `long_query_time` 阈值的 SQL 语句。慢查询是影响 MySQL 性能的主要原因之一。

## 启用慢查询日志

```sql
-- 查看当前配置
SHOW VARIABLES LIKE 'slow_query_log';
SHOW VARIABLES LIKE 'long_query_time';

-- 启用慢查询日志
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;  -- 设置阈值为 1 秒

-- 设置日志文件路径（可选）
SET GLOBAL slow_query_log_file = '/var/log/mysql/mysql-slow.log';
```

## 分析慢查询的方法

### 1. 使用 mysqldumpslow 工具

```bash
# 按查询时间排序，显示前 10 条
mysqldumpslow -s t -t 10 /var/log/mysql/mysql-slow.log

# 按查询次数排序
mysqldumpslow -s c -t 10 /var/log/mysql/mysql-slow.log
```

### 2. 使用 performance_schema

```sql
-- 查看执行时间最长的 SQL
SELECT 
    DIGEST_TEXT as query_pattern,
    COUNT_STAR as exec_count,
    AVG_TIMER_WAIT/1000000000 as avg_time_sec,
    SUM_ROWS_EXAMINED as rows_examined
FROM performance_schema.events_statements_summary_by_digest
ORDER BY AVG_TIMER_WAIT DESC
LIMIT 10;
```

### 3. 使用 EXPLAIN 分析执行计划

```sql
EXPLAIN SELECT * FROM orders WHERE customer_id = 100;
```

重点关注：
- `type`: ALL 表示全表扫描，需要优化
- `key`: 使用的索引
- `rows`: 预估扫描行数
- `Extra`: Using filesort 或 Using temporary 表示需要优化

## 常见慢查询优化方法

### 1. 添加索引

```sql
-- 单列索引
CREATE INDEX idx_customer_id ON orders(customer_id);

-- 复合索引（注意最左前缀原则）
CREATE INDEX idx_customer_status ON orders(customer_id, status);
```

### 2. 避免 SELECT *

```sql
-- 不推荐
SELECT * FROM orders WHERE customer_id = 100;

-- 推荐
SELECT id, customer_id, order_date FROM orders WHERE customer_id = 100;
```

### 3. 避免 WHERE 条件中使用函数

```sql
-- 不推荐（无法使用索引）
SELECT * FROM orders WHERE DATE(created_at) = '2024-01-01';

-- 推荐
SELECT * FROM orders WHERE created_at >= '2024-01-01' AND created_at < '2024-01-02';
```

### 4. 优化 JOIN 操作

```sql
-- 确保 JOIN 字段有索引
CREATE INDEX idx_user_id ON orders(user_id);

-- 小表驱动大表
SELECT * FROM small_table s
JOIN large_table l ON s.id = l.small_id;
```

### 5. 使用 LIMIT 分页

```sql
-- 不推荐（深度分页性能差）
SELECT * FROM orders LIMIT 100000, 10;

-- 推荐（使用覆盖索引）
SELECT o.* FROM orders o
JOIN (SELECT id FROM orders LIMIT 100000, 10) t ON o.id = t.id;
```

## 慢查询监控指标

| 指标 | 说明 | 阈值建议 |
|------|------|----------|
| Slow_queries | 累计慢查询数量 | 持续增长需关注 |
| long_query_time | 慢查询阈值 | 建议 1-2 秒 |
| 慢查询比例 | 慢查询/总查询 | < 1% |

## 最佳实践

1. **定期分析慢查询日志**：每周检查一次
2. **设置合理的阈值**：根据业务特点设置 long_query_time
3. **建立索引策略**：避免过度索引
4. **监控告警**：慢查询数量异常时发送告警
5. **代码审查**：上线前审查 SQL 性能
