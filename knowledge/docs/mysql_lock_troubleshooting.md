# MySQL 锁问题排查指南

## 锁类型概述

### 行级锁
- **共享锁 (S)**: 允许读，阻止写
- **排他锁 (X)**: 阻止读写

### 表级锁
- **意向锁**: 表明事务意图
- **元数据锁 (MDL)**: 保护表结构

### 其他锁
- **间隙锁 (Gap Lock)**: 锁定索引间隙
- **临键锁 (Next-Key Lock)**: 行锁+间隙锁

## 查看锁信息

### MySQL 5.7

```sql
-- 查看锁等待
SELECT * FROM information_schema.INNODB_LOCK_WAITS;

-- 查看锁信息
SELECT * FROM information_schema.INNODB_LOCKS;
```

### MySQL 8.0+

```sql
-- 使用 performance_schema
SELECT * FROM performance_schema.data_locks;
SELECT * FROM performance_schema.data_lock_waits;
```

### InnoDB 状态

```sql
SHOW ENGINE INNODB STATUS\G
```

## 死锁排查

### 启用死锁检测

```sql
SHOW VARIABLES LIKE 'innodb_deadlock_detect';
SET GLOBAL innodb_deadlock_detect = ON;
```

### 查看死锁日志

```sql
-- 最近一次死锁信息
SHOW ENGINE INNODB STATUS\G

-- 查找 LATEST DETECTED DEADLOCK 部分
```

### 死锁预防

1. **按相同顺序访问表**
```sql
-- 好的做法：所有事务都按 id 顺序更新
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
```

2. **保持事务简短**
```sql
-- 避免
BEGIN;
-- 执行大量操作
-- 等待用户输入
COMMIT;

-- 推荐
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
COMMIT;
```

3. **使用合适的隔离级别**
```sql
-- 查看当前隔离级别
SELECT @@transaction_isolation;

-- 设置隔离级别
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;
```

## 锁等待超时

```sql
-- 查看锁等待超时设置
SHOW VARIABLES LIKE 'innodb_lock_wait_timeout';

-- 默认 50 秒，可根据需要调整
SET GLOBAL innodb_lock_wait_timeout = 30;
```

## 常用排查 SQL

```sql
-- 查看长时间运行的事务
SELECT * FROM information_schema.INNODB_TRX
ORDER BY trx_started;

-- 查看阻塞的线程
SELECT 
    r.trx_id waiting_trx_id,
    r.trx_mysql_thread_id waiting_thread,
    r.trx_query waiting_query,
    b.trx_id blocking_trx_id,
    b.trx_mysql_thread_id blocking_thread,
    b.trx_query blocking_query
FROM information_schema.INNODB_LOCK_WAITS w
JOIN information_schema.INNODB_TRX b ON b.trx_id = w.blocking_trx_id
JOIN information_schema.INNODB_TRX r ON r.trx_id = w.requesting_trx_id;

-- 终止阻塞的线程
KILL <thread_id>;
```
