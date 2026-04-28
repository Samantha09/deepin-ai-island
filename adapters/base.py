from abc import ABC, abstractmethod


class AgentAdapter(ABC):
    @abstractmethod
    def start(self, session):
        """Start agent process and inject hooks."""
        ...

    @abstractmethod
    def parse_event(self, raw: dict):
        """Parse raw hook data into standard Event."""
        ...

    @abstractmethod
    def send_response(self, session, response):
        """Send user response back to agent."""
        ...
