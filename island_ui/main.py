import sys
import argparse
import os

# Add project root to path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import yaml
from PySide6.QtWidgets import QApplication

from island_ui.event_source import MockEventSource
from island_ui.state_machine import IslandStateMachine
from island_ui.island_window import IslandWindow


def load_config(path: str = None) -> dict:
    if path is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, "config", "default.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="Deepin AI Island")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    config = load_config()
    island_cfg = config.get("island", {})
    debug_cfg = config.get("debug", {})

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    compact_timeout = island_cfg.get("compact_timeout_ms", 5000)
    state_machine = IslandStateMachine(compact_timeout_ms=compact_timeout)

    source = MockEventSource(interval_ms=3000)

    window = IslandWindow(event_source=source, state_machine=state_machine)
    window.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
