# 单机核心版运行指南

本文是个人本地使用的主文档。部署方式不使用 Docker、不使用 Kafka；PostgreSQL 是唯一必须
运行的外部服务。

## 1. 准备环境

- macOS 或 Linux
- Python 3.12
- PostgreSQL
- Node.js 18+、pnpm

确认 PostgreSQL：

```bash
pg_isready -h 127.0.0.1 -p 5432
```

创建数据库和用户（已有时跳过）：

```bash
createuser -h 127.0.0.1 -P quantdinger
createdb -h 127.0.0.1 -O quantdinger quantdinger
```

## 2. 安装依赖

```bash
cd /Users/chinaxxren/Money/QuantDinger/backend_api_python
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

cd ../QuantDinger-Vue
corepack enable
pnpm install --frozen-lockfile
```

## 3. 配置 `.env`

```bash
cd /Users/chinaxxren/Money/QuantDinger
cp .env.example .env
```

至少填写：

```dotenv
SECRET_KEY=随机字符串
CREDENTIAL_ENCRYPTION_KEY=另一个随机字符串
DATABASE_URL=postgresql://quantdinger:数据库密码@127.0.0.1:5432/quantdinger
ADMIN_USER=quantdinger
ADMIN_PASSWORD=强密码
ADMIN_EMAIL=你的邮箱

# 单机模式
QD_PROCESS_ROLE=legacy
STRATEGY_COMMANDS_ENABLED=false
CACHE_ENABLED=false
CELERY_TASKS_ENABLED=false
```

生成随机密钥：

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

需要邮件通知时，再增加：

```dotenv
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=邮箱账号
SMTP_PASSWORD=邮箱授权码
SMTP_FROM=发件邮箱
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

## 4. 启动和停止

项目根目录的脚本会执行迁移并启动后端、前端：

```bash
cd /Users/chinaxxren/Money/QuantDinger
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
- API：<http://127.0.0.1:5000>
- 健康检查：<http://127.0.0.1:5000/api/health>
- 日志：`.quantdinger/logs/`

如只想手动迁移：

```bash
cd /Users/chinaxxren/Money/QuantDinger/backend_api_python
source .venv/bin/activate
QD_PROCESS_ROLE=migration python -m app.commands.migrate
```

迁移成功后可设置 `QD_SKIP_MIGRATION=true` 跳过脚本启动时的重复迁移。

## 5. 第一次登录

空数据库第一次迁移会使用 `.env` 中的 `ADMIN_USER`、`ADMIN_PASSWORD` 和 `ADMIN_EMAIL` 创建
管理员。登录使用用户名，不是邮箱。

如果数据库已有用户，修改 `.env` 不会覆盖已有密码。出现 `Invalid credentials` 时，先确认：

1. 登录用户名和 `ADMIN_USER` 一致；
2. 脚本使用的是项目根目录 `.env`；
3. `DATABASE_URL` 指向了正确的数据库；
4. 该用户不是旧数据库中的其他密码。

## 6. 功能边界

保留：AI 投研首页、行情/K 线、指标、策略、回测、信号通知、邮件通知、模拟盘/实盘、账户和设置。

不使用：Kafka、社区市场、会员充值、积分、邀请和 Agent/MCP。
Universe 是组合策略的一部分，不能从策略运行/回测链路中移除；AI 投研保留研究报告功能。
独立横截面因子研究报告不属于单机核心功能，已从回测中心移除；策略所需的指标和基本面数据能力保留。

Redis 和 Celery 不是登录、指标、策略编辑和本地回测的必需项。启用异步 AI、报告或缓存时再单独
安装 Redis，并按项目环境变量配置。

## 7. 常见故障

### 迁移提示无法连接 PostgreSQL

```bash
pg_isready -h 127.0.0.1 -p 5432
psql "$DATABASE_URL" -c 'SELECT 1;'
```

检查 PostgreSQL 服务、用户名、密码、端口和数据库名。

### 前端能打开但 API 失败

确认后端监听 5000 端口，并检查 `.quantdinger/logs/backend.log`。前端通过 Vite 的 `/api` 代理
访问后端，不要把 `DATABASE_URL`、SMTP 密码或交易所密钥写入 `VITE_` 变量。

### 邮件通知失败

检查 SMTP 授权码、TLS/SSL 配置和 `SMTP_FROM`。在个人中心的通知设置保存后，先发送测试通知。

### 策略不运行

单进程本地调试使用 `QD_PROCESS_ROLE=legacy`。长期运行策略时，另行启动 trading worker 和
scheduler；不要只启动 API 进程后期待策略持续执行。
