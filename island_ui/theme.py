"""主题管理与语义化颜色令牌体系."""

from enum import Enum

from PySide6.QtWidgets import QWidget


class ThemePreset(Enum):
    """可用主题预设."""

    DARK = "dark"
    LIGHT = "light"
    CLASSIC = "classic"


PALETTES: dict[str, dict[str, str]] = {
    "dark": {
        "window_bg": "#151519",
        "panel_bg": "rgba(30,30,35,1)",
        "card_bg": "rgba(255,255,255,0.05)",
        "card_bg_hover": "rgba(255,255,255,0.08)",
        "control_bg": "rgba(255,255,255,0.06)",
        "control_bg_hover": "rgba(255,255,255,0.10)",
        "primary_text": "#eeeeee",
        "secondary_text": "#888888",
        "muted_text": "rgba(255,255,255,0.4)",
        "inverse_text": "#000000",
        "border": "rgba(255,255,255,0.08)",
        "divider": "rgba(255,255,255,0.08)",
        "accent_green": "#66bf73",
        "accent_amber": "#ffb300",
        "accent_red": "#ff4d4d",
        "accent_blue": "#6699ff",
        "accent_cyan": "#00cccc",
        "accent_magenta": "#cc66cc",
        "accent_allow": "#66bf73",
        "accent_deny": "#ff4d4d",
        "accent_info": "#ffb300",
        "status_running": "#6699ff",
        "status_needs_attention": "#ffb300",
        "status_completed": "#66bf73",
    },
    "light": {
        "window_bg": "#f5f5f7",
        "panel_bg": "#ffffff",
        "card_bg": "rgba(0,0,0,0.03)",
        "card_bg_hover": "rgba(0,0,0,0.06)",
        "control_bg": "rgba(0,0,0,0.04)",
        "control_bg_hover": "rgba(0,0,0,0.08)",
        "primary_text": "#1a1a1a",
        "secondary_text": "#666666",
        "muted_text": "rgba(0,0,0,0.4)",
        "inverse_text": "#ffffff",
        "border": "rgba(0,0,0,0.08)",
        "divider": "rgba(0,0,0,0.08)",
        "accent_green": "#4caf50",
        "accent_amber": "#ff9800",
        "accent_red": "#f44336",
        "accent_blue": "#2196f3",
        "accent_cyan": "#00bcd4",
        "accent_magenta": "#9c27b0",
        "accent_allow": "#4caf50",
        "accent_deny": "#f44336",
        "accent_info": "#ff9800",
        "status_running": "#2196f3",
        "status_needs_attention": "#ff9800",
        "status_completed": "#4caf50",
    },
    "classic": {
        "window_bg": "#0d0d0d",
        "panel_bg": "rgba(24,24,24,1)",
        "card_bg": "rgba(255,255,255,0.03)",
        "card_bg_hover": "rgba(255,255,255,0.06)",
        "control_bg": "rgba(255,255,255,0.05)",
        "control_bg_hover": "rgba(255,255,255,0.09)",
        "primary_text": "#e0e0e0",
        "secondary_text": "#999999",
        "muted_text": "rgba(255,255,255,0.35)",
        "inverse_text": "#000000",
        "border": "rgba(255,255,255,0.06)",
        "divider": "rgba(255,255,255,0.06)",
        "accent_green": "#66bf73",
        "accent_amber": "#ffb300",
        "accent_red": "#ff4d4d",
        "accent_blue": "#6699ff",
        "accent_cyan": "#00cccc",
        "accent_magenta": "#cc66cc",
        "accent_allow": "#66bf73",
        "accent_deny": "#ff4d4d",
        "accent_info": "#ffb300",
        "status_running": "#6699ff",
        "status_needs_attention": "#ffb300",
        "status_completed": "#66bf73",
    },
}


class Theme:
    """管理活动色板并应用到控件."""

    def __init__(self, preset: ThemePreset = ThemePreset.DARK) -> None:
        """使用给定预设初始化.

        Args:
            preset: 初始主题预设. 默认为 DARK.
        """
        self._preset = preset

    def current_id(self) -> str:
        """返回活动预设标识符.

        Returns:
            预设值字符串, 例如 "dark".
        """
        return self._preset.value

    def current(self) -> dict[str, str]:
        """返回活动色板字典.

        Returns:
            颜色角色名到颜色值的映射.
        """
        return PALETTES[self.current_id()]

    def color(self, key: str) -> str:
        """安全地按 key 取颜色值.

        Args:
            key: 颜色令牌名.

        Returns:
            对应颜色值; 缺失时返回空字符串.
        """
        return self.current().get(key, "")

    def css(self, key: str, alpha: float | None = None) -> str:
        """取颜色值并可选覆盖 alpha.

        Args:
            key: 颜色令牌名.
            alpha: 若提供, 将颜色转为 rgba(alpha).

        Returns:
            CSS 颜色字符串.
        """
        val = self.color(key)
        if alpha is None or not val:
            return val
        # 简单处理 hex 转 rgba; 复杂场景保持原值
        if val.startswith("#") and len(val) == 7:
            r = int(val[1:3], 16)
            g = int(val[3:5], 16)
            b = int(val[5:7], 16)
            return f"rgba({r},{g},{b},{alpha})"
        if val.startswith("rgba("):
            # 替换最后一个 alpha
            parts = val[:-1].split(",")
            if len(parts) == 4:
                return f"rgba({parts[0]},{parts[1]},{parts[2]},{alpha})"
        return val

    def set_preset(self, preset: ThemePreset) -> None:
        """切换到不同预设.

        Args:
            preset: 要激活的新主题预设.
        """
        self._preset = preset

    def apply_to_widget(self, widget: QWidget) -> None:
        """通过 styleSheet 将当前色板应用到控件.

        Args:
            widget: 要设置样式的控件.
        """
        palette = self.current()
        widget.setStyleSheet(
            f"background-color: {palette['panel_bg']};"
            f" color: {palette['primary_text']};"
        )
