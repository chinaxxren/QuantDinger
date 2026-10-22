# Python 后端

本目录包含 QuantDinger 的 Flask API、领域服务、交易运行时、数据库迁移和后端测试。产品功能、环境准备与本地启动请从[项目说明](../README_CN.md)和[单机运行指南](../docs/CORE_SINGLE_HOST_CN.md)开始。

## 本地运行

日常单机使用从仓库根目录启动整个项目，不要单独启动后端：

```bash
./quantdinger.sh start
./quantdinger.sh status
./quantdinger.sh stop
```

启动脚本会执行数据库迁移并管理前后端进程。PostgreSQL 是必需依赖；Kafka 不使用。Redis/Celery 仅在启用对应缓存或异步任务时需要。

## 目录结构

```text
app/          Flask 应用、命令、配置、路由、服务和工具
migrations/   PostgreSQL 初始化结构与增量迁移
scripts/      API 契约导出和质量检查
tests/        单元、集成和发布门禁测试
```

单机进程职责、持久状态和事件处理方式见[单机架构](../docs/architecture/README_CN.md)。API 契约见[REST API 文档](../docs/api/README_CN.md)及 [`docs/api/openapi.yaml`](../docs/api/openapi.yaml)。

## 开发验证

在本目录创建并激活虚拟环境后安装 `requirements.txt` 中的依赖。运行单个测试：

```bash
python -m pytest tests/<测试文件>.py -q
```

修改路由或 OpenAPI 描述后重新导出契约：

```bash
python scripts/export_openapi.py
```

## 代码约定

- 路由负责请求解析、认证、调用服务和映射响应；领域逻辑放入服务层。
- 不把 Flask 请求对象传入领域服务。
- 交易所差异和数据规范化放在对应适配器附近。
- 状态写入应具备幂等性，并明确重试行为。
- 有限时长的异步工作由现有任务机制处理；持续运行的交易循环必须留在交易运行进程中。
- 源码注释、日志和内部错误信息使用英文；用户可见文案遵循中文界面约定。
