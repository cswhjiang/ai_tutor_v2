import importlib.util
from pathlib import Path

from src.observability.timing import (
    TIMING_LOG_PREFIX,
    build_timing_record,
    compact_text,
    summarize_payload,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_timing_analyzer_module():
    """Load the timing analyzer script as a testable module."""
    script_path = PROJECT_ROOT / "scripts" / "analyze_timing_log.py"
    spec = importlib.util.spec_from_file_location("analyze_timing_log", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_compact_text_truncates_long_payloads():
    text = "x" * 220

    compacted = compact_text(text, max_len=20)

    assert compacted.startswith("x" * 20)
    assert "truncated chars=220" in compacted


def test_summarize_payload_keeps_timing_logs_compact():
    payload = {
        "short": "ok",
        "long": "a" * 300,
        "binary": b"abc",
    }

    summarized = summarize_payload(payload, max_string_len=30)

    assert summarized["short"] == "ok"
    assert summarized["long"]["chars"] == 300
    assert summarized["binary"] == {"type": "bytes", "bytes": 3}


def test_analyzer_lists_two_agents_separately():
    analyzer = load_timing_analyzer_module()
    shot_record = build_timing_record(
        event="stage_end",
        stage="agent",
        name="SampleAgent",
        trace_id="trace-1",
        status="success",
        duration_ms=1200,
    )
    code_record = build_timing_record(
        event="stage_end",
        stage="agent",
        name="CodeGenerationAgent",
        trace_id="trace-1",
        status="success",
        duration_ms=3400,
    )
    log_text = "\n".join(
        [
            f"2026-01-01 00:00:00 | INFO | {TIMING_LOG_PREFIX} {analyzer.json.dumps(shot_record)}",
            f"2026-01-01 00:00:01 | INFO | {TIMING_LOG_PREFIX} {analyzer.json.dumps(code_record)}",
        ]
    )

    records = analyzer.parse_timing_records(log_text)
    summary = analyzer.format_timing_summary(records)

    assert len(records) == 2
    assert "| agent | SampleAgent | success | 1.20s |  |" in summary
    assert "| agent | CodeGenerationAgent | success | 3.40s |  |" in summary
