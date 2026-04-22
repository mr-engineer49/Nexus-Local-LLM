
# ─────────────────────────────────────────────
#  AGENT PANEL  (Manus-like ReAct autonomous agent)
# ─────────────────────────────────────────────

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
        if not HAS_REQUESTS:
            self.feed_line("⚠️  requests not installed. Run: pip install requests","error"); return

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

    def feed_line(self, text, level="info"):
        color = {"info":THEME["text"],"error":THEME["error"],"success":THEME["success"]}.get(level,THEME["text"])
        self.feed.append(f'<p style="color:{color};">{text}</p>')


# ─────────────────────────────────────────────
#  WORKFLOW PANEL  (Visual node automation)
# ─────────────────────────────────────────────

NODE_W, NODE_H = 160, 70

class FlowNode(QGraphicsRectItem):
    TYPES = {
        "trigger":  {"color":"#0e3a50","border":"#1a7fa0","emoji":"🔵","label":"Trigger"},
        "ai":       {"color":"#1e1040","border":"#6e56cf","emoji":"🤖","label":"AI Task"},
        "git":      {"color":"#0e2a1e","border":"#3ecf8e","emoji":"📁","label":"Git"},
        "terminal": {"color":"#2a1e0a","border":"#f7b731","emoji":"💻","label":"Terminal"},
        "condition":{"color":"#2a0e0e","border":"#f04452","emoji":"🔀","label":"Condition"},
        "notify":   {"color":"#0e0e2a","border":"#9d7ff5","emoji":"🔔","label":"Notify"},
    }

    def __init__(self, node_type, x=0, y=0, config=None):
        super().__init__(0, 0, NODE_W, NODE_H)
        self.node_type = node_type
        self.config = config or {}
        self._edges_out: list = []
        self._edges_in:  list = []
        info = self.TYPES.get(node_type, self.TYPES["terminal"])
        self.setBrush(QBrush(QColor(info["color"])))
        pen = QPen(QColor(info["border"]), 1.5)
        self.setPen(pen)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setPos(x, y)
        self.setZValue(1)
        # Title
        title = QGraphicsTextItem(f"{info['emoji']} {info['label']}", self)
        title.setDefaultTextColor(QColor(THEME["text"]))
        title.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        title.setPos(8, 6)
        # Config summary
        self._cfg_item = QGraphicsTextItem("(click to configure)", self)
        self._cfg_item.setDefaultTextColor(QColor(THEME["text2"]))
        self._cfg_item.setFont(QFont("Consolas", 8))
        self._cfg_item.setPos(8, 32)
        self._cfg_item.setTextWidth(NODE_W - 16)
        # Ports
        r = 8
        self._in_port  = QGraphicsEllipseItem(-r//2, NODE_H//2-r//2, r, r, self)
        self._in_port.setBrush(QBrush(QColor(THEME["success"]))); self._in_port.setPen(QPen(Qt.PenStyle.NoPen))
        self._out_port = QGraphicsEllipseItem(NODE_W-r//2, NODE_H//2-r//2, r, r, self)
        self._out_port.setBrush(QBrush(QColor(THEME["accent2"]))); self._out_port.setPen(QPen(Qt.PenStyle.NoPen))
        self.update_config_display()

    def update_config_display(self):
        if self.config:
            vals = list(self.config.values())
            s = str(vals[0])[:30] + ("…" if len(str(vals[0])) > 30 else "")
            self._cfg_item.setPlainText(s)
        else:
            self._cfg_item.setPlainText("(click to configure)")

    def in_port_scene_pos(self):
        return self.scenePos() + QPointF(0, NODE_H / 2)

    def out_port_scene_pos(self):
        return self.scenePos() + QPointF(NODE_W, NODE_H / 2)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for e in self._edges_out + self._edges_in:
                e.update_path()
        return super().itemChange(change, value)

    def to_dict(self):
        return {"type":self.node_type, "x":self.pos().x(), "y":self.pos().y(), "config":self.config}


class FlowEdge(QGraphicsPathItem):
    def __init__(self, src: FlowNode, dst: FlowNode):
        super().__init__()
        self.src = src; self.dst = dst
        src._edges_out.append(self); dst._edges_in.append(self)
        pen = QPen(QColor(THEME["accent"]), 2)
        pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen); self.setZValue(0)
        self.update_path()

    def update_path(self):
        s = self.src.out_port_scene_pos()
        d = self.dst.in_port_scene_pos()
        path = QPainterPath(s)
        mx = (s.x() + d.x()) / 2
        path.cubicTo(QPointF(mx, s.y()), QPointF(mx, d.y()), d)
        self.setPath(path)

    def remove(self):
        if self in self.src._edges_out: self.src._edges_out.remove(self)
        if self in self.dst._edges_in:  self.dst._edges_in.remove(self)
        sc = self.scene()
        if sc: sc.removeItem(self)


class NodeCanvas(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self._nodes: List[FlowNode] = []
        self._pending_src: Optional[FlowNode] = None

    def add_node(self, node_type, x=50, y=50):
        x += len(self._nodes) * 30 % 200
        y += len(self._nodes) * 20 % 150
        node = FlowNode(node_type, x, y)
        self.addItem(node)
        self._nodes.append(node)
        return node

    def connect_nodes(self, src: FlowNode, dst: FlowNode):
        edge = FlowEdge(src, dst)
        self.addItem(edge)

    def mouseDoubleClickEvent(self, event):
        items = self.items(event.scenePos())
        for item in items:
            if isinstance(item, FlowNode):
                self._configure_node(item); return
            # port click for connection
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        items = self.items(event.scenePos())
        clicked_node = None
        for item in items:
            if isinstance(item, FlowNode):
                clicked_node = item; break
        if event.button() == Qt.MouseButton.RightButton and clicked_node:
            # right-click = start/complete connection
            if self._pending_src is None:
                self._pending_src = clicked_node
            else:
                if self._pending_src is not clicked_node:
                    self.connect_nodes(self._pending_src, clicked_node)
                self._pending_src = None
            return
        super().mousePressEvent(event)

    def _configure_node(self, node: FlowNode):
        ntype = node.node_type
        fields = {
            "trigger":  [("type","manual|interval|file"),("interval_sec","30"),("watch_path","")],
            "ai":       [("model",""), ("prompt","")],
            "git":      [("cmd","git pull"), ("repo","")],
            "terminal": [("cmd",""), ("cwd","")],
            "condition":[("pattern",""), ("on_true","continue"),("on_false","stop")],
            "notify":   [("message",""), ("level","info")],
        }
        for key, default in fields.get(ntype, []):
            cur = node.config.get(key, default)
            val, ok = QInputDialog.getText(None, f"Configure {ntype}", f"{key}:", text=cur)
            if ok: node.config[key] = val
        node.update_config_display()

    def delete_selected(self):
        for item in self.selectedItems():
            if isinstance(item, FlowNode):
                for e in item._edges_out[:]+item._edges_in[:]: e.remove()
                self._nodes.remove(item); self.removeItem(item)
            elif isinstance(item, FlowEdge):
                item.remove()

    def to_dict(self):
        # Build adjacency: map node to index
        idx = {n:i for i,n in enumerate(self._nodes)}
        edges = []
        for n in self._nodes:
            for e in n._edges_out:
                edges.append({"from":idx[e.src],"to":idx[e.dst]})
        return {"nodes":[n.to_dict() for n in self._nodes], "edges":edges}

    def from_dict(self, data):
        self.clear(); self._nodes = []
        for nd in data.get("nodes",[]):
            self.add_node(nd["type"], nd.get("x",50), nd.get("y",50))
            self._nodes[-1].config = nd.get("config",{})
            self._nodes[-1].update_config_display()
        for ed in data.get("edges",[]):
            src = self._nodes[ed["from"]]; dst = self._nodes[ed["to"]]
            self.connect_nodes(src, dst)

    def run_flow(self, log_fn):
        """Execute nodes in topological order."""
        # Simple: iterate nodes in order, execute each
        for node in self._nodes:
            ntype = node.node_type
            cfg   = node.config
            log_fn(f"▶ Running: {FlowNode.TYPES[ntype]['emoji']} {ntype}", "cmd")
            try:
                if ntype == "terminal":
                    r = subprocess.run(cfg.get("cmd","echo ok"),
                        cwd=cfg.get("cwd",".") or ".", shell=True,
                        capture_output=True, text=True, timeout=30,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0)
                    out = (r.stdout+r.stderr).strip()
                    log_fn(out[:300] or "[done]","info")
                elif ntype == "git":
                    r = subprocess.run(cfg.get("cmd","git status"),
                        cwd=cfg.get("repo",".") or ".", shell=True,
                        capture_output=True, text=True, timeout=30,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0)
                    log_fn((r.stdout+r.stderr).strip()[:200] or "[done]","info")
                elif ntype == "notify":
                    log_fn(f"🔔 {cfg.get('message','...')}",cfg.get("level","info"))
                elif ntype == "ai":
                    log_fn(f"🤖 AI task queued (run async to see output)","warn")
                else:
                    log_fn(f"  node type '{ntype}' executed","info")
            except Exception as e:
                log_fn(f"[error] {e}","error")


class WorkflowPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(16,16,16,16); root.setSpacing(10)

        hdr = QHBoxLayout()
        t = QLabel("Automation Flows")
        t.setStyleSheet(f"font-size:18px;font-weight:bold;color:{THEME['text']};")
        hdr.addWidget(t); hdr.addStretch()
        root.addLayout(hdr)

        desc = QLabel("Visual node-based automation. Right-click nodes to connect them. Double-click to configure.")
        desc.setStyleSheet(f"color:{THEME['text2']};font-size:12px;")
        root.addWidget(desc)

        # toolbar
        tb = QHBoxLayout()
        node_types = [("🔵 Trigger","trigger"),("🤖 AI","ai"),("📁 Git","git"),
                      ("💻 Terminal","terminal"),("🔀 Condition","condition"),("🔔 Notify","notify")]
        for label, nt in node_types:
            b = QPushButton(label); b.setMaximumHeight(28)
            b.setStyleSheet("font-size:11px;padding:2px 8px;")
            b.clicked.connect(lambda _, t=nt: self._add_node(t))
            tb.addWidget(b)
        tb.addStretch()
        btn_del = QPushButton("🗑 Delete"); btn_del.setObjectName("danger")
        btn_del.clicked.connect(lambda: self.canvas.delete_selected())
        btn_clear = QPushButton("Clear All"); btn_clear.clicked.connect(self._clear_all)
        btn_save  = QPushButton("💾 Save"); btn_save.clicked.connect(self._save_flow)
        btn_load  = QPushButton("📂 Load"); btn_load.clicked.connect(self._load_flow)
        btn_run   = QPushButton("▶ Run Flow"); btn_run.setObjectName("success")
        btn_run.clicked.connect(self._run_flow)
        for b in [btn_del, btn_clear, btn_save, btn_load, btn_run]:
            tb.addWidget(b)
        root.addLayout(tb)

        # templates row
        tpl_row = QHBoxLayout()
        tpl_row.addWidget(QLabel("Templates:"))
        templates = [("Auto-Commit","auto_commit"),("AI Code Review","ai_review"),("Git+Notify","git_notify")]
        for name, tpl in templates:
            b = QPushButton(name); b.setMaximumHeight(24)
            b.setStyleSheet(f"font-size:10px;padding:1px 6px;color:{THEME['accent2']};")
            b.clicked.connect(lambda _, t=tpl: self._load_template(t))
            tpl_row.addWidget(b)
        tpl_row.addStretch()
        root.addLayout(tpl_row)

        # split: canvas + log
        split = QSplitter(Qt.Orientation.Vertical)

        self.canvas = NodeCanvas()
        self.canvas.setSceneRect(-50,-50,2000,1000)
        self.view = QGraphicsView(self.canvas)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setMinimumHeight(300)
        split.addWidget(self.view)

        self.log = LogView(); self.log.setMaximumHeight(160)
        split.addWidget(self.log)
        split.setSizes([400, 160])
        root.addWidget(split, 1)

        hints = QLabel(
            "💡 Right-click src node → right-click dst node to connect  |  "
            "Double-click node to configure  |  Click canvas + Del to remove selected")
        hints.setStyleSheet(f"color:{THEME['text3']};font-size:10px;")
        root.addWidget(hints)

    def _add_node(self, node_type):
        cx = self.view.viewport().width()//2
        cy = self.view.viewport().height()//2
        sp = self.view.mapToScene(cx, cy)
        self.canvas.add_node(node_type, sp.x()-NODE_W//2, sp.y()-NODE_H//2)
        self.log.append_line(f"Added '{node_type}' node","info")

    def _clear_all(self):
        self.canvas.clear(); self.canvas._nodes = []
        self.log.append_line("Canvas cleared","system")

    def _save_flow(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Flow", str(Path.home()), "JSON (*.json)")
        if path:
            Path(path).write_text(json.dumps(self.canvas.to_dict(), indent=2))
            self.log.append_line(f"Saved to {path}","success")

    def _load_flow(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Flow", str(Path.home()), "JSON (*.json)")
        if path:
            data = json.loads(Path(path).read_text())
            self.canvas.from_dict(data)
            self.log.append_line(f"Loaded {path}","success")

    def _run_flow(self):
        self.log.append_line("=== Running workflow ===","cmd")
        self.canvas.run_flow(self.log.append_line)
        self.log.append_line("=== Workflow complete ===","success")

    def _load_template(self, tpl):
        templates = {
            "auto_commit": {"nodes":[
                {"type":"trigger","x":50,"y":200,"config":{"type":"manual"}},
                {"type":"git","x":280,"y":200,"config":{"cmd":"git add -A","repo":"."}},
                {"type":"git","x":510,"y":200,"config":{"cmd":"git commit -m 'auto: update'","repo":"."}},
                {"type":"git","x":740,"y":200,"config":{"cmd":"git push","repo":"."}},
                {"type":"notify","x":970,"y":200,"config":{"message":"Push complete!","level":"success"}},
            ],"edges":[{"from":0,"to":1},{"from":1,"to":2},{"from":2,"to":3},{"from":3,"to":4}]},
            "ai_review": {"nodes":[
                {"type":"trigger","x":50,"y":200,"config":{"type":"manual"}},
                {"type":"terminal","x":280,"y":200,"config":{"cmd":"git diff HEAD~1","cwd":"."}},
                {"type":"ai","x":510,"y":200,"config":{"model":"","prompt":"Review this code diff and identify issues:"}},
                {"type":"notify","x":740,"y":200,"config":{"message":"Review complete","level":"info"}},
            ],"edges":[{"from":0,"to":1},{"from":1,"to":2},{"from":2,"to":3}]},
            "git_notify": {"nodes":[
                {"type":"trigger","x":50,"y":200,"config":{"type":"manual"}},
                {"type":"git","x":280,"y":200,"config":{"cmd":"git pull","repo":"."}},
                {"type":"notify","x":510,"y":200,"config":{"message":"Pull done!","level":"success"}},
            ],"edges":[{"from":0,"to":1},{"from":1,"to":2}]},
        }
        if tpl in templates:
            self.canvas.from_dict(templates[tpl])
            self.log.append_line(f"Loaded template: {tpl}","success")


# ─────────────────────────────────────────────
#  TERMINAL PANEL  (unchanged core + improvements)
# ─────────────────────────────────────────────

class TerminalPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._worker  = None
        self._history = []
        self._hist_idx= -1
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(16,16,16,16); root.setSpacing(10)

        hdr = QHBoxLayout()
        t = QLabel("Integrated Terminal")
        t.setStyleSheet(f"font-size:18px;font-weight:bold;color:{THEME['text']};")
        hdr.addWidget(t); hdr.addStretch()
        self.shell_combo = QComboBox()
        for s in self._detect_shells(): self.shell_combo.addItem(s["label"], s["type"])
        hdr.addWidget(self.shell_combo)
        btn_clear = QPushButton("Clear"); btn_clear.clicked.connect(lambda: self.output.clear_log())
        hdr.addWidget(btn_clear)
        root.addLayout(hdr)

        wd_row = QHBoxLayout()
        wd_row.addWidget(QLabel("Working dir:"))
        self.cwd_input = QLineEdit(str(Path.home()))
        btn_cwd = QPushButton("Browse"); btn_cwd.clicked.connect(self._browse_cwd)
        wd_row.addWidget(self.cwd_input); wd_row.addWidget(btn_cwd)
        root.addLayout(wd_row)

        self.output = LogView(); self.output.append_line("NEXUS Terminal ready.","system")
        root.addWidget(self.output, 1)

        quick = QHBoxLayout()
        for label, cmd in [("python --version","python --version"),("node --version","node --version"),
                           ("git --version","git --version"),("pip list","pip list"),
                           ("dir" if sys.platform=="win32" else "ls","dir" if sys.platform=="win32" else "ls"),
                           ("ollama list","ollama list")]:
            b = QPushButton(label); b.setFixedHeight(26)
            b.setStyleSheet("font-size:11px;padding:2px 8px;")
            b.clicked.connect(lambda _, c=cmd: self._run(c))
            quick.addWidget(b)
        quick.addStretch()
        root.addLayout(quick)

        inp_row = QHBoxLayout()
        lbl = QLabel("$"); lbl.setStyleSheet(f"color:{THEME['accent2']};font-weight:bold;")
        self.cmd_input = QLineEdit(); self.cmd_input.setPlaceholderText("Enter command…")
        self.cmd_input.returnPressed.connect(self._on_enter)
        self.cmd_input.installEventFilter(self)
        self.run_btn  = QPushButton("▶  Run"); self.run_btn.setObjectName("primary"); self.run_btn.clicked.connect(self._on_enter)
        self.stop_btn = QPushButton("⏹"); self.stop_btn.setFixedWidth(36); self.stop_btn.clicked.connect(self._stop)
        inp_row.addWidget(lbl); inp_row.addWidget(self.cmd_input)
        inp_row.addWidget(self.run_btn); inp_row.addWidget(self.stop_btn)
        root.addLayout(inp_row)

    def eventFilter(self, obj, event):
        if obj is self.cmd_input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:   self._hist_nav(-1); return True
            if event.key() == Qt.Key.Key_Down:  self._hist_nav(1);  return True
        return super().eventFilter(obj, event)

    def _hist_nav(self, d):
        if not self._history: return
        self._hist_idx = max(0, min(len(self._history)-1, self._hist_idx+d))
        self.cmd_input.setText(self._history[self._hist_idx])

    def _detect_shells(self):
        shells = [{"label":"CMD","type":"cmd"}]
        if shutil.which("powershell"): shells.append({"label":"PowerShell","type":"powershell"})
        if any(Path(p).exists() for p in [r"C:\Program Files\Git\bin\bash.exe"] if p):
            shells.append({"label":"Git Bash","type":"git_bash"})
        return shells

    def _browse_cwd(self):
        d = QFileDialog.getExistingDirectory(self,"Select working directory")
        if d: self.cwd_input.setText(d)

    def _on_enter(self):
        cmd = self.cmd_input.text().strip()
        if not cmd: return
        self._history.append(cmd); self._hist_idx = len(self._history)
        self.cmd_input.clear(); self._run(cmd)

    def _run(self, cmd):
        cwd = self.cwd_input.text().strip() or None
        shell_type = self.shell_combo.currentData() or "cmd"
        self.output.append_line(f"$ {cmd}","cmd")
        if self._worker and self._worker.isRunning(): self._worker.stop()
        self._worker = CommandWorker(cmd, cwd=cwd, shell_type=shell_type)
        self._worker.output.connect(lambda l: self.output.append_line(l))
        self._worker.done.connect(lambda c: self.output.append_line(
            f"[exit {c}]","success" if c==0 else "error"))
        self._worker.start()

    def _stop(self):
        if self._worker: self._worker.stop(); self.output.append_line("Terminated.","warn")


# ─────────────────────────────────────────────
#  SYSTEM MONITOR
# ─────────────────────────────────────────────

class SystemPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._timer = QTimer(self); self._timer.timeout.connect(self._update)
        self._timer.start(2000); self._update()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(16,16,16,16); root.setSpacing(12)
        t = QLabel("System Resources")
        t.setStyleSheet(f"font-size:18px;font-weight:bold;color:{THEME['text']};")
        root.addWidget(t)
        self._bars = {}; self._labels = {}
        for name, key in [("CPU","cpu"),("RAM","ram"),("Disk","disk"),("Swap","swap")]:
            box = QGroupBox(name); bl = QVBoxLayout(box)
            bar = QProgressBar(); bar.setRange(0,100); bar.setTextVisible(False)
            lbl = QLabel("–"); lbl.setStyleSheet(f"color:{THEME['text2']};font-size:12px;")
            bl.addWidget(bar); bl.addWidget(lbl)
            self._bars[key]=bar; self._labels[key]=lbl
            root.addWidget(box)
        proc_box = QGroupBox("Top Processes (CPU)"); pl = QVBoxLayout(proc_box)
        self.proc_list = QListWidget(); self.proc_list.setMaximumHeight(170)
        pl.addWidget(self.proc_list); root.addWidget(proc_box)
        net_box = QGroupBox("Network I/O"); nl = QVBoxLayout(net_box)
        self.net_lbl = QLabel("–"); self.net_lbl.setStyleSheet(f"color:{THEME['text2']};font-size:12px;")
        nl.addWidget(self.net_lbl); root.addWidget(net_box)
        btn = QPushButton("⟳ Refresh now"); btn.clicked.connect(self._update); root.addWidget(btn)
        root.addStretch()
        self._prev_net = None

    def _update(self):
        if not HAS_PSUTIL: return
        cpu  = psutil.cpu_percent(interval=None)
        vm   = psutil.virtual_memory()
        disk = psutil.disk_usage("/" if sys.platform!="win32" else "C:\\")
        swap = psutil.swap_memory()
        self._bars["cpu"].setValue(int(cpu))
        self._labels["cpu"].setText(f"{cpu:.1f}%  —  {psutil.cpu_count()} cores")
        rp = int(vm.percent); self._bars["ram"].setValue(rp)
        self._labels["ram"].setText(f"{rp}%  —  {vm.used//1024**3}/{vm.total//1024**3} GB")
        dp = int(disk.percent); self._bars["disk"].setValue(dp)
        self._labels["disk"].setText(f"{dp}%  —  {disk.used//1024**3}/{disk.total//1024**3} GB")
        sp = int(swap.percent); self._bars["swap"].setValue(sp)
        self._labels["swap"].setText(f"{sp}%")
        for key, bar in self._bars.items():
            v = bar.value()
            c = THEME["success"] if v<60 else (THEME["warning"] if v<85 else THEME["error"])
            bar.setStyleSheet(f"QProgressBar::chunk{{background:{c};border-radius:4px;}}")
        try:
            net = psutil.net_io_counters()
            if self._prev_net:
                s = net.bytes_sent-self._prev_net.bytes_sent
                r = net.bytes_recv-self._prev_net.bytes_recv
                self.net_lbl.setText(f"↑ {s//1024} KB/s  ↓ {r//1024} KB/s  "
                                     f"(total sent {net.bytes_sent//1024**2} MB / recv {net.bytes_recv//1024**2} MB)")
            self._prev_net = net
        except Exception: pass
        try:
            procs = sorted(psutil.process_iter(["pid","name","cpu_percent","memory_percent"]),
                           key=lambda p: p.info["cpu_percent"] or 0, reverse=True)[:12]
            self.proc_list.clear()
            for p in procs:
                self.proc_list.addItem(
                    f"  {p.info['name']:<26} CPU:{p.info['cpu_percent']:>5.1f}%  "
                    f"RAM:{p.info['memory_percent']:.1f}%")
        except Exception: pass


# ─────────────────────────────────────────────
#  SETTINGS PANEL  (persistent)
# ─────────────────────────────────────────────

class SettingsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(16,16,16,16); root.setSpacing(14)
        t = QLabel("Settings")
        t.setStyleSheet(f"font-size:18px;font-weight:bold;color:{THEME['text']};")
        root.addWidget(t)

        # Ollama
        ol = QGroupBox("Ollama"); oll = QVBoxLayout(ol)
        r1 = QHBoxLayout(); r1.addWidget(QLabel("Host:"))
        self.host_input = QLineEdit(SETTINGS.get("ollama_host",""))
        r1.addWidget(self.host_input); oll.addLayout(r1)
        r2 = QHBoxLayout(); r2.addWidget(QLabel("Threads:"))
        self.threads_spin = QSpinBox(); self.threads_spin.setRange(1,64)
        self.threads_spin.setValue(SETTINGS.get("ollama_threads",4))
        r2.addWidget(self.threads_spin); r2.addStretch(); oll.addLayout(r2)
        r3 = QHBoxLayout(); r3.addWidget(QLabel("GPU layers (0=CPU):"))
        self.gpu_spin = QSpinBox(); self.gpu_spin.setRange(0,128)
        self.gpu_spin.setValue(SETTINGS.get("gpu_layers",0))
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
        self.clone_dir = QLineEdit(SETTINGS.get("clone_dir",""))
        btn_br = QPushButton("Browse"); btn_br.clicked.connect(self._browse_clone)
        rg.addWidget(self.clone_dir); rg.addWidget(btn_br); gitl.addLayout(rg)
        root.addWidget(gitb)

        # Agent
        ag = QGroupBox("Agent"); agl = QVBoxLayout(ag)
        ra = QHBoxLayout(); ra.addWidget(QLabel("Max steps:"))
        self.agent_steps = QSpinBox(); self.agent_steps.setRange(1,50)
        self.agent_steps.setValue(SETTINGS.get("agent_max_steps",12))
        ra.addWidget(self.agent_steps); ra.addStretch(); agl.addLayout(ra)
        root.addWidget(ag)

        # App
        app = QGroupBox("Application"); apl = QVBoxLayout(app)
        self.cb_scroll = QCheckBox("Auto-scroll log output"); self.cb_scroll.setChecked(SETTINGS.get("autoscroll",True))
        self.cb_ts     = QCheckBox("Show timestamps"); self.cb_ts.setChecked(SETTINGS.get("timestamps",True))
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
        QMessageBox.information(self,"Saved","Settings saved to ~/.nexus_settings.json")


# ─────────────────────────────────────────────
#  SIDEBAR NAV BUTTON
# ─────────────────────────────────────────────

class NavButton(QPushButton):
    def __init__(self, icon, label):
        super().__init__(f"  {icon}  {label}")
        self.setCheckable(False); self.setProperty("active",False)

    def set_active(self, active: bool):
        self.setProperty("active", str(active).lower())
        self.style().unpolish(self); self.style().polish(self)


# ─────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"NEXUS v{APP_VERSION}  —  Local AI & Dev Workspace")
        self.resize(1280, 820); self.setMinimumSize(960, 640)
        self._build_ui()

    def _build_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        main_lay = QHBoxLayout(central)
        main_lay.setContentsMargins(0,0,0,0); main_lay.setSpacing(0)

        # sidebar
        sidebar = QWidget(); sidebar.setObjectName("sidebar")
        sb_lay  = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(0,0,0,0); sb_lay.setSpacing(0)

        logo = QLabel(f"  ⬡  NEXUS")
        logo.setStyleSheet(
            f"font-size:18px;font-weight:bold;color:{THEME['accent2']};"
            f"padding:18px 14px 6px 14px;letter-spacing:3px;")
        ver = QLabel(f"  v{APP_VERSION}  AI Workspace")
        ver.setStyleSheet(f"color:{THEME['text3']};font-size:9px;padding:0 14px 12px 14px;letter-spacing:1px;")
        sb_lay.addWidget(logo); sb_lay.addWidget(ver)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{THEME['border']};"); sb_lay.addWidget(sep)
        sb_lay.addSpacing(6)

        pages = [
            ("🤖","Ollama"),("🐙","GitHub"),("🔗","Agent"),
            ("⚡","Workflows"),("⌨","Terminal"),("📊","System"),("⚙","Settings"),
        ]
        panels = [
            OllamaPanel(), GitHubPanel(), AgentPanel(),
            WorkflowPanel(), TerminalPanel(), SystemPanel(), SettingsPanel(),
        ]
        # Add Git panel to sidebar after ollama
        pages.insert(1, ("📁","Git"))
        panels.insert(1, GitPanel())

        self._nav_btns = []
        self._stack    = QStackedWidget()
        for i, ((icon,label), panel) in enumerate(zip(pages, panels)):
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda _, idx=i: self._switch(idx))
            sb_lay.addWidget(btn); self._nav_btns.append(btn)
            self._stack.addWidget(panel)

        sb_lay.addStretch()
        sb_lay.addWidget(QLabel(f"  {'  ':>8}"))  # spacer

        main_lay.addWidget(sidebar); main_lay.addWidget(self._stack, 1)

        # status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._status_ollama = QLabel("⬡ Ollama: checking…")
        self._status_ollama.setStyleSheet(f"color:{THEME['text3']};font-size:11px;padding:0 8px;")
        self.status_bar.addWidget(self._status_ollama)
        self._check_ollama_status()

        self._switch(0)

    def _switch(self, idx):
        self._stack.setCurrentIndex(idx)
        for i,btn in enumerate(self._nav_btns): btn.set_active(i==idx)

    def _check_ollama_status(self):
        def _check():
            try:
                import urllib.request
                urllib.request.urlopen(f"{SETTINGS.get('ollama_host')}/api/tags", timeout=3)
                self._status_ollama.setText("⬡ Ollama: ●  online")
                self._status_ollama.setStyleSheet(f"color:{THEME['success']};font-size:11px;padding:0 8px;")
            except Exception:
                self._status_ollama.setText("⬡ Ollama: ○  offline")
                self._status_ollama.setStyleSheet(f"color:{THEME['text3']};font-size:11px;padding:0 8px;")
        import threading; threading.Thread(target=_check, daemon=True).start()
        QTimer.singleShot(10000, self._check_ollama_status)


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("NEXUS"); app.setApplicationVersion(APP_VERSION)
    app.setStyleSheet(STYLESHEET)
    for fname in ["Consolas","JetBrains Mono","Fira Code","Courier New"]:
        if fname in QFontDatabase.families():
            app.setFont(QFont(fname, 13)); break
    win = MainWindow(); win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
