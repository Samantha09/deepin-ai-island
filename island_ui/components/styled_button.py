"""统一风格按钮, 支持多种变体."""

from PySide6.QtWidgets import QPushButton


class StyledButton(QPushButton):
    """统一按钮: primary / secondary / ghost / danger."""

    VARIANTS = {"primary", "secondary", "ghost", "danger"}

    def __init__(self, text: str = "", variant: str = "secondary", parent=None) -> None:
        super().__init__(text, parent)
        self._variant = variant
        self._colors: dict[str, str] = {}
        self.setCursor(self.cursor())

    def set_variant(self, variant: str) -> None:
        """切换按钮变体并刷新样式."""
        if variant in self.VARIANTS:
            self._variant = variant
            self._apply_style()

    def refresh_theme(self, colors: dict[str, str]) -> None:
        """应用主题颜色."""
        self._colors = colors
        self._apply_style()

    def _apply_style(self) -> None:
        c = self._colors
        v = self._variant

        if v == "primary":
            bg = c.get("accent_blue", "#6699ff")
            fg = c.get("inverse_text", "#000000")
            hover_bg = c.get("accent_blue", "#6699ff")  # 简化, 不计算亮度
        elif v == "danger":
            bg = c.get("accent_red", "#ff4d4d")
            fg = "#ffffff"
            hover_bg = c.get("accent_red", "#ff4d4d")
        elif v == "ghost":
            bg = "transparent"
            fg = c.get("secondary_text", "#888888")
            hover_bg = c.get("card_bg_hover", "rgba(255,255,255,0.08)")
        else:  # secondary
            bg = c.get("control_bg", "rgba(255,255,255,0.06)")
            fg = c.get("primary_text", "#eeeeee")
            hover_bg = c.get("control_bg_hover", "rgba(255,255,255,0.10)")

        self.setStyleSheet(
            f"StyledButton {{"
            f"  background-color: {bg};"
            f"  color: {fg};"
            f"  border: none;"
            f"  border-radius: 8px;"
            f"  padding: 8px 14px;"
            f"  font-size: 12px;"
            f"}}"
            f"StyledButton:hover {{"
            f"  background-color: {hover_bg};"
            f"}}"
        )
