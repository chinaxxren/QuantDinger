"""Registry for the unified QuantDinger indicator library.

Each indicator implementation lives in exactly one module under
``indicator_library/indicators``. The catalog owns the execution adapter, so
callers only need the indicator ID and never maintain a second directory or
registry for calculations.
"""

from __future__ import annotations

from typing import Dict, List

from app.services.indicator_library.catalog import get_indicator_source_code
from app.services.indicator_library.types import IndicatorSpec

BUILTIN_INDICATOR_PACK_ANCHOR_NAME = "[Sample] SuperTrend Trend-Following"

_SPECS = (
    IndicatorSpec(
        identifier="supertrend_trend_following",
        name=BUILTIN_INDICATOR_PACK_ANCHOR_NAME,
        description=("Classic SuperTrend: Wilder ATR channel direction flips with chart-only long/short markers."),
        category="trend",
        tags=("trend", "atr", "filter"),
    ),
    IndicatorSpec(
        identifier="range_filter",
        name="[Default] Range Filter",
        description=("Volatility-adaptive price filter with upper/lower range bands and edge-triggered trend markers."),
        category="trend",
        tags=("trend", "range", "volatility"),
    ),
    IndicatorSpec(
        identifier="powertrend_volume_range_filter",
        name="[Default] PowerTrend Volume Range Filter",
        description=("Range Filter trend state confirmed by EMA trend strength and relative volume expansion."),
        category="volume",
        tags=("trend", "range", "volume"),
    ),
    IndicatorSpec(
        identifier="g_channels",
        name="[Default] G Channels",
        description=(
            "Recursive high/low channel with a causal midline for trend bias and breakout-style chart markers."
        ),
        category="channel",
        tags=("channel", "trend", "breakout"),
    ),
    IndicatorSpec(
        identifier="pmax_trend_filter",
        name="[Default] PMax Trend Filter",
        description=("EMA baseline plus ATR trailing stop bands inspired by PMax-style trend filters."),
        category="trend",
        tags=("trend", "atr", "trailing-stop"),
    ),
    IndicatorSpec(
        identifier="donchian_channel",
        name="[Default] Donchian Channel",
        description=("Prior-period high/low channel and midpoint with chart-only breakout markers."),
        category="channel",
        tags=("channel", "breakout", "volatility"),
    ),
    IndicatorSpec(
        identifier="rsi_momentum",
        name="[Default] RSI Momentum",
        description="Wilder RSI momentum oscillator displayed in a separate chart pane.",
        category="momentum",
        tags=("momentum", "oscillator", "rsi"),
    ),
    IndicatorSpec(
        identifier="chandelier_exit",
        name="[Default] Chandelier Exit",
        description=("ATR trailing stop levels derived from rolling highs/lows with visual trend flips."),
        category="trend",
        tags=("trend", "atr", "trailing-stop"),
    ),
    IndicatorSpec(
        identifier="macd",
        name="[Default] MACD",
        description="MACD, signal line, and histogram shown in a separate chart pane.",
        category="momentum",
        tags=("momentum", "oscillator", "macd"),
    ),
    IndicatorSpec(
        identifier="bollinger_bands",
        name="[Default] Bollinger Bands",
        description="Moving-average volatility bands with configurable period and deviation.",
        category="volatility",
        tags=("volatility", "band", "mean-reversion"),
    ),
    IndicatorSpec(
        identifier="stochastic_oscillator",
        name="[Default] Stochastic Oscillator",
        description="Smoothed stochastic %K and %D momentum oscillator in a separate pane.",
        category="momentum",
        tags=("momentum", "oscillator", "stochastic"),
    ),
    IndicatorSpec(
        identifier="adx",
        name="[Default] ADX",
        description="Average Directional Index with +DI and -DI trend-strength lines.",
        category="trend",
        tags=("trend", "momentum", "adx"),
    ),
    IndicatorSpec(
        identifier="nrtr",
        name="[Default] NRTR",
        description="Percentage-based trailing stop with optional volatility adjustment.",
        category="trend",
        tags=("trend", "trailing-stop", "volatility"),
    ),
    IndicatorSpec(
        identifier="turtle_trade_channels",
        name="[Default] Turtle Trade Channels",
        description="Prior-bar breakout and exit channels inspired by Turtle trading rules.",
        category="channel",
        tags=("channel", "breakout", "trend"),
    ),
    IndicatorSpec(
        identifier="wavetrend_oscillator",
        name="[Default] WaveTrend Oscillator",
        description="ESA/deviation-based WaveTrend oscillator with signal line.",
        category="momentum",
        tags=("momentum", "oscillator", "wavetrend"),
    ),
    IndicatorSpec(
        identifier="nadaraya_watson_envelope",
        name="[Default] Nadaraya-Watson Envelope",
        description=("Causal Gaussian-kernel smoother with ATR envelope bands for mean reversion zones."),
        category="channel",
        tags=("channel", "kernel", "mean-reversion"),
    ),
    IndicatorSpec(
        identifier="atr_rope",
        name="[Default] ATR Rope",
        description=("ATR-step trend filter with a trailing rope and chart-only direction-change markers."),
        category="trend",
        tags=("trend", "atr", "filter"),
    ),
    IndicatorSpec(
        identifier="vwap_price_channel",
        name="[Default] VWAP Price Channel",
        description="Rolling volume-weighted price channel with deviation bands.",
        category="channel",
        tags=("volume", "vwap", "channel"),
    ),
    IndicatorSpec(
        identifier="dynamic_linear_regression_channel",
        name="[Default] Dynamic Linear Regression Channel",
        description=("Causal rolling linear-regression centerline with residual-deviation bands."),
        category="channel",
        tags=("channel", "regression", "volatility"),
    ),
    IndicatorSpec(
        identifier="ut_bot_alerts",
        name="[Default] UT Bot Alerts",
        description="ATR trailing stop with chart-only price-cross markers.",
        category="trend",
        tags=("trend", "atr", "signals"),
    ),
    IndicatorSpec(
        identifier="alpha_trend",
        name="[Default] AlphaTrend",
        description="RSI-confirmed ATR trend line with chart-only crossover markers.",
        category="trend",
        tags=("trend", "atr", "momentum"),
    ),
    IndicatorSpec(
        identifier="twin_range_filter",
        name="[Default] Twin Range Filter",
        description="Dual-period volatility filter with chart-only direction-change markers.",
        category="trend",
        tags=("trend", "range", "volatility"),
    ),
    IndicatorSpec(
        identifier="qqe_signals",
        name="[Default] QQE Signals",
        description=("Smoothed RSI with volatility-adaptive QQE trailing levels and chart-only signals."),
        category="momentum",
        tags=("momentum", "rsi", "volatility"),
    ),
    IndicatorSpec(
        identifier="half_trend",
        name="[Default] HalfTrend",
        description="Swing-channel trend line with ATR bands and chart-only reversal markers.",
        category="trend",
        tags=("trend", "swing", "atr"),
    ),
    IndicatorSpec(
        identifier="pivot_point_supertrend",
        name="[Default] Pivot Point Supertrend",
        description="ATR trend bands centered on confirmed rolling swing pivots.",
        category="trend",
        tags=("trend", "pivot", "atr"),
    ),
    IndicatorSpec(
        identifier="variable_moving_average",
        name="[Default] Variable Moving Average",
        description="VIDYA-style adaptive moving average driven by normalized price momentum.",
        category="trend",
        tags=("trend", "moving-average", "adaptive"),
    ),
    IndicatorSpec(
        identifier="gaussian_filter_trend",
        name="[Default] Gaussian Filter Trend",
        description="Causal Gaussian-style smoother with ATR trend bands and visual reversal markers.",
        category="trend",
        tags=("trend", "filter", "atr"),
    ),
    IndicatorSpec(
        identifier="delta_rsi_oscillator",
        name="[Default] Delta RSI Oscillator",
        description="Fast-minus-slow RSI momentum spread with signal and histogram.",
        category="momentum",
        tags=("momentum", "rsi", "oscillator"),
    ),
    IndicatorSpec(
        identifier="keltner_channel",
        name="[Default] Keltner Channel",
        description="EMA centerline with ATR-based volatility envelopes.",
        category="channel",
        tags=("channel", "atr", "volatility"),
    ),
    IndicatorSpec(
        identifier="aroon_oscillator",
        name="[Default] Aroon Oscillator",
        description="Aroon Up/Down lines and oscillator derived from rolling high/low recency.",
        category="momentum",
        tags=("momentum", "oscillator", "trend"),
    ),
    IndicatorSpec(
        identifier="chaikin_money_flow",
        name="[Default] Chaikin Money Flow",
        description="Rolling volume-weighted buying and selling pressure oscillator.",
        category="volume",
        tags=("volume", "money-flow", "oscillator"),
    ),
    IndicatorSpec(
        identifier="true_strength_index",
        name="[Default] True Strength Index",
        description="Double-smoothed, normalized momentum with a signal line.",
        category="momentum",
        tags=("momentum", "oscillator", "trend"),
    ),
    IndicatorSpec(
        identifier="fisher_transform",
        name="[Default] Fisher Transform",
        description="Recursive Fisher transform of normalized rolling price position.",
        category="momentum",
        tags=("momentum", "oscillator", "reversal"),
    ),
    IndicatorSpec(
        identifier="ultimate_oscillator",
        name="[Default] Ultimate Oscillator",
        description="Buying-pressure oscillator combining three lookback horizons.",
        category="momentum",
        tags=("momentum", "oscillator", "volume"),
    ),
    IndicatorSpec(
        identifier="coppock_curve",
        name="[Default] Coppock Curve",
        description="Long-term momentum curve from weighted dual rate-of-change readings.",
        category="momentum",
        tags=("momentum", "roc", "trend"),
    ),
    IndicatorSpec(
        identifier="klinger_volume_oscillator",
        name="[Default] Klinger Volume Oscillator",
        description="Signed volume-force oscillator with a signal line.",
        category="volume",
        tags=("volume", "oscillator", "momentum"),
    ),
    IndicatorSpec(
        identifier="schaff_trend_cycle",
        name="[Default] Schaff Trend Cycle",
        description="Smoothed double-stochastic MACD cycle oscillator.",
        category="momentum",
        tags=("momentum", "cycle", "oscillator"),
    ),
    IndicatorSpec(
        identifier="elder_ray_index",
        name="[Default] Elder Ray Index",
        description="Bull Power and Bear Power measured against an exponential moving average.",
        category="momentum",
        tags=("momentum", "volume", "trend"),
    ),
    IndicatorSpec(
        identifier="force_index",
        name="[Default] Force Index",
        description="Volume-weighted price-change momentum with configurable EMA smoothing.",
        category="volume",
        tags=("volume", "momentum", "oscillator"),
    ),
    IndicatorSpec(
        identifier="relative_vigor_index",
        name="[Default] Relative Vigor Index",
        description="OHLC vigor oscillator with a weighted signal line.",
        category="momentum",
        tags=("momentum", "oscillator", "trend"),
    ),
    IndicatorSpec(
        identifier="trix",
        name="[Default] TRIX",
        description="Triple-smoothed EMA momentum with a signal line.",
        category="momentum",
        tags=("momentum", "oscillator", "moving-average"),
    ),
    IndicatorSpec(
        identifier="ease_of_movement",
        name="[Default] Ease of Movement",
        description="Volume-normalized price movement with a smoothed EOM line.",
        category="volume",
        tags=("volume", "momentum", "oscillator"),
    ),
    IndicatorSpec(
        identifier="mass_index",
        name="[Default] Mass Index",
        description="Range-expansion index from double-smoothed high-low movement.",
        category="volatility",
        tags=("volatility", "range", "oscillator"),
    ),
    IndicatorSpec(
        identifier="detrended_price_oscillator",
        name="[Default] Detrended Price Oscillator",
        description="Price deviation from a lagged trailing simple moving average.",
        category="momentum",
        tags=("momentum", "cycle", "oscillator"),
    ),
    IndicatorSpec(
        identifier="chande_momentum_oscillator",
        name="[Default] Chande Momentum Oscillator",
        description="Bounded momentum oscillator based on rolling gains and losses.",
        category="momentum",
        tags=("momentum", "oscillator", "reversal"),
    ),
    IndicatorSpec(
        identifier="percentage_price_oscillator",
        name="[Default] Percentage Price Oscillator",
        description="Percentage-scaled EMA spread with signal and histogram.",
        category="momentum",
        tags=("momentum", "moving-average", "oscillator"),
    ),
    IndicatorSpec(
        identifier="vortex_indicator",
        name="[Default] Vortex Indicator",
        description="Positive and negative directional movement ratios over true range.",
        category="trend",
        tags=("trend", "directional", "volatility"),
    ),
    IndicatorSpec(
        identifier="relative_volatility_index",
        name="[Default] Relative Volatility Index",
        description="Directional volatility oscillator normalized to a 0-100 scale.",
        category="volatility",
        tags=("volatility", "momentum", "oscillator"),
    ),
    IndicatorSpec(
        identifier="price_volume_trend",
        name="[Default] Price Volume Trend",
        description="Cumulative percentage price change weighted by volume.",
        category="volume",
        tags=("volume", "trend", "momentum"),
    ),
    IndicatorSpec(
        identifier="know_sure_thing",
        name="[Default] Know Sure Thing",
        description="Multi-horizon momentum oscillator with a signal line.",
        category="momentum",
        tags=("momentum", "cycle", "oscillator"),
    ),
    IndicatorSpec(
        identifier="connors_rsi",
        name="[Default] Connors RSI",
        description="Composite short-term oscillator combining price RSI, streak RSI, and return rank.",
        category="momentum",
        tags=("momentum", "rsi", "oscillator"),
    ),
    IndicatorSpec(
        identifier="volume_oscillator",
        name="[Default] Volume Oscillator",
        description="Percentage difference between fast and slow volume averages.",
        category="volume",
        tags=("volume", "momentum", "oscillator"),
    ),
    IndicatorSpec(
        identifier="balance_of_power",
        name="[Default] Balance of Power",
        description="Per-bar buying and selling pressure from open, high, low, and close.",
        category="momentum",
        tags=("momentum", "volume", "oscillator"),
    ),
    IndicatorSpec(
        identifier="choppiness_index",
        name="[Default] Choppiness Index",
        description="Range-versus-true-range measure of market choppiness.",
        category="volatility",
        tags=("volatility", "range", "trend"),
    ),
    IndicatorSpec(
        identifier="ulcer_index",
        name="[Default] Ulcer Index",
        description="Rolling root-mean-square drawdown from recent highs.",
        category="volatility",
        tags=("volatility", "drawdown", "risk"),
    ),
    IndicatorSpec(
        identifier="double_exponential_moving_average",
        name="[Default] Double Exponential Moving Average",
        description="Reduced-lag moving average formed from two exponential averages.",
        category="trend",
        tags=("trend", "moving-average", "smoothing"),
    ),
    IndicatorSpec(
        identifier="kaufman_adaptive_moving_average",
        name="[Default] Kaufman Adaptive Moving Average",
        description="Adaptive moving average driven by directional efficiency.",
        category="trend",
        tags=("trend", "moving-average", "adaptive"),
    ),
    IndicatorSpec(
        identifier="chaikin_oscillator",
        name="[Default] Chaikin Oscillator",
        description="Fast-minus-slow EMA of volume-weighted accumulation and distribution.",
        category="volume",
        tags=("volume", "momentum", "oscillator"),
    ),
    IndicatorSpec(
        identifier="std_filtered_n_pole_gaussian_filter",
        name="[Default] STD-Filtered N-Pole Gaussian Filter",
        description="Standard-deviation filtered multi-pole Gaussian-style price smoother.",
        category="trend",
        tags=("trend", "filter", "volatility"),
    ),
    IndicatorSpec(
        identifier="adaptive_trend_filter",
        name="[Default] Adaptive Trend Filter",
        description="Variance-adaptive price filter with ATR supertrend bands.",
        category="trend",
        tags=("trend", "adaptive", "atr"),
    ),
    IndicatorSpec(
        identifier="multi_step_vegas_supertrend",
        name="[Default] Multi-Step Vegas SuperTrend",
        description="Vegas volatility channel with adaptive ATR supertrend reversals.",
        category="trend",
        tags=("trend", "supertrend", "volatility"),
    ),
    IndicatorSpec(
        identifier="hull_moving_average",
        name="[Default] Hull Moving Average",
        description="Reduced-lag weighted moving average for trend visualization.",
        category="trend",
        tags=("trend", "moving-average", "smoothing"),
    ),
    IndicatorSpec(
        identifier="stochastic_rsi",
        name="[Default] Stochastic RSI",
        description="Stochastic normalization of RSI with smoothed momentum lines.",
        category="momentum",
        tags=("momentum", "rsi", "oscillator"),
    ),
    IndicatorSpec(
        identifier="ichimoku_cloud",
        name="[Default] Ichimoku Cloud",
        description="Causal Ichimoku conversion, base, and cloud boundary lines.",
        category="trend",
        tags=("trend", "cloud", "support-resistance"),
    ),
    IndicatorSpec(
        identifier="optimized_trend_tracker",
        name="[Default] Optimized Trend Tracker",
        description="CMO-adaptive moving average with optimized trailing trend lines.",
        category="trend",
        tags=("trend", "adaptive", "trailing-stop"),
    ),
    IndicatorSpec(
        identifier="dsav_dynamic_swing_vwap",
        name="[Default] DSAV Dynamic Swing Anchored VWAP",
        description="Causal swing-anchored EWMA VWAP with optional ATR adaptation.",
        category="volume",
        tags=("volume", "vwap", "swing"),
    ),
    IndicatorSpec(
        identifier="lowess_locally_weighted_scatterplot_smoothing",
        name="[Default] LOWESS Locally Weighted Scatterplot Smoothing",
        description="Volatility-weighted Gaussian price smoother with a causal LOWESS stage.",
        category="trend",
        tags=("trend", "smoothing", "lowess"),
    ),
    IndicatorSpec(
        identifier="john_ehlers_price_radio",
        name="[Default] John Ehlers The Price Radio",
        description="AM volatility envelope and FM Super Smoother of candle-body price movement.",
        category="momentum",
        tags=("ehlers", "am", "fm", "oscillator"),
    ),
    IndicatorSpec(
        identifier="adaptive_trend_trail",
        name="[Default] Adaptive Trend Trail",
        description="Multi-factor adaptive trend state with SuperTrend confirmation and chart-only trails/signals.",
        category="trend",
        tags=("trend", "adaptive", "supertrend", "trail"),
    ),
    IndicatorSpec(
        identifier="spma_trend_nal",
        name="[Default] SPMA Trend NAL",
        description="Shock-percentile moving average with adaptive volatility bands and NAL trend signals.",
        category="trend",
        tags=("trend", "adaptive", "volatility", "bands"),
    ),
    IndicatorSpec(
        identifier="lorentzian_classification",
        name="[Default] Lorentzian Classification",
        description=(
            "Causal Lorentzian-distance KNN classification with technical features, "
            "filters, and kernel-regression chart signals."
        ),
        category="machine-learning",
        tags=("machine-learning", "knn", "lorentzian", "signals"),
    ),
    IndicatorSpec(
        identifier="divergence_many_indicators",
        name="[Default] Divergence for Many Indicators v4",
        description=(
            "Causal regular and hidden bullish/bearish divergence detection across momentum and volume indicators."
        ),
        category="momentum",
        tags=("momentum", "divergence", "technical-analysis", "signals"),
    ),
    IndicatorSpec(
        identifier="knn_lorentzian_machine_learning",
        name="[Default] kNN Lorentzian Machine Learning",
        description=(
            "Causal k-nearest-neighbor Lorentzian classifier with normalized "
            "technical features and chart-only confidence signals."
        ),
        category="machine-learning",
        tags=("machine-learning", "knn", "lorentzian", "signals"),
    ),
    IndicatorSpec(
        identifier="trendlines_with_breaks",
        name="[Default] Trendlines with Breaks",
        description="Causal swing-pivot support/resistance trendlines with chart-only breakout markers.",
        category="trend",
        tags=("trend", "support-resistance", "breakout"),
    ),
    IndicatorSpec(
        identifier="trend_state_signals",
        name="[Default] Trend State Signals",
        description="Adaptive step filter with trend state and chart-only reversal markers.",
        category="trend",
        tags=("trend", "step-filter", "volatility"),
    ),
    IndicatorSpec(
        identifier="auto_chart_patterns",
        name="[Default] Auto Chart Patterns",
        description=(
            "Causal channel, wedge, and triangle detection from confirmed price pivots "
            "with chart-only breakout markers."
        ),
        category="pattern",
        tags=("pattern", "channel", "wedge", "triangle", "breakout"),
    ),
    IndicatorSpec(
        identifier="swing_highs_lows_candle_patterns",
        name="[Default] Swing Highs/Lows & Candle Patterns",
        description=("Causal swing structure and candle-pattern detector with confirmed pivot markers."),
        category="pattern",
        tags=("pattern", "swing", "candlestick", "support-resistance"),
    ),
    IndicatorSpec(
        identifier="scalping_pullback_tool",
        name="[Default] Scalping PullBack Tool",
        description=("PAC channel and EMA trend filter with causal Heikin-Ashi pullback markers."),
        category="trend",
        tags=("trend", "pullback", "pac", "heikin-ashi"),
    ),
    IndicatorSpec(
        identifier="adaptive_supertrend",
        name="[Default] Adaptive SuperTrend",
        description=("TQI-adaptive ATR SuperTrend with causal trend bands and chart-only reversal markers."),
        category="trend",
        tags=("trend", "supertrend", "atr", "adaptive"),
    ),
    IndicatorSpec(
        identifier="zero_lag_trend_signals",
        name="[Default] Zero Lag Trend Signals",
        description=(
            "Zero-lag EMA trend baseline with ATR volatility bands and chart-only trend-flip and pullback signals."
        ),
        category="trend",
        tags=("trend", "zero-lag", "atr", "signals"),
    ),
    IndicatorSpec(
        identifier="range_filter_signals",
        name="[Default] Range Filter B&S Signals",
        description=("Double-EMA range filter with directional bands and chart-only BUY/SELL signals."),
        category="trend",
        tags=("trend", "range", "signals", "volatility"),
    ),
    IndicatorSpec(
        identifier="range_filter_buy_sell",
        name="[Default] Range Filter Buy and Sell",
        description=("Configurable-source range filter with directional bands and chart-only Buy/Sell signals."),
        category="trend",
        tags=("trend", "range", "signals", "volatility"),
    ),
    IndicatorSpec(
        identifier="follow_line_indicator",
        name="[Default] Follow Line Indicator",
        description=("Bollinger breakout and ATR trailing line with chart-only trend reversal signals."),
        category="trend",
        tags=("trend", "bollinger", "atr", "signals"),
    ),
    IndicatorSpec(
        identifier="super_bollinger_trend",
        name="[Default] SuperBollingerTrend",
        description=(
            "Causal Bollinger trend bands with zigzag-style turning points and optional take-profit reference."
        ),
        category="trend",
        tags=("trend", "bollinger", "zigzag", "signals"),
    ),
    IndicatorSpec(
        identifier="rmi_trend_sniper",
        name="[Default] RMI Trend Sniper",
        description=("RMI and money-flow momentum gates with weighted trend bands and chart-only reversal signals."),
        category="momentum",
        tags=("momentum", "rmi", "mfi", "trend", "signals"),
    ),
    IndicatorSpec(
        identifier="exhaustion_levels",
        name="[Default] Exhaustion Levels",
        description=(
            "Causal exhaustion counters with persistent support/resistance levels and chart-only reversal markers."
        ),
        category="overlap",
        tags=("overlap", "support", "resistance", "exhaustion", "signals"),
    ),
    IndicatorSpec(
        identifier="smt_divergences",
        name="[Default] SMT Divergences",
        description=("Confirmed swing divergence detector with optional comparison series and chart-only SMT markers."),
        category="overlap",
        tags=("overlap", "divergence", "smt", "signals"),
    ),
    IndicatorSpec(
        identifier="pmax_on_rsi_t3",
        name="[Default] PMax on RSI w T3",
        description=(
            "Custom RSI smoothed by Tillson T3 with ATR-based PMax trailing levels and chart-only crossover signals."
        ),
        category="momentum",
        tags=("momentum", "rsi", "t3", "pmax", "signals"),
    ),
    IndicatorSpec(
        identifier="rsi_divergence_indicator",
        name="[Default] RSI Divergence Indicator",
        description=("Confirmed regular and hidden RSI divergences with chart-only markers."),
        category="momentum",
        tags=("momentum", "rsi", "divergence", "signals"),
    ),
    IndicatorSpec(
        identifier="ghost_tangent_crossings",
        name="[Default] Ghost Tangent Crossings",
        description=("Causal swing tangent projections with ghost swing points and chart-only break markers."),
        category="overlap",
        tags=("overlap", "swing", "tangent", "breakout"),
    ),
    IndicatorSpec(
        identifier="two_b_reversal_pattern",
        name="[Default] 2B Reversal Pattern (Expo)",
        description=("Confirmed swing false-break reversals with causal pending levels and chart-only signals."),
        category="overlap",
        tags=("overlap", "reversal", "swing", "signals"),
    ),
    IndicatorSpec(
        identifier="macd_leader",
        name="[Default] MACD Leader",
        description=("Residual-corrected MACD Leader oscillator with optional conventional MACD lines."),
        category="momentum",
        tags=("momentum", "macd", "oscillator"),
    ),
    IndicatorSpec(
        identifier="machine_learning_rsi",
        name="[Default] Machine Learning RSI",
        description=("KNN-enhanced RSI with causal multi-feature similarity search and optional endpoint filtering."),
        category="momentum",
        tags=("momentum", "rsi", "knn", "machine-learning"),
    ),
    IndicatorSpec(
        identifier="volume_supertrend_ai",
        name="[Default] Volume SuperTrend AI",
        description=(
            "Volume-weighted SuperTrend with causal KNN trend labels, chart-only "
            "signals, and optional cloud reference lines."
        ),
        category="trend",
        tags=("trend", "supertrend", "volume", "knn", "signals"),
    ),
    IndicatorSpec(
        identifier="false_breakout",
        name="[Default] False Breakout (Expo)",
        description=(
            "Consecutive new-high/new-low false-breakout detector with causal levels and chart-only reversal signals."
        ),
        category="overlap",
        tags=("overlap", "breakout", "reversal", "signals"),
    ),
    IndicatorSpec(
        identifier="multi_kernel_regression",
        name="[Default] Multi Kernel Regression [ChartPrime]",
        description=(
            "Causal multi-kernel regression with optional deviation bands and confirmed chart-only direction signals."
        ),
        category="overlap",
        tags=("overlap", "kernel", "regression", "trend", "signals"),
    ),
    IndicatorSpec(
        identifier="twin_optimized_trend_tracker",
        name="[Default] Twin Optimized Trend Tracker",
        description=(
            "Twin OTT lines with selectable moving-average support and causal chart-only trend reversal signals."
        ),
        category="overlap",
        tags=("overlap", "trend", "ott", "signals"),
    ),
    IndicatorSpec(
        identifier="scalp_pro",
        name="[Default] Scalp Pro",
        description=("Ehlers two-pole SuperSmoother MACD oscillator with causal chart-only crossover markers."),
        category="momentum",
        tags=("momentum", "oscillator", "macd", "signals"),
    ),
    IndicatorSpec(
        identifier="breaks_and_retests",
        name="[Default] Breaks and Retests",
        description=("Causal pivot support/resistance levels with chart-only breakout and retest markers."),
        category="overlap",
        tags=("overlap", "support", "resistance", "breakout", "retest", "signals"),
    ),
    IndicatorSpec(
        identifier="swing_failure_pattern",
        name="[Default] Swing Failure Pattern",
        description=("Causal swing-failure reversal detector with sweep and confirmation signals."),
        category="overlap",
        tags=("overlap", "swing", "reversal", "breakout", "signals"),
    ),
    IndicatorSpec(
        identifier="renko_candles_overlay",
        name="[Default] Renko Candles Overlay",
        description="Causal Renko-style candle overlay calculated from OHLC data.",
        category="overlap",
        tags=("renko", "overlay", "trend"),
    ),
    IndicatorSpec(
        identifier="hema_trend_levels",
        name="[Default] HEMA Trend Levels",
        description="Hull-style exponential average with causal ATR trend levels and reversal markers.",
        category="trend",
        tags=("trend", "moving-average", "atr", "signals"),
    ),
    IndicatorSpec(
        identifier="smart_money_breakout_signals",
        name="[Default] Smart Money Breakout Signals",
        description="Causal market-structure breakouts confirmed by candle body and relative volume.",
        category="overlap",
        tags=("overlap", "market-structure", "breakout", "volume", "signals"),
    ),
    IndicatorSpec(
        identifier="alphatrend_screener",
        name="[Default] AlphaTrend - Screener",
        description="ATR and momentum gated AlphaTrend line with causal crossover markers.",
        category="trend",
        tags=("trend", "atr", "momentum", "screener", "signals"),
    ),
    IndicatorSpec(
        identifier="smart_money_breakouts",
        name="[Default] Smart Money Breakouts",
        description=(
            "Causal smart-money pivot breakout detector with BOS/CHoCH signals, "
            "volume-bias labels, and optional chart-only risk levels."
        ),
        category="overlap",
        tags=("overlap", "smart-money", "structure", "breakout", "signals"),
    ),
    IndicatorSpec(
        identifier="macd_bollinger_bands",
        name="[Default] MACD Bollinger Bands",
        description=("MACD oscillator with a Bollinger envelope and optional chart-only crossover signals."),
        category="momentum",
        tags=("momentum", "macd", "bollinger", "volatility", "signals"),
    ),
    IndicatorSpec(
        identifier="trading_abc",
        name="[Default] Trading ABC",
        description=(
            "Causal moving-average trend, ZigZag, and ABC retracement chart indicator with visual long/short markers."
        ),
        category="overlap",
        tags=("overlap", "trend", "zigzag", "retracement", "signals"),
    ),
    IndicatorSpec(
        identifier="envelope_rsi_signals",
        name="[Default] Envelope RSI Signals",
        description=("RSI volatility envelope with causal oversold and overbought reversal signals."),
        category="momentum",
        tags=("momentum", "rsi", "envelope", "signals"),
    ),
    IndicatorSpec(
        identifier="market_structure_oscillator",
        name="[Default] Market Structure Oscillator",
        description=("Causal market-structure position oscillator with trend confirmation and crossover markers."),
        category="momentum",
        tags=("momentum", "market-structure", "oscillator", "signals"),
    ),
    IndicatorSpec(
        identifier="itg_scalper",
        name="[Default] ITG Scalper",
        description=("Fast and slow trend filters with ATR scalp bands and causal crossover markers."),
        category="trend",
        tags=("trend", "scalping", "ema", "atr", "signals"),
    ),
    IndicatorSpec(
        identifier="flawless_victory_strategy",
        name="[Default] Flawless Victory Strategy",
        description=(
            "Bollinger mean-reversion bands with RSI/MFI filters and chart-only "
            "long-entry, exit, stop-loss, and take-profit markers."
        ),
        category="overlap",
        tags=("overlap", "bollinger", "rsi", "mfi", "mean-reversion", "signals"),
    ),
    IndicatorSpec(
        identifier="atr_trailing_stop",
        name="[Default] ATR Trailing Stop",
        description=("Causal ATR trailing stop with direction flips and chart-only markers."),
        category="trend",
        tags=("trend", "atr", "trailing-stop", "signals"),
    ),
    IndicatorSpec(
        identifier="volume_weighted_macd",
        name="[Default] Volume Weighted MACD",
        description=("MACD oscillator using a causal volume-weighted price with crossover markers."),
        category="momentum",
        tags=("momentum", "macd", "volume", "oscillator", "signals"),
    ),
    IndicatorSpec(
        identifier="elder_impulse_system",
        name="[Default] Elder Impulse System",
        description=("EMA and MACD momentum impulse states with chart-only color markers."),
        category="momentum",
        tags=("momentum", "trend", "ema", "macd", "signals"),
    ),
)


def _read_source(identifier: str) -> str:
    source = get_indicator_source_code(identifier)
    if not source:
        raise ValueError(f"Indicator source is missing: {identifier}")
    return source


def builtin_indicator_specs() -> List[Dict[str, str]]:
    """Return DB-ready default indicator specs with source code included."""
    rows: List[Dict[str, str]] = []
    for spec in _SPECS:
        rows.append(
            {
                "id": spec.identifier,
                "name": spec.name,
                "description": spec.description,
                "category": spec.category,
                "tags": ",".join(spec.tags),
                "version": spec.version,
                # Keep the legacy response key while pointing at the single
                # canonical implementation module for this indicator.
                "source_file": spec.module_file,
                "code": _read_source(spec.identifier),
            }
        )
    return rows
