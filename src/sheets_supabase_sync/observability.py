from __future__ import annotations

import json
import logging
from typing import Any

SAFE_FIELDS = frozenset(
    {
        "event",
        "data_source_id",
        "sync_run_id",
        "status",
        "operation",
        "attempt",
        "attempts",
        "max_attempts",
        "error_code",
        "error_category",
        "retryable",
        "wait_ms",
        "backoff_ms",
        "duration_ms",
        "outcome",
        "rows_read",
        "rows_inserted",
        "rows_updated",
        "rows_deleted",
        "rows_restored",
        "rows_unchanged",
        "columns_read",
        "empty_rows",
        "retries",
    }
)


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    payload = {"event": event, **{key: value for key, value in fields.items() if key in SAFE_FIELDS and value is not None}}
    logger.info(json.dumps(payload, ensure_ascii=False, sort_keys=True))
