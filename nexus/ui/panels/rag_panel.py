import json, os
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QFrame, QSplitter, QLineEdit, QTextEdit,
    QFileDialog, QPlainTextEdit, QMessageBox, QProgressBar,
    QListWidget, QListWidgetItem, QTabWidget, QTreeWidgetItem, QTreeWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QTextCursor, QFont, QColor

from ...core.config import PROJECTS_FILE, SETTINGS
from ...core.style import THEME, STYLESHEET
from ...core.rag import CodebaseRAG
from ..widgets import LogView, DiffHighlighter
import requests

class RAGIndexerWorker(QThread):
    progress = pyqtSignal(int)
    log_msg = pyqtSignal(str, str)
    finished = pyqtSignal()
    
    def __init__(self, rag_engine, provider, model, host, api_key):
        super().__init__()
        self.rag_engine = rag_engine
        self.provider = provider
        self.model = model
        self.host = host
        self.api_key = api_key
        
    def run(self):
        try:
            self.rag_engine.index_project(
                provider=self.provider,
                model=self.model,
                host=self.host,
                api_key=self.api_key,
                progress_cb=self.progress.emit,
                log_cb=self.log_msg.emit
            )
        except Exception as e:
            self.log_msg.emit(f"Indexing error: {e}", "error")
        self.finished.emit()


class RAGQAWorker(QThread):
    token = pyqtSignal(str)
    done = pyqtSignal(str)
    error = pyqtSignal(str)
    sources = pyqtSignal(list)
    
    def __init__(self, query, rag_engine, provider, model, host, api_key):
        super().__init__()
        self.query = query
        self.rag_engine = rag_engine
        self.provider = provider
        self.model = model
        self.host = host
        self.api_key = api_key
        self._stop = False
        
    def run(self):
        try:
            # 1. Retrieve top context from RAG
            rag_provider = SETTINGS.get("rag_embedding_provider", "ollama")
            rag_model = SETTINGS.get("rag_embedding_model", "nomic-embed-text")
            rag_api_key = SETTINGS.get("openai_api_key", "") if rag_provider == "openai" else ""
            
            results = self.rag_engine.search(
                self.query,
                top_k=4,
                provider=rag_provider,
                model=rag_model,
                host=self.host,
                api_key=rag_api_key
            )
            
            self.sources.emit(results)
            
            context_str = ""
            if results:
                context_parts = []
                for r in results:
                    context_parts.append(
                        f"--- FILE: {r['file']} (Lines {r['start_line']}-{r['end_line']}) ---\n"
                        f"{r['text']}"
                    )
                context_str = "\n\n".join(context_parts)
            else:
                context_str = "No relevant context found in codebase."
                
            # 2. Build system prompt
            system_prompt = (
                "You are NEXUS Codebase QA — an expert software developer and assistant built into NEXUS.\n"
                "You answer user questions about their codebase by referencing the retrieved code snippets below.\n"
                "Always be specific, explain the code logic, and reference line numbers or files where relevant.\n\n"
                f"Retrieved Codebase Context:\n{context_str}"
            )
            
            # 3. Request LLM
            if self.provider == "ollama":
                body = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": self.query}
                    ],
                    "stream": True
                }
                r = requests.post(f"{self.host}/api/chat", json=body, stream=True, timeout=None)
                r.raise_for_status()
                full_response = ""
                for line in r.iter_lines():
                    if self._stop:
                        break
                    if line:
                        data = json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        if chunk:
                            self.token.emit(chunk)
                            full_response += chunk
                        if data.get("done"):
                            break
                self.done.emit(full_response)
            elif self.provider in ("openai", "openai_compatible"):
                base_url = SETTINGS.get("openai_base_url", "https://api.openai.com/v1") if self.provider == "openai" else self.host
                url = f"{base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                body = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": self.query}
                    ],
                    "stream": True
                }
                r = requests.post(url, json=body, headers=headers, stream=True, timeout=None)
                r.raise_for_status()
                full_response = ""
                for line in r.iter_lines():
                    if self._stop:
                        break
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        data_payload = line_str[6:]
                        if data_payload == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data_payload)
                            choices = chunk_data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                chunk = delta.get("content", "")
                                if chunk:
                                    self.token.emit(chunk)
                                    full_response += chunk
                        except Exception:
                            pass
                self.done.emit(full_response)
            elif self.provider == "anthropic":
                url = "https://api.anthropic.com/v1/messages"
                headers = {
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                body = {
                    "model": self.model,
                    "max_tokens": 4000,
                    "system": system_prompt,
                    "messages": [
                        {"role": "user", "content": self.query}
                    ],
                    "stream": True
                }
                r = requests.post(url, json=body, headers=headers, stream=True, timeout=None)
                r.raise_for_status()
                full_response = ""
                for line in r.iter_lines():
                    if self._stop:
                        break
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        data_payload = line_str[6:]
                        try:
                            chunk_data = json.loads(data_payload)
                            dtype = chunk_data.get("type")
                            if dtype == "content_block_delta":
                                chunk = chunk_data.get("delta", {}).get("text", "")
                                if chunk:
                                    self.token.emit(chunk)
                                    full_response += chunk
                            elif dtype == "message_stop":
                                break
                        except Exception:
                            pass
                self.done.emit(full_response)
        except Exception as e:
            self.error.emit(str(e))
            
    def stop(self):
        self._stop = True
        self.wait()


class RAGPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._projects = []
        self._rag = None
        self._indexer_worker = None
        self._qa_worker = None
        self._search_results = []
        
        self._build_ui()
        self._refresh_project_list()

    def activate(self):
        self._refresh_project_list()

    def deactivate(self):
        if self._indexer_worker and self._indexer_worker.isRunning():
            self._indexer_worker.stop()
        if self._qa_worker and self._qa_worker.isRunning():
            self._qa_worker.stop()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(12,12,12,12); root.setSpacing(8)

        # Header
        hdr = QHBoxLayout()
        t = QLabel("RAG Search")
        t.setStyleSheet(f"font-size:15px;font-weight:600;color:{THEME['text']};")
        hdr.addWidget(t); hdr.addStretch()
        root.addLayout(hdr)

        # Top Project Selector & Index Controller
        ctrl_box = QGroupBox("Project Codebase Indexing")
        cl = QVBoxLayout(ctrl_box); cl.setSpacing(6)
        
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Select Project:"))
        self.proj_combo = QComboBox(); self.proj_combo.setMinimumWidth(280)
        self.proj_combo.currentIndexChanged.connect(self._on_project_changed)
        btn_browse = QPushButton("Browse Folder"); btn_browse.clicked.connect(self._browse_folder)
        btn_refresh_list = QPushButton("⟳"); btn_refresh_list.setFixedWidth(32); btn_refresh_list.clicked.connect(self._refresh_project_list)
        r1.addWidget(self.proj_combo, 1); r1.addWidget(btn_browse); r1.addWidget(btn_refresh_list)
        cl.addLayout(r1)

        r2 = QHBoxLayout()
        self.status_lbl = QLabel("Status: Not Indexed")
        self.status_lbl.setStyleSheet(f"color:{THEME['text2']};font-size:12px;")
        self.btn_index = QPushButton("Build / Update Index"); self.btn_index.setObjectName("primary")
        self.btn_index.clicked.connect(self._run_indexing)
        r2.addWidget(self.status_lbl, 1); r2.addWidget(self.btn_index)
        cl.addLayout(r2)

        self.progress_bar = QProgressBar(); self.progress_bar.setValue(0); self.progress_bar.setVisible(False)
        cl.addWidget(self.progress_bar)
        
        root.addWidget(ctrl_box)

        # Splitter layout for Search vs Chat/Explorer
        split = QSplitter(Qt.Orientation.Horizontal)

        # LEFT PANEL: Search
        search_frame = QFrame(); sl = QVBoxLayout(search_frame); sl.setContentsMargins(0,0,0,0); sl.setSpacing(8)
        sl.addWidget(QLabel("Semantic & Keyword Search"))
        
        sr_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search query (e.g. database schema)...")
        self.search_input.returnPressed.connect(self._do_search)
        btn_search = QPushButton("Search"); btn_search.clicked.connect(self._do_search)
        sr_row.addWidget(self.search_input, 1); sr_row.addWidget(btn_search)
        sl.addLayout(sr_row)

        self.results_list = QListWidget()
        self.results_list.currentItemChanged.connect(self._on_result_selected)
        sl.addWidget(self.results_list, 1)
        
        split.addWidget(search_frame)

        # RIGHT PANEL: Chat QA and Explorer Tabs
        right_frame = QFrame(); rl = QVBoxLayout(right_frame); rl.setContentsMargins(8,0,0,0); rl.setSpacing(4)
        
        self.tabs = QTabWidget()
        
        # Tab 1: Codebase QA Chat
        self.chat_tab = QWidget(); ctl = QVBoxLayout(self.chat_tab); ctl.setSpacing(8)
        
        llm_row = QHBoxLayout()
        llm_row.addWidget(QLabel("LLM Provider:"))
        self.prov_combo = QComboBox(); self.prov_combo.addItems(["ollama", "openai", "anthropic", "openai_compatible"])
        self.prov_combo.setCurrentText(SETTINGS.get("agent_provider", "ollama"))
        llm_row.addWidget(self.prov_combo)
        llm_row.addWidget(QLabel("  Model:"))
        self.model_combo = QLineEdit(SETTINGS.get("openai_model", "gpt-4o-mini"))
        self.model_combo.setMinimumWidth(120)
        llm_row.addWidget(self.model_combo, 1)
        ctl.addLayout(llm_row)

        self.chat_view = QTextEdit(); self.chat_view.setReadOnly(True)
        self.chat_view.setStyleSheet(f"background:{THEME['bg2']};color:{THEME['text']};font-size:12px;border-radius:4px;font-family:'Consolas','Courier New',monospace;")
        ctl.addWidget(self.chat_view, 1)

        self.sources_view = QLabel("Sources: None")
        self.sources_view.setStyleSheet(f"color:{THEME['text3']};font-size:10px;")
        self.sources_view.setWordWrap(True)
        ctl.addWidget(self.sources_view)

        inp_row = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask a question about the project codebase...")
        self.chat_input.returnPressed.connect(self._send_qa)
        self.btn_send = QPushButton("Ask AI"); self.btn_send.setObjectName("primary"); self.btn_send.clicked.connect(self._send_qa)
        inp_row.addWidget(self.chat_input, 1); inp_row.addWidget(self.btn_send)
        ctl.addLayout(inp_row)

        self.tabs.addTab(self.chat_tab, "💬  Codebase QA")
        
        # Tab 2: Explorer & Code Actions
        self.explorer_tab = QWidget(); exl = QVBoxLayout(self.explorer_tab); exl.setSpacing(4)
        
        ex_split = QSplitter(Qt.Orientation.Horizontal)
        
        # File tree on the left
        self.explorer_tree = QTreeWidget()
        self.explorer_tree.setHeaderHidden(True)
        self.explorer_tree.setMinimumWidth(200)
        self.explorer_tree.currentItemChanged.connect(self._on_explorer_file_changed)
        ex_split.addWidget(self.explorer_tree)
        
        # File viewer on the right
        file_viewer_frame = QWidget(); fvl = QVBoxLayout(file_viewer_frame); fvl.setContentsMargins(0,0,0,0); fvl.setSpacing(4)
        
        self._file_path_lbl = QLabel("No file selected")
        self._file_path_lbl.setStyleSheet(f"color:{THEME['text2']};font-size:11px;padding:2px 4px;")
        fvl.addWidget(self._file_path_lbl)
        
        self.file_viewer = QTextEdit(); self.file_viewer.setReadOnly(True)
        self.file_viewer.setFont(QFont("Consolas", 11))
        self.file_viewer.setStyleSheet(f"background:{THEME['bg2']};color:{THEME['text']};border-radius:4px;")
        fvl.addWidget(self.file_viewer, 1)
        
        actions_row = QHBoxLayout()
        btn_explain = QPushButton("Explain")
        btn_explain.clicked.connect(lambda: self._trigger_selection_action("Explain this code section, how it works, and its purpose."))
        btn_optimize = QPushButton("Optimize")
        btn_optimize.clicked.connect(lambda: self._trigger_selection_action("Suggest optimizations, refactor this code section for clean architecture, and fix any potential bugs."))
        btn_tests = QPushButton("Gen Tests")
        btn_tests.clicked.connect(lambda: self._trigger_selection_action("Generate comprehensive unit tests for this code section."))
        actions_row.addWidget(btn_explain); actions_row.addWidget(btn_optimize); actions_row.addWidget(btn_tests)
        fvl.addLayout(actions_row)
        
        ex_split.addWidget(file_viewer_frame)
        ex_split.setSizes([220, 480])
        exl.addWidget(ex_split, 1)

        self.tabs.addTab(self.explorer_tab, "📁  Code Explorer")
        
        rl.addWidget(self.tabs, 1)
        
        split.addWidget(right_frame)
        split.setSizes([380, 520])

        root.addWidget(split, 1)

        # Bottom indexing logs
        self.log = LogView(); self.log.setMaximumHeight(110)
        root.addWidget(self.log)

    def _refresh_project_list(self):
        try:
            if Path(PROJECTS_FILE).exists():
                with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                    self._projects = json.load(f)
            else:
                self._projects = []
        except Exception:
            self._projects = []
            
        self.proj_combo.clear()
        for p in self._projects:
            self.proj_combo.addItem(f"📁 {p['name']}", p["path"])
            
        self._on_project_changed(self.proj_combo.currentIndex())

    def _browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select codebase folder")
        if not d:
            return
        name = Path(d).name
        if not any(p["path"] == d for p in self._projects):
            self._projects.append({"name": name, "path": d})
            try:
                with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
                    json.dump(self._projects, f, indent=2)
            except Exception:
                pass
        self._refresh_project_list()
        # Select the newly added project
        for i in range(self.proj_combo.count()):
            if self.proj_combo.itemData(i) == d:
                self.proj_combo.setCurrentIndex(i)
                break

    def _on_project_changed(self, idx):
        path = self.proj_combo.itemData(idx)
        if not path:
            self._rag = None
            self.status_lbl.setText("Status: No project selected")
            self.explorer_tree.clear()
            return
            
        self._rag = CodebaseRAG(path)
        stats = self._rag.get_index_stats()
        if stats["total_files"] == 0:
            self.status_lbl.setText("Status: Not Indexed")
        else:
            self.status_lbl.setText(f"Status: Indexed ({stats['total_files']} files, {stats['total_chunks']} chunks)")
            
        self._populate_explorer_files()

    def _populate_explorer_files(self):
        """Walk the actual project directory and build a tree view."""
        self.explorer_tree.clear()
        if not self._rag:
            return

        from nexus.core.rag import TEXT_EXTENSIONS, IGNORE_DIRS
        project_root = Path(self._rag.project_path)

        # Build nested dict {dirname: {subdir: {}, files: [...]}}
        dir_items = {}  # maps dir path -> QTreeWidgetItem

        for dirpath, dirnames, filenames in os.walk(project_root):
            # Filter ignored directories in-place
            dirnames[:] = sorted([d for d in dirnames if d not in IGNORE_DIRS])

            rel_dir = os.path.relpath(dirpath, project_root)
            if rel_dir == ".":
                parent_item = self.explorer_tree.invisibleRootItem()
            else:
                parent_item = dir_items.get(rel_dir)
                if parent_item is None:
                    continue

            # Add subdirectories as tree nodes
            for d in dirnames:
                child_rel = os.path.join(rel_dir, d) if rel_dir != "." else d
                node = QTreeWidgetItem(parent_item, [f"📁 {d}"])
                node.setData(0, Qt.ItemDataRole.UserRole, None)  # directory, no file path
                dir_items[child_rel] = node

            # Add files
            for f in sorted(filenames):
                ext = os.path.splitext(f)[1].lower()
                if ext in TEXT_EXTENSIONS:
                    child = QTreeWidgetItem(parent_item, [f])
                    abs_path = os.path.join(dirpath, f)
                    child.setData(0, Qt.ItemDataRole.UserRole, abs_path)

        # Expand the first level
        for i in range(self.explorer_tree.topLevelItemCount()):
            self.explorer_tree.topLevelItem(i).setExpanded(True)

    def _run_indexing(self):
        if not self._rag:
            QMessageBox.warning(self, "No Project", "Select a project first.")
            return
            
        provider = SETTINGS.get("rag_embedding_provider", "ollama")
        model = SETTINGS.get("rag_embedding_model", "nomic-embed-text")
        host = SETTINGS.get("ollama_host", "http://localhost:11434")
        api_key = ""
        if provider == "openai":
            api_key = SETTINGS.get("openai_api_key", "")
            if not api_key:
                QMessageBox.warning(self, "API Key Missing", "Configure your OpenAI API key in Settings first.")
                return
        
        self.btn_index.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log.append_line(f"Starting indexing for: {self._rag.project_path}", "cmd")
        
        self._indexer_worker = RAGIndexerWorker(self._rag, provider, model, host, api_key)
        self._indexer_worker.progress.connect(self.progress_bar.setValue)
        self._indexer_worker.log_msg.connect(self.log.append_line)
        self._indexer_worker.finished.connect(self._on_indexing_finished)
        self._indexer_worker.start()

    def _on_indexing_finished(self):
        self.btn_index.setEnabled(True)
        self.progress_bar.setVisible(False)
        if self._rag:
            stats = self._rag.get_index_stats()
            self.status_lbl.setText(f"Status: Indexed ({stats['total_files']} files, {stats['total_chunks']} chunks)")
            self._populate_explorer_files()

    def _do_search(self):
        query = self.search_input.text().strip()
        if not query or not self._rag:
            return
            
        provider = SETTINGS.get("rag_embedding_provider", "ollama")
        model = SETTINGS.get("rag_embedding_model", "nomic-embed-text")
        host = SETTINGS.get("ollama_host", "http://localhost:11434")
        api_key = SETTINGS.get("openai_api_key", "") if provider == "openai" else ""
        
        self.log.append_line(f"Searching codebase for: '{query}'", "cmd")
        results = self._rag.search(query, top_k=10, provider=provider, model=model, host=host, api_key=api_key)
        self._search_results = results
        
        self.results_list.clear()
        if not results:
            self.results_list.addItem("No matching snippets found.")
            return
            
        for r in results:
            item = QListWidgetItem()
            # Beautify list item display
            score_text = f"[{r['score']:.2f}]"
            file_info = f"{r['file']} (Lines {r['start_line']}-{r['end_line']})"
            snippet = r["text"].strip().replace("\n", " ")[:60] + "..."
            
            item.setText(f"{score_text} {file_info}\n  {snippet}")
            item.setData(Qt.ItemDataRole.UserRole, r)
            self.results_list.addItem(item)

    def _on_result_selected(self, current, previous):
        if not current:
            return
        data = current.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
            
        # Switch to Code Explorer tab and display the file
        self.tabs.setCurrentIndex(1)
        
        # Load the file directly into the viewer
        abs_path = Path(self._rag.project_path) / data["file"]
        self._file_path_lbl.setText(data["file"])
        try:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
            self.file_viewer.setPlainText(content)
        except Exception as e:
            self.file_viewer.setPlainText(f"Failed to read file: {e}")
                
        # Scroll to the matched lines
        self._scroll_viewer_to_line(data["start_line"], data["end_line"])

    def _on_explorer_file_changed(self, current, previous):
        if not current or not self._rag:
            self.file_viewer.clear()
            self._file_path_lbl.setText("No file selected")
            return
        
        abs_path = current.data(0, Qt.ItemDataRole.UserRole)
        if not abs_path:  # clicked a directory node
            return
        
        project_root = Path(self._rag.project_path)
        try:
            rel = os.path.relpath(abs_path, project_root)
        except ValueError:
            rel = abs_path
        self._file_path_lbl.setText(rel)
        
        try:
            content = Path(abs_path).read_text(encoding="utf-8", errors="replace")
            self.file_viewer.setPlainText(content)
        except Exception as e:
            self.file_viewer.setPlainText(f"Failed to read file: {e}")

    def _scroll_viewer_to_line(self, start, end):
        cursor = self.file_viewer.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        
        # Move down to start line (0-indexed offset)
        for _ in range(start - 1):
            cursor.movePosition(QTextCursor.MoveOperation.Down)
            
        # Set selection to highlight lines
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        self.file_viewer.setTextCursor(cursor)
        
        # Scroll screen to cursor
        self.file_viewer.ensureCursorVisible()

    def _send_qa(self):
        query = self.chat_input.text().strip()
        if not query or not self._rag:
            return
            
        self.chat_input.clear()
        self._append_chat("You", query, THEME["accent2"])
        
        provider = self.prov_combo.currentText()
        model = self.model_combo.text().strip()
        host = SETTINGS.get("ollama_host", "http://localhost:11434")
        api_key = ""
        if provider == "openai":
            api_key = SETTINGS.get("openai_api_key", "")
        elif provider == "anthropic":
            api_key = SETTINGS.get("anthropic_api_key", "")
            
        if self._qa_worker and self._qa_worker.isRunning():
            self._qa_worker.stop()
            
        self.btn_send.setEnabled(False)
        self.sources_view.setText("Sources: Retrieving codebase context...")
        
        self._qa_worker = RAGQAWorker(query, self._rag, provider, model, host, api_key)
        self._stream_started = False
        
        self._qa_worker.token.connect(self._on_qa_token)
        self._qa_worker.sources.connect(self._on_qa_sources)
        self._qa_worker.done.connect(self._on_qa_done)
        self._qa_worker.error.connect(self._on_qa_error)
        self._qa_worker.start()

    def _on_qa_token(self, token):
        if not self._stream_started:
            self.chat_view.append(f'<p style="color:{THEME["text2"]};margin:2px 0;"><b>'
                                  f'<span style="color:{THEME["success"]};">AI Code Assistant</span>:</b>&nbsp;</p>')
            self._stream_started = True
            
        cur = self.chat_view.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        self.chat_view.setTextCursor(cur)
        
        from PyQt6.QtGui import QTextCharFormat
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(THEME["text"]))
        cur.setCharFormat(fmt)
        cur.insertText(token)
        
        self.chat_view.moveCursor(QTextCursor.MoveOperation.End)

    def _on_qa_sources(self, results):
        if not results:
            self.sources_view.setText("Sources: General LLM knowledge (no matching files retrieved)")
            return
        paths = [f"{r['file']} (L{r['start_line']}-{r['end_line']})" for r in results[:3]]
        self.sources_view.setText("Sources: " + ", ".join(paths))

    def _on_qa_done(self, response):
        self.btn_send.setEnabled(True)
        self._stream_started = False
        self.chat_view.append("") # visual spacing

    def _on_qa_error(self, err):
        self.btn_send.setEnabled(True)
        self._stream_started = False
        self.chat_view.append(f'<p style="color:{THEME["error"]};margin:4px 0;"><b>Error:</b> {err}</p>')

    def _append_chat(self, speaker, text, color):
        esc = text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br>")
        self.chat_view.append(
            f'<p style="color:{THEME["text2"]};margin:4px 0;">'
            f'<b><span style="color:{color};">{speaker}:</span></b> '
            f'<span style="color:{THEME["text"]};">{esc}</span></p>'
        )
        self.chat_view.moveCursor(QTextCursor.MoveOperation.End)

    def _trigger_selection_action(self, action_prompt):
        cursor = self.file_viewer.textCursor()
        selection = cursor.selectedText().strip()
        if not selection:
            # Fall back to entire file content
            selection = self.file_viewer.toPlainText().strip()
            
        if not selection:
            QMessageBox.warning(self, "No Code", "Please select a block of code or open a non-empty file.")
            return
            
        filename = self._file_path_lbl.text() or "active_file"
        
        # Switch to chat QA
        self.tabs.setCurrentIndex(0)
        
        prompt = (
            f"Here is a code snippet from file `{filename}`:\n"
            f"```\n{selection}\n```\n\n"
            f"{action_prompt}"
        )
        self.chat_input.setText(prompt)
        self._send_qa()
