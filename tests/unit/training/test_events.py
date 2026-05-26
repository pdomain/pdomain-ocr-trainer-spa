"""events tests — @@PDEVENT@@ stdout line parsing."""

from __future__ import annotations

import json

import pytest

from pdomain_ocr_trainer_spa.training.events import is_event_line, parse_event_line


def test_is_event_line() -> None:
    assert is_event_line('@@PDEVENT@@ {"kind":"log"}')
    assert is_event_line('  @@PDEVENT@@ {"kind":"log"}')
    assert not is_event_line("plain stdout line")


def test_parse_epoch_event_maps_to_progress() -> None:
    line = '@@PDEVENT@@ {"kind":"epoch","message":"epoch 1","progress":0.5,"data":{"epoch":1}}'
    event = parse_event_line(line, job_id="j1", seq=3)
    assert event["kind"] == "progress"
    assert event["job_id"] == "j1"
    assert event["seq"] == 3
    payload = event["payload"]
    assert isinstance(payload, dict)
    assert payload["progress"] == 0.5
    assert payload["data"] == {"epoch": 1}


def test_parse_log_event() -> None:
    event = parse_event_line('@@PDEVENT@@ {"kind":"log","message":"hi"}', job_id="j", seq=0)
    assert event["kind"] == "log"


def test_parse_metric_event() -> None:
    line = '@@PDEVENT@@ {"kind":"metric","message":"val_cer","data":{"value":0.1}}'
    assert parse_event_line(line, job_id="j", seq=0)["kind"] == "metric"


def test_parse_done_event_maps_to_state_succeeded() -> None:
    event = parse_event_line('@@PDEVENT@@ {"kind":"done","message":"ok"}', job_id="j", seq=9)
    assert event["kind"] == "state"
    payload = event["payload"]
    assert isinstance(payload, dict)
    assert payload["state"] == "succeeded"


def test_parse_error_event_maps_to_state_failed() -> None:
    event = parse_event_line('@@PDEVENT@@ {"kind":"error","message":"boom"}', job_id="j", seq=9)
    payload = event["payload"]
    assert isinstance(payload, dict)
    assert payload["state"] == "failed"


def test_parse_non_event_line_raises() -> None:
    with pytest.raises(ValueError, match="not a @@PDEVENT@@ line"):
        parse_event_line("plain output", job_id="j", seq=0)


def test_parse_malformed_payload_raises() -> None:
    with pytest.raises(ValueError, match="malformed"):
        parse_event_line("@@PDEVENT@@ {not json}", job_id="j", seq=0)


def test_parse_unknown_kind_raises() -> None:
    line = "@@PDEVENT@@ " + json.dumps({"kind": "bogus", "message": "x"})
    with pytest.raises(ValueError, match="unknown TrainingEvent kind"):
        parse_event_line(line, job_id="j", seq=0)
