"""音效插件 —— 为关键事件播放提示音。"""

import os
import time
from typing import Optional

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect

from island_ui.plugin import IslandPlugin
from island_ui.events import Event


class SoundPlugin(IslandPlugin):
    """内置音效插件。

    触发映射：
    - chat.message        → music/begin.mp3
    - permission.requested → music/alarm.mp3
    - session.ended       → music/end.mp3
    """

    _SOUND_MAP = {
        "chat.message": "begin.mp3",
        "permission.requested": "alarm.mp3",
        "session.ended": "end.mp3",
    }

    _DEBOUNCE_MS = 500

    @property
    def name(self) -> str:
        return "sound"

    @property
    def version(self) -> str:
        return "1.0.0"

    def __init__(self) -> None:
        super().__init__()
        self._config_manager: Optional[object] = None
        self._effects: dict[str, QSoundEffect] = {}
        self._last_played: dict[str, float] = {}
        self._enabled = True
        self._volume = 0.8
        self._base_dir = ""

    def on_load(self, window) -> None:
        self._config_manager = getattr(window, "_config_manager", None)
        self._base_dir = self._resolve_base_dir()
        self._load_config()
        if self._config_manager is not None:
            self._config_manager.config_changed.connect(self._on_config_changed)
        self._setup_effects()

    def _resolve_base_dir(self) -> str:
        """推断项目根目录，兼容开发环境与打包环境。"""
        import sys
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return sys._MEIPASS
        this_file = os.path.abspath(__file__)
        return os.path.dirname(os.path.dirname(os.path.dirname(this_file)))

    def _load_config(self) -> None:
        if self._config_manager is None:
            return
        self._enabled = bool(self._config_manager.get("sound.enabled", True))
        vol = self._config_manager.get("sound.volume", 80)
        self._volume = max(0, min(100, int(vol))) / 100.0

    def _on_config_changed(self, key: str, value: object) -> None:
        if key == "sound.enabled":
            self._enabled = bool(value)
        elif key == "sound.volume":
            self._volume = max(0, min(100, int(value))) / 100.0
            for effect in self._effects.values():
                effect.setVolume(self._volume)
        elif key == "*":
            self._load_config()

    def _setup_effects(self) -> None:
        import logging
        logger = logging.getLogger(__name__)
        music_dir = os.path.join(self._base_dir, "music")
        for event_type, filename in self._SOUND_MAP.items():
            basename, _ = os.path.splitext(filename)
            # 优先尝试 WAV（Qt 原生支持），回退到 MP3
            for ext in (".wav", ".mp3"):
                path = os.path.join(music_dir, basename + ext)
                if os.path.exists(path):
                    break
            else:
                path = os.path.join(music_dir, filename)
            if not os.path.exists(path):
                logger.warning("音效文件不存在: %s", path)
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(path))
            effect.setVolume(self._volume)
            self._effects[event_type] = effect

    def on_event(self, event: Event) -> None:
        if not self._enabled or event.type not in self._effects:
            return
        now = time.time()
        last = self._last_played.get(event.type, 0)
        if (now - last) * 1000 < self._DEBOUNCE_MS:
            return
        self._last_played[event.type] = now
        try:
            self._effects[event.type].play()
        except Exception:
            import logging
            logging.getLogger(__name__).debug("音效播放失败: %s", event.type)
