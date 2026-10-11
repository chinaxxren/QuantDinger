# 本地源码运行 QuantDinger（不用 Docker）

本文适用于 macOS 和 Linux 上的个人单机部署。整套运行方式不使用 Docker、Docker Compose 或 Kafka：

- **PostgreSQL 必须运行**，用于保存用户、策略、订单和运行状态；
- **Kafka 不需要安装或启动**，单机策略事件在 trading worker 进程内传递；
- **Redis/Celery 是可选项**，不启动时可以运行基础 API、登录、策略编辑、行情和本地调试；
- 如果需要长期运行策略和周期性通知，建议启动本地 trading worker 与 scheduler；
- 邮件通知需要额外配置 SMTP，邮件服务本身不由 Kafka 提供。

> 本仓库包含后端源码。Web 前端源码位于同级目录 `QuantDinger-Vue/`（如果本地没有，见[前端仓库](https://github.com/OpenByteInc/QuantDinger-Vue)）。


## 最简单的启动方式

完成一次环境准备（PostgreSQL、`.env`、Python 虚拟环境、前端依赖）后，日常只需要在项目根目录执行一个脚本：

```bash
cd /Users/chinaxxren/Money/QuantDinger
./quantdinger.sh start
```

脚本会自动执行数据库迁移，然后启动后端和前端。常用命令：

```bash
./quantdinger.sh status   # 查看状态
./quantdinger.sh stop     # 停止前后端
./quantdinger.sh restart  # 重启前后端
```

默认访问地址：

- Web 页面：`http://127.0.0.1:8000`
- 后端健康检查：`http://127.0.0.1:5000/api/health`
- 日志目录：项目根目录下的 `.quantdinger/logs/`

脚本要求后端虚拟环境位于 `backend_api_python/.venv`，前端依赖已经安装在 `QuantDinger-Vue/node_modules`。如果数据库迁移已在其他方式执行过，但本次不想重复迁移，可以使用：

```bash
QD_SKIP_MIGRATION=true ./quantdinger.sh start
```

脚本只管理自己记录在 `.quantdinger/pids/` 中的进程，不会停止其他手动启动的 Python 或 Node 进程。

## 1. 前置条件

| 软件 | 要求 |
| --- | --- |
| Python | 3.12 |
| PostgreSQL | 推荐 18；已安装的兼容版本可先尝试迁移 |
| Node.js | 18+，推荐 22 LTS（仅运行 Web 页面需要） |
| pnpm | 10.x，运行前端需要 |
| Redis | 可选；启用缓存、Celery 异步任务时需要 |

确认 PostgreSQL 已启动：

```bash
pg_isready -h 127.0.0.1 -p 5432
```

如果使用 Homebrew 安装的 PostgreSQL，可以按本机版本执行：

```bash
brew services start postgresql@18
```

如果你的服务名不同，以 `brew services list` 的结果为准。

## 2. 创建 PostgreSQL 数据库

如果数据库和用户已经存在，跳过本节。以下命令会要求输入数据库用户密码：

```bash
createuser -h 127.0.0.1 -P quantdinger
createdb -h 127.0.0.1 -O quantdinger quantdinger
```

没有权限使用 `createuser` 时，用 PostgreSQL 管理员执行：

```bash
psql -h 127.0.0.1 -U postgres -d postgres
```

然后执行：

```sql
CREATE USER quantdinger WITH PASSWORD '请替换为数据库密码';
CREATE DATABASE quantdinger OWNER quantdinger;
GRANT ALL PRIVILEGES ON DATABASE quantdinger TO quantdinger;
\q
```

请勿把真实密码提交到 Git。后续 `.env` 中的密码必须与这里设置的密码一致。

## 3. 创建 Python 环境

在项目根目录执行：

```bash
cd /Users/chinaxxren/Money/QuantDinger/backend_api_python
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

如果系统中的命令就是 `python`，也可以把 `python3.12` 替换为 `python`。开发和测试依赖可以额外安装：

```bash
python -m pip install -r requirements-dev.txt
```

对于 macOS/Linux，普通本地运行优先使用 `requirements.txt`；`requirements.lock` 是面向 Linux 生产镜像的锁定依赖，不要在不同平台强行使用它解决安装问题。

## 4. 配置项目环境变量

回到项目根目录，复制模板：

```bash
cd /Users/chinaxxren/Money/QuantDinger
cp .env.example .env
```

生成两个独立的随机密钥：

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
python3 -c "import secrets; print(secrets.token_hex(32))"
```

编辑 `/Users/chinaxxren/Money/QuantDinger/.env`，至少确认以下配置。示例中的密码都是占位符，请替换为自己的值：

```dotenv
SECRET_KEY=第一条命令生成的随机值
CREDENTIAL_ENCRYPTION_KEY=第二条命令生成的随机值

ADMIN_USER=quantdinger
ADMIN_PASSWORD=请设置一个强密码
ADMIN_EMAIL=你的邮箱地址

DATABASE_URL=postgresql://quantdinger:数据库密码@127.0.0.1:5432/quantdinger

PYTHON_API_HOST=127.0.0.1
PYTHON_API_PORT=5000
PYTHON_API_DEBUG=false
FRONTEND_URL=http://127.0.0.1:8000,http://localhost:8000

# 单机模式：不使用 Kafka
QD_PROCESS_ROLE=legacy
STRATEGY_COMMANDS_ENABLED=false

# 不启动 Redis/Celery 时使用以下设置
CACHE_ENABLED=false
CELERY_TASKS_ENABLED=false
```

如果你计划接收邮件通知，再填写 SMTP 配置：

```dotenv
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=你的邮箱账号
SMTP_PASSWORD=邮箱授权码或密码
SMTP_FROM=你的邮箱账号
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

Gmail、QQ、163 等邮箱通常要求使用“应用专用密码/授权码”，不能直接使用网页登录密码。邮件配置的详细说明见[邮件通知配置](NOTIFICATION_EMAIL_CONFIG_CN.md)。

### 4.1 关于管理员账号

第一次连接一个**空数据库**时，应用会使用 `.env` 中的 `ADMIN_USER`、`ADMIN_PASSWORD` 和 `ADMIN_EMAIL` 创建管理员。

如果数据库中已经有用户，修改 `.env` 不等于重置已有用户密码；此时请使用数据库中已有的账号登录，或通过已有管理员功能修改密码。遇到 `Invalid credentials` 时，先确认：

1. 登录用户名不是邮箱，而是 `ADMIN_USER` 对应的用户名；
2. `.env` 是项目根目录的文件，而不是只修改了 `backend_api_python/.env`；
3. 后端连接的是你以为的那个数据库；
4. 数据库已经存在用户时，不能假设新的 `ADMIN_PASSWORD` 会覆盖旧密码。

## 5. 初始化数据库

保持虚拟环境已激活，在后端目录执行：

```bash
cd /Users/chinaxxren/Money/QuantDinger/backend_api_python
source .venv/bin/activate
QD_PROCESS_ROLE=migration python -m app.commands.migrate
```

迁移成功后应看到类似 `database bootstrap finished` 的完成日志。迁移失败时，先检查 PostgreSQL 是否运行，以及 `DATABASE_URL` 的用户名、密码、主机、端口和数据库名。

## 6. 启动后端

### 方式 A：个人单机开发模式（推荐）

这种方式只需要一个后端进程，不需要 Redis、Celery 或 Kafka：

```bash
cd /Users/chinaxxren/Money/QuantDinger/backend_api_python
source .venv/bin/activate
QD_PROCESS_ROLE=legacy STRATEGY_COMMANDS_ENABLED=false python run.py
```

默认监听：`http://127.0.0.1:5000`。

`legacy` 在本地单进程中启动应用所需的进程内支持服务，适合个人使用、策略编辑、行情查看、回测和本机调试。不要把 Flask 开发服务器直接暴露到公网。

### 方式 B：单机多进程模式（需要长期运行策略时推荐）

如果要让策略、交易会话和调度服务在 API 重启后保持职责隔离，请分别打开三个终端。每个终端都执行 `cd` 和 `source`：

**终端 1：API**

```bash
cd /Users/chinaxxren/Money/QuantDinger/backend_api_python
source .venv/bin/activate
QD_PROCESS_ROLE=api STRATEGY_COMMANDS_ENABLED=true python run.py
```

**终端 2：策略交易 worker**

```bash
cd /Users/chinaxxren/Money/QuantDinger/backend_api_python
source .venv/bin/activate
python -m app.commands.trading_worker
```

**终端 3：调度 worker**

```bash
cd /Users/chinaxxren/Money/QuantDinger/backend_api_python
source .venv/bin/activate
python -m app.commands.scheduler
```

这种模式仍然不需要 Kafka。PostgreSQL 负责持久化命令、租约、心跳和运行状态；K 线收盘事件由 trading worker 在进程内处理。

### 方式 C：Gunicorn API（可选）

需要用更接近生产的 HTTP 服务器时，可把终端 1 的命令替换为：

```bash
cd /Users/chinaxxren/Money/QuantDinger/backend_api_python
source .venv/bin/activate
QD_PROCESS_ROLE=api STRATEGY_COMMANDS_ENABLED=true gunicorn -c gunicorn_config.py run:app
```

Gunicorn 只负责 HTTP API；长期策略和调度仍应由上面的 trading worker、scheduler 进程负责。

## 7. 可选：启用 Redis 和 Celery

不启动 Redis/Celery 时，缓存会关闭，部分有限的异步 AI、报告和维护任务不能按队列执行或会使用本地 fallback；这不影响 Kafka 已移除，也不影响基础登录和单机策略运行。

如果需要缓存和完整的异步任务链路，在本机安装并启动 Redis，然后在 `.env` 中设置：

```dotenv
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
CELERY_REDIS_HOST=127.0.0.1
CELERY_REDIS_PORT=6379
CACHE_ENABLED=true
CELERY_TASKS_ENABLED=true
```

先启动 Redis，再打开两个终端运行：

```bash
cd /Users/chinaxxren/Money/QuantDinger/backend_api_python
source .venv/bin/activate
celery -A app.celery_app:celery_app worker --loglevel=INFO -Q jobs,ai,maintenance --concurrency=2
```

```bash
cd /Users/chinaxxren/Money/QuantDinger/backend_api_python
source .venv/bin/activate
celery -A app.celery_app:celery_app beat --loglevel=INFO --schedule=./data/celerybeat-schedule
```

Redis 不是 Kafka 的替代依赖：Redis 在这里用于缓存和 Celery 任务队列，Kafka 在当前单机版本中不需要配置。

## 8. 启动前端页面（不用 Docker）

当前前端源码在项目根目录的 `QuantDinger-Vue/`。如果该目录已经存在：

```bash
cd /Users/chinaxxren/Money/QuantDinger/QuantDinger-Vue
corepack enable
pnpm install --frozen-lockfile
pnpm run dev
```

前端默认地址是 `http://127.0.0.1:8000` 或 `http://localhost:8000`。前端开发环境已经将 `/api` 代理到 `http://127.0.0.1:5000`；如需覆盖代理目标：

```bash
VITE_DEV_PROXY_TARGET=http://127.0.0.1:5000 pnpm run dev
```

如果没有前端目录，先克隆前端仓库，再按其 `README_CN.md` 安装依赖。不要把交易所密钥、SMTP 密码或其他私密信息写入 `VITE_` 环境变量，因为它们会被编译进浏览器资源。

只运行后端时可以直接检查：

```bash
curl http://127.0.0.1:5000/api/health
```

如果启用 OpenAPI 文档（在 `.env` 设置 `OPENAPI_ENABLED=true`），还可以访问：

```text
http://127.0.0.1:5000/api/docs/swagger
```

## 9. 推荐启动顺序

日常个人使用可以按下面顺序操作：

1. 启动 PostgreSQL；
2. （可选）启动 Redis；
3. 执行数据库迁移；
4. 启动 API；
5. 需要长期策略时启动 trading worker 和 scheduler；
6. 启动前端 Vite；
7. 打开 `http://127.0.0.1:8000` 并使用管理员账号登录。

停止时，用各终端的 `Ctrl+C` 依次停止前端、worker、scheduler、API；数据库和 Redis 按本机服务管理方式停止。

## 10. 常见问题

### `Invalid credentials`

确认登录使用的是用户名而不是邮箱，并检查 API 连接的数据库是否正确。已有用户的密码不会因为修改 `.env` 自动重置；确认无误后使用已有管理员功能修改密码，或在确认本地数据库可删除的前提下重新创建一个空数据库再执行迁移。

### `Cannot connect to PostgreSQL` 或迁移失败

```bash
pg_isready -h 127.0.0.1 -p 5432
psql "$DATABASE_URL" -c 'SELECT 1;'
```

如果当前 shell 没有自动加载 `.env`，请确认后端通过项目根目录的 `.env` 启动；`run.py` 和 `app` 会自动加载它。也可以显式指定：

```bash
QUANTDINGER_ENV_FILE=/绝对路径/QuantDinger/.env QD_PROCESS_ROLE=migration python -m app.commands.migrate
```

### 页面能打开但请求失败或出现 CORS 错误

确认后端正在监听 5000 端口，前端代理目标是 `http://127.0.0.1:5000`，并且 `.env` 的 `FRONTEND_URL` 包含实际页面来源（例如 `http://127.0.0.1:8000`）。优先通过 Vite 的 `/api` 代理访问，不要让浏览器直接绕过代理访问后端。

### Redis 连接错误

如果暂时不需要缓存和 Celery，设置：

```dotenv
CACHE_ENABLED=false
CELERY_TASKS_ENABLED=false
```

然后重启后端。若已经启用 Celery，则必须先启动 Redis，并确认 `REDIS_HOST`、`CELERY_REDIS_HOST` 和端口正确。

### 邮件通知没有发送

检查 `SMTP_HOST`、端口、账号、授权码、TLS/SSL 组合和 `SMTP_FROM`，并确认邮箱服务商允许 SMTP。先在通知设置中保存配置，再触发一封测试通知；不要把 SMTP 密码提交到仓库。

### 策略没有运行

单进程模式下确认 API 是用 `QD_PROCESS_ROLE=legacy` 启动的。多进程模式下确认 trading worker 正常运行，并检查 `GET /api/health/workers` 或后端日志。只启动 `QD_PROCESS_ROLE=api` 而没有 trading worker 时，策略命令不会有实际执行者。

## 11. 相关文档

- [进程与任务所有权](../architecture/PROCESS_ROLES_AND_TASKS.md)
- [系统架构](../architecture/README_CN.md)
- [邮件通知配置](NOTIFICATION_EMAIL_CONFIG_CN.md)
- [安装故障排查](INSTALL_TROUBLESHOOTING_CN.md)
- [策略开发指南](../trading/STRATEGY_DEV_GUIDE.md)
