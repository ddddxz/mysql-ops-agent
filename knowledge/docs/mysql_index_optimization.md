# MySQL 索引优化指南

## 索引类型

### 1. 主键索引 (PRIMARY KEY)

```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100)
);
```

### 2. 唯一索引 (UNIQUE)

```sql
CREATE UNIQUE INDEX idx_email ON users(email);
```

### 3. 普通索引 (INDEX)

```sql
CREATE INDEX idx_name ON users(name);
```

### 4. 复合索引

```sql
CREATE INDEX idx_name_age ON users(name, age);
```

### 5. 全文索引 (FULLTEXT)

```sql
CREATE FULLTEXT INDEX idx_content ON articles(content);
```

## 索引设计原则

### 1. 最左前缀原则

复合索引按照定义顺序使用：

```sql
-- 索引: idx_name_age (name, age)

-- 可以使用索引
WHERE name = 'Tom'
WHERE name = 'Tom' AND age = 20

-- 不能使用索引（跳过了 name）
WHERE age = 20

-- 部分使用索引（只用到 name）
WHERE name = 'Tom' AND age > 20
```

### 2. 选择性高的列优先

```sql
-- 选择性 = 不同值数量 / 总行数
-- 选择性越高，索引效果越好

-- 高选择性（适合索引）
SELECT COUNT(DISTINCT email) / COUNT(*) FROM users;  -- 接近 1

-- 低选择性（不适合索引）
SELECT COUNT(DISTINCT gender) / COUNT(*) FROM users;  -- 接近 0.5
```

### 3. 覆盖索引

索引包含查询所需的所有字段：

```sql
-- 创建覆盖索引
CREATE INDEX idx_user_info ON users(name, email, age);

-- 使用覆盖索引（不需要回表）
SELECT name, email, age FROM users WHERE name = 'Tom';
```

## 索引分析

### 1. 查看索引使用情况

```sql
-- 查看表的索引
SHOW INDEX FROM users;

-- 查看索引统计
SELECT 
    INDEX_NAME,
    CARDINALITY,
    SEQ_IN_INDEX
FROM information_schema.STATISTICS
WHERE TABLE_NAME = 'users';
```

### 2. 分析未使用的索引

```sql
SELECT 
    OBJECT_SCHEMA as database_name,
    OBJECT_NAME as table_name,
    INDEX_NAME as index_name
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE INDEX_NAME IS NOT NULL
AND COUNT_STAR = 0
AND INDEX_NAME != 'PRIMARY';
```

### 3. 查找冗余索引

```sql
SELECT 
    TABLE_NAME,
    GROUP_CONCAT(INDEX_NAME) as indexes,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as columns
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
GROUP BY TABLE_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX)
HAVING COUNT(*) > 1;
```

## 索引优化建议

### 1. 避免索引失效

```sql
-- 不推荐：使用函数
WHERE YEAR(created_at) = 2024

-- 推荐：范围查询
WHERE created_at >= '2024-01-01' AND created_at < '2025-01-01'

-- 不推荐：隐式类型转换
WHERE phone = 13800138000  -- phone 是 VARCHAR

-- 推荐：使用字符串
WHERE phone = '13800138000'

-- 不推荐：使用 OR
WHERE name = 'Tom' OR age = 20

-- 推荐：使用 UNION
WHERE name = 'Tom' UNION SELECT * FROM users WHERE age = 20

-- 不推荐：使用 != 或 <>
WHERE status != 'deleted'

-- 不推荐：使用 NOT IN
WHERE status NOT IN ('deleted', 'archived')
```

### 2. 复合索引顺序

```sql
-- 原则：等值条件在前，范围条件在后
-- 查询: WHERE status = 'active' AND created_at > '2024-01-01'
-- 索引: CREATE INDEX idx_status_created ON users(status, created_at);
```

### 3. 索引长度优化

```sql
-- 前缀索引
CREATE INDEX idx_content ON articles(content(100));

-- 查看索引长度
SELECT 
    INDEX_NAME,
    SUB_PART,
    COLUMN_NAME
FROM information_schema.STATISTICS
WHERE TABLE_NAME = 'articles';
```

## 索引维护

### 1. 重建索引

```sql
-- 分析表
ANALYZE TABLE users;

-- 优化表（重建索引）
OPTIMIZE TABLE users;
```

### 2. 删除无用索引

```sql
-- 删除索引
DROP INDEX idx_unused ON users;

-- 或
ALTER TABLE users DROP INDEX idx_unused;
```

## 索引监控指标

| 指标 | 说明 | 阈值建议 |
|------|------|----------|
| 索引命中率 | 使用索引的查询比例 | > 95% |
| 未使用索引数量 | 从未使用的索引数 | 0 |
| 冗余索引数量 | 重复的索引数 | 0 |
| 索引大小/数据大小 | 索引空间占比 | < 50% |

## 最佳实践

1. **定期分析索引使用情况**：删除未使用的索引
2. **避免过度索引**：索引会增加写入开销
3. **使用覆盖索引**：减少回表操作
4. **注意索引顺序**：遵循最左前缀原则
5. **监控索引大小**：避免索引过大
