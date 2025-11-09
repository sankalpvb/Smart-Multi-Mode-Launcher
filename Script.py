#!/usr/bin/env python3
# designv2.py — Startup Dashboard (PySide6) — watermark removed, settings removed,
# centered Launch button with Save and GitHub on sides, inactivity auto-close (90s)

import sys
import json
import webbrowser
import subprocess
import os
import time
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QTreeWidget,
    QTreeWidgetItem, QPushButton, QLineEdit, QLabel, QListWidget, QListWidgetItem,
    QSplitter, QFileDialog, QMessageBox, QComboBox, QInputDialog, QToolBar,
    QStatusBar, QProgressBar, QSystemTrayIcon, QMenu, QDialog, QDialogButtonBox,
    QTextEdit, QStyle
)
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtCore import Qt, QObject, Signal, QThread, QTimer, QEvent

# ---------- paths & defaults ----------
CONFIG_FILE = Path.home() / ".startup_dashboard_config.json"
LOG_FILE = Path.home() / "startup_dashboard.log"

DEFAULT_MODES = {
    "Study": [
        {"name": "ChatGPT", "type": "url", "value": "https://chat.openai.com", "args": "", "delay_after": 1},
        {"name": "YouTube", "type": "url", "value": "https://www.youtube.com", "args": "", "delay_after": 0.5}
    ],
    "Web Pentest": [
        {"name": "Burp (VBS)", "type": "app", "value": r"C:\burp\Burp-Suite-Pro.vbs", "args": "", "delay_after": 2},
        {"name": "PortSwigger Labs", "type": "url", "value": "https://portswigger.net/web-security/all-labs", "args": "", "delay_after": 0}
    ],
    "Exploitation": [
        {"name": "TryHackMe", "type": "url", "value": "https://tryhackme.com/dashboard", "args": "", "delay_after": 2},
        {"name": "OneNote", "type": "app", "value": r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\OneNote.lnk", "args": "", "delay_after": 1},
        {"name": "VirtualBox App", "type": "app", "value": r"C:\Program Files\Oracle\VirtualBox\VirtualBox.exe", "args": "", "delay_after": 0}
    ],
    "Chill": [
        {"name": "Lofi YouTube", "type": "url", "value": "https://www.youtube.com/results?search_query=lofi+beats", "args": "", "delay_after": 0}
    ]
}

DEFAULT_CONFIG = {
    "profile_name": "Sankalp",
    "active_profile": "Default",
    "profiles": {
        "Default": {
            "initial_delay": 0,
            "post_open_delay": 1,
            "brave_path": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            "virtualbox_path": r"C:\Program Files\Oracle\VirtualBox\VirtualBox.exe",
            "onenote_path": r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\OneNote.lnk",
            "burp_path": r"C:\burp\Burp-Suite-Pro.vbs",
            "modes": DEFAULT_MODES
        }
    }
}

GITHUB_URL = "https://github.com/sankalpvb"
INACTIVITY_MS = 90_000  # 90 seconds (1.5 minutes)

# ---------- logging ----------
def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line)

# ---------- config I/O ----------
def load_config():
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if "profiles" not in data and "modes" in data:
                return {
                    "profile_name": data.get("profile_name", "Sankalp"),
                    "active_profile": "Default",
                    "profiles": {
                        "Default": {
                            "initial_delay": data.get("initial_delay", 0),
                            "post_open_delay": data.get("post_open_delay", 1),
                            "modes": data.get("modes", DEFAULT_MODES)
                        }
                    }
                }
            return data
        except Exception as e:
            log(f"Failed loading config: {e}")
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    try:
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        log(f"Saved config to {CONFIG_FILE}")
    except Exception as e:
        log(f"Failed saving config: {e}")

# ---------- threaded launcher ----------
class LauncherSignals(QObject):
    step_started = Signal(int, int, str)
    finished = Signal()
    error = Signal(str)

class LauncherWorker(QObject):
    def __init__(self, profile, mode_name):
        super().__init__()
        self.profile = profile
        self.mode_name = mode_name
        self.signals = LauncherSignals()
        self._abort = False

    def run(self):
        try:
            modes = self.profile.get("modes", {})
            steps = modes.get(self.mode_name, [])
            total = len(steps)
            initial_delay = float(self.profile.get("initial_delay", 0) or 0)
            post_default = float(self.profile.get("post_open_delay", 1) or 1)

            if initial_delay > 0:
                self.signals.step_started.emit(0, total, f"Stabilizing {initial_delay}s")
                time.sleep(initial_delay)

            for idx, step in enumerate(steps, start=1):
                if self._abort:
                    break
                label = step.get("name") or step.get("value")
                self.signals.step_started.emit(idx, total, label)
                stype = step.get("type", "app")
                target = step.get("value", "")
                args = step.get("args", "")
                delay_after = float(step.get("delay_after", post_default) or post_default)

                if stype == "url":
                    try:
                        webbrowser.open(target, new=2)
                        log(f"Opened URL: {target}")
                    except Exception as e:
                        log(f"Failed opening URL {target}: {e}")
                else:
                    try:
                        if os.name == "nt":
                            if target and os.path.exists(target):
                                try:
                                    os.startfile(target)
                                    log(f"os.startfile: {target}")
                                except Exception:
                                    subprocess.Popen([target] + (args.split() if args else []), shell=False)
                                    log(f"Popen fallback: {target}")
                            else:
                                subprocess.Popen(target, shell=True)
                                log(f"Popen shell: {target}")
                        else:
                            subprocess.Popen([target] + (args.split() if args else []))
                            log(f"Popen: {target}")
                    except Exception as e:
                        log(f"Failed starting app {target}: {e}")

                elapsed = 0.0
                while elapsed < delay_after:
                    if self._abort:
                        break
                    time.sleep(0.2)
                    elapsed += 0.2
                if self._abort:
                    break

            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(str(e))

    def abort(self):
        self._abort = True

# ---------- main window ----------
class StartupDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Startup Dashboard — Editor & Launcher")
        self.resize(1100, 650)

        self.cfg = load_config()
        if "profiles" not in self.cfg:
            self.cfg = DEFAULT_CONFIG.copy()

        self.profiles = self.cfg.setdefault("profiles", DEFAULT_CONFIG["profiles"])
        self.active_profile = self.cfg.get("active_profile", list(self.profiles.keys())[0])
        self.profile_name = self.cfg.get("profile_name", "Sankalp")

        self._worker = None
        self._thread = None

        # inactivity timer
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.setSingleShot(True)
        self.inactivity_timer.timeout.connect(self._on_inactivity_timeout)

        # install event filter to detect user interaction
        QApplication.instance()  # ensure app exists if called early
        self.installEventFilter(self)

        # toolbar
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        toolbar.addWidget(QLabel("Profile: "))
        self.name_edit = QLineEdit(self.profile_name)
        self.name_edit.setMaximumWidth(250)
        self.name_edit.editingFinished.connect(self.on_name_changed)
        toolbar.addWidget(self.name_edit)

        toolbar.addSeparator()
        toolbar.addWidget(QLabel("Active Profile: "))
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(list(self.profiles.keys()))
        self.profile_combo.setCurrentText(self.active_profile)
        self.profile_combo.currentTextChanged.connect(self.on_profile_changed)
        toolbar.addWidget(self.profile_combo)

        # central layout
        center = QWidget()
        main_layout = QVBoxLayout(center)
        self.setCentralWidget(center)

        top_splitter = QSplitter()
        top_splitter.setOrientation(Qt.Horizontal)

        # left pane (narrower)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8,8,8,8)
        left_layout.addWidget(QLabel("Launch Modes"))
        self.modes_list = QListWidget()
        self.modes_list.setMaximumWidth(220)
        self.modes_list.itemClicked.connect(self.on_mode_selected)
        left_layout.addWidget(self.modes_list)
        btn_add_mode = QPushButton("Add Mode"); btn_add_mode.clicked.connect(self.add_mode)
        btn_remove_mode = QPushButton("Remove Mode"); btn_remove_mode.clicked.connect(self.remove_mode)
        left_layout.addWidget(btn_add_mode); left_layout.addWidget(btn_remove_mode)
        left_layout.addSpacing(6)
        left_layout.addWidget(QLabel("Quick Search"))
        self.search_text = QLineEdit(); self.search_text.returnPressed.connect(self.quick_search)
        left_layout.addWidget(self.search_text)
        self.search_combo = QComboBox(); self.search_combo.addItems(["All", "url", "app"])
        left_layout.addWidget(self.search_combo)
        search_btn = QPushButton("Search"); search_btn.clicked.connect(self.quick_search)
        left_layout.addWidget(search_btn)

        # middle: tree
        mid_widget = QWidget()
        mid_layout = QVBoxLayout(mid_widget)
        mid_layout.setContentsMargins(8,8,8,8)
        header_row = QWidget(); header_layout = QHBoxLayout(header_row); header_layout.setContentsMargins(0,0,0,0)
        header_layout.addWidget(QLabel("Modes & Steps"))
        info_label = QLabel(" ⓘ "); info_label.setToolTip("Select a Mode (top) or Step (child). Double-click to edit.")
        header_layout.addWidget(info_label); header_layout.addStretch()
        mid_layout.addWidget(header_row)
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Name", "Type", "Value"])
        self.tree.setMaximumHeight(300)
        self.tree.itemDoubleClicked.connect(self.edit_item); self.tree.itemClicked.connect(self.on_tree_item_clicked)
        mid_layout.addWidget(self.tree)

        # mid buttons
        mid_btns = QWidget(); mid_btns_layout = QHBoxLayout(mid_btns)
        btn_add_step = QPushButton("Add Step"); btn_add_step.clicked.connect(self.add_step)
        btn_remove_step = QPushButton("Remove Step"); btn_remove_step.clicked.connect(self.remove_step)
        btn_dry_run = QPushButton("Dry Run"); btn_dry_run.clicked.connect(self.dry_run_selected)
        btn_view_log = QPushButton("View Log"); btn_view_log.clicked.connect(self.open_log_file)
        mid_btns_layout.addWidget(btn_add_step); mid_btns_layout.addWidget(btn_remove_step)
        mid_btns_layout.addWidget(btn_dry_run); mid_btns_layout.addWidget(btn_view_log)
        mid_layout.addWidget(mid_btns)

        # right editor
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8,8,8,8)
        right_layout.addWidget(QLabel("Editor"))
        self.detail_name = QLineEdit()
        self.detail_type = QComboBox(); self.detail_type.addItems(["url","app"])
        self.detail_value = QLineEdit()
        self.detail_args = QLineEdit()
        self.detail_delay = QLineEdit()
        save_detail_btn = QPushButton("Save Detail"); save_detail_btn.clicked.connect(self.save_detail_to_tree)
        right_layout.addWidget(QLabel("Name")); right_layout.addWidget(self.detail_name)
        right_layout.addWidget(QLabel("Type")); right_layout.addWidget(self.detail_type)
        right_layout.addWidget(QLabel("Value (path or url)")); right_layout.addWidget(self.detail_value)
        right_layout.addWidget(QLabel("Args (optional)")); right_layout.addWidget(self.detail_args)
        right_layout.addWidget(QLabel("Delay after (seconds)")); right_layout.addWidget(self.detail_delay)
        right_layout.addWidget(save_detail_btn); right_layout.addStretch()

        top_splitter.addWidget(left_widget)
        top_splitter.addWidget(mid_widget)
        top_splitter.addWidget(right_widget)
        top_splitter.setStretchFactor(1, 2)

        main_layout.addWidget(top_splitter)

        # bottom bar: Save (left), Launch (center), GitHub (right)
        bottom_bar = QWidget()
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(12,8,12,12)

        # Save config on left
        self.save_btn = QPushButton("💾 Save Config")
        self.save_btn.setStyleSheet("min-height:40px; font-size:14px;")
        self.save_btn.clicked.connect(self.save_config_clicked)

        # Center Launch button
        self.launch_btn = QPushButton("▶ LAUNCH SELECTED MODE")
        self.launch_btn.setStyleSheet("font-size:18px; font-weight:bold; padding:12px; min-height:56px;")
        self.launch_btn.clicked.connect(self.launch_selected_mode)

        # GitHub on right
        self.github_btn = QPushButton("GitHub")
        self.github_btn.setStyleSheet("min-height:40px; font-size:14px;")
        self.github_btn.clicked.connect(lambda: webbrowser.open(GITHUB_URL, new=2))

        bottom_layout.addWidget(self.save_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.launch_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.github_btn)

        main_layout.addWidget(bottom_bar)

        # status bar with step progress
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.progress = QProgressBar(); self.progress.setMaximum(0); self.progress.setVisible(False)
        self.step_label = QLabel("")
        self.status.addWidget(self.step_label)
        self.status.addPermanentWidget(self.progress)

        # tray icon (with standard icon)
        try:
            if QSystemTrayIcon.isSystemTrayAvailable():
                self.tray_icon = QSystemTrayIcon(parent=self)
                std_icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
                self.tray_icon.setIcon(std_icon)
                tray_menu = QMenu()
                tray_menu.addAction("Show", self.showNormal)
                tray_menu.addAction("Exit", lambda: QApplication.exit(0))
                self.tray_icon.setContextMenu(tray_menu)
                self.tray_icon.setToolTip("Startup Dashboard")
                self.tray_icon.show()
        except Exception as e:
            log(f"Tray init failed: {e}")

        # populate UI
        self.populate_modes_list()
        self.populate_tree()

        # keyboard shortcuts Ctrl+1..4
        for i in range(4):
            sc = QShortcut(QKeySequence(f"Ctrl+{i+1}"), self)
            sc.activated.connect(lambda idx=i: self._hotkey_launch(idx))

        # start inactivity timer when shown (single shot)
        QTimer.singleShot(100, self.reset_inactivity_timer)

    # event filter to catch user activity and reset inactivity timer
    def eventFilter(self, obj, event):
        if event.type() in (QEvent.MouseButtonPress, QEvent.KeyPress, QEvent.Wheel):
            self.reset_inactivity_timer()
        return super().eventFilter(obj, event)

    def reset_inactivity_timer(self):
        # do not schedule auto-close while launching (worker active)
        if self._worker is not None:
            # stop timer while worker running
            if self.inactivity_timer.isActive():
                self.inactivity_timer.stop()
            return
        # restart inactivity timer
        if self.inactivity_timer.isActive():
            self.inactivity_timer.stop()
        self.inactivity_timer.start(INACTIVITY_MS)
        log(f"Inactivity timer reset ({INACTIVITY_MS/1000}s)")

    def _on_inactivity_timeout(self):
        log("Inactivity timeout reached — closing application.")
        # only close if no worker running
        if self._worker is None:
            self.close()

    # small helper
    def set_status(self, text, timeout=5000):
        self.status.showMessage(text, timeout)
        log(text)

    # populate UI functions
    def populate_modes_list(self):
        self.modes_list.clear()
        profile = self.profiles.get(self.active_profile, {"modes": {}})
        for mode in profile.get("modes", {}).keys():
            item = QListWidgetItem(mode)
            self.modes_list.addItem(item)

    def populate_tree(self):
        self.tree.clear()
        profile = self.profiles.get(self.active_profile, {"modes": {}})
        for mode, steps in profile.get("modes", {}).items():
            mode_item = QTreeWidgetItem([mode, "", ""])
            mode_item.setExpanded(True)
            self.tree.addTopLevelItem(mode_item)
            for s in steps:
                child = QTreeWidgetItem([s.get("name", ""), s.get("type", ""), s.get("value", "")])
                mode_item.addChild(child)

    def on_mode_selected(self, item):
        mode_name = item.text()
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            if top.text(0) == mode_name:
                self.tree.setCurrentItem(top)
                top.setExpanded(True)
                break

    # add/remove/edit steps/modes (same behavior)
    def add_mode(self):
        text, ok = QInputDialog.getText(self, "Add Mode", "Mode name:")
        if ok and text.strip():
            name = text.strip()
            profile = self.profiles.setdefault(self.active_profile, {"modes": {}})["modes"]
            if name in profile:
                QMessageBox.warning(self, "Exists", "Mode already exists.")
                return
            profile[name] = []
            self.populate_modes_list()
            self.populate_tree()
            self.set_status(f"Mode '{name}' added.")

    def remove_mode(self):
        item = self.modes_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select", "Select a mode to remove.")
            return
        name = item.text()
        ok = QMessageBox.question(self, "Confirm", f"Remove mode '{name}'?")
        if ok == QMessageBox.StandardButton.Yes:
            profile = self.profiles.setdefault(self.active_profile, {"modes": {}})["modes"]
            profile.pop(name, None)
            self.populate_modes_list()
            self.populate_tree()
            self.set_status(f"Mode '{name}' removed.")

    def add_step(self):
        cur = self.tree.currentItem()
        if cur is None:
            QMessageBox.information(self, "Select", "Select a mode to add the step under (click mode).")
            return
        mode_item = cur if cur.parent() is None else cur.parent()
        name, ok = QInputDialog.getText(self, "Add Step", "Step name:")
        if not ok or not name.strip():
            return
        t, ok2 = QInputDialog.getItem(self, "Type", "Select type:", ["url", "app"], 0, False)
        if not ok2:
            return
        val, ok3 = QInputDialog.getText(self, "Value", "URL or executable path:")
        if not ok3 or not val.strip():
            return
        delay, ok4 = QInputDialog.getDouble(self, "Delay After", "Delay after (seconds):", 1.0, 0.0, 60.0, 1)
        step = {"name": name.strip(), "type": t, "value": val.strip(), "args": "", "delay_after": delay}
        mode = mode_item.text(0)
        self.profiles.setdefault(self.active_profile, {"modes": {}})["modes"].setdefault(mode, []).append(step)
        self.populate_tree()
        self.set_status(f"Step '{step['name']}' added to '{mode}'.")

    def remove_step(self):
        cur = self.tree.currentItem()
        if cur is None or cur.parent() is None:
            QMessageBox.information(self, "Select", "Select a step to remove (not a mode).")
            return
        mode = cur.parent().text(0)
        step_name = cur.text(0)
        steps = self.profiles.setdefault(self.active_profile, {"modes": {}})["modes"].get(mode, [])
        new_steps = [s for s in steps if s.get("name") != step_name]
        self.profiles[self.active_profile]["modes"][mode] = new_steps
        self.populate_tree()
        self.set_status(f"Removed step '{step_name}' from '{mode}'.")

    def edit_item(self, item, column):
        if item.parent() is None:
            return
        self.detail_name.setText(item.text(0))
        self.detail_type.setCurrentText(item.text(1))
        self.detail_value.setText(item.text(2))
        mode = item.parent().text(0)
        idx = item.parent().indexOfChild(item)
        try:
            step = self.profiles[self.active_profile]["modes"][mode][idx]
            self.detail_args.setText(step.get("args", ""))
            self.detail_delay.setText(str(step.get("delay_after", "")))
        except Exception:
            self.detail_args.setText("")
            self.detail_delay.setText("")

    def on_tree_item_clicked(self, item, col=0):
        if item.parent() is None:
            return
        self.detail_name.setText(item.text(0))
        self.detail_type.setCurrentText(item.text(1))
        self.detail_value.setText(item.text(2))
        try:
            mode = item.parent().text(0)
            idx = item.parent().indexOfChild(item)
            step = self.profiles[self.active_profile]["modes"][mode][idx]
            self.detail_args.setText(step.get("args", ""))
            self.detail_delay.setText(str(step.get("delay_after", "")))
        except Exception:
            self.detail_args.setText("")
            self.detail_delay.setText("")

    def save_detail_to_tree(self):
        cur = self.tree.currentItem()
        if cur is None or cur.parent() is None:
            QMessageBox.information(self, "Select", "Select a step to save details into.")
            return
        name = self.detail_name.text().strip()
        t = self.detail_type.currentText()
        v = self.detail_value.text().strip()
        args = self.detail_args.text().strip()
        try:
            delay = float(self.detail_delay.text().strip()) if self.detail_delay.text().strip() else 0.0
        except Exception:
            delay = 0.0
        if not name or not v:
            QMessageBox.warning(self, "Invalid", "Name and Value cannot be empty.")
            return
        mode = cur.parent().text(0)
        idx = cur.parent().indexOfChild(cur)
        steps = self.profiles[self.active_profile]["modes"].get(mode, [])
        if 0 <= idx < len(steps):
            steps[idx].update({"name": name, "type": t, "value": v, "args": args, "delay_after": delay})
        self.populate_tree()
        self.set_status("Step details updated.")

    # search
    def quick_search(self):
        q = self.search_text.text().strip().lower()
        typ = self.search_combo.currentText()
        matches = []
        for mode, steps in self.profiles[self.active_profile]["modes"].items():
            for s in steps:
                if (typ == "All" or s.get("type") == typ) and (q in s.get("name", "").lower() or q in s.get("value", "").lower()):
                    matches.append((mode, s))
        if not matches:
            QMessageBox.information(self, "Search", "No matches found.")
            return
        mode, step = matches[0]
        self.expand_mode_in_tree(mode)
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            if top.text(0) == mode:
                for j in range(top.childCount()):
                    child = top.child(j)
                    if child.text(0) == step.get("name"):
                        self.tree.setCurrentItem(child)
                        self.on_tree_item_clicked(child)
                        self.set_status(f"Found {step.get('name')} in {mode}")
                        return

    def expand_mode_in_tree(self, mode_name):
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            if top.text(0) == mode_name:
                self.tree.setCurrentItem(top)
                top.setExpanded(True)
                break

    # launching (threaded)
    def launch_selected_mode(self):
        cur = self.tree.currentItem()
        if cur is None:
            QMessageBox.information(self, "Select", "Select a mode to launch (click a mode header).")
            return
        mode_item = cur if cur.parent() is None else cur.parent()
        mode = mode_item.text(0)
        steps = self.profiles[self.active_profile]["modes"].get(mode, [])
        if not steps:
            QMessageBox.information(self, "Empty", f"No steps in '{mode}'")
            return
        # stop inactivity auto-close while launching
        if self.inactivity_timer.isActive():
            self.inactivity_timer.stop()

        self._lock_ui(True)
        profile = self.profiles[self.active_profile]
        self._worker = LauncherWorker(profile, mode)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.signals.step_started.connect(self._on_step_started)
        self._worker.signals.finished.connect(self._on_worker_finished)
        self._worker.signals.error.connect(self._on_worker_error)
        self._thread.start()
        self.set_status(f"Started launching '{mode}'")

    def _on_step_started(self, idx, total, label):
        if idx == 0:
            self.step_label.setText(label)
        else:
            self.step_label.setText(f"[{idx}/{total}] {label}")
        self.progress.setVisible(True)
        self.progress.setMaximum(0)

    def _on_worker_finished(self):
        self.set_status("Launch sequence finished")
        self.step_label.setText("")
        self.progress.setVisible(False)
        try:
            if self._thread is not None:
                self._thread.quit()
                self._thread.wait(2000)
        except Exception:
            pass
        self._worker = None
        self._thread = None
        self._lock_ui(False)
        # auto-close app after short delay
        QTimer.singleShot(500, self.close)

    def _on_worker_error(self, msg):
        log(f"Worker error: {msg}")
        QMessageBox.critical(self, "Launch error", msg)
        self._on_worker_finished()

    def _lock_ui(self, lock: bool):
        widgets = [self.modes_list, self.tree, self.search_text, self.profile_combo]
        for w in widgets:
            try: w.setDisabled(lock)
            except Exception: pass
        for btn in self.findChildren(QPushButton):
            try: btn.setDisabled(lock)
            except Exception: pass
        # keep Save & GitHub in place but disabled during launch
        self.save_btn.setDisabled(lock)
        self.github_btn.setDisabled(lock)
        self.launch_btn.setDisabled(lock)

    # dry run, logs, settings removed (settings removed as requested)
    def dry_run_selected(self):
        cur = self.tree.currentItem()
        if cur is None:
            QMessageBox.information(self, "Dry Run", "Select a mode to preview.")
            return
        item = cur if cur.parent() is None else cur.parent()
        mode = item.text(0)
        steps = self.profiles[self.active_profile]["modes"].get(mode, [])
        if not steps:
            QMessageBox.information(self, "Dry Run", f"Mode '{mode}' has no steps.")
            return
        lines = [f"{i+1}. [{s.get('type')}] {s.get('name')} -> {s.get('value')} (delay_after={s.get('delay_after','')})" for i, s in enumerate(steps)]
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Dry Run - {mode}")
        v = QVBoxLayout(dlg)
        te = QTextEdit(); te.setReadOnly(True); te.setText("\n".join(lines))
        v.addWidget(te)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        dlg.resize(600, 400)
        dlg.exec()

    def open_log_file(self):
        if LOG_FILE.exists():
            try:
                os.startfile(str(LOG_FILE))
                return
            except Exception:
                txt = LOG_FILE.read_text(encoding="utf-8") if LOG_FILE.exists() else "No log."
                dlg = QDialog(self)
                dlg.setWindowTitle("Log Viewer")
                v = QVBoxLayout(dlg)
                te = QTextEdit(); te.setReadOnly(True); te.setText(txt)
                v.addWidget(te)
                bb = QDialogButtonBox(QDialogButtonBox.Close)
                bb.rejected.connect(dlg.reject)
                v.addWidget(bb)
                dlg.resize(800, 500)
                dlg.exec()
        else:
            QMessageBox.information(self, "Log", "No log file yet.")

    def save_config_clicked(self):
        self.cfg["profile_name"] = self.name_edit.text().strip()
        self.cfg["active_profile"] = self.profile_combo.currentText()
        self.cfg["profiles"] = self.profiles
        save_config(self.cfg)
        self.set_status(f"Saved config to {CONFIG_FILE}")

    def load_config_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open config JSON", str(Path.home()), "JSON Files (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if "profiles" not in data and "modes" in data:
                self.profiles = {"Default": {"initial_delay": 0, "post_open_delay": 1, "modes": data.get("modes", DEFAULT_MODES)}}
                self.cfg = {"profile_name": data.get("profile_name", "Sankalp"), "active_profile": "Default", "profiles": self.profiles}
            else:
                self.cfg = data
                self.profiles = data.get("profiles", {})
            self.active_profile = self.cfg.get("active_profile", next(iter(self.profiles.keys())))
            self.profile_combo.clear()
            self.profile_combo.addItems(list(self.profiles.keys()))
            self.profile_combo.setCurrentText(self.active_profile)
            self.name_edit.setText(self.cfg.get("profile_name", "Sankalp"))
            self.populate_modes_list()
            self.populate_tree()
            self.set_status("Config loaded from file.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load: {e}")

    def on_name_changed(self):
        self.cfg["profile_name"] = self.name_edit.text().strip()
        self.set_status("Profile name updated.")
        self.reset_inactivity_timer()

    def on_profile_changed(self, text):
        if text and text in self.profiles:
            self.active_profile = text
            self.cfg["active_profile"] = text
            self.populate_modes_list()
            self.populate_tree()
            self.set_status(f"Switched profile to {text}")
            self.reset_inactivity_timer()

    def _hotkey_launch(self, idx):
        profile = self.profiles.get(self.active_profile, {})
        modes = list(profile.get("modes", {}).keys())
        if idx < len(modes):
            self.launch_from_name(modes[idx])

    def launch_from_name(self, mode_name):
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            if top.text(0) == mode_name:
                self.tree.setCurrentItem(top)
                self.launch_selected_mode()
                return

    def closeEvent(self, event):
        try:
            if self._worker is not None:
                log("Aborting worker on close...")
                try:
                    self._worker.abort()
                except Exception:
                    pass
            if self._thread is not None:
                try:
                    self._thread.quit()
                    self._thread.wait(2000)
                except Exception:
                    pass
        except Exception as e:
            log(f"Error during close: {e}")
        event.accept()

# ---------- run ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = StartupDashboard()
    win.show()
    # ensure QApp event loop exists before installing event filter
    app.installEventFilter(win)
    # start the inactivity timer now (in case user doesn't interact)
    win.reset_inactivity_timer()
    sys.exit(app.exec())
