# Interactive Brokers（IBKR）交易适配器

本模块通过 TWS 或 IB Gateway 支持 IBKR 交易。使用前需在本机启动并登录 TWS/Gateway，在 API 设置中启用 Socket 客户端，并允许本机连接。实时行情可能需要单独订阅。

## 常用端口

| 客户端 | 实盘 | 模拟盘 |
| --- | ---: | ---: |
| TWS | 7496 | 7497 |
| IB Gateway | 4001 | 4002 |

每个 `clientId` 同时只能保持一个连接。手动连接测试默认使用 `1`；策略交易通常使用凭证中的 `ibkr_client_id`，未设置时默认 `7`。避免多个客户端复用同一个 ID，以免互相断开。

## 连接示例

```bash
curl -X POST http://127.0.0.1:5000/api/ibkr/connect \\
  -H 'Content-Type: application/json' \\
  -d '{"host":"127.0.0.1","port":7497,"clientId":1}'
```

当前主要支持美股代码，例如 `AAPL`、`TSLA`。账户、持仓、订单、行情和交易接口以登录后的 API 契约及券商账户权限为准。`readonly` 模式用于只读查询；真实下单前先在模拟账户验证连接、数量、价格和撤单流程。

更多交易前检查见[IBKR 交易指南](../../../../docs/trading/IBKR_TRADING_GUIDE_CN.md)和[实盘交易安全指南](../../../../docs/trading/LIVE_TRADING_SAFETY_CN.md)。
