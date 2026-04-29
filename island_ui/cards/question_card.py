from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QLineEdit, QWidget

from island_ui.cards.base_card import EventCard
from island_ui.components.styled_button import StyledButton
from island_ui.events import QuestionAsked, QuestionAnswered


class QuestionCard(EventCard):
    answered = Signal(QuestionAnswered)

    def __init__(self, event: QuestionAsked, parent: QWidget = None):
        super().__init__(event, parent)
        question = event.payload.get("question", "")
        options = event.payload.get("options")
        self._colors: dict[str, str] = {}

        self.set_content("Claude asks", question)

        if options:
            self._setup_options(options)
        else:
            self._setup_text_input()

    def _setup_options(self, options: list) -> None:
        self._option_buttons: list[StyledButton] = []
        for opt in options:
            btn = StyledButton(str(opt), variant="secondary")
            btn.setStyleSheet(btn.styleSheet().replace("text-align: center;", "text-align: left;"))
            btn.clicked.connect(lambda checked, o=opt: self._on_option_selected(o))
            self._layout.addWidget(btn)
            self._option_buttons.append(btn)

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

        self._submit_btn = StyledButton("Submit", variant="primary")
        self._submit_btn.clicked.connect(self._on_text_submitted)
        input_layout.addWidget(self._submit_btn)

        self._layout.addLayout(input_layout)

    def refresh_theme(self, colors: dict[str, str]) -> None:
        self._colors = colors
        primary = colors.get("primary_text", "#eeeeee")
        accent = colors.get("accent_blue", "#6699ff")
        accent_hover = colors.get("accent_blue", "#6699ff")
        control_bg = colors.get("control_bg", "rgba(255,255,255,0.06)")
        border = colors.get("border", "rgba(255,255,255,0.08)")

        super().refresh_theme(colors)

        for btn in getattr(self, "_option_buttons", []):
            btn.refresh_theme(colors)
            # 保持左对齐
            ss = btn.styleSheet()
            if "text-align: left;" not in ss:
                btn.setStyleSheet(ss.replace("text-align: center;", "text-align: left;"))

        if hasattr(self, "_input"):
            self._input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {control_bg};
                    color: {primary};
                    border: 1px solid {border};
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-size: 13px;
                }}
            """)

        if hasattr(self, "_submit_btn"):
            self._submit_btn.setStyleSheet(f"""
                StyledButton {{
                    background-color: {accent};
                    color: {colors.get('inverse_text', '#000000')};
                    border: none;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 13px;
                }}
                StyledButton:hover {{
                    background-color: {accent_hover};
                }}
            """)

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
