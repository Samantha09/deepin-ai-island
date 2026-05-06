import sys
import argparse
import os
from pathlib import Path

def _get_base_dir() -> str:
    """获取项目根目录，兼容 PyInstaller 打包环境。"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Add project root to path for imports
_project_root = _get_base_dir()
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# QWebEngine / Chromium 兼容性配置（参考 Python-island）
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--disable-gpu-compositing "
    "--renderer-process-limit=1 "
    "--disable-extensions "
    "--no-sandbox "
    "--js-flags='--max-old-space-size=128 --expose-gc'"
)


def _fix_qt_platform() -> None:
    """Deepin/DDE 桌面默认要求 dxcb 插件，但虚拟环境 PySide6 通常没有。
    强制使用标准 xcb 平台，并指向系统 Qt 插件路径。"""
    # Deepin 会设置 QT_QPA_PLATFORM=dxcb;xcb，必须覆盖
    os.environ["QT_QPA_PLATFORM"] = "xcb"

    if os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH"):
        return

    # 检查虚拟环境是否自带平台插件
    try:
        import PySide6
        venv_plugins = Path(PySide6.__file__).parent / "plugins" / "platforms"
        if venv_plugins.exists() and any(venv_plugins.iterdir()):
            return
    except Exception:
        pass

    # 常见系统 Qt6 插件路径
    candidates = [
        "/usr/lib/x86_64-linux-gnu/qt6/plugins",
        "/usr/lib/x86_64-linux-gnu/qt5/plugins",
        "/usr/lib/qt6/plugins",
        "/usr/lib/qt5/plugins",
        "/usr/local/lib/qt6/plugins",
    ]
    for path in candidates:
        platforms = Path(path) / "platforms"
        if platforms.exists() and any(platforms.glob("libq*.so")):
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = path
            break


_fix_qt_platform()

import yaml
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from island_ui.event_source import MockEventSource
from island_ui.claude_code_source import ClaudeCodeEventSource
from island_ui.state_machine import IslandStateMachine
from island_ui.island_window import IslandWindow
from island_ui.config_manager import ConfigManager


def _setup_font(app: QApplication) -> None:
    """Set a font that supports CJK characters to avoid garbled text."""
    font = QFont()
    font.setPointSize(13)
    # Try common CJK fonts on Linux, fallback to system default
    for family in ["Noto Sans CJK SC", "WenQuanYi Micro Hei", "Source Han Sans SC", "DejaVu Sans"]:
        font.setFamily(family)
        if font.exactMatch():
            break
    app.setFont(font)


def main():
    parser = argparse.ArgumentParser(description="Deepin AI Island")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--source",
        choices=["mock", "claude"],
        default="claude",
        help="Event source: claude (default) or mock"
    )
    args = parser.parse_args()

    config_path = os.path.join(_get_base_dir(), "config", "default.yaml")
    config_manager = ConfigManager(config_path)
    config = config_manager.data
    island_cfg = config.get("island", {})
    debug_cfg = config.get("debug", {})

    # 使用软件 OpenGL 渲染，避免部分 Linux 驱动兼容问题
    QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    # 全局移除 Qt 默认焦点外框（Linux 桌面常见黄色/橙色轮廓）
    app.setStyleSheet("* { outline: none; }")
    _setup_font(app)

    compact_timeout = island_cfg.get("compact_timeout_ms", 5000)
    state_machine = IslandStateMachine(compact_timeout_ms=compact_timeout)

    if args.source == "claude":
        print("[AI Island] 模式: Claude Code 真实事件 (Unix Socket)")
        source = ClaudeCodeEventSource()
    else:
        print("[AI Island] 模式: Mock 模拟事件")
        source = MockEventSource(interval_ms=3000)

    window = IslandWindow(event_source=source, state_machine=state_machine)
    window._config_manager = config_manager
    window.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
