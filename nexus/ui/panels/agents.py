import json, os
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QTabWidget, QFrame, QSplitter, QLineEdit, 
    QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QMessageBox, QFileDialog, QProgressBar, QMenu, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor, QCursor

from ...core.config import AGENTS_FILE, SESSIONS_DIR, SETTINGS
from ...core.style import THEME, STYLESHEET
from ...core.workers import AgentWorker, OllamaListWorker
from ..widgets import LogView

class AgentPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._worker = None; self._models = []
        self._build_ui()
        self._load_models()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(16,16,16,16); root.setSpacing(12)

        hdr = QHBoxLayout()
        t = QLabel("NEXUS Agent")
        t.setStyleSheet(f"font-size:18px;font-weight:bold;color:{THEME['text']};")
        badge = QLabel("  Manus-style  ")
        badge.setStyleSheet(
            f"background:{THEME['accent']};color:white;font-size:10px;"
            "border-radius:8px;padding:2px 8px;font-weight:bold;")
        hdr.addWidget(t); hdr.addWidget(badge); hdr.addStretch()
        root.addLayout(hdr)

        # description
        desc = QLabel(
            "Autonomous AI agent powered by your local Ollama models. "
            "Give it a task and it will plan and execute steps using tools.")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{THEME['text2']};font-size:12px;")
        root.addWidget(desc)

        # configuration row
        cfg = QHBoxLayout()
        cfg.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox(); self.model_combo.setMinimumWidth(200)
        cfg.addWidget(self.model_combo)
        cfg.addWidget(QLabel("Max steps:"))
        self.steps_spin = QSpinBox(); self.steps_spin.setRange(1,30)
        self.steps_spin.setValue(SETTINGS.get("agent_max_steps",12))
        cfg.addWidget(self.steps_spin)
        cfg.addStretch()
        root.addLayout(cfg)

        # task input
        task_box = QGroupBox("Task")
        tl = QVBoxLayout(task_box)
        self.task_input = QPlainTextEdit()
        self.task_input.setPlaceholderText(
            "Describe what you want the agent to do…\n"
            "Examples:\n"
            "  • List all Python files in C:\\Projects and count lines of code\n"
            "  • Read requirements.txt and suggest package upgrades\n"
            "  • Check git status of all projects in C:\\Projects")
        self.task_input.setMaximumHeight(100)
        tl.addWidget(self.task_input)
        root.addWidget(task_box)

        # controls
        ctrl = QHBoxLayout()
        self.run_btn  = QPushButton("▶  Run Agent"); self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self.run_agent)
        self.stop_btn = QPushButton("⏹  Stop"); self.stop_btn.setObjectName("danger")
        self.stop_btn.clicked.connect(self.stop_agent)
        self.clear_btn = QPushButton("🗑  Clear"); self.clear_btn.clicked.connect(self.clear_feed)
        ctrl.addWidget(self.run_btn); ctrl.addWidget(self.stop_btn)
        ctrl.addStretch(); ctrl.addWidget(self.clear_btn)
        root.addLayout(ctrl)

        # step progress bar
        self.step_bar = QProgressBar()
        self.step_bar.setRange(0, self.steps_spin.value())
        self.step_bar.setValue(0)
        self.step_bar.setFormat("Step %v / %m")
        self.step_bar.setTextVisible(True)
        root.addWidget(self.step_bar)

        # agent feed
        feed_label = QLabel("Agent Feed")
        feed_label.setStyleSheet(f"color:{THEME['text2']};font-size:11px;text-transform:uppercase;letter-spacing:1px;")
        root.addWidget(feed_label)
        self.feed = QTextEdit(); self.feed.setReadOnly(True)
        self.feed.setObjectName("logview")
        self.feed.setStyleSheet(f"background:#08080e;font-size:13px;color:{THEME['text']};")
        root.addWidget(self.feed, 1)

        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet(f"color:{THEME['text3']};font-size:11px;")
        root.addWidget(self.status_lbl)

    def _load_models(self):
        w = OllamaListWorker(self)
        w.result.connect(lambda models: (
            self.model_combo.clear(),
            [self.model_combo.addItem(m["name"]) for m in models]
        ))
        w.start()

    def run_agent(self):
        task  = self.task_input.toPlainText().strip()
        model = self.model_combo.currentText()
        if not task:
            QMessageBox.warning(self,"No task","Enter a task first."); return
        if not model:
            QMessageBox.warning(self,"No model","Select or load an Ollama model."); return

        max_steps = self.steps_spin.value()
        self.step_bar.setMaximum(max_steps); self.step_bar.setValue(0)
        self.run_btn.setEnabled(False); self.status_lbl.setText("Agent running…")
        self._current_step = 0

        self._worker = AgentWorker(SETTINGS.get("ollama_host"), model, task, max_steps)
        self._worker.step.connect(self._on_step)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_step(self, kind: str, text: str):
        self._current_step += 1
        self.step_bar.setValue(min(self._current_step, self.step_bar.maximum()))
        cols = {
            "thought":     THEME["text2"],
            "tool":        "#6eb8ff",
            "observation": THEME["success"],
            "done":        THEME["accent2"],
            "error":       THEME["error"],
        }
        icons = {"thought":"💭","tool":"🔧","observation":"👁","done":"✅","error":"❌"}
        color = cols.get(kind, THEME["text"])
        icon  = icons.get(kind, "•")
        ts    = datetime.now().strftime("%H:%M:%S")
        esc   = text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br>")
        self.feed.append(
            f'<p style="margin:3px 0;"><span style="color:#444466;">[{ts}]</span> '
            f'{icon} <b style="color:{color};">{kind.upper()}</b>: '
            f'<span style="color:{THEME["text"]};">{esc}</span></p>'
        )
        self.feed.moveCursor(QTextCursor.MoveOperation.End)

    def _on_finished(self, result: str):
        self.run_btn.setEnabled(True)
        self.status_lbl.setText(f"Done • {datetime.now().strftime('%H:%M:%S')}")
        # Save session
        SESSIONS_DIR.mkdir(exist_ok=True)
        session = {
            "task": self.task_input.toPlainText(),
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        p = SESSIONS_DIR / f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try: p.write_text(json.dumps(session, indent=2))
        except Exception: pass

    def stop_agent(self):
        if self._worker: self._worker.stop()
        self.run_btn.setEnabled(True); self.status_lbl.setText("Stopped.")

    def clear_feed(self):
        self.feed.clear(); self.step_bar.setValue(0)
        self.status_lbl.setText("Ready")

    def activate(self): pass
    def deactivate(self): pass

class AgentStudioPanel(QWidget):
    """Create, configure, save, and run named AI agents with custom personas and tools."""

    def __init__(self):
        super().__init__()
        self._agents = []; self._worker = None; self._step_count = 0
        self._session_files = []
        self._load_agents(); self._build_ui(); self._load_ollama_models()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(16,16,16,16); root.setSpacing(12)
        hdr = QHBoxLayout()
        t = QLabel("Agent Studio")
        t.setStyleSheet(f"font-size:18px;font-weight:bold;color:{THEME['text']};")
        badge = QLabel("  create & manage agents  ")
        badge.setStyleSheet(f"background:#2d1f5e;color:{THEME['accent2']};font-size:10px;"
                            f"border-radius:8px;padding:2px 8px;font-weight:bold;border:1px solid {THEME['accent']};")
        hdr.addWidget(t); hdr.addWidget(badge); hdr.addStretch()
        root.addLayout(hdr)

        split = QSplitter(Qt.Orientation.Horizontal)

        # LEFT: agent list
        left = QFrame(); ll = QVBoxLayout(left); ll.setContentsMargins(0,0,0,0); ll.setSpacing(6)
        ll.addWidget(QLabel("Saved Agents"))
        self.agent_list = QListWidget()
        self.agent_list.currentItemChanged.connect(self._on_agent_select)
        ll.addWidget(self.agent_list,1)
        br = QHBoxLayout()
        btn_new = QPushButton("➕ New"); btn_new.clicked.connect(self._new_agent)
        btn_del = QPushButton("🗑"); btn_del.setObjectName("danger"); btn_del.setFixedWidth(32)
        btn_del.clicked.connect(self._delete_agent)
        br.addWidget(btn_new,1); br.addWidget(btn_del)
        ll.addLayout(br)
        split.addWidget(left)

        # RIGHT: tabs
        right = QFrame(); rl = QVBoxLayout(right); rl.setContentsMargins(8,0,0,0); rl.setSpacing(4)
        tabs = QTabWidget()
        tabs.addTab(self._build_config_tab(),"⚙  Config")
        tabs.addTab(self._build_run_tab(),"▶  Run")
        tabs.addTab(self._build_history_tab(),"📜  History")
        rl.addWidget(tabs,1)
        split.addWidget(right); split.setSizes([200,560])
        root.addWidget(split,1)

    def _build_config_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setSpacing(8)
        row1 = QHBoxLayout(); row1.addWidget(QLabel("Name:"))
        self.cfg_name = QLineEdit(); self.cfg_name.setPlaceholderText("My Expert Agent")
        btn_preset = QPushButton("📋 Presets"); btn_preset.setFixedWidth(80)
        btn_preset.clicked.connect(self._show_presets)
        row1.addWidget(self.cfg_name,1); row1.addWidget(btn_preset); lay.addLayout(row1)
        row2 = QHBoxLayout(); row2.addWidget(QLabel("Model:"))
        self.cfg_model = QComboBox(); self.cfg_model.setMinimumWidth(200)
        row2.addWidget(self.cfg_model,1)
        row2.addWidget(QLabel("  Max Steps:"))
        self.cfg_steps = QSpinBox(); self.cfg_steps.setRange(1,50); self.cfg_steps.setValue(10)
        row2.addWidget(self.cfg_steps); lay.addLayout(row2)
        lay.addWidget(QLabel("System Prompt / Persona:"))
        self.cfg_system = QPlainTextEdit()
        self.cfg_system.setPlaceholderText(
            "You are an expert Python developer specialized in FastAPI.\n"
            "Always write clean, typed, well-documented code.")
        lay.addWidget(self.cfg_system,1)
        lay.addWidget(QLabel("Tools (comma separated):"))
        self.cfg_tools = QLineEdit("read_file, write_file, run_command, list_dir, git_command")
        lay.addWidget(self.cfg_tools)
        wdrow = QHBoxLayout(); wdrow.addWidget(QLabel("Working Dir:"))
        self.cfg_wd = QLineEdit(); self.cfg_wd.setPlaceholderText("Optional default working directory")
        btn_wd = QPushButton("Browse"); btn_wd.clicked.connect(self._browse_wd)
        wdrow.addWidget(self.cfg_wd,1); wdrow.addWidget(btn_wd); lay.addLayout(wdrow)
        btn_save = QPushButton("💾  Save Agent"); btn_save.setObjectName("primary")
        btn_save.clicked.connect(self._save_agent); lay.addWidget(btn_save)
        return w

    def _build_run_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setSpacing(8)
        lay.addWidget(QLabel("Task:"))
        self.run_task = QPlainTextEdit()
        self.run_task.setPlaceholderText(
            "Describe the task for this agent...\n"
            "Examples:\n"
            "• Analyze Python files in working dir and list potential bugs\n"
            "• Create a Flask REST API with JWT authentication\n"
            "• Review git log and summarize changes from last week")
        self.run_task.setMaximumHeight(100)
        lay.addWidget(self.run_task)
        ctrl = QHBoxLayout()
        self.run_btn = QPushButton("▶  Run Agent"); self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self._run_agent)
        self.stop_btn = QPushButton("⏹  Stop"); self.stop_btn.setObjectName("danger")
        self.stop_btn.clicked.connect(self._stop_agent)
        ctrl.addWidget(self.run_btn); ctrl.addWidget(self.stop_btn); ctrl.addStretch()
        lay.addLayout(ctrl)
        self.step_bar = QProgressBar(); self.step_bar.setRange(0,12); self.step_bar.setValue(0)
        self.step_bar.setFormat("Step %v / %m"); self.step_bar.setTextVisible(True)
        lay.addWidget(self.step_bar)
        lay.addWidget(QLabel("Agent Feed:"))
        self.run_feed = QTextEdit(); self.run_feed.setReadOnly(True)
        self.run_feed.setStyleSheet(f"background:#08080e;color:{THEME['text']};font-size:12px;border-radius:4px;")
        lay.addWidget(self.run_feed,1)
        return w

    def _build_history_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setSpacing(8)
        top = QHBoxLayout()
        top.addWidget(QLabel("Recent Agent Sessions"))
        btn_ref = QPushButton("⟳ Refresh"); btn_ref.clicked.connect(self._load_history)
        top.addWidget(btn_ref); top.addStretch(); lay.addLayout(top)
        self.history_list = QListWidget()
        self.history_list.currentItemChanged.connect(self._on_history_select)
        lay.addWidget(self.history_list,1)
        lay.addWidget(QLabel("Result:"))
        self.history_detail = QPlainTextEdit(); self.history_detail.setReadOnly(True)
        self.history_detail.setStyleSheet(f"background:#080810;color:{THEME['text2']};font-size:12px;")
        self.history_detail.setMaximumHeight(120)
        lay.addWidget(self.history_detail)
        self._load_history(); return w

    def _load_agents(self):
        try:
            if Path(AGENTS_FILE).exists():
                with open(AGENTS_FILE) as f: self._agents = json.load(f)
        except Exception: self._agents = []

    def _save_agents_file(self):
        try:
            with open(AGENTS_FILE,"w") as f: json.dump(self._agents,f,indent=2)
        except Exception: pass

    def _load_ollama_models(self):
        w = OllamaListWorker(self)
        w.result.connect(lambda models: (
            self.cfg_model.clear(),
            [self.cfg_model.addItem(m["name"]) for m in models]
        ))
        w.start()

    def _refresh_agent_list(self):
        self.agent_list.clear()
        for a in self._agents:
            self.agent_list.addItem(f"  {a.get('name','')}  [{a.get('model','')}]")

    def _on_agent_select(self, cur, _):
        if not cur: return
        idx = self.agent_list.row(cur)
        if 0 <= idx < len(self._agents):
            a = self._agents[idx]
            self.cfg_name.setText(a.get("name",""))
            self.cfg_system.setPlainText(a.get("system",""))
            self.cfg_tools.setText(a.get("tools","read_file, write_file, run_command, list_dir"))
            self.cfg_wd.setText(a.get("cwd",""))
            self.cfg_steps.setValue(a.get("max_steps",10))
            mdl = a.get("model","")
            for i in range(self.cfg_model.count()):
                if self.cfg_model.itemText(i)==mdl: self.cfg_model.setCurrentIndex(i); break

    def _new_agent(self):
        self.cfg_name.setText("New Agent"); self.cfg_system.clear()
        self.cfg_tools.setText("read_file, write_file, run_command, list_dir, git_command")
        self.cfg_wd.clear(); self.cfg_steps.setValue(10)

    def _delete_agent(self):
        idx = self.agent_list.currentRow()
        if 0<=idx<len(self._agents):
            self._agents.pop(idx); self._save_agents_file(); self._refresh_agent_list()

    def _show_presets(self):
        menu = QMenu(self)
        menu.setStyleSheet(STYLESHEET)
        presets = {
            "🐍 Python Expert": "You are a senior Python architect. Write idiomatic, typed code using modern libraries.",
            "🕸 Web Dev (JS/TS)": "You are a full-stack web developer. Focus on React/Next.js and clean CSS.",
            "🔒 Security Auditor": "You are a security researcher. Analyze code for vulnerabilities (XSS, SQLi, Buffer Overflows).",
            "📄 Documentation Specialist": "You are a technical writer. Create clear, concise READMEs and API docs from source code.",
            "🧪 Test Engineer": "You are a QA engineer. Generate comprehensive unit and integration tests."
        }
        for name in presets:
            menu.addAction(name).triggered.connect(lambda _, n=name, p=presets[name]: self._apply_preset(n, p))
        menu.exec(QCursor.pos())

    def _apply_preset(self, name, prompt):
        self.cfg_name.setText(name.split(" ",1)[1])
        self.cfg_system.setPlainText(prompt)
        QMessageBox.information(self, "Preset Applied", f"Applied '{name}' persona.")

    def _save_agent(self):
        name = self.cfg_name.text().strip()
        if not name: QMessageBox.warning(self,"Name required","Enter agent name."); return
        agent = {"name":name, "model":self.cfg_model.currentText(),
                 "system":self.cfg_system.toPlainText(), "tools":self.cfg_tools.text(),
                 "cwd":self.cfg_wd.text().strip(), "max_steps":self.cfg_steps.value()}
        for i,a in enumerate(self._agents):
            if a["name"]==name:
                self._agents[i]=agent; self._save_agents_file()
                self._refresh_agent_list()
                QMessageBox.information(self,"Saved",f"Agent '{name}' updated."); return
        self._agents.append(agent); self._save_agents_file(); self._refresh_agent_list()
        QMessageBox.information(self,"Saved",f"Agent '{name}' created.")

    def _browse_wd(self):
        d = QFileDialog.getExistingDirectory(self,"Working directory")
        if d: self.cfg_wd.setText(d)

    def _run_agent(self):
        model = self.cfg_model.currentText()
        task  = self.run_task.toPlainText().strip()
        if not task or not model:
            QMessageBox.warning(self,"Missing","Select a model and enter a task."); return
        max_steps = self.cfg_steps.value()
        self.step_bar.setMaximum(max_steps); self.step_bar.setValue(0)
        self._step_count = 0; self.run_btn.setEnabled(False); self.run_feed.clear()
        self._worker = AgentWorker(SETTINGS.get("ollama_host"), model, task, max_steps)
        custom_sys = self.cfg_system.toPlainText().strip()
        if custom_sys:
            self._worker._SYSTEM = custom_sys + "\n\n" + AgentWorker._SYSTEM
        self._worker.step.connect(self._on_step)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_step(self, kind, text):
        self._step_count += 1; self.step_bar.setValue(self._step_count)
        cols = {"thought":THEME["text2"],"tool":"#6eb8ff","observation":THEME["success"],
                "done":THEME["accent2"],"error":THEME["error"]}
        icons = {"thought":"💭","tool":"🔧","observation":"👁","done":"✅","error":"❌"}
        color = cols.get(kind,THEME["text"]); icon = icons.get(kind,"•")
        ts = datetime.now().strftime("%H:%M:%S")
        esc = text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br>")
        self.run_feed.append(
            f'<p style="margin:2px 0;"><span style="color:#444466;">[{ts}]</span> '
            f'{icon} <b style="color:{color};">{kind.upper()}</b>: '
            f'<span style="color:{THEME["text"]};">{esc}</span></p>')
        self.run_feed.moveCursor(QTextCursor.MoveOperation.End)

    def _on_finished(self, result):
        self.run_btn.setEnabled(True)
        SESSIONS_DIR.mkdir(exist_ok=True)
        agent_name = self.cfg_name.text() or "unnamed"
        session = {"agent":agent_name,"task":self.run_task.toPlainText(),
                   "result":result,"timestamp":datetime.now().isoformat()}
        p = SESSIONS_DIR/f"studio_{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try: p.write_text(json.dumps(session,indent=2))
        except Exception: pass
        self._load_history()

    def _stop_agent(self):
        if self._worker: self._worker.stop(); self.run_btn.setEnabled(True)

    def _load_history(self):
        self.history_list.clear(); self._session_files = []
        if SESSIONS_DIR.exists():
            files = sorted(SESSIONS_DIR.glob("studio_*.json"), reverse=True)[:25]
            for f in files:
                try:
                    d = json.loads(f.read_text())
                    self.history_list.addItem(
                        f"[{d.get('timestamp','')[:16]}] {d.get('agent','')} — {d.get('task','')[:45]}")
                    self._session_files.append(f)
                except Exception: pass

    def _on_history_select(self, cur, _):
        if not cur: return
        idx = self.history_list.row(cur)
        if 0<=idx<len(self._session_files):
            try:
                d = json.loads(self._session_files[idx].read_text())
                self.history_detail.setPlainText(
                    f"Agent: {d.get('agent','')}\nTask: {d.get('task','')}\n\nResult:\n{d.get('result','')}")
            except Exception: pass

    def activate(self): pass
    def deactivate(self): pass
