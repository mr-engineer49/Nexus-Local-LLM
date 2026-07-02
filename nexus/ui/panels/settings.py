from pathlib import Path
import json, requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QGroupBox, QSpinBox, QCheckBox, QPushButton, QMessageBox, QFileDialog, QComboBox, QSplitter, QListWidget, QStackedWidget
)
from PyQt6.QtCore import Qt, QSize
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
        
        hdr = QHBoxLayout()
        t = QLabel("⚙ Settings")
        t.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {THEME['text']};")
        hdr.addWidget(t); hdr.addStretch()
        btn_save = QPushButton("💾 Save Settings"); btn_save.setObjectName("primary")
        btn_save.clicked.connect(self._save)
        hdr.addWidget(btn_save)
        root.addLayout(hdr)

        split = QSplitter(Qt.Orientation.Horizontal)
        
        self.nav = QListWidget()
        self.nav.setStyleSheet(f"background: {THEME['bg2']}; color: {THEME['text']}; border: 1px solid {THEME['border']}; border-radius: 4px; font-size: 13px; outline: none;")
        self.nav.setFixedWidth(180)
        
        self.stack = QStackedWidget()
        
        categories = [
            ("General App", self._build_general()),
            ("Local AI (Ollama)", self._build_ollama()),
            ("LLM API Keys", self._build_api_keys()),
            ("Agent Studio", self._build_agent()),
            ("RAG & Code Search", self._build_rag()),
            ("LangSmith", self._build_langsmith()),
            ("GitHub & Git", self._build_git())
        ]
        
        for name, widget in categories:
            self.nav.addItem(name)
            self.stack.addWidget(widget)
            
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)
        
        split.addWidget(self.nav)
        split.addWidget(self.stack)
        split.setSizes([180, 700])
        root.addWidget(split, 1)

    def _create_password_field(self, label_text, default_val, test_url=None, auth_header="Bearer"):
        row = QHBoxLayout()
        row.addWidget(QLabel(label_text))
        inp = QLineEdit(default_val)
        inp.setEchoMode(QLineEdit.EchoMode.Password)
        row.addWidget(inp, 1)
        
        btn_eye = QPushButton("👁")
        btn_eye.setFixedWidth(30)
        btn_eye.setCheckable(True)
        btn_eye.toggled.connect(lambda chk: inp.setEchoMode(QLineEdit.EchoMode.Normal if chk else QLineEdit.EchoMode.Password))
        row.addWidget(btn_eye)
        
        if test_url:
            btn_test = QPushButton("Test")
            btn_test.clicked.connect(lambda: self._test_api_key(inp.text().strip(), test_url, auth_header))
            row.addWidget(btn_test)
            
        return row, inp

    def _test_api_key(self, key, url, auth_header):
        if not key:
            QMessageBox.warning(self, "Empty Key", "Please enter an API key to test.")
            return
        try:
            headers = {"Authorization": f"{auth_header} {key}"} if auth_header else {}
            if "google" in url:
                url = f"{url}?key={key}"
                headers = {}
                
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code in [200, 204]:
                QMessageBox.information(self, "Success", "API Key is valid and active! 🟢")
            else:
                QMessageBox.warning(self, "Failed", f"API test failed. 🔴\\nStatus Code: {r.status_code}\\nResponse: {r.text[:200]}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to connect: {e}")

    def _build_general(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        app = QGroupBox("Application Preferences"); apl = QVBoxLayout(app)
        self.cb_scroll = QCheckBox("Auto-scroll log output"); self.cb_scroll.setChecked(bool(SETTINGS.get("autoscroll",True)))
        self.cb_ts     = QCheckBox("Show timestamps in logs"); self.cb_ts.setChecked(bool(SETTINGS.get("timestamps",True)))
        apl.addWidget(self.cb_scroll); apl.addWidget(self.cb_ts)
        lay.addWidget(app)
        return w

    def _build_ollama(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        ol = QGroupBox("Ollama Configuration"); oll = QVBoxLayout(ol)
        
        r1 = QHBoxLayout(); r1.addWidget(QLabel("Host URL:"))
        self.host_input = QLineEdit(SETTINGS.get("ollama_host","http://localhost:11434"))
        r1.addWidget(self.host_input, 1)
        btn_ping = QPushButton("Ping Host")
        btn_ping.clicked.connect(lambda: self._test_api_key("dummy", f"{self.host_input.text().strip()}/api/version", None))
        r1.addWidget(btn_ping)
        oll.addLayout(r1)
        
        r2 = QHBoxLayout(); r2.addWidget(QLabel("CPU Threads:"))
        self.threads_spin = QSpinBox(); self.threads_spin.setRange(1,64)
        self.threads_spin.setValue(int(SETTINGS.get("ollama_threads",4)))
        r2.addWidget(self.threads_spin); r2.addStretch(); oll.addLayout(r2)
        
        r3 = QHBoxLayout(); r3.addWidget(QLabel("GPU layers (0=CPU):"))
        self.gpu_spin = QSpinBox(); self.gpu_spin.setRange(0,128)
        self.gpu_spin.setValue(int(SETTINGS.get("gpu_layers",0)))
        r3.addWidget(self.gpu_spin); r3.addStretch(); oll.addLayout(r3)
        
        lay.addWidget(ol)
        return w

    def _build_api_keys(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        grp = QGroupBox("LLM API Keys"); gl = QVBoxLayout(grp)
        
        r1, self.oai_key = self._create_password_field("OpenAI:", SETTINGS.get("openai_api_key", ""), "https://api.openai.com/v1/models")
        gl.addLayout(r1)
        
        r2, self.ant_key = self._create_password_field("Anthropic:", SETTINGS.get("anthropic_api_key", ""), "https://api.anthropic.com/v1/models", "x-api-key")
        gl.addLayout(r2)
        
        r3, self.google_key = self._create_password_field("Google Gemini:", SETTINGS.get("google_api_key", ""), "https://generativelanguage.googleapis.com/v1beta/models", "")
        gl.addLayout(r3)
        
        r4, self.groq_key = self._create_password_field("Groq:", SETTINGS.get("groq_api_key", ""), "https://api.groq.com/openai/v1/models")
        gl.addLayout(r4)
        
        r5, self.together_key = self._create_password_field("Together AI:", SETTINGS.get("together_api_key", ""), "https://api.together.xyz/v1/models")
        gl.addLayout(r5)
        
        r6, self.hf_key = self._create_password_field("HuggingFace:", SETTINGS.get("huggingface_api_key", ""), "https://huggingface.co/api/whoami-v2")
        gl.addLayout(r6)
        
        lay.addWidget(grp)
        return w

    def _build_agent(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        ag = QGroupBox("Agent Defaults"); agl = QVBoxLayout(ag)
        
        ra1 = QHBoxLayout(); ra1.addWidget(QLabel("Default Provider:"))
        self.prov_combo = QComboBox(); self.prov_combo.addItems(["ollama", "openai", "anthropic", "google", "groq", "together", "openai_compatible"])
        self.prov_combo.setCurrentText(SETTINGS.get("agent_provider", "ollama"))
        ra1.addWidget(self.prov_combo); ra1.addStretch(); agl.addLayout(ra1)
        
        ra = QHBoxLayout(); ra.addWidget(QLabel("Max ReAct Steps:"))
        self.agent_steps = QSpinBox(); self.agent_steps.setRange(1,50)
        self.agent_steps.setValue(int(SETTINGS.get("agent_max_steps",12)))
        ra.addWidget(self.agent_steps); ra.addStretch(); agl.addLayout(ra)
        
        lay.addWidget(ag)
        return w

    def _build_rag(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        rag = QGroupBox("RAG Configuration"); ragl = QVBoxLayout(rag)
        
        rrag1 = QHBoxLayout(); rrag1.addWidget(QLabel("Embedding Provider:"))
        self.rag_prov_combo = QComboBox(); self.rag_prov_combo.addItems(["ollama", "openai"])
        self.rag_prov_combo.setCurrentText(SETTINGS.get("rag_embedding_provider", "ollama"))
        rrag1.addWidget(self.rag_prov_combo); rrag1.addStretch(); ragl.addLayout(rrag1)
        
        rrag2 = QHBoxLayout(); rrag2.addWidget(QLabel("Embedding Model:"))
        self.rag_model_input = QLineEdit(SETTINGS.get("rag_embedding_model", "nomic-embed-text"))
        rrag2.addWidget(self.rag_model_input); ragl.addLayout(rrag2)
        
        rrag3 = QHBoxLayout()
        rrag3.addWidget(QLabel("Chunk Size:"))
        self.rag_chunk_size = QSpinBox(); self.rag_chunk_size.setRange(200, 5000); self.rag_chunk_size.setSingleStep(100)
        self.rag_chunk_size.setValue(int(SETTINGS.get("rag_chunk_size", 1000)))
        rrag3.addWidget(self.rag_chunk_size)
        
        rrag3.addWidget(QLabel("  Chunk Overlap:"))
        self.rag_chunk_overlap = QSpinBox(); self.rag_chunk_overlap.setRange(0, 1000); self.rag_chunk_overlap.setSingleStep(50)
        self.rag_chunk_overlap.setValue(int(SETTINGS.get("rag_chunk_overlap", 200)))
        rrag3.addWidget(self.rag_chunk_overlap); rrag3.addStretch(); ragl.addLayout(rrag3)
        
        lay.addWidget(rag)
        return w

    def _build_langsmith(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        ls = QGroupBox("LangSmith Tracing"); lsl = QVBoxLayout(ls)
        
        rls1, self.ls_key = self._create_password_field("API Key:", SETTINGS.get("langsmith_api_key", ""), "https://api.smith.langchain.com/api/v1/workspaces")
        lsl.addLayout(rls1)
        
        rls2 = QHBoxLayout(); rls2.addWidget(QLabel("Project Name:"))
        self.ls_proj = QLineEdit(SETTINGS.get("langsmith_project", "nexus-default"))
        rls2.addWidget(self.ls_proj); lsl.addLayout(rls2)
        
        rls3 = QHBoxLayout(); rls3.addWidget(QLabel("Endpoint URL:"))
        self.ls_end = QLineEdit(SETTINGS.get("langsmith_endpoint", "https://api.smith.langchain.com"))
        rls3.addWidget(self.ls_end); lsl.addLayout(rls3)
        
        lay.addWidget(ls)
        return w

    def _build_git(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        gh = QGroupBox("GitHub"); ghl = QVBoxLayout(gh)
        r1, self.gh_token = self._create_password_field("Token (ghp_):", SETTINGS.get("github_token", ""), "https://api.github.com/user")
        ghl.addLayout(r1)
        lay.addWidget(gh)
        
        gitb = QGroupBox("Git Projects"); gitl = QVBoxLayout(gitb)
        rg = QHBoxLayout(); rg.addWidget(QLabel("Default clone dir:"))
        self.clone_dir = QLineEdit(SETTINGS.get("clone_dir",str(Path.home())))
        btn_br = QPushButton("Browse"); btn_br.clicked.connect(self._browse_clone)
        rg.addWidget(self.clone_dir); rg.addWidget(btn_br); gitl.addLayout(rg)
        lay.addWidget(gitb)
        
        return w

    def _browse_clone(self):
        d = QFileDialog.getExistingDirectory(self,"Select clone directory")
        if d: self.clone_dir.setText(d)

    def _save(self):
        SETTINGS.set("ollama_host", self.host_input.text().strip())
        SETTINGS.set("ollama_threads", self.threads_spin.value())
        SETTINGS.set("gpu_layers", self.gpu_spin.value())
        SETTINGS.set("github_token", self.gh_token.text().strip())
        SETTINGS.set("clone_dir", self.clone_dir.text().strip())
        SETTINGS.set("agent_provider", self.prov_combo.currentText())
        SETTINGS.set("openai_api_key", self.oai_key.text().strip())
        SETTINGS.set("anthropic_api_key", self.ant_key.text().strip())
        SETTINGS.set("google_api_key", self.google_key.text().strip())
        SETTINGS.set("groq_api_key", self.groq_key.text().strip())
        SETTINGS.set("together_api_key", self.together_key.text().strip())
        SETTINGS.set("huggingface_api_key", self.hf_key.text().strip())
        SETTINGS.set("agent_max_steps", self.agent_steps.value())
        SETTINGS.set("langsmith_api_key", self.ls_key.text().strip())
        SETTINGS.set("langsmith_project", self.ls_proj.text().strip())
        SETTINGS.set("langsmith_endpoint", self.ls_end.text().strip())
        SETTINGS.set("rag_embedding_provider", self.rag_prov_combo.currentText())
        SETTINGS.set("rag_embedding_model", self.rag_model_input.text().strip())
        SETTINGS.set("rag_chunk_size", self.rag_chunk_size.value())
        SETTINGS.set("rag_chunk_overlap", self.rag_chunk_overlap.value())
        SETTINGS.set("autoscroll", self.cb_scroll.isChecked())
        SETTINGS.set("timestamps", self.cb_ts.isChecked())
        SETTINGS.save()
        QMessageBox.information(self,"Saved","Settings saved successfully.")
