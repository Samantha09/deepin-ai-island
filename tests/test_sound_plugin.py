# tests/test_sound_plugin.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import MagicMock, patch

from island_ui.plugins.sound_plugin import SoundPlugin
from island_ui.events import Event, ChatMessage
from island_ui.config_manager import ConfigManager


def test_sound_plugin_name_and_version():
    p = SoundPlugin()
    assert p.name == "sound"
    assert p.version == "1.0.0"


@patch('island_ui.plugins.sound_plugin.QSoundEffect')
def test_on_event_plays_begin_for_chat_message(mock_qsound_cls):
    mock_effect = MagicMock()
    mock_qsound_cls.return_value = mock_effect

    p = SoundPlugin()
    window = MagicMock()
    window._config_manager = None
    p.on_load(window)

    event = ChatMessage(session_id="s1", role="assistant", content="hello")
    p.on_event(event)

    mock_effect.play.assert_called_once()


@patch('island_ui.plugins.sound_plugin.QSoundEffect')
def test_debounce_prevents_double_play(mock_qsound_cls):
    mock_effect = MagicMock()
    mock_qsound_cls.return_value = mock_effect

    p = SoundPlugin()
    window = MagicMock()
    window._config_manager = None
    p.on_load(window)

    event = ChatMessage(session_id="s1", role="assistant", content="hello")
    p.on_event(event)
    p.on_event(event)  # 立即再次触发

    assert mock_effect.play.call_count == 1


@patch('island_ui.plugins.sound_plugin.QSoundEffect')
def test_disabled_does_not_play(mock_qsound_cls):
    mock_effect = MagicMock()
    mock_qsound_cls.return_value = mock_effect

    p = SoundPlugin()
    cfg = ConfigManager()
    cfg.set("sound.enabled", False)

    window = MagicMock()
    window._config_manager = cfg
    p.on_load(window)

    event = ChatMessage(session_id="s1", role="assistant", content="hello")
    p.on_event(event)

    mock_effect.play.assert_not_called()


@patch('island_ui.plugins.sound_plugin.QSoundEffect')
def test_config_volume_change_updates_effects(mock_qsound_cls):
    mock_effect = MagicMock()
    mock_qsound_cls.return_value = mock_effect

    p = SoundPlugin()
    cfg = ConfigManager()
    cfg.set("sound.volume", 50)

    window = MagicMock()
    window._config_manager = cfg
    p.on_load(window)

    # 初始加载时设置一次音量
    mock_effect.setVolume.assert_called_with(0.5)

    # 运行时修改配置
    cfg.set("sound.volume", 30)
    # set() 会触发 config_changed 信号
    # 由于 QSignal 在纯单元测试中不会真正跨对象发射，
    # 这里直接调用回调验证逻辑
    p._on_config_changed("sound.volume", 30)
    mock_effect.setVolume.assert_called_with(0.3)


if __name__ == "__main__":
    test_sound_plugin_name_and_version()
    test_on_event_plays_begin_for_chat_message()
    test_debounce_prevents_double_play()
    test_disabled_does_not_play()
    test_config_volume_change_updates_effects()
    print("All sound plugin tests passed!")
