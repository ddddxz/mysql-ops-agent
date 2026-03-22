# MySQL 锁与事务分析

## MySQL 锁类型

### 1. 表级锁

- **表共享读锁 (READ)**：允许并发读，禁止写
- **表独占写锁 (WRITE)**：禁止其他读写

```sql
-- 加锁
LOCK TABLES users READ;
LOCK TABLES users WRITE;

-- 解锁
UNLOCK TABLES;
```

### 2. 行级锁 (InnoDB)

- **共享锁 (S)**：`SELECT ... LOCK IN SHARE MODE`
- **排他锁 (X)**：`SELECT ... FOR UPDATE`
- **意向锁**：IS、IX（自动添加）

```sql
-- 共享锁
SELECT * FROM users WHERE id = 1 LOCK IN SHARE MODE;

-- 排他锁
SELECT * FROM users WHERE id = 1 FOR UPDATE;
```

### 3. 间隙锁 (Gap Lock)

防止幻读，锁定索引记录之间的间隙。

## 查看锁信息

### 1. 查看当前锁等待

```sql
-- MySQL 5.7
SELECT 
    r.trx_id as waiting_trx_id,
    r.trx_mysql_thread_id as waiting_thread,
    r.trx_query as waiting_query,
    b.trx_id as blocking_trx_id,
    b.trx_mysql_thread_id as blocking_thread,
    b.trx_query as blocking_query
FROM information_schema.INNODB_LOCK_WAITS w
JOIN information_schema.INNODB_TRX b ON b.trx_id = w.blocking_trx_id
JOIN information_schema.INNODB_TRX r ON r.trx_id = w.requesting_trx_id;

-- MySQL 8.0+
SELECT * FROM performance_schema.data_lock_waits;
```

### 2. 查看当前事务

```sql
SELECT 
    trx_id,
    trx_state,
    trx_started,
    TIMESTAMPDIFF(SECOND, trx_started, NOW()) as duration_sec,
    trx_mysql_thread_id as thread_id,
    trx_rows_locked
FROM information_schema.INNODB_TRX
ORDER BY trx_started;
```

### 3. 查看 InnoDB 状态

```sql
SHOW ENGINE INNODB STATUS\G
```

重点关注 `LATEST DETECTED DEADLOCK` 部分。

## 死锁分析

### 死锁产生条件

1. 互斥条件
2. 请求与保持条件
3. 不剥夺条件
4. 循环等待条件

### 死锁示例

```sql
-- 事务 A
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;

-- 事务 B（同时执行）
BEGIN;
UPDATE accounts SET balance = balance - 50 WHERE id = 2;
UPDATE accounts SET balance = balance + 50 WHERE id = 1;  -- 死锁！
COMMIT;
```

### 死锁预防

1. **按固定顺序访问表和行**
2. **保持事务简短**
3. **避免长事务**
4. **使用较低的隔离级别**（如 READ COMMITTED）

## 长事务处理

### 查找长事务

```sql
SELECT 
    trx_id,
    trx_state,
    TIMESTAMPDIFF(SECOND, trx_started, NOW()) as duration_sec,
    trx_mysql_thread_id as thread_id
FROM information_schema.INNODB_TRX
WHERE TIMESTAMPDIFF(SECOND, trx_started, NOW()) > 60;
```

### 终止长事务

```sql
-- 查找线程 ID
SELECT trx_mysql_thread_id FROM information_schema.INNODB_TRX WHERE trx_id = '事务ID';

-- 终止连接
KILL 线程ID;
```

## 锁监控指标

| 指标 | 说明 | 阈值建议 |
|------|------|----------|
| Table_locks_waited | 表锁等待次数 | 持续增长需关注 |
| Innodb_row_lock_waits | 行锁等待次数 | 持续增长需关注 |
| Innodb_row_lock_time_avg | 平均行锁等待时间 | < 50ms |
| 锁等待比例 | waited/(immediate+waited) | < 1% |

## 最佳实践

1. **保持事务简短**：事务越短，锁持有时间越短
2. **按固定顺序访问资源**：避免死锁
3. **使用合适的隔离级别**：根据业务需求选择
4. **避免锁等待超时**：设置合理的 innodb_lock_wait_timeout
5. **监控锁指标**：及时发现锁问题
