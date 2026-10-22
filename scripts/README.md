# 仓库脚本说明

这些脚本用于项目启动、配置和仓库检查。前端构建命令请查看独立目录 `QuantDinger-Vue/README_CN.md`。

根目录脚本：

| 脚本 | 用途 |
| --- | --- |
| `../quantdinger.sh` | 本地后端与前端的启动、停止、重启和状态查看；不依赖 Docker。 |

仓库维护脚本：

| 脚本 | 用途 |
| --- | --- |
| `generate-secret-key.sh`、`generate-secret-key.ps1` | 生成安全随机密钥并更新 `.env`。 |
| `sync_env.py` | 补充 `.env.example` 中缺少的配置项，不覆盖已有值。 |
| `bump_version.py`、`check_version.py` | 更新并校验版本文件。 |
| `check_docs.py` | 检查文档结构、站内链接、代码围栏和引用资源。 |
| `check_mojibake.py` | 检查文件中常见的编码乱码。 |
