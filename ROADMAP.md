# QuantDinger 项目路线图

路线图用于记录方向，不代表发布日期承诺。具体范围和进度以对应的 GitHub Issue、Project 和里程碑为准；规划会根据技术评审、用户反馈、安全审查和数据提供方验证调整。

- [QuantDinger 路线图项目](https://github.com/orgs/OpenByteInc/projects/1)
- [路线图索引 #257](https://github.com/OpenByteInc/QuantDinger/issues/257)
- [投研与交易执行里程碑](https://github.com/OpenByteInc/QuantDinger/milestone/1)

## 规划状态

以下状态名与 GitHub 项目字段一致，保留英文以便检索：

| 状态 | 含义 |
| --- | --- |
| `Proposed` | 已记录问题，范围尚未确认。 |
| `RFC` | 正在讨论产品行为或架构。 |
| `Ready` | 验收条件和职责边界已明确。 |
| `Claimed` | 贡献者与维护者已确认任务范围。 |
| `In progress` | 正在实现或编写文档。 |
| `Review` | Pull Request 正在审查。 |
| `Done` | 改动已合并并完成文档记录。 |

`Now`、`Next`、`Later` 和 `Exploring` 是规划时间范围，不构成交付保证。

## 当前主题

当前公开主题聚焦于从动态股票池筛选，逐步完善组合研究、配对/价差建模、交易执行和可审计分析：

| 工作方向 | 优先级 | 规划范围 | 跟踪问题 |
| --- | --- | --- | --- |
| 动态股票池与时点筛选 | P0 | Now | [#251](https://github.com/OpenByteInc/QuantDinger/issues/251) |
| 组合策略与定时再平衡 | P0 | Now | [#252](https://github.com/OpenByteInc/QuantDinger/issues/252) |
| 配对与价差交易基础 | P0 | Now | [#253](https://github.com/OpenByteInc/QuantDinger/issues/253) |
| 多腿订单协调与恢复 | P0 | Next | [#254](https://github.com/OpenByteInc/QuantDinger/issues/254) |
| 配对持仓、盈亏与分析 | P1 | Next | [#255](https://github.com/OpenByteInc/QuantDinger/issues/255) |
| 可审计的 AI 入场过滤 | P1 | Done | [#263](https://github.com/OpenByteInc/QuantDinger/issues/263) |
| 外部信号接入 | P1 | Next | [#256](https://github.com/OpenByteInc/QuantDinger/issues/256) |

## 参与路线图

只有标记为 `Ready` 且明确欢迎贡献的任务，才适合直接开始实现。较大的路线图主题应先拆成小任务。开始前请阅读相关 Issue 和架构文档，在 Issue 中说明计划、涉及模块和验证方式，并等待维护者确认范围。

宽泛的产品构想可在 [GitHub Discussions](https://github.com/OpenByteInc/QuantDinger/discussions) 讨论；范围明确的改进可直接提交功能请求。不要在公开内容中包含凭据、私人财务记录或可利用的安全细节。
