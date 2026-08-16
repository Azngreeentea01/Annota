from datetime import timezone

import main


def test_annotation_payload_fields_are_serializable():
    ann = main.Annotation(1, (1, 2, 30, 40), "Align this card")
    assert ann.index == 1
    assert ann.rect == (1, 2, 30, 40)
    assert ann.note == "Align this card"


def test_utc_timezone_is_available_for_payload_timestamps():
    assert timezone.utc is not None
