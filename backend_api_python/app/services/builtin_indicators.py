"""Seed and maintain the built-in chart indicator library for each user.

The default library is local-first: users receive editable copies of the
indicator source, and every built-in indicator source lives in its own canonical
module under ``app/services/indicator_library/indicators``.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from app.services.indicator_library import (
    BUILTIN_INDICATOR_PACK_ANCHOR_NAME,
    builtin_indicator_specs,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


# Used for idempotency on registration. Keep in sync with the registry anchor.
_BUILTIN_PACK_ANCHOR_NAME = BUILTIN_INDICATOR_PACK_ANCHOR_NAME
_LEGACY_EXECUTION_TOKENS = (
    "open_long",
    "close_long",
    "open_short",
    "close_short",
    "# @strategy",
    "exit_owner",
    "signal_form",
)
_LEGACY_BUILTIN_SAMPLE_NAMES = (
    _BUILTIN_PACK_ANCHOR_NAME,
    "[示例] 布林带触及",
    "[示例] MACD 柱穿零轴",
    "[示例] 双均线策略",
    "[示例] RSI 超买超卖",
    "Dual Moving Average Strategy",
)


def _builtin_specs() -> List[Dict[str, str]]:
    """Return DB-ready built-in indicators.

    The executable code is loaded from one file per indicator by the registry;
    this function remains as a thin compatibility wrapper for existing callers
    and tests.
    """
    return builtin_indicator_specs()


def seed_builtin_indicators_for_new_user(db: Any, user_id: int) -> int:
    """
    注册成功后写入默认指标库。若该用户已有锚点名称指标则跳过（幂等）。
    返回本次插入条数。
    """
    if not user_id:
        return 0
    now = int(time.time())
    cur = db.cursor()
    try:
        cur.execute(
            """
            SELECT 1 AS x
            FROM qd_indicator_codes
            WHERE user_id = ? AND name = ?
            LIMIT 1
            """,
            (user_id, _BUILTIN_PACK_ANCHOR_NAME),
        )
        if cur.fetchone():
            return 0

        inserted = 0
        for spec in _builtin_specs():
            cur.execute(
                """
                INSERT INTO qd_indicator_codes
                  (user_id, is_buy, end_time, name, code, description,
                   asset_type, createtime, updatetime, created_at, updated_at)
                VALUES (?, 0, 1, ?, ?, ?, 'indicator', ?, ?, NOW(), NOW())
                """,
                (
                    user_id,
                    spec["name"],
                    spec["code"],
                    spec["description"],
                    now,
                    now,
                ),
            )
            inserted += 1
        db.commit()
        if inserted:
            logger.info("Seeded %s builtin indicator(s) for new user_id=%s", inserted, user_id)
        return inserted
    except Exception as e:
        logger.warning("seed_builtin_indicators_for_new_user failed user_id=%s: %s", user_id, e)
        try:
            db.rollback()
        except Exception:
            pass
        return 0
    finally:
        try:
            cur.close()
        except Exception:
            pass


def sync_builtin_indicator_library_for_existing_users() -> int:
    """Insert newly added built-ins for users who already have an account.

    Existing indicator rows are intentionally left untouched. This makes the
    library upgrade additive: a user can edit or delete a built-in without a
    later application restart overwriting that work. The query-and-insert
    sequence is idempotent for the single-host deployment and safe to repeat on
    every API bootstrap.
    """
    from app.utils.db import get_db_connection

    specs = _builtin_specs()
    if not specs:
        return 0

    now = int(time.time())
    inserted = 0

    with get_db_connection() as db:
        cur = db.cursor()
        try:
            cur.execute("SELECT id FROM qd_users")
            users = cur.fetchall() or []
            for user in users:
                user_id = user.get("id") if isinstance(user, dict) else user[0]
                if not user_id:
                    continue

                cur.execute(
                    "SELECT name FROM qd_indicator_codes WHERE user_id = ?",
                    (user_id,),
                )
                existing_names = {
                    row.get("name") if isinstance(row, dict) else row[0]
                    for row in (cur.fetchall() or [])
                }
                missing_specs = [spec for spec in specs if spec["name"] not in existing_names]
                for spec in missing_specs:
                    cur.execute(
                        """
                        INSERT INTO qd_indicator_codes
                          (user_id, is_buy, end_time, name, code, description,
                           asset_type, createtime, updatetime, created_at, updated_at)
                        VALUES (?, 0, 1, ?, ?, ?, 'indicator', ?, ?, NOW(), NOW())
                        """,
                        (
                            user_id,
                            spec["name"],
                            spec["code"],
                            spec["description"],
                            now,
                            now,
                        ),
                    )
                    inserted += 1

            db.commit()
            if inserted:
                logger.info("Synced %s missing builtin indicator(s) for existing users", inserted)
            return inserted
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            logger.warning("sync_builtin_indicator_library_for_existing_users failed: %s", e)
            return 0
        finally:
            try:
                cur.close()
            except Exception:
                pass


def _code_contains_legacy_execution_contract(code: str) -> bool:
    raw = code or ""
    return any(token in raw for token in _LEGACY_EXECUTION_TOKENS)


def upgrade_builtin_indicator_samples() -> int:
    """
    Upgrade persisted official samples to the current chart-indicator contract.

    Older built-in samples contained execution-contract annotations and signal
    column names. This intentionally updates only known official sample names
    when those legacy tokens are still present.
    """
    from app.utils.db import get_db_connection

    specs = _builtin_specs()
    if not specs:
        return 0

    target = specs[0]
    placeholders = ",".join(["?"] * len(_LEGACY_BUILTIN_SAMPLE_NAMES))
    now = int(time.time())
    updated = 0

    with get_db_connection() as db:
        cur = db.cursor()
        try:
            cur.execute(
                f"""
                SELECT id, name, code
                FROM qd_indicator_codes
                WHERE (is_buy IS NULL OR is_buy = 0)
                  AND name IN ({placeholders})
                """,
                tuple(_LEGACY_BUILTIN_SAMPLE_NAMES),
            )
            rows = cur.fetchall() or []
            for row in rows:
                row_id = row.get("id") if isinstance(row, dict) else row[0]
                code = row.get("code") if isinstance(row, dict) else row[2]
                if not _code_contains_legacy_execution_contract(code or ""):
                    continue
                cur.execute(
                    """
                    UPDATE qd_indicator_codes
                    SET name = ?, code = ?, description = ?,
                        updatetime = ?, updated_at = NOW()
                    WHERE id = ?
                    """,
                    (
                        target["name"],
                        target["code"],
                        target["description"],
                        now,
                        row_id,
                    ),
                )
                updated += int(cur.rowcount or 0)
            db.commit()
            if updated:
                logger.info("Upgraded %s builtin indicator sample(s) to chart-only contract", updated)
            return updated
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            logger.warning("upgrade_builtin_indicator_samples failed: %s", e)
            return 0
        finally:
            try:
                cur.close()
            except Exception:
                pass
