from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from datetime import datetime
import uuid


@dataclass
class Event:
    type: str
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
        }


@dataclass
class SessionStarted(Event):
    type: str = field(default="session.started", init=False)


@dataclass
class SessionEnded(Event):
    type: str = field(default="session.ended", init=False)


@dataclass
class PermissionRequested(Event):
    type: str = field(default="permission.requested", init=False)
    action: str = field(default="")

    def __post_init__(self):
        if self.action and "action" not in self.payload:
            self.payload["action"] = self.action


@dataclass
class QuestionAsked(Event):
    type: str = field(default="question.asked", init=False)
    question: str = field(default="")
    options: Optional[list] = field(default=None)

    def __post_init__(self):
        if self.question and "question" not in self.payload:
            self.payload["question"] = self.question
        if self.options is not None and "options" not in self.payload:
            self.payload["options"] = self.options


@dataclass
class ProgressUpdated(Event):
    type: str = field(default="progress.updated", init=False)
    message: str = field(default="")
    percent: Optional[int] = field(default=None)

    def __post_init__(self):
        if self.message and "message" not in self.payload:
            self.payload["message"] = self.message
        if self.percent is not None and "percent" not in self.payload:
            self.payload["percent"] = self.percent


@dataclass
class ChatMessage(Event):
    type: str = field(default="chat.message", init=False)
    role: str = field(default="assistant")  # user, assistant, system
    content: str = field(default="")

    def __post_init__(self):
        if self.content and "content" not in self.payload:
            self.payload["content"] = self.content
        if self.role and "role" not in self.payload:
            self.payload["role"] = self.role


@dataclass
class Response:
    type: str
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    session_id: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
        }


@dataclass
class PermissionResolved(Response):
    type: str = field(default="permission.resolved", init=False)
    approved: bool = field(default=False)

    def __post_init__(self):
        self.payload["approved"] = self.approved


@dataclass
class QuestionAnswered(Response):
    type: str = field(default="question.answered", init=False)
    answer: str = field(default="")

    def __post_init__(self):
        self.payload["answer"] = self.answer


def event_to_dict(event: Event) -> dict:
    return event.to_dict()


def event_from_dict(data: dict) -> Event:
    event_type = data.get("type", "")
    payload = data.get("payload", {})
    timestamp = data.get("timestamp", datetime.now().timestamp())
    session_id = data.get("session_id", str(uuid.uuid4()))

    type_map = {
        "session.started": SessionStarted,
        "session.ended": SessionEnded,
        "permission.requested": PermissionRequested,
        "question.asked": QuestionAsked,
        "progress.updated": ProgressUpdated,
    }

    cls = type_map.get(event_type, Event)

    if cls is Event:
        return cls(type=event_type, payload=payload, timestamp=timestamp, session_id=session_id)
    elif cls is PermissionRequested:
        return cls(payload=payload, timestamp=timestamp, session_id=session_id, action=payload.get("action", ""))
    elif cls is QuestionAsked:
        return cls(payload=payload, timestamp=timestamp, session_id=session_id, question=payload.get("question", ""), options=payload.get("options"))
    elif cls is ProgressUpdated:
        return cls(payload=payload, timestamp=timestamp, session_id=session_id, message=payload.get("message", ""), percent=payload.get("percent"))
    else:
        return cls(payload=payload, timestamp=timestamp, session_id=session_id)
