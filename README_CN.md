# QuantDinger 单机核心版

QuantDinger 是一个面向个人使用的 AI 投研与量化交易工具。当前单机版只保留核心闭环：

```text
登录/注册 -> AI 投研 -> 指标 -> 策略 -> 回测 -> 信号通知 -> 模拟盘/实盘
```

AI 投研首页必须保留。社区市场、会员充值、积分、邀请和 Agent/MCP 已从单机版移除。
Universe 仍由组合策略执行与回测使用；AI 投研首页及研究报告能力保留。独立因子研究报告已移除。

## 本地启动

不使用 Docker，不使用 Kafka。只需要 PostgreSQL、Python、Node.js 和 pnpm。

```bash
cd /Users/chinaxxren/Money/QuantDinger
cp .env.example .env
./quantdinger.sh start
```

常用命令：

```bash
./quantdinger.sh status
./quantdinger.sh stop
./quantdinger.sh restart
```

默认地址：

- Web：<http://127.0.0.1:8000>
- API 健康检查：<http://127.0.0.1:5000/api/health>
- 日志：`.quantdinger/logs/`

完整的本地准备、数据库初始化、SMTP 和故障排查见[单机运行指南](docs/CORE_SINGLE_HOST_CN.md)。

## 最小配置

在项目根目录 `.env` 中至少配置：

```dotenv
SECRET_KEY=请生成随机值
CREDENTIAL_ENCRYPTION_KEY=请生成另一个随机值
DATABASE_URL=postgresql://quantdinger:数据库密码@127.0.0.1:5432/quantdinger
ADMIN_USER=quantdinger
ADMIN_PASSWORD=请设置强密码
ADMIN_EMAIL=你的邮箱地址
QD_PROCESS_ROLE=legacy
STRATEGY_COMMANDS_ENABLED=false
CACHE_ENABLED=false
CELERY_TASKS_ENABLED=false
```

空数据库首次迁移时会创建管理员。已有数据库不会因为修改 `.env` 自动重置密码；登录时使用
用户名，不是邮箱。推荐使用强密码，不要继续使用旧的 `quantdinger / 123456`。

邮件通知需要额外配置 SMTP：

```dotenv
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=你的邮箱账号
SMTP_PASSWORD=邮箱授权码
SMTP_FROM=你的邮箱账号
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

## 核心模块

- **AI 投研首页**：行情、K 线、市场研究和 AI 对话。
- **指标**：内置指标、指标 IDE 和图表渲染。
- **策略**：CTA/组合策略编辑、保存和运行配置。
- **回测**：使用本地策略和行情数据进行回测。
- **信号通知**：按策略信号触发站内、邮件、Telegram、Discord 或 Webhook 通知。
- **实盘**：先使用模拟盘；确认风险后再配置交易所 API Key。
- **个人中心/设置**：账号、密码、MFA、通知、SMTP、行情和 AI 提供商配置。

Kafka 不需要安装。单机事件在本地进程内处理，PostgreSQL 保存用户、策略、任务和运行状态。
Redis/Celery 不是基础登录、指标、策略编辑和本地回测的前置条件；只有需要缓存或队列异步任务
时再启用。

## 常见问题

### 数据库迁移失败

```bash
pg_isready -h 127.0.0.1 -p 5432
psql "$DATABASE_URL" -c 'SELECT 1;'
```

确认 PostgreSQL 已启动，且 `.env` 中的用户、密码、端口和数据库名正确。

### `Invalid credentials`

确认使用的是 `ADMIN_USER` 对应的用户名。已有数据库不会读取新的 `ADMIN_PASSWORD` 覆盖旧密码；
请使用旧账号修改密码，或在确认数据可删除后重新创建空数据库。

### 邮件没有发送

检查 SMTP 主机、端口、TLS/SSL、邮箱授权码和 `SMTP_FROM`，保存通知设置后先发送测试通知。

### 策略没有运行

先查看 `.quantdinger/logs/backend.log`。长期运行策略时，再启动本地 trading worker 和 scheduler；
具体命令见[单机运行指南](docs/CORE_SINGLE_HOST_CN.md)。

## 相关中文文档

- [单机运行指南](docs/CORE_SINGLE_HOST_CN.md)
- [邮件通知配置](docs/deployment/NOTIFICATION_EMAIL_CONFIG_CN.md)
- [策略开发指南](docs/trading/STRATEGY_DEV_GUIDE_CN.md)
- [指标开发指南](docs/trading/INDICATOR_DEV_GUIDE_CN.md)
- [实盘交易安全](docs/trading/LIVE_TRADING_SAFETY_CN.md)
