# tests/test_clear_completed.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import MagicMock

from island_ui.session import Session
from island_ui.events import SessionStarted, SessionEnded, ProgressUpdated


def _make_window():
    """构造一个带 sessions 的 mock window。"""
    window = MagicMock()
    window._sessions = {}
    window._completed_timers = {}
    window._config_manager = MagicMock()

    def _push():
        pass
    window._push_sessions_to_web = _push

    # 绑定要测试的方法
    from island_ui.island_window import IslandWindow
    window.clear_completed_sessions = lambda: IslandWindow.clear_completed_sessions(window)
    window.set_sound_enabled = lambda e: IslandWindow.set_sound_enabled(window, e)
    window.set_sound_volume = lambda v: IslandWindow.set_sound_volume(window, v)

    return window


def test_clear_completed_removes_completed_and_idle():
    window = _make_window()
    s1 = Session(id="s1", name="Running", agent="test", terminal="")
    s1.status = "running"
    s2 = Session(id="s2", name="Completed", agent="test", terminal="")
    s2.status = "completed"
    s3 = Session(id="s3", name="Idle", agent="test", terminal="")
    s3.status = "idle"
    s4 = Session(id="s4", name="Needs Attention", agent="test", terminal="")
    s4.status = "needs_attention"

    window._sessions = {"s1": s1, "s2": s2, "s3": s3, "s4": s4}
    window.clear_completed_sessions()

    assert "s1" in window._sessions
    assert "s2" not in window._sessions
    assert "s3" not in window._sessions
    assert "s4" in window._sessions


def test_clear_completed_cleans_timers():
    window = _make_window()
    from PySide6.QtCore import QTimer
    timer = QTimer()
    window._completed_timers["s2"] = timer

    s = Session(id="s2", name="Completed", agent="test", terminal="")
    s.status = "completed"
    window._sessions = {"s2": s}
    window.clear_completed_sessions()

    assert "s2" not in window._completed_timers


def test_clear_completed_no_op_when_nothing_to_remove():
    window = _make_window()
    s1 = Session(id="s1", name="Running", agent="test", terminal="")
    s1.status = "running"
    window._sessions = {"s1": s1}

    window.clear_completed_sessions()
    assert "s1" in window._sessions


def test_set_sound_enabled_updates_config():
    window = _make_window()
    window.set_sound_enabled(False)
    window._config_manager.set.assert_called_once_with("sound.enabled", False)


def test_set_sound_volume_clamps_and_updates_config():
    window = _make_window()
    window.set_sound_volume(150)
    window._config_manager.set.assert_called_once_with("sound.volume", 100)

    window._config_manager.reset_mock()
    window.set_sound_volume(-10)
    window._config_manager.set.assert_called_once_with("sound.volume", 0)


if __name__ == "__main__":
    test_clear_completed_removes_completed_and_idle()
    test_clear_completed_cleans_timers()
    test_clear_completed_no_op_when_nothing_to_remove()
    test_set_sound_enabled_updates_config()
    test_set_sound_volume_clamps_and_updates_config()
    print("All clear-completed tests passed!")
