import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from island_ui.events import (
    Event,
    SessionStarted,
    SessionEnded,
    PermissionRequested,
    QuestionAsked,
    ProgressUpdated,
    PermissionResolved,
    QuestionAnswered,
    event_to_dict,
    event_from_dict,
)


def test_event_base():
    e = Event(type="test", payload={"key": "value"})
    assert e.type == "test"
    assert e.payload == {"key": "value"}
    assert e.timestamp > 0
    assert len(e.session_id) > 0


def test_session_started():
    e = SessionStarted()
    assert e.type == "session.started"
    d = event_to_dict(e)
    assert d["type"] == "session.started"


def test_session_ended():
    e = SessionEnded()
    assert e.type == "session.ended"


def test_permission_requested():
    e = PermissionRequested(action="edit main.py")
    assert e.type == "permission.requested"
    assert e.action == "edit main.py"
    assert e.payload["action"] == "edit main.py"


def test_question_asked():
    e = QuestionAsked(question="Continue?", options=["Yes", "No"])
    assert e.type == "question.asked"
    assert e.question == "Continue?"
    assert e.options == ["Yes", "No"]
    assert e.payload["question"] == "Continue?"
    assert e.payload["options"] == ["Yes", "No"]


def test_question_asked_no_options():
    e = QuestionAsked(question="What is your name?")
    assert e.options is None
    assert "options" not in e.payload


def test_progress_updated():
    e = ProgressUpdated(message="Analyzing code...", percent=50)
    assert e.type == "progress.updated"
    assert e.message == "Analyzing code..."
    assert e.percent == 50


def test_permission_resolved():
    r = PermissionResolved(approved=True)
    assert r.type == "permission.resolved"
    assert r.payload["approved"] is True


def test_question_answered():
    r = QuestionAnswered(answer="Use pytest")
    assert r.type == "question.answered"
    assert r.payload["answer"] == "Use pytest"


def test_event_serialization_roundtrip():
    original = PermissionRequested(action="delete file.txt")
    d = event_to_dict(original)
    restored = event_from_dict(d)
    assert restored.type == original.type
    assert restored.payload == original.payload
    assert restored.session_id == original.session_id


def test_event_from_dict_all_types():
    tests = [
        ({"type": "session.started", "payload": {}}, SessionStarted),
        ({"type": "session.ended", "payload": {}}, SessionEnded),
        ({"type": "permission.requested", "payload": {"action": "x"}}, PermissionRequested),
        ({"type": "question.asked", "payload": {"question": "q"}}, QuestionAsked),
        ({"type": "progress.updated", "payload": {"message": "m"}}, ProgressUpdated),
    ]
    for data, expected_cls in tests:
        e = event_from_dict(data)
        assert isinstance(e, expected_cls), f"Expected {expected_cls}, got {type(e)}"


def test_event_from_dict_unknown_type():
    e = event_from_dict({"type": "unknown.event", "payload": {}})
    assert isinstance(e, Event)
    assert e.type == "unknown.event"


if __name__ == "__main__":
    test_event_base()
    test_session_started()
    test_session_ended()
    test_permission_requested()
    test_question_asked()
    test_question_asked_no_options()
    test_progress_updated()
    test_permission_resolved()
    test_question_answered()
    test_event_serialization_roundtrip()
    test_event_from_dict_all_types()
    test_event_from_dict_unknown_type()
    print("All events tests passed!")
