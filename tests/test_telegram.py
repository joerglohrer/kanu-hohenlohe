import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
from src.notify.telegram import (
    should_push, compose_message, send_push, PushDecision,
)

NOW = datetime(2026, 4, 18, 11, 0, tzinfo=timezone.utc)

def _status(days_stufen):
    return {
        "generated_at": NOW.isoformat(),
        "latest_level_cm": 68,
        "days": [
            {"day": f"2026-04-{18+i}", "stufe": s, "emoji": "🛶" if s == "gruen" else "😐",
             "level_cm": 66, "regen_24h_mm": 0.5, "begruendung": "x", "confidence": 1.0}
            for i, s in enumerate(days_stufen)
        ],
    }

def test_no_push_when_nothing_changed(tmp_path):
    cur = tmp_path / "status.json"; prv = tmp_path / "status.prev.json"
    cur.write_text(json.dumps(_status(["gelb", "gelb", "gelb"])))
    prv.write_text(json.dumps(_status(["gelb", "gelb", "gelb"])))
    d = should_push(cur, prv, last_push_ts=None, now=NOW)
    assert d.kind == PushDecision.NONE

def test_push_on_transition_to_green(tmp_path):
    cur = tmp_path / "status.json"; prv = tmp_path / "status.prev.json"
    cur.write_text(json.dumps(_status(["gruen", "gruen", "gruen"])))
    prv.write_text(json.dumps(_status(["gelb", "gelb", "gelb"])))
    d = should_push(cur, prv, last_push_ts=None, now=NOW)
    assert d.kind == PushDecision.GREEN_WINDOW

def test_push_on_new_two_day_green_block(tmp_path):
    cur = tmp_path / "status.json"; prv = tmp_path / "status.prev.json"
    cur.write_text(json.dumps(_status(["gelb", "gruen", "gruen"])))
    prv.write_text(json.dumps(_status(["gelb", "gelb", "gelb"])))
    d = should_push(cur, prv, last_push_ts=None, now=NOW)
    assert d.kind == PushDecision.GREEN_WINDOW

def test_rate_limit_blocks_within_12h(tmp_path):
    cur = tmp_path / "status.json"; prv = tmp_path / "status.prev.json"
    cur.write_text(json.dumps(_status(["gruen", "gruen", "gruen"])))
    prv.write_text(json.dumps(_status(["gelb", "gelb", "gelb"])))
    recent = NOW - timedelta(hours=6)
    d = should_push(cur, prv, last_push_ts=recent, now=NOW)
    assert d.kind == PushDecision.RATE_LIMITED

def test_compose_message_mentions_level_and_days():
    msg = compose_message(_status(["gruen", "gruen", "gelb"]))
    assert "68" in msg and "cm" in msg
    assert "🛶" in msg

def test_send_push_uses_env_and_posts():
    with patch("src.notify.telegram.requests.post") as p, \
         patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "T", "TELEGRAM_CHAT_ID": "C"}):
        p.return_value.status_code = 200
        p.return_value.json.return_value = {"ok": True}
        send_push("hallo")
        p.assert_called_once()
        args, kwargs = p.call_args
        assert "T" in args[0]  # bot token in URL
        assert kwargs["json"]["chat_id"] == "C"
        assert kwargs["json"]["text"] == "hallo"

def test_rate_limit_allows_at_12h_boundary(tmp_path):
    cur = tmp_path / "status.json"; prv = tmp_path / "status.prev.json"
    cur.write_text(json.dumps(_status(["gruen", "gruen", "gruen"])))
    prv.write_text(json.dumps(_status(["gelb", "gelb", "gelb"])))
    at_boundary = NOW - timedelta(hours=12)
    d = should_push(cur, prv, last_push_ts=at_boundary, now=NOW)
    assert d.kind == PushDecision.GREEN_WINDOW

def test_should_push_tolerates_day_without_stufe_key(tmp_path):
    cur = tmp_path / "status.json"; prv = tmp_path / "status.prev.json"
    # malformed: days contain entries without "stufe"
    cur.write_text(json.dumps({"days": [{"emoji": "🛶"}]}))
    prv.write_text(json.dumps({"days": []}))
    d = should_push(cur, prv, last_push_ts=None, now=NOW)
    # no crash; neither green nor rate-limited → NONE
    assert d.kind == PushDecision.NONE

def test_send_push_raises_when_env_missing():
    with patch.dict("os.environ", {}, clear=True):
        import pytest
        with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
            send_push("hi")
