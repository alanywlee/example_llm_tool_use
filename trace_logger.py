from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any


def _json_default(obj: Any) -> str:
    return repr(obj)


class TraceLogger:
    """
    Simple file-based trace logger.

    Log file path format:
        logs/YYYYMMDD-HHMMSS-trace.log

    The logger writes JSON Lines so it is easy to grep, parse, or load later.
    """

    def __init__(self, log_dir: str = "logs") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        startup_time = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.log_path = self.log_dir / f"{startup_time}-trace.log"

        logger_name = f"trace.{startup_time}"
        self._logger = logging.getLogger(logger_name)
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        handler = logging.FileHandler(self.log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(handler)

        self.event(
            "trace_started",
            {
                "log_path": str(self.log_path),
                "startup_time": startup_time,
            },
        )

    def event(self, event_name: str, payload: dict[str, Any] | None = None) -> None:
        record = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "event": event_name,
            "payload": payload or {},
        }

        self._logger.info(
            json.dumps(record, ensure_ascii=False, default=_json_default)
        )

    def text(self, event_name: str, text: str) -> None:
        self.event(event_name, {"text": text})


def compact_messages_for_trace(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Keep trace useful without dumping huge payloads blindly.
    """
    compact: list[dict[str, Any]] = []

    for message in messages:
        role = message.get("role")
        content = message.get("content")

        item: dict[str, Any] = {
            "role": role,
        }

        if isinstance(content, str):
            item["content_preview"] = content[:1000]
            item["content_length"] = len(content)
        else:
            item["content"] = content

        if "tool_calls" in message:
            item["tool_calls"] = message["tool_calls"]

        if "tool_call_id" in message:
            item["tool_call_id"] = message["tool_call_id"]

        if "name" in message:
            item["name"] = message["name"]

        compact.append(item)

    return compact
