
# ─────────────────────────────────────────────
#  PROJECT RUNNER PANEL
# ─────────────────────────────────────────────

AGENTS_FILE = Path.home() / ".nexus_agents.json"

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
        for b in [self.btn_install,self.btn_run,self.btn_dev,self.btn_test,self.btn_stop]:
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
        self._refresh_list()

    def _load_projects(self):
        try:
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
        self.log.append_line(f"Project: {Path(path).name}  [{self._detected_stack['info']['name'] if self._detected_stack else '?'}]","info")

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


# ─────────────────────────────────────────────
#  AGENT STUDIO PANEL
# ─────────────────────────────────────────────

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
        row1.addWidget(self.cfg_name,1); lay.addLayout(row1)
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


# ─────────────────────────────────────────────
#  STATUS DASHBOARD
# ─────────────────────────────────────────────

class StatusDashboard(QWidget):
    """Live overview: Ollama status, active models, agent sessions, system resources."""

    def __init__(self):
        super().__init__()
        self._build_ui()
        self._timer = QTimer(self); self._timer.timeout.connect(self._refresh)
        self._timer.start(6000); self._refresh()

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

        if SESSIONS_DIR.exists():
            files = sorted(SESSIONS_DIR.glob("*.json"), reverse=True)
            self.sess_lbl.setText(f"{len(files)} session(s)")
            if files:
                try:
                    d = json.loads(files[0].read_text())
                    self.sess_latest.setText(f"Latest: {d.get('timestamp','')[:16]} — {d.get('agent','')}")
                except Exception: pass
            self.sessions_tree.clear()
            for f in files[:20]:
                try:
                    d = json.loads(f.read_text())
                    self.sessions_tree.addTopLevelItem(QTreeWidgetItem([
                        d.get("timestamp","")[:16],
                        d.get("agent","") or d.get("model",""),
                        d.get("task","")[:55],
                        d.get("result","")[:45],
                    ]))
                except Exception: pass

        if HAS_PSUTIL:
            cpu = psutil.cpu_percent(interval=None)
            vm  = psutil.virtual_memory()
            disk = psutil.disk_usage("/" if sys.platform!="win32" else "C:\\")
            self.cpu_lbl.setText(f"CPU: {cpu:.1f}%  ({psutil.cpu_count()} cores)")
            self.ram_lbl.setText(f"RAM: {vm.used//1024**3}/{vm.total//1024**3} GB  ({vm.percent:.0f}%)")
            self.disk_lbl.setText(f"Disk: {disk.used//1024**3}/{disk.total//1024**3} GB  ({disk.percent:.0f}%)")

        try:
            with open(PROJECTS_FILE) as f: projs = json.load(f)
            self.proj_lbl.setText(f"{len(projs)} project(s) registered")
        except Exception:
            self.proj_lbl.setText("0 projects")

    def _quick_action(self, action):
        if action == "__sys_snap__":
            if HAS_PSUTIL:
                cpu  = psutil.cpu_percent(interval=1)
                vm   = psutil.virtual_memory()
                disk = psutil.disk_usage("/" if sys.platform!="win32" else "C:\\")
                self.quick_log.append_line(
                    f"CPU:{cpu:.1f}%  RAM:{vm.percent:.0f}%  Disk:{disk.percent:.0f}%","info")
            return
        if action == "__git_all__":
            try:
                with open(PROJECTS_FILE) as f: projs = json.load(f)
            except Exception: projs = []
            for p in projs[:6]:
                r = subprocess.run("git status --short --branch", cwd=p["path"], shell=True,
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0)
                self.quick_log.append_line(f"{p['name']}: {(r.stdout+r.stderr).strip()[:70]}","info")
            return
        if action == "__list_sessions__":
            if SESSIONS_DIR.exists():
                files = sorted(SESSIONS_DIR.glob("*.json"),reverse=True)[:10]
                for f in files:
                    try:
                        d = json.loads(f.read_text())
                        self.quick_log.append_line(
                            f"[{d.get('timestamp','')[:16]}] {d.get('agent','?')} — {d.get('result','')[:50]}","info")
                    except Exception: pass
            return
        w = CommandWorker(action, shell_type="cmd")
        w.output.connect(lambda l: self.quick_log.append_line(l))
        w.done.connect(lambda c: self.quick_log.append_line(f"[exit {c}]","success" if c==0 else "error"))
        w.start(); self._qw = w

