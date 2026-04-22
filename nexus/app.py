import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QStackedWidget, QStatusBar, QLabel, QApplication, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from .core.config import SETTINGS, APP_VERSION
from .core.style import STYLESHEET, THEME
from .ui.widgets import NavButton
from .ui.panels.dashboard import StatusDashboard
from .ui.panels.ollama import OllamaPanel
from .ui.panels.git_github import GitPanel, GitHubPanel
from .ui.panels.agents import AgentPanel, AgentStudioPanel
from .ui.panels.workflow import WorkflowPanel
from .ui.panels.terminal_system import TerminalPanel, SystemPanel
from .ui.panels.projects import ProjectRunnerPanel
from .ui.panels.settings import SettingsPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"NEXUS v{APP_VERSION}"); self.resize(1160, 780)
        self._build_ui()
        self._check_ollama_status()

    def _build_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        main_lay = QHBoxLayout(central); main_lay.setContentsMargins(0,0,0,0); main_lay.setSpacing(0)

        # Sidebar
        sidebar = QFrame(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(200)
        sb_lay = QVBoxLayout(sidebar); sb_lay.setContentsMargins(0,10,0,10); sb_lay.setSpacing(2)
        
        self._stack = QStackedWidget()
        self._nav_btns = []
        
        pages = [
            ("Dashboard", "⬡", StatusDashboard),
            ("Ollama",    "🤖", OllamaPanel),
            ("Git",       "🌿", GitPanel),
            ("GitHub",    "🐙", GitHubPanel),
            ("Chat",      "💬", AgentPanel),
            ("Studio",    "🎭", AgentStudioPanel),
            ("Projects",  "📁", ProjectRunnerPanel),
            ("Workflow",  "⛓", WorkflowPanel),
            ("Terminal",  "🐚", TerminalPanel),
            ("System",    "📊", SystemPanel),
            ("Settings",  "⚙", SettingsPanel),
        ]

        for i, (name, icon, cls) in enumerate(pages):
            btn = NavButton(name, icon)
            btn.clicked.connect(lambda _, idx=i: self._switch(idx))
            sb_lay.addWidget(btn)
            self._nav_btns.append(btn)
            panel = cls()
            self._stack.addWidget(panel)

        sb_lay.addStretch()
        main_lay.addWidget(sidebar); main_lay.addWidget(self._stack, 1)

        # Status Bar
        self.status_bar = QStatusBar(); self.setStatusBar(self.status_bar)
        self._status_ollama = QLabel("⬡ Ollama: checking…")
        self._status_ollama.setStyleSheet(f"color:{THEME['text3']};font-size:11px;padding:0 8px;")
        self.status_bar.addWidget(self._status_ollama)

        self._current_idx = -1
        self._switch(0)

    def _switch(self, idx):
        if idx == self._current_idx: return
        
        # 1. Hibernate old panel
        if self._current_idx != -1:
            old_panel = self._stack.widget(self._current_idx)
            if hasattr(old_panel, "deactivate"):
                old_panel.deactivate()

        # 2. Activate new panel
        self._current_idx = idx
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_btns):
            btn.set_active(i == idx)
        
        new_panel = self._stack.widget(idx)
        if hasattr(new_panel, "activate"):
            new_panel.activate()

    def _check_ollama_status(self):
        def _check():
            try:
                import urllib.request, json
                with urllib.request.urlopen(f"{SETTINGS.get('ollama_host')}/api/tags", timeout=3) as r:
                    self._status_ollama.setText("⬡ Ollama: ●  online")
                    self._status_ollama.setStyleSheet(f"color:{THEME['success']};font-size:11px;padding:0 8px;")
            except Exception:
                self._status_ollama.setText("⬡ Ollama: ○  offline")
                self._status_ollama.setStyleSheet(f"color:{THEME['error']};font-size:11px;padding:0 8px;")
        
        import threading
        threading.Thread(target=_check, daemon=True).start()
        # Re-check every 30 seconds
        QTimer.singleShot(30000, self._check_ollama_status)

    def closeEvent(self, event):
        """Clean up all processes and threads on exit."""
        self.status_bar.showMessage("Shutting down NEXUS engine...")
        for i in range(self._stack.count()):
            panel = self._stack.widget(i)
            if hasattr(panel, "deactivate"): 
                panel.deactivate()
            
            # Stop all worker threads in the panel
            for attr_name in dir(panel):
                if "worker" in attr_name.lower():
                    attr = getattr(panel, attr_name)
                    if hasattr(attr, "stop"):
                        try:
                            attr.stop()
                        except Exception:
                            pass
        event.accept()

    def refresh_all_projects(self):
        for i in range(self._stack.count()):
            p = self._stack.widget(i)
            if hasattr(p, "_refresh_list"): p._refresh_list()
            elif hasattr(p, "_refresh_combo"): p._refresh_combo()

