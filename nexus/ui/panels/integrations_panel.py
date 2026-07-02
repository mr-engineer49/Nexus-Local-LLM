import subprocess, sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QFrame, QGridLayout, QPushButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from ...core.style import THEME
from ...core.config import SETTINGS

class CheckWorker(QThread):
    result_sig = pyqtSignal(bool, str)
    def __init__(self, check_func):
        super().__init__()
        self.check_func = check_func
    def run(self):
        try:
            status, detail = self.check_func()
            self.result_sig.emit(status, detail)
        except Exception as e:
            self.result_sig.emit(False, str(e))

class IntegrationsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def activate(self):
        pass

    def deactivate(self):
        pass

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        hdr = QLabel("🔌 Integrations Dashboard")
        hdr.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {THEME['text']};")
        root.addWidget(hdr)

        desc = QLabel("Connect and monitor your LLM providers, developer tools, and AI frameworks.")
        desc.setStyleSheet(f"color: {THEME['text2']}; font-size: 13px;")
        desc.setWordWrap(True)
        root.addWidget(desc)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background: transparent;")

        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(24)

        # 1. LLM Providers
        self._add_section("LLM Providers", [
            ("Ollama", self._check_ollama),
            ("OpenAI", lambda: self._check_api_key("openai_api_key", "https://api.openai.com/v1/models", "Bearer")),
            ("Anthropic", lambda: self._check_api_key("anthropic_api_key", "https://api.anthropic.com/v1/models", "x-api-key")),
            ("Google Gemini", lambda: self._check_api_key("google_api_key", "https://generativelanguage.googleapis.com/v1beta/models", "")),
            ("Groq", lambda: self._check_api_key("groq_api_key", "https://api.groq.com/openai/v1/models", "Bearer")),
            ("Together AI", lambda: self._check_api_key("together_api_key", "https://api.together.xyz/v1/models", "Bearer")),
            ("HuggingFace", lambda: self._check_api_key("huggingface_api_key", "https://huggingface.co/api/whoami-v2", "Bearer"))
        ])

        # 2. Developer Tools
        self._add_section("Developer Tools", [
            ("Docker", lambda: self._check_cli("docker --version")),
            ("Node.js (npm)", lambda: self._check_cli("npm --version")),
            ("Python (pip)", lambda: self._check_cli("pip --version")),
            ("uv", lambda: self._check_cli("uv --version")),
            ("Git", lambda: self._check_cli("git --version"))
        ])

        # 3. AI Frameworks
        self._add_section("AI Frameworks", [
            ("LangChain", lambda: self._check_python_module("langchain")),
            ("LangGraph", lambda: self._check_python_module("langgraph")),
            ("LangSmith", lambda: self._check_python_module("langsmith")),
            ("CrewAI", lambda: self._check_python_module("crewai")),
            ("AutoGen", lambda: self._check_python_module("autogen"))
        ])

        self.scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        root.addWidget(scroll)

    def _add_section(self, title, items):
        sec = QWidget()
        lay = QVBoxLayout(sec)
        lay.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel(title)
        lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {THEME['accent']}; margin-bottom: 8px;")
        lay.addWidget(lbl)

        grid = QGridLayout()
        grid.setSpacing(12)
        row = 0
        col = 0
        for name, check_func in items:
            card = self._create_card(name, check_func)
            grid.addWidget(card, row, col)
            col += 1
            if col > 1:  # 2 columns
                col = 0
                row += 1
                
        lay.addLayout(grid)
        self.scroll_layout.addWidget(sec)

    def _create_card(self, name, check_func):
        card = QFrame()
        card.setStyleSheet(f"background: {THEME['bg2']}; border-radius: 8px; border: 1px solid {THEME['border']};")
        lay = QHBoxLayout(card)
        
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {THEME['text']}; border: none;")
        lay.addWidget(name_lbl)
        
        lay.addStretch()
        
        status_lbl = QLabel("...")
        status_lbl.setStyleSheet(f"color: {THEME['text2']}; font-size: 12px; border: none;")
        lay.addWidget(status_lbl)
        
        btn = QPushButton("Test")
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {THEME['bg3']}; color: {THEME['text']};
                border: 1px solid {THEME['border']}; border-radius: 4px; padding: 4px 12px;
            }}
            QPushButton:hover {{ background: {THEME['accent']}; color: white; border-color: {THEME['accent']}; }}
        """)
        btn.clicked.connect(lambda: self._run_check(check_func, status_lbl))
        lay.addWidget(btn)
        
        # Initial check
        self._run_check(check_func, status_lbl)
        
        return card

    def _run_check(self, check_func, label):
        label.setText("Checking...")
        label.setStyleSheet(f"color: {THEME['text2']}; font-size: 12px; border: none;")
        
        # Keep track of active workers to prevent garbage collection
        if not hasattr(self, "_workers"):
            self._workers = []
            
        worker = CheckWorker(check_func)
        self._workers.append(worker)
        
        def on_done(status, detail):
            if status:
                label.setText(f"🟢 {detail}")
                label.setStyleSheet(f"color: #4ade80; font-size: 12px; border: none;")
            else:
                label.setText(f"🔴 {detail}")
                label.setStyleSheet(f"color: #f87171; font-size: 12px; border: none;")
            try:
                self._workers.remove(worker)
            except ValueError:
                pass
                
        worker.result_sig.connect(on_done)
        worker.start()

    def _check_ollama(self):
        host = SETTINGS.get("ollama_host", "http://localhost:11434")
        try:
            import requests
            r = requests.get(f"{host}/api/version", timeout=2)
            if r.status_code == 200:
                return True, r.json().get("version", "OK")
            return False, f"HTTP {r.status_code}"
        except Exception:
            return False, "Offline"

    def _check_api_key(self, key_name, url, auth_header):
        val = SETTINGS.get(key_name, "")
        if not val:
            return False, "Missing Key"
        
        import requests
        try:
            headers = {"Authorization": f"{auth_header} {val}"} if auth_header else {}
            if "google" in url:
                url = f"{url}?key={val}"
                headers = {}
            r = requests.get(url, headers=headers, timeout=3)
            if r.status_code in [200, 204]:
                return True, "Active 🟢"
            return False, f"Failed (HTTP {r.status_code})"
        except Exception:
            return False, "Connection Error"

    def _check_cli(self, cmd):
        try:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3,
                encoding="utf-8", errors="replace", creationflags=flags)
            if res.returncode == 0:
                v = res.stdout.strip().split('\\n')[0]
                if len(v) > 20: v = v[:17] + "..."
                return True, v
            return False, "Not installed"
        except Exception:
            return False, "Error"

    def _check_python_module(self, module_name):
        try:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            res = subprocess.run(f"{sys.executable} -c \"import {module_name}; print({module_name}.__version__)\"", 
                                 shell=True, capture_output=True, text=True, timeout=3,
                                 encoding="utf-8", errors="replace", creationflags=flags)
            if res.returncode == 0:
                return True, f"v{res.stdout.strip()}"
            # Some modules don't have __version__ but are importable
            res2 = subprocess.run(f"{sys.executable} -c \"import {module_name}\"", 
                                 shell=True, capture_output=True, text=True, timeout=3,
                                 encoding="utf-8", errors="replace", creationflags=flags)
            if res2.returncode == 0:
                return True, "Installed"
            return False, "Not installed"
        except Exception:
            return False, "Error"
