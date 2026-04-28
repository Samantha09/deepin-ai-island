from PySide6.QtWidgets import QWidget

from island_ui.cards.base_card import EventCard
from island_ui.cards.permission_card import PermissionCard
from island_ui.cards.question_card import QuestionCard
from island_ui.cards.progress_card import ProgressCard
from island_ui.events import (
    Event,
    PermissionRequested,
    QuestionAsked,
    ProgressUpdated,
)


class CardFactory:
    @staticmethod
    def create_card(event: Event, parent: QWidget = None) -> EventCard | None:
        if isinstance(event, PermissionRequested):
            return PermissionCard(event, parent)
        elif isinstance(event, QuestionAsked):
            return QuestionCard(event, parent)
        elif isinstance(event, ProgressUpdated):
            return ProgressCard(event, parent)
        else:
            return None
