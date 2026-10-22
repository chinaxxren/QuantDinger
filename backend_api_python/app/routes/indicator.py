"""
Indicator APIs (local-first).

These endpoints are used by the frontend `/indicator-analysis` page.
In the original architecture, the frontend called PHP endpoints like:
`/addons/quantdinger/indicator/getIndicators`.

For local mode, we expose Python equivalents under `/api/indicator/*`.
"""

from __future__ import annotations

import json
import re
import time
import traceback
from typing import Any, Dict, List
from flask import Response, g, jsonify, request
from app.openapi.blueprint import HumanBlueprint as Blueprint

from app.utils.db import get_db_connection
from app.utils.logger import get_logger
from app.services.ai_generation_contracts import (
    INDICATOR_GENERATION_CONTRACT,
    INDICATOR_REPAIR_REQUIREMENTS,
)
from app.services.ai_copilot_context import fit_messages_to_budget
from app.services.ai_authoring_intent import resolve_authoring_intent
from app.services.indicator_ai_generation import generate_indicator_code_candidate
from app.services.indicator_ai_workspace import (
    begin_turn as begin_indicator_ai_turn,
    classify_indicator_ai_intent,
    complete_discussion_turn as complete_indicator_ai_discussion_turn,
    complete_turn as complete_indicator_ai_turn,
    get_workspace as get_indicator_ai_workspace,
)
from app.services.indicator_workspace import is_indicator_ide_listable
from app.services.indicator_versions import (
    insert_indicator_version,
)
from app.utils.auth import login_required
from app.services.indicator_validation import (
    indicator_debug_summary,
    validate_indicator_code,
)

logger = get_logger(__name__)

indicator_blp = Blueprint("indicator", __name__)


INDICATOR_IDE_SYSTEM_PROMPT = """You write production-ready QuantDinger chart indicators.
The runtime provides pandas as `pd`, numpy as `np`, an OHLCV DataFrame named `df`, and a `params` dict.
Keep every generated file chart-only: no orders, positions, schedules, leverage, network, file I/O, reflection, or dynamic execution.
Use pandas Series for rolling, fill, shift, ewm, iloc, and list conversion. Coerce numpy results with
`pd.Series(value, index=df.index)` before pandas-only operations so DatetimeIndex alignment is preserved.
Visual markers should normally be one-bar events. A safe edge pattern is:
`previous = condition.shift(1, fill_value=False).astype(bool)` followed by `condition & ~previous`.
Return one complete Python source file only, without markdown fences or surrounding prose.
"""


def _sse_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _now_ts() -> int:
    return int(time.time())


def _extract_indicator_meta_from_code(code: str) -> Dict[str, str]:
    """
    Extract indicator name/description from python code.
    Expected variables:
      my_indicator_name = "..."
      my_indicator_description = "..."
    """
    if not code or not isinstance(code, str):
        return {"name": "", "description": ""}

    # Simple assignment capture for single/double quoted strings.
    name_match = re.search(r'^\s*my_indicator_name\s*=\s*([\'"])(.*?)\1\s*$', code, re.MULTILINE)
    desc_match = re.search(r'^\s*my_indicator_description\s*=\s*([\'"])(.*?)\1\s*$', code, re.MULTILINE)

    name = (name_match.group(2).strip() if name_match else "")[:100]
    description = (desc_match.group(2).strip() if desc_match else "")[:500]
    return {"name": name, "description": description}


def _insert_indicator_version(cur, indicator_id: int, user_id: int, name: str, description: str, code: str) -> int:
    return insert_indicator_version(cur, indicator_id, user_id, name, description, code)


def _row_to_indicator(row: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    """
    Map database row -> frontend expected indicator shape.

    Frontend uses:
    - id, name, description, code
    - is_buy (1 bought, 0 custom)
    - user_id / userId
    - end_time (optional)
    """
    is_encrypted = int(row.get("is_encrypted") or 0)
    is_buy = int(row.get("is_buy") or 0)
    code_hidden = bool(is_encrypted and is_buy)
    runtime_code = row.get("code") or ""
    from app.services.indicator_signal_alerts import is_indicator_signal_capable

    return {
        "id": row.get("id"),
        "user_id": row.get("user_id") if row.get("user_id") is not None else user_id,
        "is_buy": is_buy,
        "end_time": row.get("end_time") if row.get("end_time") is not None else 1,
        "name": row.get("name") or "",
        "code": "" if code_hidden else (row.get("code") or ""),
        # Hidden source code still needs executable code for chart rendering.
        # Keep the editor-facing `code` blank, but authorize the owner's copy to run.
        "runtime_code": runtime_code if code_hidden else "",
        "description": row.get("description") or "",
        "signal_capable": is_indicator_signal_capable(runtime_code),
        "is_encrypted": is_encrypted,
        "code_hidden": 1 if code_hidden else 0,
        # Prefer MySQL-like time fields; fallback to legacy local columns.
        "createtime": row.get("createtime") or row.get("created_at"),
        "updatetime": row.get("updatetime") or row.get("updated_at"),
    }


def _validate_indicator_code_internal(code: str, user_params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return validate_indicator_code(code, user_params)


def _indicator_debug_summary(validation: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return indicator_debug_summary(validation)
def _request_lang(default: str = "zh-CN") -> str:
    raw = (
        request.headers.get("X-App-Lang")
        or request.headers.get("Accept-Language")
        or default
    )
    lang = str(raw or default).split(",", 1)[0].strip()
    return lang or default


def _is_zh_lang(lang: str | None) -> bool:
    return str(lang or "zh-CN").strip().lower().startswith("zh")


def _indicator_ai_text(key: str, lang: str = "zh-CN") -> str:
    texts = {
        "prompt_required": "Prompt cannot be empty",
        "candidate_ready": "A candidate version is ready and has passed automatic code checks. Preview it before applying it to the editor.",
        "candidate_needs_review": "A candidate is ready, but automatic checks found issues. Review the validation result before applying it.",
        "no_declared_params": "no declared tunable parameters",
        "no_standard_outputs": "no recognized standard output structure",
        "discussion_summary": (
            "The current indicator is {name}. Declared parameters: {params}. "
            "Recognized outputs: {outputs}. You can ask about a variable, signal condition, or chart element. "
            "This answer did not generate or modify code."
        ),
    }
    if _is_zh_lang(lang):
        zh_texts = {
            "prompt_required": "请输入指标修改需求",
            "candidate_ready": "候选版本已生成并通过自动代码检查。请先预览，再决定是否应用到编辑器。",
            "candidate_needs_review": "候选版本已生成，但自动检查发现问题。请先查看检查结果，不要直接应用。",
            "no_declared_params": "未声明可调参数",
            "no_standard_outputs": "尚未识别到标准输出结构",
            "discussion_summary": (
                "当前指标是「{name}」。代码声明的参数包括：{params}；输出结构包括：{outputs}。"
                "你可以继续问具体变量、信号条件或图表含义。这次仅回答问题，没有生成或修改代码。"
            ),
        }
        return zh_texts.get(key, texts.get(key, key))
    return texts.get(key, key)


def _indicator_discussion_fallback(existing: str, context: Dict[str, Any], lang: str) -> str:
    indicator_name = str(context.get("indicatorName") or "").strip() or "this indicator"
    param_names = re.findall(r"^\s*#\s*@param\s+([A-Za-z_]\w*)", existing, flags=re.MULTILINE)
    output_parts = [
        key
        for key in ("plots", "signals", "layers")
        if re.search(rf"['\"]{key}['\"]\s*:", existing)
    ]
    separator = "、" if _is_zh_lang(lang) else ", "
    params_text = separator.join(param_names[:8]) or _indicator_ai_text("no_declared_params", lang)
    outputs_text = separator.join(output_parts) or _indicator_ai_text("no_standard_outputs", lang)
    return _indicator_ai_text("discussion_summary", lang).format(
        name=indicator_name,
        params=params_text,
        outputs=outputs_text,
    )


def _indicator_hint_to_text(hint_code: str, params: Dict[str, Any] | None = None, lang: str = "zh-CN") -> str:
    params = params or {}
    if hint_code == "DECLARED_PARAMS_NOT_READ_VIA_PARAMS_GET":
        names = params.get("names") or []
        joined = ", ".join(names) or "parameters"
        return f"Declared parameters are not being read via params.get(...): {joined}."
    if hint_code == "PARAM_DEFAULT_MISMATCH":
        items = params.get("items") or []
        parts = [
            f"{item.get('name')}: @param={item.get('declared')}, params.get fallback={item.get('fallback')}"
            for item in items
        ]
        detail = "; ".join(parts) or "parameter defaults"
        return (
            f"Parameter default mismatch: {detail}. "
            "The # @param default must exactly match the params.get(..., default) fallback."
        )
    if hint_code == "SIGNAL_MARKERS_USE_WHERE_NONE":
        return "Signal markers use where(..., None).tolist(); prefer an explicit None list to avoid NaN rendering issues."
    if hint_code == "MISSING_OUTPUT":
        return "Missing output dictionary."
    if hint_code == "EXECUTION_COLUMNS_IGNORED_FOR_INDICATOR":
        return "Execution columns are ignored in chart indicators. Convert this idea to Strategy API V2 before backtesting or live trading."
    if hint_code == "STRATEGY_ANNOTATIONS_IGNORED_FOR_INDICATOR":
        return "# @strategy annotations are forbidden in chart indicators. Put risk, sizing, timeframe, and execution rules in Strategy API V2 code."
    if hint_code == "MISSING_DF_COPY":
        return "Missing df = df.copy()."
    if hint_code == "MISSING_INDICATOR_NAME":
        return "Missing my_indicator_name."
    if hint_code == "MISSING_INDICATOR_DESCRIPTION":
        return "Missing my_indicator_description."
    if hint_code == "NDARRAY_PANDAS_METHOD_MISUSE":
        symbol = params.get("symbol") or "ndarray"
        method = params.get("method") or "?"
        return (
            f"Pandas method called on a numpy ndarray: {symbol}.{method}(...). "
            "Wrap with pd.Series(arr, index=df.index) before calling pandas methods, "
            "or rewrite with pandas-native .where/.clip/.abs."
        )
    if hint_code == "HELPER_RETURNS_NDARRAY":
        names_str = params.get("names_str") or ", ".join(params.get("names") or []) or "helper"
        return (
            f"User helpers return numpy ndarray: {names_str}. "
            "Downstream .rolling/.fillna/.shift/.ewm/.iloc on the result will AttributeError; "
            "have the helper return a Series instead (e.g. num / den.replace(0, np.nan).fillna(0))."
        )
    if hint_code == "RUNTIME_ERROR_ON_VERIFY":
        error_type = params.get("error_type") or "RuntimeError"
        detail = params.get("detail") or ""
        return f"Sandbox dry-run raised {error_type}: {detail}."
    if hint_code == "FUTURE_DATA_LEAK":
        snippet = params.get("snippet") or "?"
        kind = params.get("kind") or ""
        kind_en = {
            "shift": "negative shift",
            "iloc": "forward iloc offset",
            "bars_ago": "negative bars_ago",
        }.get(kind, kind or "unknown pattern")
        return (
            f"Future data leak detected ({kind_en}): {snippet}. "
            "Backtest is reading bars that haven't happened yet, which can NEVER be reproduced live. "
            "Use .shift(N) with positive N or iloc[i-N] to reference the past instead."
        )
    return f"Code hint detected: {hint_code}"


def _indicator_human_summary(
    initial_validation: Dict[str, Any],
    final_validation: Dict[str, Any],
    auto_fix_applied: bool,
    auto_fix_succeeded: bool,
    returned_candidate: str,
    lang: str = "zh-CN",
) -> Dict[str, Any]:
    initial_hints = initial_validation.get("hints") or []
    final_hints = final_validation.get("hints") or []
    initial_codes = {h.get("code") for h in initial_hints if h.get("code")}
    final_codes = {h.get("code") for h in final_hints if h.get("code")}
    fixed_codes = sorted(initial_codes - final_codes)
    remaining_codes = sorted(final_codes)

    fixed_messages = [
        _indicator_hint_to_text(h.get("code"), h.get("params"), lang=lang)
        for h in initial_hints
        if h.get("code") in fixed_codes
    ]
    remaining_messages = [
        _indicator_hint_to_text(h.get("code"), h.get("params"), lang=lang)
        for h in final_hints
        if h.get("code") in remaining_codes
    ]

    if auto_fix_applied and auto_fix_succeeded:
        title = "AI auto-fixed the indicator code and returned a more stable version"
    elif auto_fix_applied:
        title = "AI attempted to auto-fix the code, but some issues still remain"
    else:
        title = "AI generated indicator code and it passed the current QA flow"

    if returned_candidate == "repaired":
        returned_text = "The returned code is the auto-fixed version."
    else:
        returned_text = "The returned code is the initially generated version."

    return {
        "title": title,
        "returned_text": returned_text,
        "fixed_messages": fixed_messages,
        "remaining_messages": remaining_messages,
    }


@indicator_blp.route("/getIndicators", methods=["GET"])
@login_required
def get_indicators():
    """
    Get indicator list for the current user.

    Response:
      { code: 1, data: [ ... ] }
    """
    try:
        user_id = g.user_id

        with get_db_connection() as db:
            cur = db.cursor()
            # Get user's own indicators (both purchased and custom).
            cur.execute(
                """
                SELECT
                  id, user_id, is_buy, end_time, name, code, description, is_encrypted,
                  COALESCE(asset_type, 'indicator') as asset_type,
                  createtime, updatetime, created_at, updated_at
                FROM qd_indicator_codes
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            )
            rows = cur.fetchall() or []
            cur.close()

        rows = [
            r for r in rows
            if is_indicator_ide_listable(
                code=r.get("code") or "",
                asset_type=r.get("asset_type") or "indicator",
            )
        ]
        out = [_row_to_indicator(r, user_id) for r in rows]
        return jsonify({"code": 1, "msg": "success", "data": out})
    except Exception as e:
        logger.error(f"get_indicators failed: {str(e)}", exc_info=True)
        return jsonify({"code": 0, "msg": str(e), "data": []}), 500

@indicator_blp.route("/chart-indicators", methods=["GET"])
@login_required
def chart_indicator_catalog():
    """Return backend-computed chart indicator metadata for the K-line UI."""
    from app.services.indicator_chart_workflow import catalog

    return jsonify({"code": 1, "msg": "success", "data": catalog()})


@indicator_blp.route("/chart-indicators/compute", methods=["POST"])
@login_required
def chart_indicator_compute():
    """Compute chart indicators from frontend OHLCV bars without changing chart layout."""
    try:
        payload = request.get_json(silent=True) or {}
        from app.services.indicator_chart_workflow import compute

        items = compute(payload.get("bars"), payload.get("indicators") or [])
        return jsonify({"code": 1, "msg": "success", "data": {"items": items}})
    except ValueError as exc:
        return jsonify({"code": 0, "msg": str(exc), "data": {"items": []}}), 400
    except Exception as exc:
        logger.error(f"chart_indicator_compute failed: {exc}", exc_info=True)
        return jsonify({"code": 0, "msg": "indicator.computeFailed", "data": {"items": []}}), 500



@indicator_blp.route("/saveIndicator", methods=["POST"])
@login_required
def save_indicator():
    """
    Create or update an indicator for the current user.

    Request (frontend sends many extra fields; we store only the essentials):
      {
        id: number (0 for create),
        name: string,
        code: string,
        allowEmptyDraft?: boolean,
        description?: string,
        ...
      }
    """
    try:
        data = request.get_json() or {}
        user_id = g.user_id
        indicator_id = int(data.get("id") or 0)
        code = str(data.get("code") or "")
        name = str(data.get("name") or "").strip()
        description = str(data.get("description") or "").strip()
        allow_empty_draft = data.get("allowEmptyDraft") is True or data.get("allow_empty_draft") is True
        if not code.strip() and not allow_empty_draft:
            return jsonify({"code": 0, "msg": "code is required", "data": None}), 400
        if code.strip():
            from app.utils.safe_exec import validate_code_safety
            is_safe_code, unsafe_reason = validate_code_safety(code)
            if not is_safe_code:
                return jsonify({"code": 0, "msg": f"Unsafe indicator code: {unsafe_reason}", "data": None}), 400
        meta = _extract_indicator_meta_from_code(code)
        name = name or meta.get("name") or "Custom Indicator"
        description = description or meta.get("description") or ""
        now = _now_ts()

        with get_db_connection() as db:
            cur = db.cursor()
            if indicator_id > 0:
                cur.execute(
                    """
                    UPDATE qd_indicator_codes
                    SET name = ?, code = ?, description = ?, asset_type = ?,
                        is_encrypted = 0, updatetime = ?, updated_at = NOW()
                    WHERE id = ? AND user_id = ? AND COALESCE(is_buy, 0) = 0
                    """,
                    (name, code, description, "indicator", now, indicator_id, user_id),
                )
                if cur.rowcount == 0:
                    cur.close()
                    return jsonify({"code": 0, "msg": "indicator not found", "data": None}), 404
            else:
                cur.execute(
                    """
                    INSERT INTO qd_indicator_codes
                      (user_id, is_buy, end_time, name, code, description, asset_type,
                       is_encrypted, createtime, updatetime, created_at, updated_at)
                    VALUES (?, 0, 1, ?, ?, ?, ?, 0, ?, ?, NOW(), NOW())
                    """,
                    (user_id, name, code, description, "indicator", now, now),
                )
                indicator_id = int(cur.lastrowid or 0)
            _insert_indicator_version(cur, indicator_id, user_id, name, description, code)
            db.commit()
            cur.close()
        return jsonify({"code": 1, "msg": "success", "data": {"id": indicator_id, "userid": user_id}})
    except Exception as e:
        logger.error(f"save_indicator failed: {str(e)}", exc_info=True)
        return jsonify({"code": 0, "msg": str(e), "data": None}), 500


@indicator_blp.route("/deleteIndicator", methods=["POST"])
@login_required
def delete_indicator():
    """Delete an indicator by id for the current user."""
    try:
        data = request.get_json() or {}
        user_id = g.user_id
        indicator_id = int(data.get("id") or 0)
        if not indicator_id:
            return jsonify({"code": 0, "msg": "id is required", "data": None}), 400

        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                "DELETE FROM qd_indicator_codes WHERE id = ? AND user_id = ? AND COALESCE(is_buy, 0) = 0",
                (indicator_id, user_id),
            )
            if cur.rowcount == 0:
                cur.close()
                return jsonify({"code": 0, "msg": "indicator not found", "data": None}), 404
            db.commit()
            cur.close()

        return jsonify({"code": 1, "msg": "success", "data": {"deleted": True}})
    except Exception as e:
        logger.error(f"delete_indicator failed: {str(e)}", exc_info=True)
        return jsonify({"code": 0, "msg": str(e), "data": None}), 500


@indicator_blp.route("/aiGenerate", methods=["POST"])
@login_required
def ai_generate():
    """
    SSE endpoint to generate indicator code.

    Frontend expects 'text/event-stream' with chunks:
      data: {"content":"..."}\n\n
    then:
      data: [DONE]\n\n

    Local-first: if OpenRouter key is not configured, we return a reasonable template.
    """
    data = request.get_json() or {}
    lang = _request_lang()
    prompt = (data.get("prompt") or "").strip()
    existing = str(data.get("existingCode") or "")
    context = data.get("context") if isinstance(data.get("context"), dict) else {}
    source = str(data.get("source") or context.get("source") or "").strip()
    indicator_id = context.get("indicatorId")
    requested_interaction_mode = str(data.get("interactionMode") or "auto").strip().lower()
    resolved_interaction_mode = "modify"
    workspace_context: Dict[str, Any] | None = None

    if not prompt:
        # Keep SSE contract (match PHP behavior) so frontend doesn't look "stuck".
        def _err_stream():
            yield "data: " + _sse_json({"error": _indicator_ai_text("prompt_required", lang)}) + "\n\n"
            yield "data: [DONE]\n\n"

        return Response(
            _err_stream(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    if source == "indicator_ide":
        intent_messages: List[Dict[str, Any]] = []
        if requested_interaction_mode == "auto" and indicator_id not in (None, ""):
            try:
                intent_workspace = get_indicator_ai_workspace(g.user_id, int(indicator_id))
                intent_messages = list(intent_workspace.get("messages") or [])
            except Exception as exc:
                logger.info("indicator intent history unavailable; continuing without it: %s", exc)
        intent_decision = resolve_authoring_intent(
            prompt=prompt,
            requested_mode=requested_interaction_mode,
            asset_kind="chart_indicator",
            existing_code=existing,
            recent_messages=intent_messages,
            fallback_classifier=classify_indicator_ai_intent,
        )
        resolved_interaction_mode = str(intent_decision["intent"])
        logger.info(
            "indicator authoring intent=%s source=%s confidence=%.2f",
            resolved_interaction_mode,
            intent_decision.get("source"),
            float(intent_decision.get("confidence") or 0.0),
        )

    # QuantDinger indicator IDE: chart render only; strategies are separate script assets.
    # Marker edge contract: shift(1, fill_value=False).astype(bool)
    system_prompt = INDICATOR_IDE_SYSTEM_PROMPT + "\n\n" + INDICATOR_GENERATION_CONTRACT

    def _generate_discussion_via_llm() -> str:
        """Answer a code question without returning replacement source."""
        from app.services.llm import LLMService

        llm = LLMService()
        if not llm.get_api_key():
            return _indicator_discussion_fallback(existing, context, lang)

        discussion_system = """You are QuantDinger's indicator-code reviewer.
Answer the user's question about the currently open indicator. Use the same language as the user.
Explain concrete logic, parameters, plots, visual signals, edge cases, and limitations from the supplied source.
Never claim that code was changed. Do not return a full replacement script and do not create a code candidate.
When useful, cite short variable or function names from the source, but keep the answer concise and readable.
Lead with the conclusion. By default use 4-8 short points and stay under 700 Chinese characters or 350 English words; only go deeper when the user explicitly asks for a detailed walkthrough.
If the question actually requests a code modification, explain what should change and ask the user to state the desired change explicitly; do not write the replacement code in this discussion response."""
        messages: List[Dict[str, str]] = [{"role": "system", "content": discussion_system}]
        if workspace_context:
            summary_text = json.dumps(workspace_context.get("summary") or {}, ensure_ascii=False, default=str)
            messages.append({
                "role": "system",
                "content": "# Bounded indicator conversation memory\n" + summary_text[:4000],
            })
            for item in workspace_context.get("recent_messages") or []:
                role = str(item.get("role") or "")
                content_text = str(item.get("content") or "").strip()
                if role in {"user", "assistant"} and content_text:
                    messages.append({"role": role, "content": content_text[:2000]})

        chart_context = {
            "market": context.get("market"),
            "symbol": context.get("symbol"),
            "timeframe": context.get("timeframe"),
            "indicator_name": context.get("indicatorName"),
            "indicator_description": context.get("indicatorDescription"),
        }
        messages.append({
            "role": "user",
            "content": (
                "# Current chart context\n"
                + json.dumps(chart_context, ensure_ascii=False, default=str)
                + "\n\n# Current indicator source (source of truth)\n```python\n"
                + existing[:36000]
                + "\n```\n\n# User question\n"
                + prompt
            ),
        })
        messages, budget_debug = fit_messages_to_budget(messages, max_tokens=32000)
        logger.info("indicator discussion context budget=%s", _sse_json(budget_debug))
        answer = llm.call_llm_api(
            messages=messages,
            model=llm.get_default_model(),
            temperature=0.25,
            use_json_mode=False,
        )
        return str(answer or "").strip() or _indicator_discussion_fallback(existing, context, lang)

    def _template_code() -> str:
        from app.services.indicator_default_template import build_default_indicator_template

        desc = (prompt or "").replace("\n", " ")[:200]
        if not desc:
            desc = "Moving average chart indicator template with visual markers."
        code = build_default_indicator_template(
            name="Custom Indicator",
            description=desc,
        )
        if existing:
            code = "# Existing code was provided as context.\n" + code
        return code

    def _generate_code_via_llm() -> tuple[str, Dict[str, Any]]:
        return generate_indicator_code_candidate(
            prompt=prompt,
            existing=existing,
            context=context,
            system_prompt=system_prompt,
            workspace_context=workspace_context,
            template_factory=_template_code,
            logger=logger,
        )

    AUTO_FIX_HINT_CODES = {
        "DECLARED_PARAMS_NOT_READ_VIA_PARAMS_GET",
        "PARAM_DEFAULT_MISMATCH",
        "SIGNAL_MARKERS_USE_WHERE_NONE",
        "MISSING_OUTPUT",
        "MISSING_DF_COPY",
        "MISSING_INDICATOR_NAME",
        "MISSING_INDICATOR_DESCRIPTION",
        "EXECUTION_COLUMNS_IGNORED_FOR_INDICATOR",
        "STRATEGY_ANNOTATIONS_IGNORED_FOR_INDICATOR",
    }

    def _needs_auto_fix(validation: Dict[str, Any]) -> bool:
        if not validation.get("success"):
            return True
        for hint in validation.get("hints", []):
            if hint.get("code") in AUTO_FIX_HINT_CODES:
                return True
        return False

    def _format_validation_issues(validation: Dict[str, Any]) -> str:
        issues: List[str] = []
        if not validation.get("success"):
            issues.append(f"- Verification failed: {validation.get('msg')}")
            if validation.get("details"):
                issues.append(f"- Details: {validation.get('details')}")
        for hint in validation.get("hints", []):
            code_name = hint.get("code") or "UNKNOWN"
            params = hint.get("params") or {}
            if params:
                issues.append(f"- Hint {code_name}: {json.dumps(params, ensure_ascii=False)}")
            else:
                issues.append(f"- Hint {code_name}")
        return "\n".join(issues) if issues else "- No issues provided"

    def _repair_code_via_llm(bad_code: str, validation: Dict[str, Any]) -> str:
        from app.services.llm import LLMService

        llm = LLMService()
        current_model = llm.get_code_generation_model()
        current_api_key = llm.get_api_key()
        if not current_api_key:
            return bad_code

        issues_text = _format_validation_issues(validation)
        repair_prompt = (
            "You produced QuantDinger indicator code that failed automatic validation. "
            "Fix the code while preserving the user's visual indicator idea and parameters. "
            "Return one full replacement script only.\n\n"
            f"# Original user request\n{prompt}\n\n"
            f"# Validation issues to fix\n{issues_text}\n\n"
            "# Current code\n```python\n"
            + bad_code.strip()
            + "\n```\n\n"
            + INDICATOR_REPAIR_REQUIREMENTS
        )

        content = llm.call_llm_api(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": repair_prompt},
            ],
            model=current_model,
            temperature=0.2,
            use_json_mode=False,
        )

        content = (content or "").strip()
        if content.startswith("```python"):
            content = content[9:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip() or bad_code

    def _generate_final_code() -> tuple[str, Dict[str, Any], Dict[str, Any]]:
        try:
            code_text, edit_plan = _generate_code_via_llm()
        except Exception as e:
            logger.error(f"ai_generate LLM failed, fallback to template. Error: {type(e).__name__}: {e}")
            code_text = _template_code()
            edit_plan = {"executor": "template", "operation": "generate_candidate", "error": str(e)}

        validation = _validate_indicator_code_internal(code_text)
        if not _needs_auto_fix(validation):
            debug = {
                "auto_fix_applied": False,
                "auto_fix_succeeded": False,
                "returned_candidate": "initial",
                "initial_validation": _indicator_debug_summary(validation),
                "final_validation": _indicator_debug_summary(validation),
            }
            debug["human_summary"] = _indicator_human_summary(
                validation, validation, False, False, "initial", lang=lang
            )
            logger.info("ai_generate debug=%s", _sse_json(debug))
            return code_text, debug, edit_plan

        logger.warning("ai_generate produced code needing auto-fix: %s", _format_validation_issues(validation))
        try:
            repaired = _repair_code_via_llm(code_text, validation)
        except Exception as e:
            logger.error(f"ai_generate auto-fix failed, returning safe template. Error: {type(e).__name__}: {e}")
            fallback_code = _template_code()
            fallback_validation = _validate_indicator_code_internal(fallback_code)
            debug = {
                "auto_fix_applied": True,
                "auto_fix_succeeded": False,
                "returned_candidate": "template",
                "initial_validation": _indicator_debug_summary(validation),
                "final_validation": _indicator_debug_summary(fallback_validation),
                "auto_fix_error": str(e),
            }
            debug["human_summary"] = _indicator_human_summary(
                validation, fallback_validation, True, False, "template", lang=lang
            )
            logger.info("ai_generate debug=%s", _sse_json(debug))
            return fallback_code, debug, {"executor": "template", "operation": "repair_fallback"}

        repaired_validation = _validate_indicator_code_internal(repaired)
        if repaired_validation.get("success") and not _needs_auto_fix(repaired_validation):
            logger.info("ai_generate auto-fix succeeded")
            debug = {
                "auto_fix_applied": True,
                "auto_fix_succeeded": True,
                "returned_candidate": "repaired",
                "initial_validation": _indicator_debug_summary(validation),
                "final_validation": _indicator_debug_summary(repaired_validation),
            }
            debug["human_summary"] = _indicator_human_summary(
                validation, repaired_validation, True, True, "repaired", lang=lang
            )
            logger.info("ai_generate debug=%s", _sse_json(debug))
            return repaired, debug, {"executor": "model_repair", "operation": "generate_candidate"}

        repaired_hint_codes = {h.get("code") for h in repaired_validation.get("hints", [])}
        if repaired_validation.get("success"):
            logger.warning("ai_generate auto-fix improved code but some non-blocking issues remain")
            debug = {
                "auto_fix_applied": True,
                "auto_fix_succeeded": True,
                "returned_candidate": "repaired",
                "initial_validation": _indicator_debug_summary(validation),
                "final_validation": _indicator_debug_summary(repaired_validation),
            }
            debug["human_summary"] = _indicator_human_summary(
                validation, repaired_validation, True, True, "repaired", lang=lang
            )
            logger.info("ai_generate debug=%s", _sse_json(debug))
            return repaired, debug, {"executor": "model_repair", "operation": "generate_candidate"}

        if repaired_hint_codes.intersection(AUTO_FIX_HINT_CODES):
            logger.warning("ai_generate auto-fix still has blocking issues, returning safe template")
            fallback_code = _template_code()
            fallback_validation = _validate_indicator_code_internal(fallback_code)
            debug = {
                "auto_fix_applied": True,
                "auto_fix_succeeded": False,
                "returned_candidate": "template",
                "initial_validation": _indicator_debug_summary(validation),
                "final_validation": _indicator_debug_summary(fallback_validation),
            }
            debug["human_summary"] = _indicator_human_summary(
                validation, fallback_validation, True, False, "template", lang=lang
            )
            logger.info("ai_generate debug=%s", _sse_json(debug))
            return fallback_code, debug, {"executor": "template", "operation": "repair_fallback"}

        debug = {
            "auto_fix_applied": True,
            "auto_fix_succeeded": False,
            "returned_candidate": "repaired",
            "initial_validation": _indicator_debug_summary(validation),
            "final_validation": _indicator_debug_summary(repaired_validation),
        }
        debug["human_summary"] = _indicator_human_summary(
            validation, repaired_validation, True, False, "repaired", lang=lang
        )
        logger.info("ai_generate debug=%s", _sse_json(debug))
        return repaired, debug, {"executor": "model_repair", "operation": "generate_candidate"}

    # Capture user_id before generator runs (generator executes outside request context)
    user_id = g.user_id
    def stream():
        nonlocal workspace_context
        if source == "indicator_ide" and indicator_id not in (None, ""):
            try:
                workspace_context = begin_indicator_ai_turn(
                    user_id,
                    int(indicator_id),
                    prompt,
                    intent=resolved_interaction_mode,
                )
            except (LookupError, PermissionError, ValueError) as exc:
                yield "data: " + _sse_json({"error": str(exc)}) + "\n\n"
                yield "data: [DONE]\n\n"
                return
            except Exception as exc:
                logger.error("begin indicator AI turn failed: %s", exc, exc_info=True)
                yield "data: " + _sse_json({"error": "indicator_ai_workspace_unavailable"}) + "\n\n"
                yield "data: [DONE]\n\n"
                return

        if workspace_context and resolved_interaction_mode == "discussion":
            try:
                discussion_text = _generate_discussion_via_llm()
                workspace_result = complete_indicator_ai_discussion_turn(
                    user_id=user_id,
                    workspace=workspace_context,
                    answer=discussion_text,
                )
                yield "data: " + _sse_json({"workspace": workspace_result}) + "\n\n"
                chunk_size = 240
                for i in range(0, len(discussion_text), chunk_size):
                    yield "data: " + _sse_json({"content": discussion_text[i : i + chunk_size]}) + "\n\n"
                yield "data: [DONE]\n\n"
                return
            except Exception as exc:
                logger.error("indicator AI discussion failed: %s", exc, exc_info=True)
                yield "data: " + _sse_json({"error": "indicator_ai_discussion_failed"}) + "\n\n"
                yield "data: [DONE]\n\n"
                return

        code_text, debug_info, edit_plan = _generate_final_code()

        if workspace_context:
            validation = _validate_indicator_code_internal(code_text)
            validation["edit_plan"] = edit_plan
            assistant_text = _indicator_ai_text("candidate_ready", lang)
            if not validation.get("success"):
                assistant_text = _indicator_ai_text("candidate_needs_review", lang)
            try:
                workspace_result = complete_indicator_ai_turn(
                    user_id=user_id,
                    workspace=workspace_context,
                    prompt=prompt,
                    base_code=existing,
                    candidate_code=code_text,
                    validation=validation,
                    assistant_text=assistant_text,
                )
                yield "data: " + _sse_json({"workspace": workspace_result}) + "\n\n"
            except Exception as exc:
                logger.error("complete indicator AI turn failed: %s", exc, exc_info=True)
                yield "data: " + _sse_json({"error": "indicator_ai_workspace_save_failed"}) + "\n\n"
                yield "data: [DONE]\n\n"
                return

        yield "data: " + _sse_json({"debug": debug_info}) + "\n\n"

        # Stream in chunks (front-end appends).
        chunk_size = 200
        for i in range(0, len(code_text), chunk_size):
            chunk = code_text[i : i + chunk_size]
            yield "data: " + _sse_json({"content": chunk}) + "\n\n"
        yield "data: [DONE]\n\n"

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )




# Keep the public blueprint and URL prefix stable while locating secondary
# endpoint families next to the workflows they expose.
from app.routes.indicator_ai_routes import register_indicator_ai_routes
from app.routes.indicator_aux_routes import register_indicator_aux_routes

register_indicator_ai_routes(
    indicator_blp,
    validate_code=_validate_indicator_code_internal,
    logger=logger,
)
register_indicator_aux_routes(indicator_blp)
