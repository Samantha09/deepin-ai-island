from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame, QPushButton, QLabel,
)
from PySide6.QtGui import QFont

from island_ui.cards.base_card import EventCard
from island_ui.cards.session_list_item import SessionListItem
from island_ui.session import Session


class ExpandedPanel(QWidget):
    session_selected = Signal(str)
    session_hovered = Signal(str)
    back_to_list = Signal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._cards: list[EventCard] = []
        self._session_items: dict[str, SessionListItem] = {}
        self._current_session_id: str = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.setMinimumWidth(360)

        # ── Session List View ──
        self._session_list_widget = QWidget()
        self._session_list_layout = QVBoxLayout(self._session_list_widget)
        self._session_list_layout.setContentsMargins(12, 12, 12, 12)
        self._session_list_layout.setSpacing(8)
        self._session_list_layout.addStretch()

        self._session_scroll = QScrollArea()
        self._session_scroll.setWidgetResizable(True)
        self._session_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._session_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._session_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._session_scroll.setWidget(self._session_list_widget)
        self._session_scroll.setMinimumHeight(200)

        # ── Event Detail View ──
        self._detail_widget = QWidget()
        self._detail_layout = QVBoxLayout(self._detail_widget)
        self._detail_layout.setContentsMargins(12, 12, 12, 12)
        self._detail_layout.setSpacing(10)

        # Back button
        self._back_btn = QPushButton("←  Back")
        self._back_btn.setStyleSheet("""
            QPushButton {
                border: none;
                font-size: 13px;
                padding: 4px;
                text-align: left;
            }
        """)
        self._back_btn.clicked.connect(self._on_back)
        self._detail_layout.addWidget(self._back_btn)

        self._detail_title = QLabel("")
        self._detail_title.setStyleSheet("font-size: 14px; color: #eeeeee; font-weight: 500;")
        self._detail_layout.addWidget(self._detail_title)

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(10)
        self._cards_layout.addStretch()
        self._detail_layout.addWidget(self._cards_container)

        self._detail_scroll = QScrollArea()
        self._detail_scroll.setWidgetResizable(True)
        self._detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._detail_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._detail_scroll.setWidget(self._detail_widget)
        self._detail_scroll.setMinimumHeight(200)

        # Add both to main layout, only one visible at a time
        self._layout.addWidget(self._session_scroll)
        self._layout.addWidget(self._detail_scroll)

        self._show_view("list")

    def _show_view(self, view: str) -> None:
        if view == "list":
            self._session_scroll.setVisible(True)
            self._detail_scroll.setVisible(False)
            self._current_session_id = ""
        else:
            self._session_scroll.setVisible(False)
            self._detail_scroll.setVisible(True)

    def show_session_list(self) -> None:
        self._show_view("list")
        self._clear_selection()

    def show_event_detail(self, session_id: str, session_name: str) -> None:
        self._current_session_id = session_id
        self._detail_title.setText(session_name)
        # 立即从布局中移除旧卡片，避免 deleteLater 异步删除期间参与 sizeHint 计算
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        self._cards.clear()
        self._show_view("detail")
        self._set_selected_session(session_id)

    def _set_selected_session(self, session_id: str) -> None:
        """高亮当前选中的会话项，清除其他项的高亮."""
        for sid, item in self._session_items.items():
            item.set_selected(sid == session_id)

    def _clear_selection(self) -> None:
        """清除所有会话项的选中高亮."""
        for item in self._session_items.values():
            item.set_selected(False)

    def add_session_item(self, session: Session) -> None:
        if session.id in self._session_items:
            self._session_items[session.id].update_status()
            return
        item = SessionListItem(session, self._session_list_widget)
        item.clicked.connect(self.session_selected.emit)
        item.hovered.connect(self.session_hovered.emit)
        self._session_items[session.id] = item
        # Insert before stretch
        self._session_list_layout.insertWidget(self._session_list_layout.count() - 1, item)
        if hasattr(self, "_colors"):
            item.refresh_theme(self._colors)
        self._update_minimum_height()

    def update_session_item(self, session: Session) -> None:
        if session.id in self._session_items:
            self._session_items[session.id].update_status()

    def add_event_card(self, card: EventCard) -> None:
        self._cards.append(card)
        self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
        if hasattr(self, "_colors"):
            card.refresh_theme(self._colors)
        card.resolved.connect(self._on_card_resolved)

    def _on_card_resolved(self, card: EventCard) -> None:
        if card in self._cards:
            self._cards.remove(card)

    def _on_back(self) -> None:
        self.back_to_list.emit()
        self.show_session_list()

    def clear_cards(self) -> None:
        """清理所有事件卡片。"""
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        self._cards.clear()

    def remove_session_item(self, session_id: str) -> None:
        item = self._session_items.pop(session_id, None)
        if item:
            item.deleteLater()
            self._update_minimum_height()

    def clear_sessions(self) -> None:
        for item in self._session_items.values():
            item.deleteLater()
        self._session_items.clear()

    def _update_minimum_height(self) -> None:
        count = len(self._session_items)
        if count == 0:
            self.setMinimumHeight(120)
            self._session_list_widget.setMinimumHeight(80)
        else:
            # 每个 item ~58px + margins 24px + spacing between items
            height = 58 * count + 24 + max(0, count - 1) * 8
            target = min(height + 20, 400)
            target = max(target, 200)  # 不低于 QScrollArea 的 minimumHeight
            self.setMinimumHeight(target)
            self._session_list_widget.setMinimumHeight(height)

    def card_count(self) -> int:
        return len(self._cards)

    def unresolved_count(self) -> int:
        return sum(1 for c in self._cards if not c.is_resolved())

    def cards(self) -> list[EventCard]:
        return list(self._cards)

    def refresh_theme(self, colors: dict[str, str]) -> None:
        """Refresh panel and child widgets with the given color palette."""
        self._colors = colors
        bg = colors.get("panel_bg", "#000000")
        primary = colors.get("primary_text", "#ffffff")
        secondary = colors.get("secondary_text", "#8e8e93")

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                border-radius: 24px;
                border: none;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea::viewport {{
                background-color: {bg};
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 4px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {colors.get("muted_text", "#636366")};
                border-radius: 2px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        self._session_list_widget.setStyleSheet(f"background-color: {bg};")
        self._detail_widget.setStyleSheet(f"background-color: {bg};")
        self._cards_container.setStyleSheet(f"background-color: {bg};")
        self._session_scroll.viewport().setStyleSheet(f"background-color: {bg};")
        self._detail_scroll.viewport().setStyleSheet(f"background-color: {bg};")
        self._detail_title.setStyleSheet(
            f"font-size: 14px; color: {primary}; font-weight: 500;"
        )
        self._back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {secondary};
                border: none;
                font-size: 13px;
                padding: 4px;
                text-align: left;
            }}
            QPushButton:hover {{
                color: {primary};
            }}
        """)
        for item in self._session_items.values():
            item.refresh_theme(colors)
        for card in self._cards:
            card.refresh_theme(colors)
