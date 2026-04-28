import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PySide6.QtCore import QCoreApplication, QTimer
from island_ui.state_machine import IslandStateMachine, IslandState


def test_state_transitions():
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    sm = IslandStateMachine(compact_timeout_ms=200)

    assert sm.state() == IslandState.IDLE

    sm.on_event_arrived()
    assert sm.state() == IslandState.COMPACT

    sm.on_expand_requested()
    assert sm.state() == IslandState.EXPANDED

    sm.on_collapse_requested()
    assert sm.state() == IslandState.COMPACT

    # Wait for idle timeout
    done = [False]

    def check():
        if sm.state() == IslandState.IDLE:
            done[0] = True
            app.quit()

    timer = QTimer()
    timer.timeout.connect(check)
    timer.start(100)

    # Safety quit
    QTimer.singleShot(1000, app.quit)

    app.exec()

    assert done[0], f"Expected IDLE after timeout, got {sm.state()}"
    print("State machine test passed!")


if __name__ == "__main__":
    test_state_transitions()
