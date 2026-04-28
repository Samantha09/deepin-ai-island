from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QLineEdit, QWidget

from island_ui.cards.base_card import EventCard
from island_ui.events import QuestionAsked, QuestionAnswered


class QuestionCard(EventCard):
    answered = Signal(QuestionAnswered)

    def __init__(self, event: QuestionAsked, parent: QWidget = None):
        super().__init__(event, parent)
        question = event.payload.get("question", "")
        options = event.payload.get("options")

        self.set_content("Claude asks", question)

        if options:
            self._setup_options(options)
        else:
            self._setup_text_input()

    def _setup_options(self, options: list) -> None:
        for opt in options:
            btn = QPushButton(str(opt))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.08);
                    color: #eeeeee;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 14px;
                    font-size: 13px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.15);
                }
            """)
            btn.clicked.connect(lambda checked, o=opt: self._on_option_selected(o))
            self._layout.addWidget(btn)

    def _setup_text_input(self) -> None:
        input_layout = QVBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("Type your answer...")
        self._input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.08);
                color: #eeeeee;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }
        """)
        input_layout.addWidget(self._input)

        submit_btn = QPushButton("Submit")
        submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        submit_btn.clicked.connect(self._on_text_submitted)
        input_layout.addWidget(submit_btn)

        self._layout.addLayout(input_layout)

    def _on_option_selected(self, option: str) -> None:
        response = QuestionAnswered(answer=option, session_id=self._event.session_id)
        self.answered.emit(response)
        self.mark_resolved()

    def _on_text_submitted(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        response = QuestionAnswered(answer=text, session_id=self._event.session_id)
        self.answered.emit(response)
        self.mark_resolved()
