import json, os, re, time
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QListWidget, QListWidgetItem, QPushButton, 
    QTextEdit, QLineEdit, QSplitter, QMessageBox, QComboBox,
    QGroupBox, QScrollArea, QFormLayout, QTextBrowser
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from ...core.style import THEME, STYLESHEET
from ...core.config import SETTINGS
from ...core.workers import OllamaListWorker

PROMPTS_FILE = Path.home() / ".nexus_prompts.json"

DEFAULT_PROMPTS = [
    {
        "id": "code_review",
        "name": "Code Review",
        "category": "Development",
        "system": "You are a senior software engineer conducting a thorough code review. Focus on architecture, performance, security, and readability.",
        "template": "Please review the following code:\n\n```{code}```\n\nProvide constructive feedback, point out potential bugs, and suggest improvements."
    },
    {
        "id": "bug_analysis",
        "name": "Bug Analysis",
        "category": "Debugging",
        "system": "You are an expert debugging assistant. Analyze the provided stack trace or bug description and identify the root cause.",
        "template": "I encountered the following issue/error:\n\n```{error}```\n\nContext:\n{context}\n\nWhat is causing this and how do I fix it?"
    },
    {
        "id": "unit_tests",
        "name": "Generate Unit Tests",
        "category": "Testing",
        "system": "You are a QA automation expert. Write comprehensive, edge-case covering unit tests for the provided code.",
        "template": "Write unit tests for this code using {framework}:\n\n```{code}```"
    },
    {
        "id": "refactor",
        "name": "Refactor Legacy Code",
        "category": "Development",
        "system": "You are a software architect specializing in clean code and design patterns.",
        "template": "Refactor this legacy code to be more modular, readable, and performant. Explain the changes you made.\n\n```{code}```"
    }
]

class PlaygroundWorker(QThread):
    token = pyqtSignal(str)
    done = pyqtSignal(str, float, float)
    error = pyqtSignal(str)

    def __init__(self, provider, model, system, prompt):
        super().__init__()
        self.provider = provider
        self.model = model
        self.system = system
        self.prompt = prompt

    def run(self):
        from ...core.langchain_agent import build_llm, HAS_LANGCHAIN
        start = time.time()
        try:
            if HAS_LANGCHAIN:
                llm = build_llm(self.provider, self.model)
                from langchain_core.messages import SystemMessage, HumanMessage
                messages = []
                if self.system:
                    messages.append(SystemMessage(content=self.system))
                messages.append(HumanMessage(content=self.prompt))
                
                full = ""
                tok_cnt = 0
                for chunk in llm.stream(messages):
                    c = chunk.content
                    if c:
                        full += c
                        tok_cnt += len(c.split())
                        self.token.emit(c)
                
                elapsed = time.time() - start
                tps = tok_cnt / elapsed if elapsed > 0 else 0
                self.done.emit(full, elapsed, tps)
            else:
                import requests
                from ...core.config import SETTINGS
                host = SETTINGS.get("ollama_host", "http://localhost:11434")
                body = {
                    "model": self.model,
                    "prompt": f"{self.system}\n\n{self.prompt}" if self.system else self.prompt,
                    "stream": True
                }
                r = requests.post(f"{host}/api/generate", json=body, stream=True, timeout=60)
                r.raise_for_status()
                full = ""
                tok_cnt = 0
                for line in r.iter_lines():
                    if line:
                        data = json.loads(line)
                        chunk = data.get("response", "")
                        if chunk:
                            full += chunk
                            tok_cnt += len(chunk.split())
                            self.token.emit(chunk)
                elapsed = time.time() - start
                tps = tok_cnt / elapsed if elapsed > 0 else 0
                self.done.emit(full, elapsed, tps)
        except Exception as e:
            self.error.emit(str(e))

class PromptsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._prompts = []
        self.var_widgets = {}
        self._worker = None
        self._load_prompts()
        self._build_ui()
        self._load_ollama_models()

    def activate(self):
        self._load_ollama_models()

    def deactivate(self):
        if self._worker and self._worker.isRunning():
            self._worker.terminate()

    def _load_prompts(self):
        if PROMPTS_FILE.exists():
            try:
                with open(PROMPTS_FILE, "r") as f:
                    self._prompts = json.load(f)
            except Exception:
                self._prompts = list(DEFAULT_PROMPTS)
        else:
            self._prompts = list(DEFAULT_PROMPTS)
            self._save_prompts()

    def _save_prompts(self):
        try:
            with open(PROMPTS_FILE, "w") as f:
                json.dump(self._prompts, f, indent=2)
        except Exception as e:
            print(f"Failed to save prompts: {e}")

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        hdr = QHBoxLayout()
        t = QLabel("📝 Prompt Sandbox & Templates")
        t.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {THEME['text']};")
        
        btn_new = QPushButton("+ New Template")
        btn_new.clicked.connect(self._new_template)
        
        hdr.addWidget(t)
        hdr.addStretch()
        hdr.addWidget(btn_new)
        root.addLayout(hdr)

        split = QSplitter(Qt.Orientation.Horizontal)
        
        # 1. Left side - Templates List
        list_container = QWidget()
        list_lay = QVBoxLayout(list_container); list_lay.setContentsMargins(0,0,0,0)
        list_lay.addWidget(QLabel("Templates"))
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"background: {THEME['bg2']}; color: {THEME['text']}; border: 1px solid {THEME['border']}; border-radius: 4px;")
        self.list_widget.itemSelectionChanged.connect(self._on_select)
        list_lay.addWidget(self.list_widget)
        split.addWidget(list_container)
        
        # 2. Middle side - Template Editor
        edit_widget = QWidget()
        el = QVBoxLayout(edit_widget)
        el.setContentsMargins(0, 0, 0, 0)
        
        el.addWidget(QLabel("Template Editor"))
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        r1.addWidget(self.name_edit)
        r1.addWidget(QLabel("Category:"))
        self.cat_edit = QLineEdit()
        r1.addWidget(self.cat_edit)
        el.addLayout(r1)
        
        el.addWidget(QLabel("System Prompt:"))
        self.sys_edit = QTextEdit()
        self.sys_edit.setMaximumHeight(80)
        el.addWidget(self.sys_edit)
        
        el.addWidget(QLabel("User Template (use {variable} placeholders):"))
        self.tpl_edit = QTextEdit()
        self.tpl_edit.textChanged.connect(self._update_variables_form)
        el.addWidget(self.tpl_edit, 1)
        
        actions = QHBoxLayout()
        btn_del = QPushButton("🗑️ Delete")
        btn_del.setStyleSheet("color: #f87171;")
        btn_del.clicked.connect(self._delete_current)
        btn_save = QPushButton("💾 Save")
        btn_save.clicked.connect(self._save_current)
        actions.addWidget(btn_del)
        actions.addStretch()
        actions.addWidget(btn_save)
        el.addLayout(actions)
        split.addWidget(edit_widget)
        
        # 3. Right side - Dynamic Playground Sandbox
        play_widget = QGroupBox("Interactive Sandbox Playground")
        play_lay = QVBoxLayout(play_widget)
        
        # Provider & Model selectors
        p_row = QHBoxLayout()
        p_row.addWidget(QLabel("Provider:"))
        self.play_prov = QComboBox()
        self.play_prov.addItems(["ollama", "openai", "google", "groq", "together", "anthropic"])
        self.play_prov.currentTextChanged.connect(self._on_provider_changed)
        p_row.addWidget(self.play_prov)
        
        p_row.addWidget(QLabel("Model:"))
        self.play_model = QComboBox()
        self.play_model.setEditable(True)
        p_row.addWidget(self.play_model, 1)
        play_lay.addLayout(p_row)
        
        # Dynamic inputs scroll area
        play_lay.addWidget(QLabel("Template Variables Inputs:"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(150)
        scroll.setStyleSheet(f"background: {THEME['bg2']}; border: 1px solid {THEME['border']}; border-radius: 4px;")
        
        scroll_content = QWidget()
        self.var_form = QFormLayout(scroll_content)
        scroll.setWidget(scroll_content)
        play_lay.addWidget(scroll)
        
        # Streaming output text browser
        play_lay.addWidget(QLabel("Generated Sandbox Output:"))
        self.play_output = QTextBrowser()
        self.play_output.setStyleSheet("background: #08080f; color: #f0f0f0; border-radius: 4px; font-family: Consolas;")
        play_lay.addWidget(self.play_output, 1)
        
        # Bottom controls and performance metrics
        bot_row = QHBoxLayout()
        self.stats_lbl = QLabel("Speed: – | Latency: –")
        self.stats_lbl.setStyleSheet(f"color: {THEME['text2']}; font-size: 11px;")
        
        self.btn_run_sandbox = QPushButton("⚡ Run Sandbox")
        self.btn_run_sandbox.setObjectName("primary")
        self.btn_run_sandbox.clicked.connect(self._run_playground)
        
        bot_row.addWidget(self.stats_lbl, 1)
        bot_row.addWidget(self.btn_run_sandbox)
        play_lay.addLayout(bot_row)
        
        split.addWidget(play_widget)
        
        # Set column split sizes
        split.setSizes([180, 420, 500])
        root.addWidget(split, 1)
        
        self._refresh_list()

    def _refresh_list(self):
        self.list_widget.clear()
        for p in self._prompts:
            item = QListWidgetItem(f"{p['name']} ({p.get('category', 'General')})")
            item.setData(Qt.ItemDataRole.UserRole, p['id'])
            self.list_widget.addItem(item)

    def _new_template(self):
        import uuid
        new_id = str(uuid.uuid4())[:8]
        new_p = {
            "id": new_id,
            "name": "New Template",
            "category": "Custom",
            "system": "You are a helpful assistant.",
            "template": "Hello {name}, welcome to the playground!"
        }
        self._prompts.append(new_p)
        self._refresh_list()
        
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == new_id:
                self.list_widget.setCurrentItem(item)
                break

    def _on_select(self):
        items = self.list_widget.selectedItems()
        if not items:
            self.name_edit.clear()
            self.cat_edit.clear()
            self.sys_edit.clear()
            self.tpl_edit.clear()
            return
            
        pid = items[0].data(Qt.ItemDataRole.UserRole)
        p = next((x for x in self._prompts if x['id'] == pid), None)
        if p:
            self.name_edit.setText(p.get("name", ""))
            self.cat_edit.setText(p.get("category", ""))
            self.sys_edit.setPlainText(p.get("system", ""))
            self.tpl_edit.setPlainText(p.get("template", ""))
            self._update_variables_form()

    def _save_current(self):
        items = self.list_widget.selectedItems()
        if not items:
            return
            
        pid = items[0].data(Qt.ItemDataRole.UserRole)
        p = next((x for x in self._prompts if x['id'] == pid), None)
        if p:
            p["name"] = self.name_edit.text()
            p["category"] = self.cat_edit.text()
            p["system"] = self.sys_edit.toPlainText()
            p["template"] = self.tpl_edit.toPlainText()
            self._save_prompts()
            self._refresh_list()
            
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == pid:
                    self.list_widget.setCurrentItem(item)
                    break
            QMessageBox.information(self, "Saved", "Template saved successfully.")

    def _delete_current(self):
        items = self.list_widget.selectedItems()
        if not items:
            return
            
        pid = items[0].data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, "Delete", "Delete this template?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._prompts = [x for x in self._prompts if x['id'] != pid]
            self._save_prompts()
            self._refresh_list()

    def _update_variables_form(self):
        template = self.tpl_edit.toPlainText()
        vars_found = sorted(list(set(re.findall(r"\{([a-zA-Z0-9_]+)\}", template))))
        
        current_vars = list(self.var_widgets.keys())
        if vars_found == current_vars:
            return
            
        while self.var_form.count():
            item = self.var_form.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        self.var_widgets.clear()
        
        for var in vars_found:
            if var.lower() in ("code", "error", "context", "text", "diff", "prompt", "query"):
                inp = QTextEdit()
                inp.setMaximumHeight(70)
                inp.setStyleSheet(f"background: {THEME['bg3']}; color: {THEME['text']}; border: 1px solid {THEME['border']};")
            else:
                inp = QLineEdit()
                inp.setStyleSheet(f"background: {THEME['bg3']}; color: {THEME['text']}; border: 1px solid {THEME['border']};")
            self.var_form.addRow(QLabel(f"{var}:"), inp)
            self.var_widgets[var] = inp

    def _on_provider_changed(self, provider):
        self.play_model.clear()
        if provider == "ollama":
            self._load_ollama_models()
        else:
            defaults = {
                "openai": ["gpt-4o-mini", "gpt-4o"],
                "google": ["gemini-2.0-flash", "gemini-1.5-pro"],
                "groq": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
                "together": ["meta-llama/Llama-3.3-70B-Instruct-Turbo"],
                "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"]
            }
            self.play_model.addItems(defaults.get(provider, []))

    def _load_ollama_models(self):
        if self.play_prov.currentText() != "ollama":
            return
        w = OllamaListWorker(self)
        w.result.connect(lambda models: (
            self.play_model.clear(),
            [self.play_model.addItem(m["name"]) for m in models]
        ))
        w.start()

    def _run_playground(self):
        provider = self.play_prov.currentText()
        model = self.play_model.currentText()
        system = self.sys_edit.toPlainText()
        template = self.tpl_edit.toPlainText()
        
        # Build prompt using variable inputs
        values = {}
        for var, widget in self.var_widgets.items():
            if isinstance(widget, QTextEdit):
                values[var] = widget.toPlainText()
            else:
                values[var] = widget.text()
                
        try:
            rendered_prompt = template.format(**values)
        except KeyError as e:
            QMessageBox.warning(self, "Missing Variable", f"Template rendering failed: missing variable {e}")
            return
            
        self.play_output.clear()
        self.btn_run_sandbox.setEnabled(False)
        self.stats_lbl.setText("Streaming output...")
        
        self._worker = PlaygroundWorker(provider, model, system, rendered_prompt)
        self._worker.token.connect(lambda t: (self.play_output.insertPlainText(t), self.play_output.moveCursor(Qt.CursorMoveStyle.VisualCharacter)))
        
        def on_done(full_text, elapsed, tps):
            self.stats_lbl.setText(f"Speed: {tps:.1f} tok/s | Latency: {elapsed:.2f}s")
            self.btn_run_sandbox.setEnabled(True)
            
        def on_error(err):
            self.play_output.setHtml(f"<span style='color: #f87171;'>[ERROR] {err}</span>")
            self.stats_lbl.setText("Execution failed.")
            self.btn_run_sandbox.setEnabled(True)
            
        self._worker.done.connect(on_done)
        self._worker.error.connect(on_error)
        self._worker.start()
