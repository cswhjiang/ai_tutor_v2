#!/usr/bin/env python3
"""Analyze AI Tutor structured timing logs."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


TIMING_LOG_PREFIX = "AI_TUTOR_TIMING"


def parse_timing_records(text: str) -> list[dict[str, Any]]:
    """Parse structured timing records from log text."""
    records: list[dict[str, Any]] = []
    for line in text.splitlines():
        prefix_index = line.find(TIMING_LOG_PREFIX)
        if prefix_index < 0:
            continue
        payload = line[prefix_index + len(TIMING_LOG_PREFIX) :].strip()
        if not payload:
            continue
        try:
            record = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def load_timing_records(paths: Iterable[Path]) -> list[dict[str, Any]]:
    """Load structured timing records from one or more log files."""
    records: list[dict[str, Any]] = []
    for path in paths:
        records.extend(parse_timing_records(path.read_text(encoding="utf-8")))
    return records


def _format_duration(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value) / 1000:.2f}s"
    except (TypeError, ValueError):
        return str(value)


def _format_metadata(metadata: Any) -> str:
    if not metadata:
        return ""
    if isinstance(metadata, dict):
        compact = {
            key: value
            for key, value in metadata.items()
            if key in {"status", "route", "mode", "scene_name", "artifact_count", "output_chars", "video_bytes"}
        }
        if compact:
            return json.dumps(compact, ensure_ascii=False, sort_keys=True)
    return ""


def format_timing_summary(records: list[dict[str, Any]]) -> str:
    """Format timing records as Markdown grouped by trace id."""
    end_records = [record for record in records if record.get("event") == "stage_end"]
    if not end_records:
        return "No timing records found."

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in end_records:
        grouped[str(record.get("trace_id") or "unknown")].append(record)

    lines: list[str] = []
    for trace_id, trace_records in sorted(grouped.items()):
        trace_records.sort(key=lambda item: str(item.get("timestamp") or ""))
        total_ms = sum(
            float(record.get("duration_ms") or 0)
            for record in trace_records
            if record.get("stage") == "http" and record.get("name") == "chat_request"
        )
        if not total_ms:
            total_ms = sum(
                float(record.get("duration_ms") or 0)
                for record in trace_records
                if record.get("stage") == "agent"
            )

        lines.append(f"## Trace `{trace_id}`")
        if total_ms:
            lines.append(f"Total: {_format_duration(total_ms)}")
        lines.append("")
        lines.append("| Stage | Name | Status | Duration | Metadata |")
        lines.append("|---|---|---:|---:|---|")
        for record in trace_records:
            lines.append(
                "| {stage} | {name} | {status} | {duration} | {metadata} |".format(
                    stage=record.get("stage", ""),
                    name=record.get("name", ""),
                    status=record.get("status", ""),
                    duration=_format_duration(record.get("duration_ms")),
                    metadata=_format_metadata(record.get("metadata")),
                )
            )
        lines.append("")
    return "\n".join(lines).rstrip()


def main() -> int:
    """Run the timing analyzer CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", nargs="+", type=Path, help="Log files to analyze")
    args = parser.parse_args()

    records = load_timing_records(args.logs)
    print(format_timing_summary(records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
