"""Metadata registry for QuantDinger agent tools.

This registry describes system workflows that the AI may plan around. It is not
an execution engine; routes that mutate state still enforce their own auth and
safety checks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolDefinition:
    id: str
    category: str
    label_zh: str
    label_en: str
    description_zh: str
    description_en: str
    route: str | None = None
    action: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    requires: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()
    risk_level: str = "read"
    read_only: bool = True
    enabled: bool = True
    priority: int = 50
    safety: str = ""

    def pick(self, language: str, zh: str, en: str) -> str:
        return zh if (language or "").lower().startswith("zh") else en

    def to_public(self, language: str) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "label": self.pick(language, self.label_zh, self.label_en),
            "description": self.pick(language, self.description_zh, self.description_en),
            "route": self.route,
            "action": self.action,
            "parameters": dict(self.parameters or {}),
            "requires": list(self.requires),
            "produces": list(self.produces),
            "risk_level": self.risk_level,
            "read_only": self.read_only,
            "enabled": self.enabled,
            "priority": self.priority,
            "safety": self.safety,
}
    def prompt_line(self, language: str) -> str:
        label = self.pick(language, self.label_zh, self.label_en)
        description = self.pick(language, self.description_zh, self.description_en)
        requires = ", ".join(self.requires) if self.requires else "none"
        produces = ", ".join(self.produces) if self.produces else "tool result"
        safety = f" Safety: {self.safety}" if self.safety else ""
        return (
            f"- {self.id}: {label}. {description} "
            f"Requires: {requires}. Produces: {produces}. "
            f"Risk: {self.risk_level}. Read-only: {self.read_only}.{safety}"
        )


TOOLS: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        id="market_data.lookup",
        category="market",
        label_zh="行情与K线查询",
        label_en="Market data lookup",
        description_zh="查询系统已有数据源中的价格、K线、成交量和基础指标。",
        description_en="Read prices, klines, volume, and basic indicators from configured data sources.",
        route="/api/indicator/kline",
        requires=("market", "symbol"),
        produces=("market_snapshot",),
        risk_level="read",
        priority=100,
    ),
    ToolDefinition(
        id="market_query.plan",
        category="market",
        label_zh="行情需求规划",
        label_en="Market query planning",
        description_zh="把自然语言问题归一为标的、周期、指标、回看长度和数据新鲜度要求。",
        description_en="Normalize a natural-language question into instruments, timeframes, metrics, lookback and freshness requirements.",
        requires=("user_question",),
        produces=("market_query_plan",),
        risk_level="read",
        priority=101,
    ),
    ToolDefinition(
        id="technical_analysis.compute",
        category="market",
        label_zh="技术证据计算",
        label_en="Technical evidence calculation",
        description_zh="基于已完成OHLCV计算指标、枢轴支撑阻力、量价关系与突破确认。",
        description_en="Compute indicators, pivot levels, volume-price evidence and breakout confirmation from closed OHLCV bars.",
        requires=("ohlcv", "market_query_plan"),
        produces=("technical_evidence",),
        risk_level="read",
        priority=99,
    ),
    ToolDefinition(
        id="settings.preflight",
        category="operations",
        label_zh="部署配置检查",
        label_en="Setup preflight",
        description_zh="检查 LLM、数据源、券商账户和通知配置是否可用。",
        description_en="Check LLM, data source, broker, and notification readiness.",
        route="/api/ai/agent/preflight",
        produces=("setup_checklist",),
        risk_level="read",
        priority=96,
    ),
    ToolDefinition(
        id="watchlist.add",
        category="workspace",
        label_zh="添加自选",
        label_en="Add watchlist item",
        description_zh="将用户确认的标的加入自选列表。",
        description_en="Add a user-confirmed symbol to the watchlist.",
        route="/api/market/watchlist/add",
        requires=("market", "symbol"),
        produces=("watchlist_item",),
        risk_level="write_config",
        read_only=False,
        priority=82,
    ),
    ToolDefinition(
        id="scheduled_analysis.create",
        category="automation",
        label_zh="创建定时分析任务",
        label_en="Create scheduled analysis",
        description_zh="在用户确认周期、通知方式和触发条件后创建 AI 定时分析任务。",
        description_en="Create an AI scheduled analysis after interval, notification, and trigger conditions are confirmed.",
        requires=("market", "symbol", "interval", "notification", "conditions"),
        produces=("scheduled_task",),
        risk_level="write_config",
        read_only=False,
        priority=84,
        safety="Ask for missing schedule fields before creating the task.",
    ),
    ToolDefinition(
        id="indicator.generate",
        category="strategy",
        label_zh="生成指标研发草稿",
        label_en="Generate indicator draft",
        description_zh="根据用户确认的需求生成只用于图表展示的 QuantDinger 指标草稿。",
        description_en="Generate a chart-only QuantDinger indicator draft after requirements are confirmed.",
        route="/indicator-ide",
        requires=("indicator_requirements",),
        produces=("indicator_code", "visualization_plan"),
        risk_level="write_draft",
        read_only=False,
        priority=90,
    ),
    ToolDefinition(
        id="script_strategy.generate",
        category="strategy",
        label_zh="生成脚本策略",
        label_en="Generate script strategy",
        description_zh="根据已确认需求生成 Strategy API V2 Python 草稿。",
        description_en="Generate a Strategy API V2 Python draft after requirements are confirmed.",
        route="/strategy-ide?tab=script",
        requires=("strategy_requirements",),
        produces=("strategy_source", "backtest_plan"),
        risk_level="write_draft",
        read_only=False,
        priority=88,
    ),
)


def list_tools(language: str = "zh-CN") -> list[dict[str, Any]]:
    items = sorted((tool for tool in TOOLS if tool.enabled), key=lambda tool: (-tool.priority, tool.id))
    return [tool.to_public(language) for tool in items]


def build_tool_prompt(language: str = "zh-CN", intent: str = "") -> str:
    intent_text = (intent or "").lower()
    tools = [tool for tool in TOOLS if tool.enabled]
    if intent_text:
        targeted = [
            tool
            for tool in tools
            if tool.category in intent_text or any(token in tool.id for token in intent_text.split("_"))
        ]
        if targeted:
            tools = targeted
    tools = sorted(tools, key=lambda tool: (-tool.priority, tool.id))[:8]
    lines = [
        "[QuantDinger tool registry]",
        "These are available system workflows. Treat write tools as user-confirmed handoffs, not autonomous execution.",
        "Live trading boundary: strategy deployments are created stopped. Live orders require explicit user confirmation and server-side enablement.",
    ]
    lines.extend(tool.prompt_line(language) for tool in tools)
    return "\n".join(lines)


def public_tool_registry(language: str = "zh-CN") -> dict[str, Any]:
    categories: dict[str, int] = {}
    for tool in TOOLS:
        if tool.enabled:
            categories[tool.category] = categories.get(tool.category, 0) + 1
    return {
        "version": "2026.10.22.1",
        "total": sum(categories.values()),
        "categories": categories,
        "tools": list_tools(language),
    }
