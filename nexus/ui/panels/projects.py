import json, subprocess, sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QGroupBox, QFrame, QSplitter, QLineEdit, QTextEdit, 
    QFileDialog, QPlainTextEdit, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor

from ...core.config import PROJECTS_FILE, SETTINGS
from ...core.style import THEME
from ...core.workers import CommandWorker, OllamaListWorker, OllamaAPIWorker
from ..widgets import LogView

class ProjectRunnerPanel(QWidget):
    """Auto-detect project stack, run locally, and attach a local Ollama model as AI assistant."""

    STACKS = {
        "package.json":       {"name":"Node.js",  "install":"npm install",                   "run":"npm start",    "dev":"npm run dev",  "test":"npm test"},
        "requirements.txt":   {"name":"Python",   "install":"pip install -r requirements.txt","run":"python main.py","dev":"python app.py","test":"pytest"},
        "pyproject.toml":     {"name":"Python",   "install":"pip install -e .",              "run":"python -m app","dev":"",             "test":"pytest"},
        "Cargo.toml":         {"name":"Rust",     "install":"cargo build",                   "run":"cargo run",    "dev":"cargo run",    "test":"cargo test"},
        "go.mod":             {"name":"Go",       "install":"go mod download",               "run":"go run .",     "dev":"go run .",     "test":"go test ./..."},
        "docker-compose.yml": {"name":"Docker",   "install":"docker-compose pull",           "run":"docker-compose up","dev":"docker-compose up","test":""},
        "Makefile":           {"name":"Make",     "install":"make install",                  "run":"make run",     "dev":"make dev",     "test":"make test"},
        "pom.xml":            {"name":"Java/Maven","install":"mvn install",                  "run":"mvn exec:java","dev":"mvn spring-boot:run","test":"mvn test"},
        "build.gradle":       {"name":"Java/Gradle","install":"gradle build",                "run":"gradle run",   "dev":"gradle bootRun","test":"gradle test"},
    }

    def __init__(self):
        super().__init__()
        self._worker = None; self._ai_worker = None
        self._projects = []; self._detected_stack = None
        self._ai_response_started = False
        self._load_projects(); self._build_ui(); self._load_ollama_models()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(16,16,16,16); root.setSpacing(12)

        hdr = QHBoxLayout()
        t = QLabel("Project Runner")
        t.setStyleSheet(f"font-size:18px;font-weight:bold;color:{THEME['text']};")
        badge = QLabel("  auto-detect & run  ")
        badge.setStyleSheet(f"background:{THEME['success']};color:{THEME['bg']};font-size:10px;"
                            "border-radius:8px;padding:2px 8px;font-weight:bold;")
        hdr.addWidget(t); hdr.addWidget(badge); hdr.addStretch()
        root.addLayout(hdr)

        sel_box = QGroupBox("Select Project")
        sl = QHBoxLayout(sel_box)
        self.proj_combo = QComboBox(); self.proj_combo.setMinimumWidth(280)
        self.proj_combo.currentIndexChanged.connect(self._on_proj_change)
        btn_browse = QPushButton("Browse"); btn_browse.clicked.connect(self._browse_proj)
        btn_ref = QPushButton("⟳"); btn_ref.setFixedWidth(32); btn_ref.clicked.connect(self._refresh_list)
        sl.addWidget(self.proj_combo,1); sl.addWidget(btn_browse); sl.addWidget(btn_ref)
        root.addWidget(sel_box)

        stack_box = QGroupBox("Detected Stack")
        stk = QVBoxLayout(stack_box)
        self.stack_lbl = QLabel("No project selected")
        self.stack_lbl.setStyleSheet(f"color:{THEME['accent2']};font-size:14px;font-weight:bold;")
        self.stack_files_lbl = QLabel("")
        self.stack_files_lbl.setStyleSheet(f"color:{THEME['text2']};font-size:11px;")
        stk.addWidget(self.stack_lbl); stk.addWidget(self.stack_files_lbl)
        root.addWidget(stack_box)

        split = QSplitter(Qt.Orientation.Horizontal)

        # Left: actions
        left = QFrame(); ll = QVBoxLayout(left); ll.setContentsMargins(0,0,0,0); ll.setSpacing(8)
        ll.addWidget(QLabel("Quick Actions"))
        self.btn_install = QPushButton("📦  Install Dependencies"); self.btn_install.setObjectName("primary")
        self.btn_install.clicked.connect(lambda: self._run_action("install"))
        self.btn_run = QPushButton("▶  Run Project"); self.btn_run.setObjectName("success")
        self.btn_run.clicked.connect(lambda: self._run_action("run"))
        self.btn_dev = QPushButton("🔥  Dev Server"); self.btn_dev.setObjectName("success")
        self.btn_dev.clicked.connect(lambda: self._run_action("dev"))
        self.btn_test = QPushButton("🧪  Run Tests"); self.btn_test.setObjectName("warn")
        self.btn_test.clicked.connect(lambda: self._run_action("test"))
        self.btn_stop = QPushButton("⏹  Stop"); self.btn_stop.setObjectName("danger")
        self.btn_stop.clicked.connect(self._stop)
        self.btn_term = QPushButton("🐚  Open in Terminal"); self.btn_term.clicked.connect(self._open_terminal)
        for b in [self.btn_install,self.btn_run,self.btn_dev,self.btn_test,self.btn_stop,self.btn_term]:
            b.setMinimumHeight(34); ll.addWidget(b)
        ll.addSpacing(6); ll.addWidget(QLabel("Custom command:"))
        self.custom_cmd = QLineEdit(); self.custom_cmd.setPlaceholderText("python manage.py runserver")
        self.custom_cmd.returnPressed.connect(self._run_custom)
        btn_cust = QPushButton("▶ Run"); btn_cust.setObjectName("success"); btn_cust.clicked.connect(self._run_custom)
        ll.addWidget(self.custom_cmd); ll.addWidget(btn_cust); ll.addStretch()
        split.addWidget(left)

        # Right: AI assistant
        right = QFrame(); rl = QVBoxLayout(right); rl.setContentsMargins(8,0,0,0); rl.setSpacing(8)
        rl.addWidget(QLabel("AI Project Assistant"))
        ai_row = QHBoxLayout()
        ai_row.addWidget(QLabel("Model:"))
        self.ai_model_combo = QComboBox(); self.ai_model_combo.setMinimumWidth(180)
        ai_row.addWidget(self.ai_model_combo,1)
        rl.addLayout(ai_row)
        self.ai_question = QPlainTextEdit()
        self.ai_question.setPlaceholderText(
            "Ask the AI about this project...\n"
            "• How do I run this project?\n"
            "• What does this codebase do?\n"
            "• How to add authentication?")
        self.ai_question.setMaximumHeight(90)
        rl.addWidget(self.ai_question)
        btn_ask = QPushButton("Ask AI about Project"); btn_ask.setObjectName("primary")
        btn_ask.clicked.connect(self._ask_ai); rl.addWidget(btn_ask)
        self.ai_response = QTextEdit(); self.ai_response.setReadOnly(True)
        self.ai_response.setStyleSheet(f"background:#080810;color:{THEME['text']};font-size:12px;border-radius:4px;")
        rl.addWidget(self.ai_response,1)
        split.addWidget(right); split.setSizes([260,320])
        root.addWidget(split,1)

        self.log = LogView(); self.log.setMaximumHeight(140)
        root.addWidget(self.log)

    def activate(self):
        self._refresh_list()

    def deactivate(self): pass

    def _load_projects(self):
        try:
            if Path(PROJECTS_FILE).exists():
                with open(PROJECTS_FILE) as f: self._projects = json.load(f)
        except Exception: self._projects = []

    def _refresh_list(self):
        self._load_projects(); self.proj_combo.clear()
        for p in self._projects:
            self.proj_combo.addItem(f"  {p['name']}", p["path"])

    def _browse_proj(self):
        d = QFileDialog.getExistingDirectory(self, "Select project folder")
        if not d: return
        name = Path(d).name
        if not any(p["path"]==d for p in self._projects):
            self._projects.append({"name":name,"path":d})
            try:
                with open(PROJECTS_FILE,"w") as f: json.dump(self._projects,f,indent=2)
            except Exception: pass
        self._refresh_list()
        for i in range(self.proj_combo.count()):
            if self.proj_combo.itemData(i)==d: self.proj_combo.setCurrentIndex(i); break

    def _on_proj_change(self, idx):
        path = self.proj_combo.itemData(idx)
        if path: self._detect_stack(path)

    def _detect_stack(self, path):
        p = Path(path); found = []
        detected = None
        for fname, info in self.STACKS.items():
            if (p/fname).exists():
                found.append(fname)
                if detected is None: detected = (fname, info)
        if detected:
            fname, info = detected
            self._detected_stack = {"path":path,"fname":fname,"info":info}
            self.stack_lbl.setText(f"{info['name']}  •  {fname}")
            self.stack_files_lbl.setText("Also: "+", ".join(found[1:]) if len(found)>1 else "")
        else:
            self._detected_stack = None
            self.stack_lbl.setText("Unknown / Generic project")
            self.stack_files_lbl.setText(f"No known config files found in {path}")
        self.log.append_line(f"Project: {Path(path).name}","info")

    def _run_action(self, action):
        if not self._detected_stack: self.log.append_line("No stack detected","error"); return
        cmd = self._detected_stack["info"].get(action,"")
        if not cmd: self.log.append_line(f"No '{action}' command for this stack","warn"); return
        self._exec_cmd(cmd, self._detected_stack["path"])

    def _run_custom(self):
        cmd = self.custom_cmd.text().strip()
        if not cmd: return
        path = self.proj_combo.itemData(self.proj_combo.currentIndex()) or "."
        self._exec_cmd(cmd, path)

    def _exec_cmd(self, cmd, cwd):
        self.log.append_line(f"$ {cmd}","cmd")
        if self._worker and self._worker.isRunning(): self._worker.stop()
        self._worker = CommandWorker(cmd, cwd=cwd, shell_type="cmd")
        self._worker.output.connect(lambda l: self.log.append_line(l))
        self._worker.done.connect(lambda c: self.log.append_line(
            f"[exit {c}]","success" if c==0 else "error"))
        self._worker.start()

    def _open_terminal(self):
        path = self.proj_combo.itemData(self.proj_combo.currentIndex())
        if not path: return
        mw = QApplication.activeWindow()
        if hasattr(mw, "_switch"):
             # Finding terminal panel by name in nav buttons
             for i, btn in enumerate(mw._nav_btns):
                 if "Terminal" in btn.text():
                     mw._switch(i)
                     break

    def _stop(self):
        if self._worker: self._worker.stop(); self.log.append_line("Stopped.","warn")

    def _load_ollama_models(self):
        w = OllamaListWorker(self)
        w.result.connect(lambda models: (
            self.ai_model_combo.clear(),
            [self.ai_model_combo.addItem(m["name"]) for m in models]
        ))
        w.start()

    def _ask_ai(self):
        model = self.ai_model_combo.currentText()
        question = self.ai_question.toPlainText().strip()
        if not model or not question: return
        path = self.proj_combo.itemData(self.proj_combo.currentIndex()) or "."
        p = Path(path); context_parts = []
        for cf in ["README.md","readme.md","package.json","requirements.txt","pyproject.toml","Cargo.toml","go.mod"]:
            fp = p/cf
            if fp.exists():
                try: context_parts.append(f"=== {cf} ===\n{fp.read_text(errors='replace')[:600]}")
                except Exception: pass
            if len(context_parts)>=3: break
        context = "\n\n".join(context_parts)
        stack = self._detected_stack["info"]["name"] if self._detected_stack else "Unknown"
        system = (f"You are an expert {stack} developer. Project: {path}\n\nContext:\n{context}")
        self.ai_response.clear(); self._ai_response_started = False
        msgs = [{"role":"user","content":question}]
        if self._ai_worker and self._ai_worker.isRunning(): self._ai_worker.stop()
        self._ai_worker = OllamaAPIWorker(SETTINGS.get("ollama_host"), model, msgs, system)
        self._ai_worker.token.connect(self._on_ai_token)
        self._ai_worker.done.connect(lambda _: self.log.append_line("AI done","success"))
        self._ai_worker.error.connect(lambda e: self.ai_response.append(f'<span style="color:{THEME["error"]};">{e}</span>'))
        self._ai_worker.start()

    def _on_ai_token(self, tok):
        if not self._ai_response_started:
            self.ai_response.clear(); self._ai_response_started = True
        esc = tok.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br>")
        cur = self.ai_response.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End); self.ai_response.setTextCursor(cur)
        self.ai_response.insertHtml(f'<span style="color:{THEME["text"]};">{esc}</span>')
        self.ai_response.moveCursor(QTextCursor.MoveOperation.End)
