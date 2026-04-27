"""
nexus/ui/panels/langsmith_panel.py
────────────────────────────────────
LangSmith dashboard panel for NEXUS.

Tabs
────
1. Connection  — API key, project, endpoint, tracing toggle, test connection
2. Runs        — Browse & inspect recent LangSmith runs with full trace detail
3. Datasets    — Browse datasets + examples, run batch evaluation
"""

import json
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QCheckBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QTextEdit,
    QListWidget, QListWidgetItem, QFrame, QComboBox, QMessageBox,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QTextCursor

from ...core.config import SETTINGS
from ...core.style import THEME
from ...core.langchain_agent import configure_langsmith, HAS_LANGSMITH

# ── Background worker ─────────────────────────────────────────────────────────

class _LSWorker(QThread):
    """Generic background worker: calls fn(*args) and emits result or error."""
    result = pyqtSignal(object)
    error  = pyqtSignal(str)

    def __init__(self, fn, *args):
        super().__init__()
        self._fn = fn
        self._args = args

    def run(self):
        try:
            self.result.emit(self._fn(*self._args))
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}")


def _make_client(api_key: str = "", endpoint: str = ""):
    from langsmith import Client
    return Client(
        api_key=api_key or SETTINGS.get("langsmith_api_key"),
        api_url=endpoint or SETTINGS.get("langsmith_endpoint"),
    )


# ── Status badge helper ───────────────────────────────────────────────────────

def _status_label(text: str, ok: bool) -> QLabel:
    lbl = QLabel(text)
    color = THEME["success"] if ok else THEME["error"]
    lbl.setStyleSheet(
        f"color:{color};font-weight:bold;font-size:12px;"
        f"border:1px solid {color};border-radius:6px;padding:2px 10px;"
    )
    return lbl


# ── Main Panel ────────────────────────────────────────────────────────────────

class LangSmithPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._worker: QThread | None = None
        self._run_ids: list = []
        self._dataset_ids: list = []
        self._example_ids: list = []
        self._build_ui()

    def activate(self):   pass
    def deactivate(self): pass

    # ── UI builder ────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("LangSmith")
        title.setStyleSheet(f"font-size:18px;font-weight:bold;color:{THEME['text']};")
        badge = QLabel("  tracing & evals  ")
        badge.setStyleSheet(
            f"background:#1a1040;color:{THEME['accent2']};font-size:10px;"
            f"border-radius:8px;padding:2px 8px;font-weight:bold;"
            f"border:1px solid {THEME['accent']};"
        )
        self._conn_badge = QLabel("○ Disconnected")
        self._conn_badge.setStyleSheet(f"color:{THEME['error']};font-size:11px;")
        hdr.addWidget(title)
        hdr.addWidget(badge)
        hdr.addStretch()
        hdr.addWidget(self._conn_badge)
        root.addLayout(hdr)

        if not HAS_LANGSMITH:
            warn = QLabel(
                "⚠  langsmith not installed.\n"
                "Run:  pip install langsmith"
            )
            warn.setStyleSheet(f"color:{THEME['warning']};font-size:13px;padding:20px;")
            warn.setWordWrap(True)
            root.addWidget(warn)
            root.addStretch()
            return

        tabs = QTabWidget()
        tabs.addTab(self._build_connection_tab(), "🔌  Connection")
        tabs.addTab(self._build_runs_tab(),       "📋  Runs")
        tabs.addTab(self._build_datasets_tab(),   "🗄  Datasets")
        tabs.addTab(self._build_bridge_tab(),     "🛠  Bridge")
        root.addWidget(tabs, 1)

    # ── Tab 1: Connection ─────────────────────────────────────────────────────

    def _build_connection_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        creds = QGroupBox("Credentials")
        cl = QVBoxLayout(creds)

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("API Key:"))
        self._api_key = QLineEdit(SETTINGS.get("langsmith_api_key", ""))
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText("ls__xxxxxxxxxxxxxxxxxxxxxxxx")
        r1.addWidget(self._api_key)
        cl.addLayout(r1)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Project:"))
        self._project = QLineEdit(SETTINGS.get("langsmith_project", "nexus-default"))
        r2.addWidget(self._project)
        cl.addLayout(r2)

        r3 = QHBoxLayout()
        r3.addWidget(QLabel("Endpoint:"))
        self._endpoint = QLineEdit(SETTINGS.get("langsmith_endpoint", "https://api.smith.langchain.com"))
        r3.addWidget(self._endpoint)
        cl.addLayout(r3)

        lay.addWidget(creds)

        ctrl = QHBoxLayout()
        btn_test = QPushButton("🔌  Test Connection")
        btn_test.setObjectName("primary")
        btn_test.clicked.connect(self._test_connection)
        btn_save = QPushButton("💾  Save")
        btn_save.clicked.connect(self._save_settings)
        ctrl.addWidget(btn_test)
        ctrl.addWidget(btn_save)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        self._trace_check = QCheckBox("Enable LangSmith Tracing for all agent runs")
        self._trace_check.setChecked(bool(SETTINGS.get("langchain_tracing", False)))
        self._trace_check.setStyleSheet(f"color:{THEME['text']};font-size:13px;")
        self._trace_check.toggled.connect(self._toggle_tracing)
        lay.addWidget(self._trace_check)

        self._test_log = QTextEdit()
        self._test_log.setReadOnly(True)
        self._test_log.setMaximumHeight(180)
        self._test_log.setStyleSheet(
            f"background:#08080e;color:{THEME['text']};font-size:12px;border-radius:4px;"
        )
        lay.addWidget(self._test_log)

        tips = QGroupBox("Quick Links")
        tl = QVBoxLayout(tips)
        for label, url in [
            ("🌐 Open LangSmith Dashboard", "https://smith.langchain.com"),
            ("📖 LangSmith Docs", "https://docs.smith.langchain.com"),
            ("📦 LangChain Hub",  "https://smith.langchain.com/hub"),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, u=url: self._open_url(u))
            tl.addWidget(btn)
        lay.addWidget(tips)
        lay.addStretch()
        return w

    # ── Tab 2: Runs ───────────────────────────────────────────────────────────

    def _build_runs_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(8)

        top = QHBoxLayout()
        top.addWidget(QLabel("Project:"))
        self._runs_project = QLineEdit(SETTINGS.get("langsmith_project", "nexus-default"))
        self._runs_project.setMaximumWidth(220)
        top.addWidget(self._runs_project)
        self._runs_limit = QComboBox()
        for n in [10, 25, 50, 100]:
            self._runs_limit.addItem(f"Last {n}", n)
        top.addWidget(self._runs_limit)
        btn_refresh = QPushButton("⟳  Refresh")
        btn_refresh.clicked.connect(self._load_runs)
        top.addWidget(btn_refresh)
        top.addStretch()
        lay.addLayout(top)

        self._runs_progress = QProgressBar()
        self._runs_progress.setRange(0, 0)
        self._runs_progress.setVisible(False)
        self._runs_progress.setMaximumHeight(4)
        lay.addWidget(self._runs_progress)

        split = QSplitter(Qt.Orientation.Vertical)

        # Top: table
        self._runs_table = QTableWidget(0, 6)
        self._runs_table.setHorizontalHeaderLabels(["Time", "Name", "Type", "Status", "Latency", "Tokens"])
        self._runs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._runs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._runs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._runs_table.setAlternatingRowColors(True)
        self._runs_table.setStyleSheet(
            f"QTableWidget{{background:{THEME['bg2']};color:{THEME['text']};gridline-color:{THEME['border']};}}"
            f"QTableWidget::item:selected{{background:{THEME['bg3']};color:{THEME['accent2']};}}"
            f"QTableWidget::item:alternate{{background:{THEME['bg']};}}"
        )
        self._runs_table.currentCellChanged.connect(self._on_run_select)
        split.addWidget(self._runs_table)

        # Bottom: detail
        detail_frame = QFrame()
        dl = QVBoxLayout(detail_frame)
        dl.setContentsMargins(0, 4, 0, 0)
        dl.addWidget(QLabel("Run Detail (Inputs → Steps → Output):"))
        self._run_detail = QTextEdit()
        self._run_detail.setReadOnly(True)
        self._run_detail.setStyleSheet(
            f"background:#06060c;color:{THEME['text']};font-size:12px;border-radius:4px;"
        )
        dl.addWidget(self._run_detail)
        split.addWidget(detail_frame)
        split.setSizes([300, 200])
        lay.addWidget(split, 1)

        self._runs_status = QLabel("Click ⟳ Refresh to load runs.")
        self._runs_status.setStyleSheet(f"color:{THEME['text3']};font-size:11px;")
        lay.addWidget(self._runs_status)
        return w

    # ── Tab 3: Datasets ───────────────────────────────────────────────────────

    def _build_datasets_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(8)

        top = QHBoxLayout()
        top.addWidget(QLabel("Datasets"))
        btn_refresh = QPushButton("⟳  Refresh")
        btn_refresh.clicked.connect(self._load_datasets)
        top.addWidget(btn_refresh)
        top.addStretch()
        lay.addLayout(top)

        self._ds_progress = QProgressBar()
        self._ds_progress.setRange(0, 0)
        self._ds_progress.setVisible(False)
        self._ds_progress.setMaximumHeight(4)
        lay.addWidget(self._ds_progress)

        split = QSplitter(Qt.Orientation.Horizontal)

        # Left: dataset list
        left = QFrame()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(QLabel("Datasets:"))
        self._ds_list = QListWidget()
        self._ds_list.currentItemChanged.connect(self._on_dataset_select)
        ll.addWidget(self._ds_list, 1)
        split.addWidget(left)

        # Right: examples table
        right = QFrame()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 0, 0, 0)
        rl.addWidget(QLabel("Examples:"))
        self._ex_table = QTableWidget(0, 3)
        self._ex_table.setHorizontalHeaderLabels(["#", "Input (preview)", "Output (preview)"])
        self._ex_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._ex_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._ex_table.setStyleSheet(
            f"QTableWidget{{background:{THEME['bg2']};color:{THEME['text']};gridline-color:{THEME['border']};}}"
        )
        rl.addWidget(self._ex_table, 1)

        eval_row = QHBoxLayout()
        eval_row.addWidget(QLabel("Run eval against selected dataset:"))
        self._eval_model_input = QLineEdit()
        self._eval_model_input.setPlaceholderText("model name (e.g. llama3)")
        self._eval_model_input.setMaximumWidth(200)
        eval_row.addWidget(self._eval_model_input)
        btn_eval = QPushButton("▶  Run Evaluation")
        btn_eval.setObjectName("primary")
        btn_eval.clicked.connect(self._run_evaluation)
        eval_row.addWidget(btn_eval)
        eval_row.addStretch()
        rl.addLayout(eval_row)

        self._eval_log = QTextEdit()
        self._eval_log.setReadOnly(True)
        self._eval_log.setMaximumHeight(130)
        self._eval_log.setStyleSheet(
            f"background:#06060c;color:{THEME['text']};font-size:12px;border-radius:4px;"
        )
        rl.addWidget(self._eval_log)
        split.addWidget(right)
        split.setSizes([200, 520])
        lay.addWidget(split, 1)

        self._ds_status = QLabel("Click ⟳ Refresh to load datasets.")
        self._ds_status.setStyleSheet(f"color:{THEME['text3']};font-size:11px;")
        lay.addWidget(self._ds_status)
        return w

    # ── Actions: Connection ───────────────────────────────────────────────────

    def _test_connection(self):
        self._test_log.clear()
        self._log_test("🔌 Testing connection to LangSmith…", THEME["text2"])
        api_key  = self._api_key.text().strip()
        project  = self._project.text().strip()
        endpoint = self._endpoint.text().strip()

        if not api_key:
            self._log_test("❌ API key is empty.", THEME["error"])
            return

        def _fetch():
            client = _make_client(api_key, endpoint)
            projects = list(client.list_projects())
            return projects

        w = _LSWorker(_fetch)
        w.result.connect(self._on_test_ok)
        w.error.connect(self._on_test_err)
        w.start()
        self._worker = w

    def _on_test_ok(self, projects):
        self._conn_badge.setText("● Connected")
        self._conn_badge.setStyleSheet(f"color:{THEME['success']};font-size:11px;font-weight:bold;")
        self._log_test(f"✅ Connected! Found {len(projects)} project(s):", THEME["success"])
        for p in projects[:10]:
            self._log_test(f"   • {getattr(p, 'name', str(p))}", THEME["text"])

    def _on_test_err(self, err):
        self._conn_badge.setText("○ Disconnected")
        self._conn_badge.setStyleSheet(f"color:{THEME['error']};font-size:11px;")
        self._log_test(f"❌ {err}", THEME["error"])

    def _log_test(self, msg: str, color: str):
        self._test_log.append(f'<span style="color:{color};">{msg}</span>')
        self._test_log.moveCursor(QTextCursor.MoveOperation.End)

    def _save_settings(self):
        SETTINGS.set("langsmith_api_key",  self._api_key.text().strip())
        SETTINGS.set("langsmith_project",  self._project.text().strip())
        SETTINGS.set("langsmith_endpoint", self._endpoint.text().strip())
        SETTINGS.save()
        self._log_test("💾 Settings saved.", THEME["success"])

    def _toggle_tracing(self, checked: bool):
        SETTINGS.set("langchain_tracing", checked)
        SETTINGS.save()
        configure_langsmith(checked)
        state = "enabled" if checked else "disabled"
        self._log_test(f"🔍 LangSmith tracing {state}.", THEME["accent2"] if checked else THEME["text3"])

    def _open_url(self, url: str):
        import webbrowser
        webbrowser.open(url)

    # ── Actions: Runs ─────────────────────────────────────────────────────────

    def _load_runs(self):
        project = self._runs_project.text().strip() or SETTINGS.get("langsmith_project")
        limit   = self._runs_limit.currentData() or 25
        self._runs_progress.setVisible(True)
        self._runs_status.setText("Loading…")
        self._run_ids.clear()

        def _fetch():
            client = _make_client()
            return list(client.list_runs(project_name=project, limit=limit))

        w = _LSWorker(_fetch)
        w.result.connect(self._populate_runs)
        w.error.connect(lambda e: (
            self._runs_status.setText(f"Error: {e}"),
            self._runs_progress.setVisible(False),
        ))
        w.start()
        self._worker = w

    def _populate_runs(self, runs: list):
        self._runs_progress.setVisible(False)
        self._run_ids = [r.id for r in runs]
        self._run_objects = runs
        t = self._runs_table
        t.setRowCount(0)

        for r in runs:
            row = t.rowCount()
            t.insertRow(row)
            ts       = str(getattr(r, "start_time", ""))[:16]
            name     = str(getattr(r, "name", "") or "")[:40]
            rtype    = str(getattr(r, "run_type", "") or "")
            status   = str(getattr(r, "status",   "") or "")
            lat_s    = getattr(r, "latency", None)
            lat      = f"{lat_s:.2f}s" if lat_s else "–"
            tokens   = str(getattr(r, "total_tokens", "") or "–")

            for col, val in enumerate([ts, name, rtype, status, lat, tokens]):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(
                    THEME["success"] if status == "success" else
                    THEME["error"]   if status == "error"   else
                    THEME["text"]
                ))
                t.setItem(row, col, item)

        self._runs_status.setText(f"{len(runs)} runs loaded from '{self._runs_project.text()}'.")

    def _on_run_select(self, row, *_):
        if row < 0 or row >= len(self._run_objects):
            return
        r = self._run_objects[row]
        parts = []
        parts.append(f"<b>ID:</b> {r.id}")
        parts.append(f"<b>Name:</b> {r.name}  |  <b>Type:</b> {r.run_type}  |  <b>Status:</b> {r.status}")

        inp = getattr(r, "inputs", {}) or {}
        out = getattr(r, "outputs", {}) or {}
        err = getattr(r, "error", "") or ""

        parts.append(f"<br><b>Inputs:</b><pre>{json.dumps(inp, indent=2)[:1200]}</pre>")
        if out:
            parts.append(f"<b>Outputs:</b><pre>{json.dumps(out, indent=2)[:1200]}</pre>")
        if err:
            parts.append(f"<b style='color:{THEME['error']};'>Error:</b> {err[:600]}")

        self._run_detail.setHtml("<br>".join(parts))

    # ── Actions: Datasets ─────────────────────────────────────────────────────

    def _load_datasets(self):
        self._ds_progress.setVisible(True)
        self._ds_status.setText("Loading datasets…")

        def _fetch():
            client = _make_client()
            return list(client.list_datasets(limit=50))

        w = _LSWorker(_fetch)
        w.result.connect(self._populate_datasets)
        w.error.connect(lambda e: (
            self._ds_status.setText(f"Error: {e}"),
            self._ds_progress.setVisible(False),
        ))
        w.start()
        self._worker = w

    def _populate_datasets(self, datasets: list):
        self._ds_progress.setVisible(False)
        self._ds_list.clear()
        self._dataset_ids = []
        for d in datasets:
            name = getattr(d, "name", str(d))
            desc = getattr(d, "description", "") or ""
            item = QListWidgetItem(f"{name}\n  {desc[:60]}")
            self._ds_list.addItem(item)
            self._dataset_ids.append(d.id)
        self._ds_status.setText(f"{len(datasets)} datasets loaded.")

    def _on_dataset_select(self, cur, _):
        if not cur:
            return
        idx = self._ds_list.row(cur)
        if idx < 0 or idx >= len(self._dataset_ids):
            return
        dataset_id = self._dataset_ids[idx]

        def _fetch():
            client = _make_client()
            return list(client.list_examples(dataset_id=dataset_id, limit=50))

        w = _LSWorker(_fetch)
        w.result.connect(self._populate_examples)
        w.start()
        self._worker = w

    def _populate_examples(self, examples: list):
        self._example_ids = [e.id for e in examples]
        t = self._ex_table
        t.setRowCount(0)
        for i, e in enumerate(examples):
            t.insertRow(i)
            inp = json.dumps(getattr(e, "inputs", {}) or {})[:80]
            out = json.dumps(getattr(e, "outputs", {}) or {})[:80]
            t.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            t.setItem(i, 1, QTableWidgetItem(inp))
            t.setItem(i, 2, QTableWidgetItem(out))

    def _run_evaluation(self):
        idx = self._ds_list.currentRow()
        if idx < 0 or idx >= len(self._dataset_ids):
            QMessageBox.warning(self, "No dataset", "Select a dataset first.")
            return
        model = self._eval_model_input.text().strip() or SETTINGS.get("default_model") or "llama3"
        dataset_id = self._dataset_ids[idx]
        self._eval_log.clear()
        self._eval_log.append(f'<span style="color:{THEME["accent2"]};">▶ Starting evaluation on dataset {str(dataset_id)[:8]}… model={model}</span>')

        def _run():
            from langsmith import Client
            from langsmith.evaluation import evaluate
            from langchain_ollama import ChatOllama
            from langchain_core.messages import HumanMessage

            client  = _make_client()
            llm     = ChatOllama(model=model, base_url=SETTINGS.get("ollama_host"))

            def _predict(inputs: dict) -> dict:
                q = str(list(inputs.values())[0]) if inputs else ""
                r = llm.invoke([HumanMessage(content=q)])
                return {"output": r.content}

            results = evaluate(
                _predict,
                data=dataset_id,
                client=client,
                experiment_prefix="nexus-eval",
            )
            return list(results)

        w = _LSWorker(_run)
        w.result.connect(self._on_eval_done)
        w.error.connect(lambda e: self._eval_log.append(
            f'<span style="color:{THEME["error"]};">❌ {e}</span>'
        ))
        w.start()
        self._worker = w

    def _on_eval_done(self, results: list):
        self._eval_log.append(
            f'<span style="color:{THEME["success"]};">✅ Evaluation complete. {len(results)} results.</span>'
        )
        for r in results[:20]:
            self._eval_log.append(
                f'<span style="color:{THEME["text2"]};">  • {r}</span>'
            )

    # ── Tab 4: Bridge Utilities ────────────────────────────────────────────────

    def _build_bridge_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        # Prompt Puller Section
        prompt_group = QGroupBox("Prompt Hub Puller")
        pl = QVBoxLayout(prompt_group)
        
        pr1 = QHBoxLayout()
        pr1.addWidget(QLabel("Prompt Name:"))
        self._bridge_prompt_name = QLineEdit("kingseno49/system_prompt:staging")
        pr1.addWidget(self._bridge_prompt_name)
        pl.addLayout(pr1)

        pr2 = QHBoxLayout()
        pr2.addWidget(QLabel("Output JSON:"))
        self._bridge_prompt_out = QLineEdit("prompt.json")
        pr2.addWidget(self._bridge_prompt_out)
        
        btn_pull = QPushButton("⬇ Pull Prompt")
        btn_pull.setObjectName("primary")
        btn_pull.clicked.connect(self._pull_prompt_action)
        pr2.addWidget(btn_pull)
        pl.addLayout(pr2)

        self._bridge_prompt_log = QTextEdit()
        self._bridge_prompt_log.setReadOnly(True)
        self._bridge_prompt_log.setMaximumHeight(120)
        self._bridge_prompt_log.setStyleSheet(
            f"background:#08080e;color:{THEME['text']};font-size:12px;border-radius:4px;"
        )
        pl.addWidget(self._bridge_prompt_log)
        lay.addWidget(prompt_group)

        # Agent Tester Section
        agent_group = QGroupBox("LangGraph Agent Tester")
        al = QVBoxLayout(agent_group)

        ar1 = QHBoxLayout()
        ar1.addWidget(QLabel("Test Input:"))
        self._bridge_agent_input = QLineEdit("Hello LangGraph!")
        ar1.addWidget(self._bridge_agent_input)

        btn_agent = QPushButton("▶ Run Agent")
        btn_agent.setObjectName("primary")
        btn_agent.clicked.connect(self._run_agent_action)
        ar1.addWidget(btn_agent)
        al.addLayout(ar1)

        self._bridge_agent_log = QTextEdit()
        self._bridge_agent_log.setReadOnly(True)
        self._bridge_agent_log.setStyleSheet(
            f"background:#08080e;color:{THEME['text']};font-size:12px;border-radius:4px;"
        )
        al.addWidget(self._bridge_agent_log)
        lay.addWidget(agent_group)

        return w

    def _pull_prompt_action(self):
        prompt_name = self._bridge_prompt_name.text().strip()
        out_file = self._bridge_prompt_out.text().strip()
        
        if not prompt_name:
            return

        self._bridge_prompt_log.clear()
        self._bridge_prompt_log.append(f'<span style="color:{THEME["text2"]};">⬇ Pulling prompt {prompt_name}...</span>')

        def _run_pull():
            import sys
            import os
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)
            from scripts.langsmith_pull import pull_langsmith_prompt
            
            # Using the module function directly
            return pull_langsmith_prompt(prompt_name, out_file)

        w = _LSWorker(_run_pull)
        w.result.connect(self._on_prompt_pulled)
        w.error.connect(lambda e: self._bridge_prompt_log.append(f'<span style="color:{THEME["error"]};">❌ {e}</span>'))
        w.start()
        self._worker = w

    def _on_prompt_pulled(self, prompt_obj):
        if not prompt_obj:
            self._bridge_prompt_log.append(f'<span style="color:{THEME["error"]};">❌ Failed to pull prompt or it returned empty.</span>')
            return
        
        out_file = self._bridge_prompt_out.text().strip()
        self._bridge_prompt_log.append(f'<span style="color:{THEME["success"]};">✅ Prompt pulled successfully and saved to {out_file}</span>')
        try:
            import json
            from langchain_core.load import dumpd
            self._bridge_prompt_log.append(f"<pre>{json.dumps(dumpd(prompt_obj), indent=2)[:500]}...</pre>")
        except Exception:
            self._bridge_prompt_log.append(f"Object: {str(prompt_obj)[:300]}...")

    def _run_agent_action(self):
        input_text = self._bridge_agent_input.text().strip()
        if not input_text:
            return

        self._bridge_agent_log.clear()
        self._bridge_agent_log.append(f'<span style="color:{THEME["text2"]};">▶ Running graph with input: "{input_text}"...</span>')

        def _run_graph():
            import sys
            import os
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)
            from scripts.langgraph_agent import run_agent
            
            return run_agent(input_text)

        w = _LSWorker(_run_graph)
        w.result.connect(self._on_agent_done)
        w.error.connect(lambda e: self._bridge_agent_log.append(f'<span style="color:{THEME["error"]};">❌ {e}</span>'))
        w.start()
        self._worker = w

    def _on_agent_done(self, result):
        if not result:
            self._bridge_agent_log.append(f'<span style="color:{THEME["error"]};">❌ Agent returned empty result.</span>')
            return
            
        self._bridge_agent_log.append(f'<span style="color:{THEME["success"]};">✅ Agent executed successfully.</span>')
        output = result.get("output", str(result))
        self._bridge_agent_log.append(f'<b style="color:{THEME["accent2"]};">Response:</b><br/>{output}')

