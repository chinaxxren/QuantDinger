# Alpaca 交易适配器

本模块通过 Alpaca REST API 支持美股、ETF 和加密货币交易。账号凭证在“账户 → 券商账户”中配置，并按用户加密保存；纸面交易和实盘使用不同的账户凭证与 API 地址。开始交易前请先使用纸面账户验证连接和下单流程。

## 依赖与客户端

运行环境需要 `alpaca-py`。模块对外提供 `AlpacaClient` 和 `AlpacaConfig`：

```python
from app.services.alpaca_trading import AlpacaClient, AlpacaConfig

config = AlpacaConfig(api_key="...", secret_key="...", paper=True)
client = AlpacaClient(config)
client.connect()
summary = client.get_account_summary()
client.disconnect()
```

加密货币使用 `market_type="crypto"`，交易对采用 Alpaca 格式，例如 `BTC/USD`。美股类别股使用 `BRK.B`。不要把其他交易所的 `BTC/USDT` 格式直接当作 Alpaca 市场标识。

## 能力边界

当前适配器覆盖账户、持仓、订单、行情和基础市价/限价下单。是否可交易、交易时段、最小数量、行情订阅和账户权限以 Alpaca 账户及官方 API 返回为准。未接入的高级订单、期权和行情 WebSocket 不应被视为已支持。

连接测试和下单走 REST Trading API，不使用行情 WebSocket。若独立脚本收到 WebSocket 认证错误，请检查脚本的认证消息和订阅格式；这不代表本模块的 REST 连接配置有误。

更多交易风险和上线检查见[实盘交易安全指南](../../../../docs/trading/LIVE_TRADING_SAFETY_CN.md)。官方资料：[alpaca-py](https://alpaca.markets/sdks/python)、[Alpaca API](https://docs.alpaca.markets/reference)。
