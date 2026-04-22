from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QGroupBox, QSpinBox, QCheckBox, QPushButton, QMessageBox, QFileDialog
)
from ...core.config import SETTINGS
from ...core.style import THEME

class SettingsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def activate(self): pass
    def deactivate(self): pass

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(16,16,16,16); root.setSpacing(14)
        t = QLabel("Settings")
        t.setStyleSheet(f"font-size:18px;font-weight:bold;color:{THEME['text']};")
        root.addWidget(t)

        # Ollama
        ol = QGroupBox("Ollama"); oll = QVBoxLayout(ol)
        r1 = QHBoxLayout(); r1.addWidget(QLabel("Host:"))
        self.host_input = QLineEdit(SETTINGS.get("ollama_host","http://localhost:11434"))
        r1.addWidget(self.host_input); oll.addLayout(r1)
        r2 = QHBoxLayout(); r2.addWidget(QLabel("Threads:"))
        self.threads_spin = QSpinBox(); self.threads_spin.setRange(1,64)
        self.threads_spin.setValue(int(SETTINGS.get("ollama_threads",4)))
        r2.addWidget(self.threads_spin); r2.addStretch(); oll.addLayout(r2)
        r3 = QHBoxLayout(); r3.addWidget(QLabel("GPU layers (0=CPU):"))
        self.gpu_spin = QSpinBox(); self.gpu_spin.setRange(0,128)
        self.gpu_spin.setValue(int(SETTINGS.get("gpu_layers",0)))
        r3.addWidget(self.gpu_spin); r3.addStretch(); oll.addLayout(r3)
        root.addWidget(ol)

        # GitHub
        gh = QGroupBox("GitHub"); ghl = QVBoxLayout(gh)
        r = QHBoxLayout(); r.addWidget(QLabel("Token (ghp_…):"))
        self.gh_token = QLineEdit(SETTINGS.get("github_token",""))
        self.gh_token.setEchoMode(QLineEdit.EchoMode.Password)
        r.addWidget(self.gh_token); ghl.addLayout(r)
        root.addWidget(gh)

        # Git
        gitb = QGroupBox("Git"); gitl = QVBoxLayout(gitb)
        rg = QHBoxLayout(); rg.addWidget(QLabel("Default clone dir:"))
        self.clone_dir = QLineEdit(SETTINGS.get("clone_dir",str(Path.home())))
        btn_br = QPushButton("Browse"); btn_br.clicked.connect(self._browse_clone)
        rg.addWidget(self.clone_dir); rg.addWidget(btn_br); gitl.addLayout(rg)
        root.addWidget(gitb)

        # Agent
        ag = QGroupBox("Agent"); agl = QVBoxLayout(ag)
        ra = QHBoxLayout(); ra.addWidget(QLabel("Max steps:"))
        self.agent_steps = QSpinBox(); self.agent_steps.setRange(1,50)
        self.agent_steps.setValue(int(SETTINGS.get("agent_max_steps",12)))
        ra.addWidget(self.agent_steps); ra.addStretch(); agl.addLayout(ra)
        root.addWidget(ag)

        # App
        app = QGroupBox("Application"); apl = QVBoxLayout(app)
        self.cb_scroll = QCheckBox("Auto-scroll log output"); self.cb_scroll.setChecked(bool(SETTINGS.get("autoscroll",True)))
        self.cb_ts     = QCheckBox("Show timestamps"); self.cb_ts.setChecked(bool(SETTINGS.get("timestamps",True)))
        apl.addWidget(self.cb_scroll); apl.addWidget(self.cb_ts)
        root.addWidget(app)

        btn_save = QPushButton("💾  Save Settings"); btn_save.setObjectName("primary")
        btn_save.clicked.connect(self._save)
        root.addWidget(btn_save)
        root.addStretch()

    def _browse_clone(self):
        d = QFileDialog.getExistingDirectory(self,"Select clone directory")
        if d: self.clone_dir.setText(d)

    def _save(self):
        SETTINGS.set("ollama_host", self.host_input.text().strip())
        SETTINGS.set("ollama_threads", self.threads_spin.value())
        SETTINGS.set("gpu_layers", self.gpu_spin.value())
        SETTINGS.set("github_token", self.gh_token.text().strip())
        SETTINGS.set("clone_dir", self.clone_dir.text().strip())
        SETTINGS.set("agent_max_steps", self.agent_steps.value())
        SETTINGS.set("autoscroll", self.cb_scroll.isChecked())
        SETTINGS.set("timestamps", self.cb_ts.isChecked())
        SETTINGS.save()
        QMessageBox.information(self,"Saved","Settings saved.")
