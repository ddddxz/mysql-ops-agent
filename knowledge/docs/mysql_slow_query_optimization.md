# MySQL 慢查询优化指南

## 什么是慢查询

慢查询是指执行时间超过 `long_query_time` 阈值的 SQL 语句。默认阈值为 10 秒，建议设置为 1-2 秒。

## 启用慢查询日志

```sql
-- 查看当前配置
SHOW VARIABLES LIKE 'slow_query_log';
SHOW VARIABLES LIKE 'long_query_time';

-- 启用慢查询日志
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 2;
```

## 分析慢查询

### 使用 EXPLAIN

```sql
EXPLAIN SELECT * FROM users WHERE email = 'test@example.com';
```

关键指标：
- **type**: ALL 表示全表扫描，需要优化
- **key**: 使用的索引名称
- **rows**: 预估扫描行数
- **Extra**: 额外信息，Using filesort 或 Using temporary 需要关注

### 常见优化方法

1. **添加索引**
```sql
CREATE INDEX idx_email ON users(email);
```

2. **避免 SELECT ***
```sql
-- 不推荐
SELECT * FROM users;

-- 推荐
SELECT id, name, email FROM users;
```

3. **优化 JOIN**
```sql
-- 确保 JOIN 列有索引
CREATE INDEX idx_user_id ON orders(user_id);
```

4. **使用覆盖索引**
```sql
-- 创建覆盖索引
CREATE INDEX idx_user_email_name ON users(email, name);

-- 查询可以直接从索引获取数据
SELECT name FROM users WHERE email = 'test@example.com';
```

## 监控慢查询

```sql
-- 查看慢查询数量
SHOW GLOBAL STATUS LIKE 'Slow_queries';

-- 从 performance_schema 获取慢查询
SELECT * FROM performance_schema.events_statements_summary_by_digest
ORDER BY SUM_TIMER_WAIT DESC
LIMIT 10;
```
