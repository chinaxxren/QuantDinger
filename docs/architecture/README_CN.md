# 系统架构总览

QuantDinger 的单机运行时将 HTTP 请求、交易控制与执行、领域调度、有限后台任务和数据库迁移拆成明确的进程角色。PostgreSQL 负责持久状态与所有权协调；K 线收盘事件通过交易工作进程内的本地事件总线分发，因此当前单机安装不需要 Kafka。两套 Redis 分别服务于缓存和持久任务，不能混用。

## 运行职责

| 进程 | 负责 | 不应负责 |
| --- | --- | --- |
| `backend` | 鉴权、校验、查询、提交持久命令 | 交易循环和长期调度 |
| `trading-worker` | 控制/实时策略、本地 K 线策略运行时、券商会话、带 fencing 的下单、对账、持久化网格 Actor | 对外 HTTP 请求 |
| `scheduler-worker` | 组合、部署、支付和通知等领域调度 | 通用 Celery 任务 |
| `celery-worker` | 有限、可序列化、可重试的后台任务 | 长期策略运行时 |
| `migration` | 按顺序应用数据库结构更新 | 并发提供 API 服务 |

## 状态与并发

- PostgreSQL 是命令、租约、心跳、审计、Actor 邮箱、策略和交易状态的持久事实来源。
- 交易工作进程使用有界协作式运行时调度器与进程内事件总线处理 K 线收盘通知；此实现满足当前单机部署，不依赖外部事件代理。
- `redis` 是可淘汰缓存，不能承担持久任务队列。
- `redis-jobs` 是 Celery broker 与结果存储，启用 AOF 和 `noeviction`，需要监控内存。
- 幂等键、数据库认领、可续租租约和 fencing token 用于阻止重复执行与过期 Worker 写入。

## 按修改类型阅读

| 修改任务 | 详细文档 |
| --- | --- |
| 理解包与进程归属 | [后端架构（英文）](ARCHITECTURE.md) |
| 保持依赖方向 | [模块边界（英文）](MODULE_BOUNDARIES.md) |
| 修改并发或持久任务 | [并发模型（英文）](CONCURRENCY_MODEL.md) |
| 判断任务属于哪个进程 | [进程职责（英文）](PROCESS_ROLES_AND_TASKS.md) |
| 查看历史分布式运行时设计 | [历史 Kafka 扩容文档（英文）](../deployment/DISTRIBUTED_RUNTIME_SCALING.md) |
| 新增路由、适配器、任务或服务 | [扩展指南（英文）](EXTENSION_GUIDE.md) |
| 修改 HTTP 契约 | [API 约定（英文）](API_CONVENTIONS.md) |

进行较大修改前，应先明确：哪个进程拥有该工作、持久状态存在哪里、如何重试与幂等，
以及哪项测试能够证明边界没有被破坏。
