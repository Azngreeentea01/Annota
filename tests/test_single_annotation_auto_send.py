import main


class _FakeSignal:
    def __init__(self):
        self.calls = []

    def emit(self, *args):
        self.calls.append(args)


class _FakeOverlay:
    def __init__(self, count):
        self.annotations = [object() for _ in range(count)]
        self.finishedCapture = _FakeSignal()
        self.review_calls = 0
        self.closed = False

    def _show_review(self):
        self.review_calls += 1

    def _build_payload(self):
        return "capture.png", "annotation notes", "capture.json"

    def close(self):
        self.closed = True


def test_single_annotation_auto_send_skips_review(monkeypatch):
    overlay = _FakeOverlay(1)
    applied = []
    cleared = []
    monkeypatch.setattr(main, "_apply_pending_send_route", lambda: applied.append(True))
    monkeypatch.setattr(main, "_clear_pending_send_route", lambda: cleared.append(True))
    monkeypatch.setattr(main, "_diagnostic_event", lambda *_args, **_kwargs: None)

    main._annota_auto_send_or_review(overlay)

    assert overlay.review_calls == 0
    assert overlay.finishedCapture.calls == [
        ("capture.png", "annotation notes", "capture.json")
    ]
    assert overlay.closed
    assert applied == [True]
    assert cleared == [True]


def test_multiple_annotations_auto_send_opens_review(monkeypatch):
    overlay = _FakeOverlay(2)
    monkeypatch.setattr(
        main,
        "_apply_pending_send_route",
        lambda: (_ for _ in ()).throw(AssertionError("direct send should not run")),
    )

    main._annota_auto_send_or_review(overlay)

    assert overlay.review_calls == 1
    assert overlay.finishedCapture.calls == []
    assert not overlay.closed


def test_no_annotations_auto_send_does_nothing():
    overlay = _FakeOverlay(0)

    main._annota_auto_send_or_review(overlay)

    assert overlay.review_calls == 0
    assert overlay.finishedCapture.calls == []
    assert not overlay.closed
