"""Secondary indicator endpoint families registered on the main blueprint."""

from __future__ import annotations

import time

from flask import g, jsonify, request

from app.services.indicator_params import get_indicator_params
from app.services.indicator_versions import (
    get_version as get_indicator_code_version,
    list_versions as list_indicator_code_versions,
    restore_version as restore_indicator_code_version,
)
from app.services.indicator_signal_alerts import IndicatorSignalAlertService
from app.utils.auth import login_required
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _now_ts() -> int:
    return int(time.time())


def register_indicator_aux_routes(blueprint) -> None:
    """Attach version, parameter, and preview routes to the existing blueprint."""

    @blueprint.route("/versions", methods=["GET"])
    @login_required
    def list_indicator_versions():
        try:
            indicator_id = int(request.args.get("indicatorId") or request.args.get("indicator_id") or 0)
            if not indicator_id:
                return jsonify({"code": 0, "msg": "indicatorId is required", "data": []}), 400
            ok, rows = list_indicator_code_versions(int(g.user_id), indicator_id)
            if not ok:
                return jsonify({"code": 0, "msg": "indicator not found", "data": []}), 404
            return jsonify({"code": 1, "msg": "success", "data": rows})
        except Exception as exc:
            logger.error("list_indicator_versions failed: %s", exc, exc_info=True)
            return jsonify({"code": 0, "msg": str(exc), "data": []}), 500

    @blueprint.route("/versions/<int:version_id>", methods=["GET"])
    @login_required
    def get_indicator_version(version_id: int):
        try:
            row = get_indicator_code_version(int(g.user_id), int(version_id))
            if not row:
                return jsonify({"code": 0, "msg": "version not found", "data": None}), 404
            return jsonify({"code": 1, "msg": "success", "data": row})
        except Exception as exc:
            logger.error("get_indicator_version failed: %s", exc, exc_info=True)
            return jsonify({"code": 0, "msg": str(exc), "data": None}), 500

    @blueprint.route("/versions/restore", methods=["POST"])
    @login_required
    def restore_indicator_version():
        try:
            data = request.get_json() or {}
            version_id = int(data.get("versionId") or data.get("version_id") or 0)
            if not version_id:
                return jsonify({"code": 0, "msg": "versionId is required", "data": None}), 400
            restored = restore_indicator_code_version(int(g.user_id), version_id, _now_ts())
            if not restored:
                return jsonify({"code": 0, "msg": "version not found", "data": None}), 404
            return jsonify({"code": 1, "msg": "success", "data": restored})
        except Exception as exc:
            logger.error("restore_indicator_version failed: %s", exc, exc_info=True)
            return jsonify({"code": 0, "msg": str(exc), "data": None}), 500

    @blueprint.route("/getIndicatorParams", methods=["GET"])
    @login_required
    def get_indicator_params_route():
        try:
            raw_id = request.args.get("indicator_id")
            if not raw_id:
                return jsonify({"code": 0, "msg": "indicator_id is required", "data": None}), 400
            try:
                indicator_id = int(raw_id)
            except ValueError:
                return jsonify({"code": 0, "msg": "indicator_id must be an integer", "data": None}), 400
            return jsonify({"code": 1, "msg": "success", "data": get_indicator_params(indicator_id)})
        except Exception as exc:
            logger.error("get_indicator_params failed: %s", exc, exc_info=True)
            return jsonify({"code": 0, "msg": str(exc), "data": None}), 500

    @blueprint.route("/chart-preview", methods=["POST"])
    @login_required
    def preview_indicator_chart():
        try:
            data = IndicatorSignalAlertService().preview_chart(g.user_id, request.get_json() or {})
            return jsonify({"code": 1, "msg": "success", "data": data})
        except ValueError as exc:
            return jsonify({"code": 0, "msg": str(exc), "data": None}), 400
        except Exception as exc:
            logger.error("preview_indicator_chart failed: %s", exc, exc_info=True)
            return jsonify({"code": 0, "msg": str(exc), "data": None}), 500
