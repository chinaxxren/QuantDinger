"""AI authoring HTTP endpoints for indicator assets."""

from __future__ import annotations

from flask import g, jsonify, request

from app.utils.auth import login_required


def register_indicator_ai_routes(blueprint, *, validate_code, logger) -> None:
    """Attach AI workspace and code quality endpoints to the indicator blueprint."""
    from app.services.indicator_ai_workspace import (
        clear_workspace as clear_indicator_ai_workspace,
        get_workspace as get_indicator_ai_workspace,
        set_change_status as set_indicator_ai_change_status,
    )
    from app.services.indicator_code_quality import analyze_indicator_code_quality

    @blueprint.route("/aiWorkspace/<int:indicator_id>", methods=["GET"])
    @login_required
    def indicator_ai_workspace(indicator_id: int):
        """Load the bounded AI authoring workspace for one owned indicator."""
        try:
            data = get_indicator_ai_workspace(g.user_id, indicator_id)
            return jsonify({"code": 1, "msg": "success", "data": data})
        except LookupError as exc:
            return jsonify({"code": 0, "msg": str(exc), "data": None}), 404
        except PermissionError as exc:
            return jsonify({"code": 0, "msg": str(exc), "data": None}), 403
        except Exception as exc:
            logger.error("indicator_ai_workspace failed: %s", exc, exc_info=True)
            return jsonify({"code": 0, "msg": str(exc), "data": None}), 500


    @blueprint.route("/aiWorkspace/<int:indicator_id>", methods=["DELETE"])
    @login_required
    def delete_indicator_ai_workspace(indicator_id: int):
        """Clear conversation and pending candidates without touching saved code."""
        try:
            data = clear_indicator_ai_workspace(g.user_id, indicator_id)
            return jsonify({"code": 1, "msg": "success", "data": data})
        except LookupError as exc:
            return jsonify({"code": 0, "msg": str(exc), "data": None}), 404
        except PermissionError as exc:
            return jsonify({"code": 0, "msg": str(exc), "data": None}), 403
        except Exception as exc:
            logger.error("delete_indicator_ai_workspace failed: %s", exc, exc_info=True)
            return jsonify({"code": 0, "msg": str(exc), "data": None}), 500


    @blueprint.route("/aiWorkspace/changes/<int:change_id>/status", methods=["POST"])
    @login_required
    def update_indicator_ai_change_status(change_id: int):
        """Mark a generated candidate as applied or discarded."""
        try:
            status = str((request.get_json() or {}).get("status") or "").strip().lower()
            data = set_indicator_ai_change_status(g.user_id, change_id, status)
            return jsonify({"code": 1, "msg": "success", "data": data})
        except ValueError as exc:
            return jsonify({"code": 0, "msg": str(exc), "data": None}), 400
        except LookupError as exc:
            return jsonify({"code": 0, "msg": str(exc), "data": None}), 404
        except PermissionError as exc:
            return jsonify({"code": 0, "msg": str(exc), "data": None}), 403
        except Exception as exc:
            logger.error("update_indicator_ai_change_status failed: %s", exc, exc_info=True)
            return jsonify({"code": 0, "msg": str(exc), "data": None}), 500



    @blueprint.route("/codeQualityHints", methods=["POST"])
    @login_required
    def code_quality_hints():
        """
        Heuristic hints + runtime smoke-execution for indicator code.

        Request body:
            code (required): Indicator source code

        Returns hints with severity, code, and params. Static analysis catches
        structural issues; a sandboxed dry-run surfaces runtime errors before backtest.
        """
        data = request.get_json() or {}
        code_str = data.get("code") or ""
        hints = analyze_indicator_code_quality(code_str)

        # If static analysis already found a deterministic error, skip the dry-run.
        # We do NOT skip on warn/info because those don't block execution and the user
        # benefits from the runtime check finishing the picture.
        has_static_error = any(h.get("severity") == "error" for h in hints)
        if not has_static_error and code_str.strip():
            try:
                validation = validate_code(code_str)
            except Exception as e:  # never let the smoke run break the endpoint
                logger.warning("codeQualityHints dry-run crashed: %s", e)
                validation = None

            if validation is not None and not validation.get("success"):
                error_type = validation.get("error_type") or "RuntimeError"
                detail = validation.get("details") or validation.get("msg") or ""
                # Trim noisy tracebacks: keep only the last meaningful line.
                short_detail = ""
                if detail:
                    for line in str(detail).strip().splitlines()[::-1]:
                        line = line.strip()
                        if line and not line.startswith("File "):
                            short_detail = line[:300]
                            break
                    if not short_detail:
                        short_detail = str(detail).strip().splitlines()[-1][:300]
                hints.append(
                    {
                        "severity": "error",
                        "code": "RUNTIME_ERROR_ON_VERIFY",
                        "params": {
                            "error_type": error_type,
                            "detail": short_detail,
                        },
                    }
                )

        return jsonify({"code": 1, "data": {"hints": hints}})
