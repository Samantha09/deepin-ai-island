from PySide6.QtWidgets import QWidget

from island_ui.cards.base_card import EventCard
from island_ui.cards.permission_card import PermissionCard
from island_ui.cards.question_card import QuestionCard
from island_ui.cards.message_card import MessageCard
from island_ui.events import (
    Event,
    PermissionRequested,
    QuestionAsked,
    ProgressUpdated,
    SessionStarted,
    SessionEnded,
)


class CardFactory:
    @staticmethod
    def create_card(event: Event, parent: QWidget = None) -> EventCard | None:
        if isinstance(event, PermissionRequested):
            return PermissionCard(event, parent)
        elif isinstance(event, QuestionAsked):
            return QuestionCard(event, parent)
        elif isinstance(event, (ProgressUpdated, SessionStarted, SessionEnded)):
            if isinstance(event, ProgressUpdated):
                msg = event.payload.get("message", "")
                # 跳过与 PermissionCard 重复的等待消息，以及信息量低的已完成消息
                if msg.startswith(("等待批准", "已完成")):
                    return None
            return MessageCard(event, parent)
        else:
            return None
