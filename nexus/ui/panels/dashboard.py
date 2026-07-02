import json, subprocess, sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QSplitter, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from ...core.config import SETTINGS, SESSIONS_DIR, PROJECTS_FILE, HAS_PSUTIL
from ...core.style import THEME
from ...core.workers import CommandWorker
from ..widgets import LogView

if HAS_PSUTIL:
    import psutil

class GitStatusWorker(QThread):
    output_line = pyqtSignal(str)
    def __init__(self, projects):
        super().__init__()
        self.projects = projects
    def run(self):
        for p in self.projects[:6]:
            try:
                import subprocess, sys
                r = subprocess.run("git status --short --branch", cwd=p["path"], shell=True,
                    capture_output=True, text=True, timeout=5,
                    encoding="utf-8", errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0)
                out = (r.stdout + r.stderr).strip()[:70]
                self.output_line.emit(f"{p['name']}: {out}")
            except Exception as e:
                self.output_line.emit(f"{p['name']}: [error] {e}")

class SessionListWorker(QThread):
    output_line = pyqtSignal(str)
    def __init__(self, session_dir):
        super().__init__()
        self.session_dir = session_dir
    def run(self):
        import json
        if self.session_dir.exists():
            files = sorted(self.session_dir.glob("*.json"), reverse=True)[:10]
            for f in files:
                try:
                    d = json.loads(f.read_text())
                    self.output_line.emit(f"[{d.get('timestamp','')[:16]}] {d.get('agent','?')} — {d.get('result','')[:50]}")
                except Exception:
                    pass

class StatusDashboard(QWidget):
    """Live overview: Ollama status, active models, agent sessions, system resources."""
    def __init__(self):
        super().__init__()
        self._last_sess_count = -1
        self._build_ui()
        self._timer = QTimer(self); self._timer.timeout.connect(self._refresh)
        # Timer started by activate, stopped by deactivate (hibernation logic)

    def activate(self):
        self._refresh()
        self._timer.start(6000)

    def deactivate(self):
        self._timer.stop()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(16,16,16,16); root.setSpacing(12)
        hdr = QHBoxLayout()
        t = QLabel("Status Dashboard")
        t.setStyleSheet(f"font-size:18px;font-weight:bold;color:{THEME['text']};")
        btn_ref = QPushButton("⟳ Refresh"); btn_ref.clicked.connect(self._refresh)
        hdr.addWidget(t); hdr.addStretch(); hdr.addWidget(btn_ref)
        root.addLayout(hdr)

        # Status cards row
        cards_row = QHBoxLayout()
        self._ollama_card  = self._make_card("🤖 Ollama", cards_row)
        self.ollama_status = QLabel("Checking…")
        self.ollama_status.setStyleSheet(f"color:{THEME['text2']};font-weight:bold;font-size:13px;")
        self.ollama_models_lbl = QLabel("")
        self.ollama_models_lbl.setStyleSheet(f"color:{THEME['accent2']};font-size:11px;")
        self.ollama_models_lbl.setWordWrap(True)
        self._ollama_card.layout().addWidget(self.ollama_status)
        self._ollama_card.layout().addWidget(self.ollama_models_lbl)
        self._ollama_card.layout().addStretch()

        self._sess_card = self._make_card("🔗 Sessions", cards_row)
        self.sess_lbl = QLabel("0 sessions"); self.sess_lbl.setStyleSheet(f"color:{THEME['text2']};font-size:13px;")
        self.sess_latest = QLabel(""); self.sess_latest.setStyleSheet(f"color:{THEME['text3']};font-size:11px;")
        self.sess_latest.setWordWrap(True)
        self._sess_card.layout().addWidget(self.sess_lbl); self._sess_card.layout().addWidget(self.sess_latest)
        self._sess_card.layout().addStretch()

        self._sys_card = self._make_card("📊 System", cards_row)
        self.cpu_lbl = QLabel("CPU: –"); self.cpu_lbl.setStyleSheet(f"color:{THEME['text2']};font-size:13px;")
        self.ram_lbl = QLabel("RAM: –"); self.ram_lbl.setStyleSheet(f"color:{THEME['text2']};font-size:13px;")
        self.disk_lbl = QLabel("Disk: –"); self.disk_lbl.setStyleSheet(f"color:{THEME['text2']};font-size:11px;")
        self._sys_card.layout().addWidget(self.cpu_lbl)
        self._sys_card.layout().addWidget(self.ram_lbl)
        self._sys_card.layout().addWidget(self.disk_lbl)
        self._sys_card.layout().addStretch()

        self._proj_card = self._make_card("📁 Projects", cards_row)
        self.proj_lbl = QLabel("–"); self.proj_lbl.setStyleSheet(f"color:{THEME['text2']};font-size:13px;")
        self._proj_card.layout().addWidget(self.proj_lbl); self._proj_card.layout().addStretch()
        root.addLayout(cards_row)

        split = QSplitter(Qt.Orientation.Horizontal)

        # Sessions table
        sess_w = QFrame(); sess_w.setObjectName("card"); sl = QVBoxLayout(sess_w)
        lbl = QLabel("Recent Agent Sessions")
        lbl.setStyleSheet(f"color:{THEME['text2']};font-size:11px;text-transform:uppercase;letter-spacing:1px;")
        sl.addWidget(lbl)
        self.sessions_tree = QTreeWidget()
        self.sessions_tree.setHeaderLabels(["Time","Agent","Task","Result"])
        self.sessions_tree.setColumnWidth(0,130); self.sessions_tree.setColumnWidth(1,100)
        self.sessions_tree.setColumnWidth(2,180)
        sl.addWidget(self.sessions_tree,1)
        split.addWidget(sess_w)

        # Quick actions
        qa_w = QFrame(); qa_w.setObjectName("card"); ql = QVBoxLayout(qa_w)
        lbl2 = QLabel("Quick Actions")
        lbl2.setStyleSheet(f"color:{THEME['text2']};font-size:11px;text-transform:uppercase;letter-spacing:1px;")
        ql.addWidget(lbl2)
        for label, action in [
            ("Show Ollama running models", "ollama ps"),
            ("List all local models",      "ollama list"),
            ("Git status all projects",    "__git_all__"),
            ("System resource snapshot",   "__sys_snap__"),
            ("List agent sessions",        "__list_sessions__"),
        ]:
            b = QPushButton(label); b.setMinimumHeight(32)
            b.clicked.connect(lambda _, a=action: self._quick_action(a)); ql.addWidget(b)
        ql.addStretch()
        self.quick_log = LogView(); self.quick_log.setMaximumHeight(180)
        ql.addWidget(self.quick_log)
        split.addWidget(qa_w); split.setSizes([520,280])
        root.addWidget(split,1)

    def _make_card(self, title, parent_layout):
        card = QFrame(); card.setObjectName("card")
        cl = QVBoxLayout(card); cl.setSpacing(4)
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color:{THEME['accent2']};font-weight:bold;font-size:13px;")
        cl.addWidget(lbl); parent_layout.addWidget(card,1)
        return card

    def _refresh(self):
        # 1. Ollama status 
        def _check_ollama():
            try:
                import urllib.request
                with urllib.request.urlopen(
                        f"{SETTINGS.get('ollama_host')}/api/tags", timeout=3) as r:
                    data = json.loads(r.read())
                    models = [m["name"] for m in data.get("models",[])]
                    self.ollama_status.setText(f"Online  ({len(models)} models)")
                    self.ollama_status.setStyleSheet(f"color:{THEME['success']};font-weight:bold;font-size:13px;")
                    self.ollama_models_lbl.setText(", ".join(models[:5])+("…" if len(models)>5 else ""))
            except Exception:
                self.ollama_status.setText("Offline")
                self.ollama_status.setStyleSheet(f"color:{THEME['error']};font-weight:bold;font-size:13px;")
                self.ollama_models_lbl.setText("Start Ollama to enable AI features")
        import threading; threading.Thread(target=_check_ollama, daemon=True).start()

        # 2. Sessions refresh
        if SESSIONS_DIR.exists():
            files = sorted(SESSIONS_DIR.glob("*.json"), reverse=True)
            if len(files) == self._last_sess_count:
                pass 
            else:
                self._last_sess_count = len(files)
                self.sess_lbl.setText(f"{len(files)} session(s)")
                
                self.sessions_tree.clear()
                for f in files[:10]:
                    # Prevent heavy JSON parsing on UI thread; just use basic metadata
                    size_kb = f.stat().st_size // 1024
                    self.sessions_tree.addTopLevelItem(QTreeWidgetItem([
                        f.stem[-15:] if "_" in f.stem else f.stem,
                        "Agent Session",
                        f"Size: {size_kb} KB",
                        "View in Agents Tab"
                    ]))

        if HAS_PSUTIL:
            cpu = psutil.cpu_percent(interval=None)
            vm  = psutil.virtual_memory()
            disk = psutil.disk_usage("/" if sys.platform!="win32" else "C:\\")
            self.cpu_lbl.setText(f"CPU: {cpu:.1f}%")
            self.ram_lbl.setText(f"RAM: {vm.percent:.0f}%")
            self.disk_lbl.setText(f"Disk: {disk.percent:.0f}%")

        try:
            if PROJECTS_FILE.exists():
                with open(PROJECTS_FILE) as f: projs = json.load(f)
                self.proj_lbl.setText(f"{len(projs)} project(s) registered")
            else:
                self.proj_lbl.setText("0 projects")
        except Exception:
            self.proj_lbl.setText("0 projects")

    def _quick_action(self, action):
        if action == "__sys_snap__":
            if HAS_PSUTIL:
                cpu  = psutil.cpu_percent(interval=None) # Non-blocking!
                vm   = psutil.virtual_memory()
                disk = psutil.disk_usage("/" if sys.platform!="win32" else "C:\\")
                self.quick_log.append_line(
                    f"CPU:{cpu:.1f}%  RAM:{vm.percent:.0f}%  Disk:{disk.percent:.0f}%","info")
            return
        if action == "__git_all__":
            try:
                if PROJECTS_FILE.exists():
                    with open(PROJECTS_FILE) as f: projs = json.load(f)
                else: projs = []
            except Exception: projs = []
            if not projs:
                self.quick_log.append_line("No projects found", "warn")
                return
            self.quick_log.append_line("Checking status of all projects in background...", "info")
            self._git_worker = GitStatusWorker(projs)
            self._git_worker.output_line.connect(lambda l: self.quick_log.append_line(l, "info"))
            self._git_worker.start()
            return
        if action == "__list_sessions__":
            self.quick_log.append_line("Loading sessions in background...", "info")
            self._sess_worker = SessionListWorker(SESSIONS_DIR)
            self._sess_worker.output_line.connect(lambda l: self.quick_log.append_line(l, "info"))
            self._sess_worker.start()
            return
        w = CommandWorker(action, shell_type="cmd")
        w.output.connect(lambda l: self.quick_log.append_line(l))
        w.done.connect(lambda c: self.quick_log.append_line(f"[exit {c}]","success" if c==0 else "error"))
        w.start(); self._qw = w
