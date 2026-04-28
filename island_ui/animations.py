from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QPoint, QObject
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect


class FadeSlideInAnimation(QObject):
    def __init__(self, widget: QWidget, duration_ms: int = 250, parent: QObject = None):
        super().__init__(parent or widget)
        self._widget = widget
        self._duration_ms = duration_ms

        self._opacity_effect = QGraphicsOpacityEffect(widget)
        self._opacity_effect.setOpacity(0.0)
        widget.setGraphicsEffect(self._opacity_effect)

        self._opacity_anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._opacity_anim.setDuration(duration_ms)
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._pos_anim = QPropertyAnimation(widget, b"pos", self)
        self._pos_anim.setDuration(duration_ms)
        self._pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def start(self) -> None:
        start_pos = self._widget.pos() + QPoint(0, -10)
        end_pos = self._widget.pos()
        self._pos_anim.setStartValue(start_pos)
        self._pos_anim.setEndValue(end_pos)

        self._opacity_anim.start()
        self._pos_anim.start()


class FadeSlideOutAnimation(QObject):
    def __init__(self, widget: QWidget, duration_ms: int = 250, parent: QObject = None):
        super().__init__(parent or widget)
        self._widget = widget
        self._duration_ms = duration_ms

        self._opacity_effect = QGraphicsOpacityEffect(widget)
        self._opacity_effect.setOpacity(1.0)
        widget.setGraphicsEffect(self._opacity_effect)

        self._opacity_anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._opacity_anim.setDuration(duration_ms)
        self._opacity_anim.setStartValue(1.0)
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.InCubic)

        self._pos_anim = QPropertyAnimation(widget, b"pos", self)
        self._pos_anim.setDuration(duration_ms)
        self._pos_anim.setEasingCurve(QEasingCurve.Type.InCubic)

    def start(self) -> None:
        start_pos = self._widget.pos()
        end_pos = self._widget.pos() + QPoint(0, -10)
        self._pos_anim.setStartValue(start_pos)
        self._pos_anim.setEndValue(end_pos)

        self._opacity_anim.finished.connect(self._widget.hide)
        self._opacity_anim.start()
        self._pos_anim.start()


class HeightAnimation(QObject):
    def __init__(self, widget: QWidget, duration_ms: int = 300, parent: QObject = None):
        super().__init__(parent or widget)
        self._widget = widget
        self._anim = QPropertyAnimation(widget, b"maximumHeight", self)
        self._anim.setDuration(duration_ms)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def set_target(self, target_height: int) -> None:
        self._anim.setStartValue(self._widget.height())
        self._anim.setEndValue(target_height)

    def start(self) -> None:
        self._anim.start()


class WidthAnimation(QObject):
    def __init__(self, widget: QWidget, duration_ms: int = 300, parent: QObject = None):
        super().__init__(parent or widget)
        self._widget = widget
        self._anim = QPropertyAnimation(widget, b"minimumWidth", self)
        self._anim.setDuration(duration_ms)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def set_target(self, target_width: int) -> None:
        self._anim.setStartValue(self._widget.width())
        self._anim.setEndValue(target_width)

    def start(self) -> None:
        self._anim.start()
