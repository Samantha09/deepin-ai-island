from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame,
)

from island_ui.cards.base_card import EventCard


class ExpandedPanel(QWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._cards: list[EventCard] = []
        self._setup_ui()
        self._setup_style()

    def _setup_ui(self) -> None:
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._container.setStyleSheet("background-color: #1e1e23;")
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(12, 12, 12, 12)
        self._container_layout.setSpacing(10)
        self._container_layout.addStretch()

        self._scroll.setWidget(self._container)
        self._layout.addWidget(self._scroll)

    def _setup_style(self) -> None:
        self.setStyleSheet("""
            ExpandedPanel {
                background-color: #1e1e23;
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def add_card(self, card: EventCard) -> None:
        self._cards.append(card)
        # Insert before the stretch
        self._container_layout.insertWidget(self._container_layout.count() - 1, card)
        card.resolved.connect(self._on_card_resolved)

    def _on_card_resolved(self, card: EventCard) -> None:
        if card in self._cards:
            self._cards.remove(card)
        # card.deleteLater() is handled by the card itself after animation

    def remove_card(self, card: EventCard) -> None:
        if card in self._cards:
            self._cards.remove(card)
            card.deleteLater()

    def clear_cards(self) -> None:
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()

    def card_count(self) -> int:
        return len(self._cards)

    def unresolved_count(self) -> int:
        return sum(1 for c in self._cards if not c.is_resolved())

    def cards(self) -> list[EventCard]:
        return list(self._cards)
