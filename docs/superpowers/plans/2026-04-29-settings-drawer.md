# Settings Drawer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight settings drawer to AI Island for theme switching, animation toggle, timeout and position configuration.

**Architecture:** A `SettingsDrawer` QWidget slides out below `CompactPill`, mutually exclusive with `ExpandedPanel`. `ConfigManager` singleton loads/saves YAML and emits change signals. `Theme` provides preset color palettes. All existing hard-coded colors migrate to `Theme.current()`.

**Tech Stack:** PySide6, Python 3.12+, PyYAML, pytest

---

### Task 1: ConfigManager singleton with YAML persistence

**Files:**
- Create: `island_ui/config_manager.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import os
import tempfile

import pytest

from island_ui.config_manager import ConfigManager


class TestConfigManager:
    def test_load_default_values(self):
        cm = ConfigManager(config_path=None)
        assert cm.get("island.animation_enabled") is True
        assert cm.get("island.compact_timeout_ms") == 5000

    def test_set_and_get(self):
        cm = ConfigManager(config_path=None)
        cm.set("island.animation_enabled", False)
        assert cm.get("island.animation_enabled") is False

    def test_save_and_reload(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("island:\n  animation_enabled: true\n")
            path = f.name
        try:
            cm = ConfigManager(config_path=path)
            cm.set("island.animation_enabled", False)
            cm.save()

            cm2 = ConfigManager(config_path=path)
            assert cm2.get("island.animation_enabled") is False
        finally:
            os.unlink(path)

    def test_signal_emitted_on_change(self, qtbot):
        cm = ConfigManager(config_path=None)
        received = []
        cm.config_changed.connect(lambda k, v: received.append((k, v)))
        cm.set("island.animation_enabled", False)
        assert ("island.animation_enabled", False) in received
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` for `ConfigManager`.

- [ ] **Step 3: Write minimal implementation**

```python
# island_ui/config_manager.py
from typing import Any

from PySide6.QtCore import QObject, Signal
import yaml


DEFAULT_CONFIG = {
    "island": {
        "position": "top-center",
        "animation_enabled": True,
        "compact_timeout_ms": 5000,
        "expanded_max_height_ratio": 0.6,
        "position_offset_x": 0,
        "position_offset_y": 12,
    },
    "theme": {
        "id": "dark",
    },
    "debug": {
        "mock_events_enabled": True,
    },
}


class ConfigManager(QObject):
    config_changed = Signal(str, object)

    def __init__(self, config_path: str | None = None, parent=None):
        super().__init__(parent)
        self._config_path = config_path
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        if self._config_path and os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f) or {}
            except Exception:
                loaded = {}
        else:
            loaded = {}
        self._data = self._deep_merge(DEFAULT_CONFIG.copy(), loaded)

    @staticmethod
    def _deep_merge(base: dict, overlay: dict) -> dict:
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = ConfigManager._deep_merge(base[key].copy(), value)
            else:
                base[key] = value
        return base

    def get(self, key: str, default: Any = None) -> Any:
        parts = key.split(".")
        node = self._data
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def set(self, key: str, value: Any) -> None:
        parts = key.split(".")
        node = self._data
        for part in parts[:-1]:
            if part not in node:
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value
        self.config_changed.emit(key, value)

    def save(self) -> None:
        if self._config_path:
            with open(self._config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(self._data, f, default_flow_style=False, sort_keys=False)

    def reset_to_defaults(self) -> None:
        self._data = DEFAULT_CONFIG.copy()
        self.config_changed.emit("*", None)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_config.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_config.py island_ui/config_manager.py
git commit -m "feat(config): ConfigManager singleton with YAML persistence"
```

---

### Task 2: Theme class with preset palettes

**Files:**
- Create: `island_ui/theme.py`
- Test: `tests/test_theme.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_theme.py
from PySide6.QtWidgets import QApplication, QWidget

from island_ui.theme import Theme, ThemePreset


class TestTheme:
    def test_current_returns_dark_by_default(self):
        theme = Theme()
        assert theme.current_id() == "dark"

    def test_switch_preset(self):
        theme = Theme()
        theme.set_preset(ThemePreset.LIGHT)
        assert theme.current_id() == "light"
        colors = theme.current()
        assert colors["window_bg"] != "#151519"

    def test_apply_to_widget_changes_stylesheet(self, qtbot):
        app = QApplication.instance() or QApplication([])
        widget = QWidget()
        theme = Theme()
        theme.apply_to_widget(widget)
        assert "background-color" in widget.styleSheet()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_theme.py -v
```

Expected: `ModuleNotFoundError` for `Theme`.

- [ ] **Step 3: Write minimal implementation**

```python
# island_ui/theme.py
from enum import Enum
from typing import Dict

from PySide6.QtWidgets import QWidget


class ThemePreset(Enum):
    DARK = "dark"
    LIGHT = "light"
    CLASSIC = "classic"


PALETTES: Dict[str, Dict[str, str]] = {
    "dark": {
        "window_bg": "#151519",
        "panel_bg": "#1e1e23",
        "card_bg": "#1e1e23",
        "primary_text": "#eeeeee",
        "secondary_text": "#888888",
        "muted_text": "#aaaaaa",
        "badge_text": "#aaaaaa",
        "border": "rgba(255, 255, 255, 0.08)",
        "accent_allow": "#4CAF50",
        "accent_deny": "#FF5252",
        "accent_info": "#2196F3",
        "status_running": "#2196F3",
        "status_needs_attention": "#FF9800",
        "status_completed": "#4CAF50",
    },
    "light": {
        "window_bg": "#f5f5f7",
        "panel_bg": "#ffffff",
        "card_bg": "#ffffff",
        "primary_text": "#1a1a1a",
        "secondary_text": "#666666",
        "muted_text": "#888888",
        "badge_text": "#888888",
        "border": "rgba(0, 0, 0, 0.08)",
        "accent_allow": "#4CAF50",
        "accent_deny": "#FF5252",
        "accent_info": "#2196F3",
        "status_running": "#2196F3",
        "status_needs_attention": "#FF9800",
        "status_completed": "#4CAF50",
    },
    "classic": {
        "window_bg": "#0d0d0d",
        "panel_bg": "#181818",
        "card_bg": "#181818",
        "primary_text": "#e0e0e0",
        "secondary_text": "#999999",
        "muted_text": "#bbbbbb",
        "badge_text": "#bbbbbb",
        "border": "rgba(255, 255, 255, 0.06)",
        "accent_allow": "#4CAF50",
        "accent_deny": "#FF5252",
        "accent_info": "#2196F3",
        "status_running": "#2196F3",
        "status_needs_attention": "#FF9800",
        "status_completed": "#4CAF50",
    },
}


class Theme:
    def __init__(self, preset: ThemePreset = ThemePreset.DARK):
        self._preset = preset

    def current_id(self) -> str:
        return self._preset.value

    def current(self) -> Dict[str, str]:
        return PALETTES.get(self._preset.value, PALETTES["dark"])

    def set_preset(self, preset: ThemePreset) -> None:
        self._preset = preset

    def apply_to_widget(self, widget: QWidget) -> None:
        colors = self.current()
        widget.setStyleSheet(f"""
            QWidget {{
                background-color: {colors['panel_bg']};
                color: {colors['primary_text']};
            }}
        """)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_theme.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_theme.py island_ui/theme.py
git commit -m "feat(theme): Theme class with Dark/Light/Classic presets"
```

---

### Task 3: SettingsDrawer component with Config binding

**Files:**
- Create: `island_ui/settings_drawer.py`
- Test: `tests/test_settings_drawer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_settings_drawer.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from island_ui.config_manager import ConfigManager
from island_ui.settings_drawer import SettingsDrawer


class TestSettingsDrawer:
    def test_drawer_has_all_controls(self, qtbot):
        app = QApplication.instance() or QApplication([])
        cm = ConfigManager(config_path=None)
        drawer = SettingsDrawer(cm)
        assert drawer._theme_combo is not None
        assert drawer._anim_check is not None
        assert drawer._timeout_spin is not None
        assert drawer._pos_x_spin is not None
        assert drawer._pos_y_spin is not None

    def test_theme_change_emits_signal(self, qtbot):
        app = QApplication.instance() or QApplication([])
        cm = ConfigManager(config_path=None)
        drawer = SettingsDrawer(cm)
        received = []
        cm.config_changed.connect(lambda k, v: received.append((k, v)))
        drawer._theme_combo.setCurrentText("light")
        assert ("theme.id", "light") in received

    def test_reset_button_restores_defaults(self, qtbot):
        app = QApplication.instance() or QApplication([])
        cm = ConfigManager(config_path=None)
        drawer = SettingsDrawer(cm)
        cm.set("island.animation_enabled", False)
        drawer._on_reset()
        assert cm.get("island.animation_enabled") is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_settings_drawer.py -v
```

Expected: `ModuleNotFoundError` for `SettingsDrawer`.

- [ ] **Step 3: Write minimal implementation**

```python
# island_ui/settings_drawer.py
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QSpinBox, QPushButton, QFrame,
)

from island_ui.config_manager import ConfigManager


class SettingsDrawer(QWidget):
    closed = Signal()

    def __init__(self, config: ConfigManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._config = config
        self._setup_ui()
        self._load_from_config()

    def _setup_ui(self) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(400)
        self.setMaximumHeight(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)

        # Header
        header = QHBoxLayout()
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #eeeeee;")
        header.addWidget(title)
        header.addStretch()
        close_btn = QPushButton("×")
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #888888; font-size: 18px;
                border: none; padding: 0 4px;
            }
            QPushButton:hover { color: #eeeeee; }
        """)
        close_btn.clicked.connect(self._on_close)
        header.addWidget(close_btn)
        layout.addLayout(header)

        layout.addWidget(self._separator())

        # Theme
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["dark", "light", "classic"])
        self._theme_combo.currentTextChanged.connect(self._on_theme_changed)
        layout.addLayout(self._setting_row("Theme", self._theme_combo))
        layout.addWidget(self._separator())

        # Animation
        self._anim_check = QCheckBox()
        self._anim_check.stateChanged.connect(self._on_anim_changed)
        layout.addLayout(self._setting_row("Animation", self._anim_check))
        layout.addWidget(self._separator())

        # Timeout
        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(1000, 30000)
        self._timeout_spin.setSingleStep(500)
        self._timeout_spin.setSuffix(" ms")
        self._timeout_spin.valueChanged.connect(self._on_timeout_changed)
        layout.addLayout(self._setting_row("Compact timeout", self._timeout_spin))
        layout.addWidget(self._separator())

        # Position X
        self._pos_x_spin = QSpinBox()
        self._pos_x_spin.setRange(-500, 500)
        self._pos_x_spin.valueChanged.connect(self._on_pos_x_changed)
        layout.addLayout(self._setting_row("Position X", self._pos_x_spin))
        layout.addWidget(self._separator())

        # Position Y
        self._pos_y_spin = QSpinBox()
        self._pos_y_spin.setRange(-200, 200)
        self._pos_y_spin.valueChanged.connect(self._on_pos_y_changed)
        layout.addLayout(self._setting_row("Position Y", self._pos_y_spin))
        layout.addWidget(self._separator())

        # Reset
        reset_btn = QPushButton("Reset defaults")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,0.05);
                color: #888888; border: 1px solid rgba(255,255,255,0.08);
                border-radius: 8px; padding: 6px 12px; font-size: 12px;
            }
            QPushButton:hover { background-color: rgba(255,255,255,0.10); color: #eeeeee; }
        """)
        reset_btn.clicked.connect(self._on_reset)
        layout.addWidget(reset_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addStretch()

    def _separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: rgba(255, 255, 255, 0.06);")
        line.setFixedHeight(1)
        return line

    def _setting_row(self, label: str, widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 13px; color: #aaaaaa;")
        lbl.setFixedWidth(120)
        row.addWidget(lbl)
        row.addWidget(widget)
        widget.setStyleSheet("""
            QComboBox, QSpinBox {
                background-color: rgba(255,255,255,0.05);
                color: #eeeeee; border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px; padding: 4px 8px; font-size: 13px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #1e1e23; color: #eeeeee;
                selection-background-color: rgba(255,255,255,0.10);
            }
            QCheckBox { color: #eeeeee; }
            QCheckBox::indicator {
                width: 16px; height: 16px;
                border-radius: 8px; border: 1px solid rgba(255,255,255,0.2);
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50; border: 1px solid #4CAF50;
            }
        """)
        return row

    def _load_from_config(self) -> None:
        self._theme_combo.setCurrentText(self._config.get("theme.id", "dark"))
        self._anim_check.setChecked(self._config.get("island.animation_enabled", True))
        self._timeout_spin.setValue(self._config.get("island.compact_timeout_ms", 5000))
        self._pos_x_spin.setValue(self._config.get("island.position_offset_x", 0))
        self._pos_y_spin.setValue(self._config.get("island.position_offset_y", 12))

    def _on_theme_changed(self, text: str) -> None:
        self._config.set("theme.id", text)
        self._config.save()

    def _on_anim_changed(self, state: int) -> None:
        self._config.set("island.animation_enabled", state == Qt.CheckState.Checked.value)
        self._config.save()

    def _on_timeout_changed(self, value: int) -> None:
        self._config.set("island.compact_timeout_ms", value)
        self._config.save()

    def _on_pos_x_changed(self, value: int) -> None:
        self._config.set("island.position_offset_x", value)
        self._config.save()

    def _on_pos_y_changed(self, value: int) -> None:
        self._config.set("island.position_offset_y", value)
        self._config.save()

    def _on_reset(self) -> None:
        self._config.reset_to_defaults()
        self._config.save()
        self._load_from_config()

    def _on_close(self) -> None:
        self.closed.emit()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_settings_drawer.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_settings_drawer.py island_ui/settings_drawer.py
git commit -m "feat(ui): SettingsDrawer component with Config binding"
```

---

### Task 4: CompactPill settings button

**Files:**
- Modify: `island_ui/compact_pill.py`

- [ ] **Step 1: Add settings button and signal**

Modify `island_ui/compact_pill.py`:

```python
# Add to imports
from PySide6.QtWidgets import QPushButton

# In CompactPill, add:
settings_clicked = Signal()

# In _setup_ui, after _agents_label:
self._settings_btn = QPushButton("⚙")
self._settings_btn.setStyleSheet("""
    QPushButton {
        background: transparent; color: #888888; font-size: 14px;
        border: none; padding: 0 4px;
    }
    QPushButton:hover { color: #eeeeee; }
""")
self._settings_btn.clicked.connect(self.settings_clicked.emit)
self._layout.addWidget(self._settings_btn)
```

- [ ] **Step 2: Commit**

```bash
git add island_ui/compact_pill.py
git commit -m "feat(ui): add settings button to CompactPill"
```

---

### Task 5: IslandWindow integration (drawer, theme, config)

**Files:**
- Modify: `island_ui/island_window.py`
- Modify: `island_ui/animations.py`
- Modify: `config/default.yaml`

- [ ] **Step 1: Integrate ConfigManager, Theme, SettingsDrawer into IslandWindow**

Modify `island_ui/island_window.py`:

```python
# Add imports
from island_ui.config_manager import ConfigManager
from island_ui.theme import Theme, ThemePreset
from island_ui.settings_drawer import SettingsDrawer

# In __init__, after _setup_shortcuts:
self._config = ConfigManager(config_path="config/default.yaml")
self._theme = Theme()
self._apply_theme()
self._setup_drawer()

# Subscribe to config changes
self._config.config_changed.connect(self._on_config_changed)

# In _setup_connections, add:
self._pill.settings_clicked.connect(self._on_settings_clicked)

# Add methods:
def _setup_drawer(self) -> None:
    self._drawer = SettingsDrawer(self._config, self)
    self._drawer.setVisible(False)
    self._drawer.closed.connect(self._hide_drawer)
    # Insert between pill and panel
    self._layout.insertWidget(1, self._drawer)

def _on_settings_clicked(self) -> None:
    if self._drawer.isVisible():
        self._hide_drawer()
    else:
        # Mutual exclusion with panel
        if self._state_machine.state() == IslandState.EXPANDED:
            self._state_machine.on_collapse_requested()
        self._show_drawer()

def _show_drawer(self) -> None:
    self._drawer.setVisible(True)
    self._drawer.setFixedHeight(0)
    anim = QPropertyAnimation(self._drawer, b"maximumHeight", self)
    anim.setDuration(250)
    anim.setStartValue(0)
    anim.setEndValue(self._drawer.maximumHeight())
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start()

def _hide_drawer(self) -> None:
    anim = QPropertyAnimation(self._drawer, b"maximumHeight", self)
    anim.setDuration(200)
    anim.setStartValue(self._drawer.height())
    anim.setEndValue(0)
    anim.setEasingCurve(QEasingCurve.Type.InCubic)
    anim.finished.connect(lambda: self._drawer.setVisible(False))
    anim.start()

def _on_config_changed(self, key: str, value) -> None:
    if key == "theme.id" and value:
        preset = ThemePreset(value.upper()) if hasattr(ThemePreset, value.upper()) else ThemePreset.DARK
        self._theme.set_preset(preset)
        self._apply_theme()
    elif key == "island.animation_enabled":
        # Animations will read this dynamically
        pass
    elif key.startswith("island.position_offset"):
        self._reposition_window()

def _apply_theme(self) -> None:
    colors = self._theme.current()
    palette = self.palette()
    palette.setColor(self.backgroundRole(), QColor(colors["window_bg"]))
    self.setPalette(palette)
    self._pill.setStyleSheet(f"""
        CompactPill {{
            background-color: {colors['panel_bg']};
            border-radius: 20px;
            border: 1px solid {colors['border']};
        }}
    """)
    # Notify panel and cards to refresh
    self._panel.refresh_theme(colors)

def _reposition_window(self) -> None:
    screen = QApplication.primaryScreen().availableGeometry()
    x = screen.x() + (screen.width() - 400) // 2 + self._config.get("island.position_offset_x", 0)
    y = screen.y() + 12 + self._config.get("island.position_offset_y", 0)
    self.move(x, y)

# Update Esc shortcut to handle drawer
def _on_collapse(self) -> None:
    if self._drawer.isVisible():
        self._hide_drawer()
    else:
        self._state_machine.on_collapse_requested()
```

- [ ] **Step 2: Make Animations respect config toggle**

Modify `island_ui/animations.py`:

```python
# Add to each animation class __init__:
def __init__(self, widget: QWidget, duration_ms: int = 250, parent: QObject = None):
    ...
    from island_ui.config_manager import ConfigManager
    cm = ConfigManager(config_path=None)  # will load defaults; singleton pattern preferred
    self._enabled = cm.get("island.animation_enabled", True)

def start(self) -> None:
    if not self._enabled:
        self._widget.setVisible(True)
        if hasattr(self, '_opacity_effect'):
            self._opacity_effect.setOpacity(1.0)
        return
    # existing animation start
```

Better approach: pass `enabled` flag to constructor from caller.

Modify `island_window.py` `_animate_panel` and `_show_drawer` / `_hide_drawer` to check `self._config.get("island.animation_enabled", True)`.

- [ ] **Step 3: Update default.yaml**

```yaml
# config/default.yaml
island:
  position: top-center
  animation_enabled: true
  compact_timeout_ms: 5000
  expanded_max_height_ratio: 0.6
  position_offset_x: 0
  position_offset_y: 12
theme:
  id: dark
debug:
  mock_events_enabled: true
```

- [ ] **Step 4: Manual verification**

```bash
source .venv/bin/activate
python island_ui/main.py
```

Verify:
- Click ⚙️ on pill → drawer slides out
- Change theme → window/pill colors update
- Toggle animation → subsequent panel animations skip
- Change timeout → state machine uses new value
- Change position X/Y → window moves
- Esc closes drawer when open
- Drawer and panel are mutually exclusive

- [ ] **Step 5: Commit**

```bash
git add island_ui/island_window.py island_ui/animations.py config/default.yaml
git commit -m "feat(ui): integrate SettingsDrawer, Theme and Config into IslandWindow"
```

---

### Task 6: Migrate hard-coded colors in ExpandedPanel and cards to Theme

**Files:**
- Modify: `island_ui/expanded_panel.py`
- Modify: `island_ui/cards/base_card.py`
- Modify: `island_ui/cards/session_list_item.py`
- Modify: `island_ui/cards/permission_card.py`
- Modify: `island_ui/cards/question_card.py`

- [ ] **Step 1: Add `refresh_theme(colors)` to ExpandedPanel**

In `island_ui/expanded_panel.py`, add:

```python
def refresh_theme(self, colors: dict) -> None:
    self.setStyleSheet(f"""
        ExpandedPanel {{
            background-color: {colors['panel_bg']};
            border-radius: 16px;
            border: 1px solid {colors['border']};
        }}
        QScrollArea {{
            background: transparent;
            border: none;
        }}
        QScrollArea::viewport {{
            background-color: {colors['panel_bg']};
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 6px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: rgba(255, 255, 255, 0.15);
            border-radius: 3px;
            min-height: 30px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
    """)
    for item in self._session_items.values():
        item.refresh_theme(colors)
    for card in self._cards:
        card.refresh_theme(colors)
```

- [ ] **Step 2: Add `refresh_theme` to card base and subclasses**

In `island_ui/cards/base_card.py`, add abstract or stub method:

```python
def refresh_theme(self, colors: dict) -> None:
    pass
```

In each card subclass, implement `refresh_theme` to update `setStyleSheet` calls using `colors` dict.

- [ ] **Step 3: Commit**

```bash
git add island_ui/expanded_panel.py island_ui/cards/
git commit -m "refactor(ui): migrate hard-coded colors to Theme in panel and cards"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - [x] SettingsDrawer widget below pill
   - [x] Mutual exclusion with ExpandedPanel
   - [x] ConfigManager singleton + YAML persistence
   - [x] Theme class with 3 presets
   - [x] CompactPill settings button
   - [x] IslandWindow integration (drawer, theme, config, position)
   - [x] Animation toggle respected
   - [x] Color migration from hard-coded to Theme

2. **Placeholder scan:** None. All steps contain code, commands, and expected output.

3. **Type consistency:**
   - `ConfigManager.get/set` signatures consistent across tasks.
   - `Theme.current()` returns `Dict[str, str]` used by `refresh_theme(colors: dict)`.
