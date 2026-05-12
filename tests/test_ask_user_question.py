"""测试 AskUserQuestion 事件路由：PermissionRequest + tool_name=AskUserQuestion → QuestionAsked"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from island_ui.claude_code_source import ClaudeCodeEventSource
from island_ui.events import QuestionAsked, PermissionRequested


def _make_ask_user_question_data():
    """构造 Claude Code 实际发送的 AskUserQuestion PermissionRequest 数据"""
    return {
        "session_id": "test-session-001",
        "transcript_path": "/home/san/.claude/projects/test/test-session-001.jsonl",
        "cwd": "/home/san/test",
        "permission_mode": "default",
        "hook_event_name": "PermissionRequest",
        "tool_name": "AskUserQuestion",
        "tool_input": {
            "questions": [{
                "question": "你想使用哪个框架？",
                "header": "框架选择",
                "options": [
                    {"label": "React", "description": "Facebook 的 UI 库"},
                    {"label": "Vue", "description": "渐进式框架"},
                    {"label": "Angular", "description": "Google 的框架"},
                ],
                "multiSelect": False,
            }]
        },
    }


def test_parse_ask_user_question_as_question_asked():
    """PermissionRequest + AskUserQuestion 应解析为 QuestionAsked 事件"""
    source = ClaudeCodeEventSource()
    data = _make_ask_user_question_data()
    event = source._parse_socket_event(data)

    assert isinstance(event, QuestionAsked), f"期望 QuestionAsked，实际 {type(event).__name__}"
    assert event.question == "你想使用哪个框架？"
    assert event.options == ["React", "Vue", "Angular"]
    assert event.session_id == "test-session-001"


def test_parse_ask_user_question_extracts_header():
    """AskUserQuestion 的 header 应存入 payload"""
    source = ClaudeCodeEventSource()
    data = _make_ask_user_question_data()
    event = source._parse_socket_event(data)

    assert event.payload.get("header") == "框架选择"


def test_parse_ask_user_question_stores_raw_options():
    """AskUserQuestion 的原始选项（含 description）应保留在 payload"""
    source = ClaudeCodeEventSource()
    data = _make_ask_user_question_data()
    event = source._parse_socket_event(data)

    raw_options = event.payload.get("raw_options", [])
    assert len(raw_options) == 3
    assert raw_options[0]["label"] == "React"
    assert raw_options[0]["description"] == "Facebook 的 UI 库"


def test_parse_ask_user_question_marks_from_permission():
    """AskUserQuestion 应标记来源为 PermissionRequest，便于响应路由"""
    source = ClaudeCodeEventSource()
    data = _make_ask_user_question_data()
    event = source._parse_socket_event(data)

    assert event.payload.get("_from_permission_request") is True


def test_parse_normal_permission_unchanged():
    """普通 PermissionRequest（非 AskUserQuestion）应仍解析为 PermissionRequested"""
    source = ClaudeCodeEventSource()
    data = {
        "session_id": "test-session-001",
        "hook_event_name": "PermissionRequest",
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"},
        "tool_use_id": "tool_abc123",
    }
    event = source._parse_socket_event(data)

    assert isinstance(event, PermissionRequested), f"期望 PermissionRequested，实际 {type(event).__name__}"
    assert "Bash" in event.action


def test_parse_ask_user_question_with_multiSelect():
    """multiSelect 选项应保留在 payload 中"""
    source = ClaudeCodeEventSource()
    data = _make_ask_user_question_data()
    data["tool_input"]["questions"][0]["multiSelect"] = True
    event = source._parse_socket_event(data)

    assert event.payload.get("multiSelect") is True


if __name__ == "__main__":
    test_parse_ask_user_question_as_question_asked()
    test_parse_ask_user_question_extracts_header()
    test_parse_ask_user_question_stores_raw_options()
    test_parse_ask_user_question_marks_from_permission()
    test_parse_normal_permission_unchanged()
    test_parse_ask_user_question_with_multiSelect()
    print("All AskUserQuestion tests passed!")
