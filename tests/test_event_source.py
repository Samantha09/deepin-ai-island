import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PySide6.QtCore import QCoreApplication, QTimer
from island_ui.event_source import MockEventSource
from island_ui.events import SessionStarted, PermissionRequested


def test_mock_source_emits_events():
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    source = MockEventSource(interval_ms=100)
    received = []

    def on_event(event):
        received.append(event)

    source.event_received.connect(on_event)
    source.start()

    # Give some time for the timer to fire a couple of events
    loop_count = [0]

    def check():
        loop_count[0] += 1
        if loop_count[0] >= 3 or len(received) >= 2:
            app.quit()

    timer = QTimer()
    timer.timeout.connect(check)
    timer.start(50)

    app.exec()

    assert len(received) >= 2, f"Expected at least 2 events, got {len(received)}"
    assert isinstance(received[0], SessionStarted)
    assert isinstance(received[1], PermissionRequested)
    source.stop()
    print("MockEventSource test passed!")


if __name__ == "__main__":
    test_mock_source_emits_events()
