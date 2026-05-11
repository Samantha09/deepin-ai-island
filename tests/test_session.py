import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
from island_ui.session import Session
from island_ui.events import ChatMessage, ProgressUpdated, QuestionAsked


def test_session_last_updated_default():
    s = Session(id="s1", name="Test", agent="a1", terminal="t1")
    assert s.last_updated > 0
    assert s.last_updated >= s.start_time


def test_session_last_updated_on_add_event():
    s = Session(id="s1", name="Test", agent="a1", terminal="t1")
    before = s.last_updated
    time.sleep(0.01)
    s.add_event(ChatMessage(session_id="s1", role="user", content="hello"))
    assert s.last_updated > before


def test_session_last_updated_reflects_latest_event():
    s = Session(id="s1", name="Test", agent="a1", terminal="t1")
    s.add_event(ChatMessage(session_id="s1", role="user", content="first"))
    time.sleep(0.01)
    s.add_event(ProgressUpdated(session_id="s1", message="second"))
    assert s.last_updated == s.events[-1].timestamp


def test_question_asked_sets_needs_attention():
    s = Session(id="test", name="test", agent="Claude Code", terminal="")
    s.status = "running"
    s.add_event(QuestionAsked(session_id="test", question="Continue?", options=["Yes", "No"]))
    assert s.status == "needs_attention"


def test_question_answered_restores_running():
    s = Session(id="test", name="test", agent="Claude Code", terminal="")
    s.status = "running"
    s.add_event(QuestionAsked(session_id="test", question="Continue?", options=["Yes", "No"], payload={"tool_use_id": "q-001"}))
    assert s.status == "needs_attention"
    # 模拟用户回答后 mark_permission_resolved 恢复状态
    s.mark_permission_resolved("q-001")
    s.add_event(ChatMessage(session_id="test", role="user", content="Yes"))
    assert s.status == "running"


if __name__ == "__main__":
    test_session_last_updated_default()
    test_session_last_updated_on_add_event()
    test_session_last_updated_reflects_latest_event()
    print("All session tests passed!")
