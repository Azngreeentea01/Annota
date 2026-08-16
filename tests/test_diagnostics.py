import json

import main


def test_diagnostics_are_disabled_by_default(tmp_path, monkeypatch):
    target = tmp_path / "trace.jsonl"
    monkeypatch.delenv(main.DIAGNOSTIC_FILE_ENV, raising=False)

    main._diagnostic_event("should_not_write", value=1)

    assert not target.exists()


def test_diagnostics_write_local_jsonl_when_explicitly_enabled(tmp_path, monkeypatch):
    target = tmp_path / "trace.jsonl"
    monkeypatch.setenv(main.DIAGNOSTIC_FILE_ENV, str(target))

    main._diagnostic_event("qa_event", value=7)

    record = json.loads(target.read_text(encoding="utf-8").strip())
    assert record["event"] == "qa_event"
    assert record["value"] == 7
    assert record["pid"] > 0
    assert record["timestamp"]
