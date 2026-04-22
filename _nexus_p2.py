
# ─────────────────────────────────────────────
#  LOG WIDGET  +  DIFF HIGHLIGHTER
# ─────────────────────────────────────────────

class LogView(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setObjectName("logview"); self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._colors = {
            "info":"#b0ffb0","warn":"#f7b731","error":"#f04452",
            "cmd":"#6e9fff","system":"#8888aa","success":"#3ecf8e",
            "token":"#d0d0ff",
        }

    def append_line(self, text: str, level="info"):
        color = self._colors.get(level, self._colors["info"])
        ts    = datetime.now().strftime("%H:%M:%S")
        html  = (f'<span style="color:#444466;">[{ts}]</span> '
                 f'<span style="color:{color};">{self._esc(text)}</span>')
        self.append(html)
        self.moveCursor(QTextCursor.MoveOperation.End)

    def append_token(self, tok: str):
        """Append streaming token without newline/timestamp."""
        cur = self.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cur)
        self.insertHtml(f'<span style="color:#d0d0ff;">{self._esc(tok)}</span>')
        self.moveCursor(QTextCursor.MoveOperation.End)

    def _esc(self, t):
        return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br>")

    def clear_log(self):
        self.clear(); self.append_line("— log cleared —","system")


class DiffHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text):
        fmt = QTextCharFormat()
        if text.startswith("+++") or text.startswith("---"):
            fmt.setForeground(QColor("#9d7ff5")); fmt.setFontWeight(700)
        elif text.startswith("+"):
            fmt.setForeground(QColor("#3ecf8e"))
        elif text.startswith("-"):
            fmt.setForeground(QColor("#f04452"))
        elif text.startswith("@@"):
            fmt.setForeground(QColor("#f7b731"))
        elif text.startswith("diff ") or text.startswith("index "):
            fmt.setForeground(QColor("#8888aa"))
        else:
            return
        self.setFormat(0, len(text), fmt)


# ─────────────────────────────────────────────
#  OLLAMA PANEL  (enhanced)
# ─────────────────────────────────────────────

class OllamaPanel(QWidget):
    log_signal = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self._worker = None; self._models = []; self._info_worker = None
        self._build_ui()
        self.refresh_models()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16,16,16,16); root.setSpacing(12)

        # header
        hdr = QHBoxLayout()
        t = QLabel("Ollama Models")
        t.setStyleSheet(f"font-size:18px;font-weight:bold;color:{THEME['text']};")
        hdr.addWidget(t); hdr.addStretch()
        self.status_lbl = QLabel("●  checking…")
        self.status_lbl.setStyleSheet(f"color:{THEME['text3']};font-size:11px;")
        hdr.addWidget(self.status_lbl)
        btn_ref = QPushButton("⟳  Refresh"); btn_ref.clicked.connect(self.refresh_models)
        hdr.addWidget(btn_ref)
        root.addLayout(hdr)

        # tabs
        tabs = QTabWidget()
        tabs.addTab(self._build_models_tab(), "📦  Models")
        tabs.addTab(self._build_benchmark_tab(), "⚡  Benchmark")
        root.addWidget(tabs, 1)

        # log
        self.log = LogView(); self.log.setMaximumHeight(150)
        root.addWidget(self.log)

    def _build_models_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setSpacing(10)

        # pull
        pull_box = QGroupBox("Pull Model from Hub")
        pl = QHBoxLayout(pull_box)
        self.pull_input = QLineEdit()
        self.pull_input.setPlaceholderText("llama3, mistral, phi3, gemma2, codellama, qwen2…")
        self.pull_btn = QPushButton("⬇  Pull"); self.pull_btn.setObjectName("primary")
        self.pull_btn.clicked.connect(self.pull_model)
        pl.addWidget(self.pull_input); pl.addWidget(self.pull_btn)
        lay.addWidget(pull_box)

        # list + actions
        split = QSplitter(Qt.Orientation.Horizontal)
        left = QFrame(); ll = QVBoxLayout(left); ll.setContentsMargins(0,0,0,0)
        ll.addWidget(QLabel("Local Models"))
        self.model_list = QListWidget()
        self.model_list.currentItemChanged.connect(self._on_select)
        ll.addWidget(self.model_list, 1)
        split.addWidget(left)

        right = QFrame(); rl = QVBoxLayout(right)
        rl.setContentsMargins(8,0,0,0); rl.setSpacing(8)
        rl.addWidget(QLabel("Model Info"))
        self.model_info = QLabel("Select a model")
        self.model_info.setWordWrap(True)
        self.model_info.setStyleSheet(f"color:{THEME['text2']};font-size:12px;")
        rl.addWidget(self.model_info)

        # hw
        self.hw_label = QLabel()
        self.hw_label.setWordWrap(True)
        self.hw_label.setStyleSheet(f"color:{THEME['text3']};font-size:11px;")
        rl.addWidget(self.hw_label)
        rl.addSpacing(6)

        for label, fn, oid in [
            ("💬  Chat",       self.open_chat,    "primary"),
            ("▶  Serve",      self.run_model,    "success"),
            ("🔍  Show Info",  self.show_info,    ""),
            ("⏹  Stop",       self.stop_model,   ""),
            ("🗑  Delete",     self.delete_model, "danger"),
        ]:
            b = QPushButton(label); b.setObjectName(oid) if oid else None
            b.setMinimumHeight(34); b.clicked.connect(fn); rl.addWidget(b)

        rl.addStretch()
        split.addWidget(right); split.setSizes([320,220])
        lay.addWidget(split, 1)

        self.progress = QProgressBar(); self.progress.setVisible(False)
        lay.addWidget(self.progress)
        self._detect_hw()
        return w

    def _build_benchmark_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setSpacing(10)
        top = QHBoxLayout()
        top.addWidget(QLabel("Model:"))
        self.bench_model = QComboBox(); self.bench_model.setMinimumWidth(200)
        top.addWidget(self.bench_model)
        top.addWidget(QLabel("Prompt:"))
        self.bench_prompt = QLineEdit("Explain quantum entanglement in one sentence.")
        top.addWidget(self.bench_prompt, 1)
        btn = QPushButton("⚡  Run Benchmark"); btn.setObjectName("primary")
        btn.clicked.connect(self.run_benchmark)
        top.addWidget(btn)
        lay.addLayout(top)
        self.bench_log = LogView()
        lay.addWidget(self.bench_log, 1)
        return w

    # ── actions ─────────────────────────────

    def refresh_models(self):
        self.status_lbl.setText("●  loading…")
        w = OllamaListWorker(self); w.result.connect(self._populate); w.error.connect(
            lambda e: (self.status_lbl.setText("●  error"), self.log.append_line(e,"error"))); w.start()

    def _populate(self, models):
        self._models = models
        self.model_list.clear(); self.bench_model.clear()
        for m in models:
            self.model_list.addItem(f"  {m['name']}   [{m['size']}]")
            self.bench_model.addItem(m["name"])
        self.status_lbl.setText(f"●  {len(models)} model(s)")
        self.log.append_line(f"Found {len(models)} local model(s)", "success")

    def _on_select(self, cur, _):
        if not cur: return
        idx = self.model_list.row(cur)
        if 0 <= idx < len(self._models):
            m = self._models[idx]
            self.model_info.setText(f"<b>{m['name']}</b><br>Size: {m['size']}")

    def _selected(self):
        item = self.model_list.currentItem()
        if not item: return None
        idx = self.model_list.row(item)
        return self._models[idx]["name"] if 0 <= idx < len(self._models) else None

    def pull_model(self):
        name = self.pull_input.text().strip()
        if not name: return
        self.log.append_line(f"Pulling {name}…","cmd")
        self.progress.setVisible(True); self.progress.setRange(0,0)
        self._run_cmd(f"ollama pull {name}", on_done=self._pull_done)

    def _pull_done(self, code):
        self.progress.setVisible(False)
        if code == 0:
            self.log.append_line("Pull complete.","success"); self.refresh_models()
        else:
            self.log.append_line("Pull failed.","error")

    def run_model(self):
        m = self._selected()
        if m: self.log.append_line(f"Serving {m}…","cmd"); self._run_cmd(f"ollama run {m}")

    def open_chat(self):
        m = self._selected()
        if not m: QMessageBox.information(self,"Select model","Select a model first."); return
        dlg = ChatDialog(m, SETTINGS.get("ollama_host"), self)
        dlg.exec()

    def show_info(self):
        m = self._selected()
        if not m: return
        self.log.append_line(f"Fetching info for {m}…","cmd")
        self._info_worker = OllamaModelInfoWorker(SETTINGS.get("ollama_host"), m)
        self._info_worker.result.connect(self._show_info_result)
        self._info_worker.error.connect(lambda e: self.log.append_line(e,"error"))
        self._info_worker.start()

    def _show_info_result(self, data):
        details = data.get("modelfile","")[:300] or str(data)[:300]
        QMessageBox.information(self, "Model Info", details)

    def stop_model(self):
        if self._worker: self._worker.stop(); self.log.append_line("Stopped.","warn")

    def delete_model(self):
        m = self._selected()
        if not m: return
        if QMessageBox.question(self,"Delete",f"Delete '{m}'? Removes local weights.",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self._run_cmd(f"ollama rm {m}", on_done=lambda _: self.refresh_models())

    def run_benchmark(self):
        model  = self.bench_model.currentText()
        prompt = self.bench_prompt.text().strip()
        if not model or not prompt: return
        self.bench_log.append_line(f"Benchmarking {model}…","cmd")
        t0 = time.time()
        self._bench_tokens = 0
        host = SETTINGS.get("ollama_host")
        msgs = [{"role":"user","content":prompt}]
        w = OllamaAPIWorker(host, model, msgs)
        w.token.connect(lambda t: setattr(self,'_bench_tokens', self._bench_tokens+1))
        w.done.connect(lambda _: self._bench_done(model, t0))
        w.error.connect(lambda e: self.bench_log.append_line(e,"error"))
        w.start(); self._bench_worker = w

    def _bench_done(self, model, t0):
        elapsed = time.time() - t0
        tps = self._bench_tokens / max(elapsed, 0.001)
        self.bench_log.append_line(
            f"✅  {model}: {self._bench_tokens} tokens in {elapsed:.2f}s → {tps:.1f} tok/s","success")

    def _run_cmd(self, cmd, on_done=None):
        if self._worker and self._worker.isRunning(): self._worker.stop()
        self._worker = CommandWorker(cmd, shell_type="cmd")
        self._worker.output.connect(lambda l: self.log.append_line(l,"info"))
        if on_done: self._worker.done.connect(on_done)
        self._worker.done.connect(lambda c: self.log.append_line(
            f"Process exited ({c})", "success" if c==0 else "error"))
        self._worker.start()

    def _detect_hw(self):
        try:
            r = subprocess.run(["nvidia-smi","--query-gpu=name,memory.total","--format=csv,noheader"],
                capture_output=True,text=True,timeout=4,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0)
            if r.returncode==0 and r.stdout.strip():
                self.hw_label.setText(f"🎮  GPU: {r.stdout.strip()}"); return
        except Exception: pass
        if HAS_PSUTIL:
            vm = psutil.virtual_memory()
            self.hw_label.setText(f"🖥  CPU  |  RAM: {vm.total//1024**3} GB")


# ─────────────────────────────────────────────
#  CHAT DIALOG  (streaming, history, system prompt)
# ─────────────────────────────────────────────

class ChatDialog(QDialog):
    def __init__(self, model: str, host: str, parent=None):
        super().__init__(parent)
        self.model=model; self.host=host
        self.history: List[Dict] = []   # [{role,content}]
        self._worker = None; self._cur_html = ""
        self.setWindowTitle(f"Chat — {model}")
        self.resize(760, 580)
        self._build_ui()
        self.setStyleSheet(STYLESHEET)
        SESSIONS_DIR.mkdir(exist_ok=True)

    def _build_ui(self):
        lay = QVBoxLayout(self); lay.setSpacing(8)

        title = QLabel(f"💬  {self.model}")
        title.setStyleSheet(f"font-size:16px;font-weight:bold;color:{THEME['accent2']};")
        lay.addWidget(title)

        # system prompt
        sys_row = QHBoxLayout()
        sys_row.addWidget(QLabel("System:"))
        self.sys_input = QLineEdit()
        self.sys_input.setPlaceholderText("Optional system prompt / persona…")
        sys_row.addWidget(self.sys_input, 1)
        btn_clr = QPushButton("🗑 Clear history"); btn_clr.clicked.connect(self._clear_history)
        btn_save = QPushButton("💾 Save"); btn_save.clicked.connect(self._save_chat)
        sys_row.addWidget(btn_clr); sys_row.addWidget(btn_save)
        lay.addLayout(sys_row)

        # chat display
        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.chat_view.setObjectName("logview")
        self.chat_view.setStyleSheet(
            f"background:#080812;color:{THEME['text']};font-size:13px;")
        lay.addWidget(self.chat_view, 1)

        # input
        inp_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message and press Enter…")
        self.input.returnPressed.connect(self.send)
        self.send_btn = QPushButton("Send ↵"); self.send_btn.setObjectName("primary")
        self.send_btn.clicked.connect(self.send)
        self.stop_btn = QPushButton("⏹"); self.stop_btn.setFixedWidth(36)
        self.stop_btn.clicked.connect(self._stop)
        inp_row.addWidget(self.input, 1)
        inp_row.addWidget(self.send_btn); inp_row.addWidget(self.stop_btn)
        lay.addLayout(inp_row)

        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet(f"color:{THEME['text3']};font-size:11px;")
        lay.addWidget(self.status_lbl)

    def send(self):
        msg = self.input.text().strip()
        if not msg: return
        self.input.clear()
        self.history.append({"role":"user","content":msg})
        self._append_bubble("You", msg, THEME["accent2"])
        self.status_lbl.setText("Thinking…"); self.send_btn.setEnabled(False)

        # Start streaming worker
        if self._worker and self._worker.isRunning(): self._worker.stop()
        self._worker = OllamaAPIWorker(
            self.host, self.model, list(self.history), self.sys_input.text().strip())
        self._stream_buf = ""
        self._stream_started = False
        self._worker.token.connect(self._on_token)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_token(self, tok: str):
        if not self._stream_started:
            # Open the assistant bubble
            self.chat_view.append(
                f'<p style="color:{THEME["text2"]};margin:2px 0;"><b>'
                f'<span style="color:{THEME["success"]};">{self.model}</span>:</b>&nbsp;'
            )
            self._stream_started = True
        esc = tok.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br>")
        cur = self.chat_view.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        self.chat_view.setTextCursor(cur)
        self.chat_view.insertHtml(f'<span style="color:{THEME["text"]};">{esc}</span>')
        self.chat_view.moveCursor(QTextCursor.MoveOperation.End)
        self._stream_buf += tok

    def _on_done(self, full: str):
        response = full or self._stream_buf
        if response:
            self.history.append({"role":"assistant","content":response})
            if not self._stream_started:
                self._append_bubble(self.model, response, THEME["text"])
            else:
                self.chat_view.append("")  # close paragraph
        self.status_lbl.setText("Ready"); self.send_btn.setEnabled(True)
        self._stream_started = False

    def _on_error(self, err: str):
        self._append_bubble("Error", err, THEME["error"])
        self.status_lbl.setText("Error"); self.send_btn.setEnabled(True)

    def _append_bubble(self, speaker, text, color):
        esc = text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br>")
        self.chat_view.append(
            f'<p style="color:{THEME["text2"]};margin:4px 0;">'
            f'<b><span style="color:{color};">{speaker}:</span></b> '
            f'<span style="color:{THEME["text"]};">{esc}</span></p>'
        )
        self.chat_view.moveCursor(QTextCursor.MoveOperation.End)

    def _stop(self):
        if self._worker: self._worker.stop(); self.status_lbl.setText("Stopped.")
        self.send_btn.setEnabled(True)

    def _clear_history(self):
        self.history.clear(); self.chat_view.clear()
        self.chat_view.append(f'<p style="color:{THEME["text3"]};">History cleared.</p>')

    def _save_chat(self):
        path = SESSIONS_DIR / f"{self.model}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps({"model":self.model,"history":self.history},indent=2))
        QMessageBox.information(self,"Saved",f"Saved to {path}")
