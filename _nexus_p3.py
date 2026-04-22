
# ─────────────────────────────────────────────
#  GIT PANEL  (enhanced: tabs — Local | Branches | Diff | Stage & Commit)
# ─────────────────────────────────────────────

class GitPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._worker = None; self._projects = []
        self._load_projects(); self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(16,16,16,16); root.setSpacing(12)

        hdr = QHBoxLayout()
        t = QLabel("Git Projects")
        t.setStyleSheet(f"font-size:18px;font-weight:bold;color:{THEME['text']};")
        hdr.addWidget(t); hdr.addStretch(); root.addLayout(hdr)

        # project selector strip
        ps = QHBoxLayout()
        ps.addWidget(QLabel("Active project:"))
        self.proj_combo = QComboBox(); self.proj_combo.setMinimumWidth(260)
        self.proj_combo.currentIndexChanged.connect(self._on_proj_combo)
        btn_add = QPushButton("➕ Add"); btn_add.clicked.connect(self._browse_add)
        btn_clone = QPushButton("⬇ Clone"); btn_clone.clicked.connect(self._do_clone_dialog)
        btn_rm = QPushButton("✕ Remove"); btn_rm.setObjectName("danger")
        btn_rm.clicked.connect(self._remove_proj)
        ps.addWidget(self.proj_combo, 1)
        ps.addWidget(btn_add); ps.addWidget(btn_clone); ps.addWidget(btn_rm)
        root.addLayout(ps)

        self.proj_info_lbl = QLabel("No project selected")
        self.proj_info_lbl.setStyleSheet(f"color:{THEME['text3']};font-size:11px;")
        root.addWidget(self.proj_info_lbl)

        # tabs
        tabs = QTabWidget()
        tabs.addTab(self._build_gitops_tab(), "🔧  Git Ops")
        tabs.addTab(self._build_branch_tab(), "🌿  Branches")
        tabs.addTab(self._build_diff_tab(),   "🔍  Diff")
        tabs.addTab(self._build_commit_tab(), "📦  Stage & Commit")
        root.addWidget(tabs, 1)

        self.progress = QProgressBar(); self.progress.setVisible(False)
        root.addWidget(self.progress)
        self.log = LogView(); self.log.setMaximumHeight(140)
        root.addWidget(self.log)
        self._refresh_combo()

    def _build_gitops_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setSpacing(8)
        for label, fn in [
            ("git pull",           self.git_pull),
            ("git fetch --all",    self.git_fetch),
            ("git status",         self.git_status),
            ("git log --oneline",  self.git_log),
        ]:
            b = QPushButton(label); b.setMinimumHeight(34); b.clicked.connect(fn)
            lay.addWidget(b)
        lay.addSpacing(6); lay.addWidget(QLabel("Custom command:"))
        row = QHBoxLayout()
        self.custom_cmd = QLineEdit(); self.custom_cmd.setPlaceholderText("git stash")
        self.custom_cmd.returnPressed.connect(self.run_custom)
        btn = QPushButton("▶ Run"); btn.setObjectName("success"); btn.clicked.connect(self.run_custom)
        row.addWidget(self.custom_cmd, 1); row.addWidget(btn)
        lay.addLayout(row); lay.addStretch()
        return w

    def _build_branch_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setSpacing(8)
        top = QHBoxLayout()
        top.addWidget(QLabel("Branches:"))
        btn_ref = QPushButton("⟳"); btn_ref.setFixedWidth(32); btn_ref.clicked.connect(self.refresh_branches)
        top.addWidget(btn_ref); top.addStretch()
        lay.addLayout(top)
        self.branch_list = QListWidget()
        lay.addWidget(self.branch_list, 1)
        row = QHBoxLayout()
        self.new_branch_input = QLineEdit(); self.new_branch_input.setPlaceholderText("new-branch-name")
        btn_new    = QPushButton("➕ Create"); btn_new.clicked.connect(self.create_branch)
        btn_switch = QPushButton("⇄ Switch");  btn_switch.clicked.connect(self.switch_branch)
        btn_merge  = QPushButton("⊕ Merge");   btn_merge.clicked.connect(self.merge_branch)
        btn_del    = QPushButton("🗑 Delete");  btn_del.setObjectName("danger"); btn_del.clicked.connect(self.delete_branch)
        row.addWidget(self.new_branch_input, 1)
        row.addWidget(btn_new); row.addWidget(btn_switch)
        row.addWidget(btn_merge); row.addWidget(btn_del)
        lay.addLayout(row)
        return w

    def _build_diff_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setSpacing(8)
        top = QHBoxLayout()
        self.diff_selector = QComboBox()
        self.diff_selector.addItems(["Working tree (unstaged)", "Staged changes", "Last commit", "Custom ref…"])
        btn_diff = QPushButton("Show Diff"); btn_diff.setObjectName("primary")
        btn_diff.clicked.connect(self.show_diff)
        top.addWidget(self.diff_selector, 1); top.addWidget(btn_diff)
        lay.addLayout(top)
        self.diff_view = QPlainTextEdit(); self.diff_view.setReadOnly(True)
        self.diff_view.setFont(QFont("Consolas", 11))
        self.diff_view.setStyleSheet(f"background:#080810;color:{THEME['text']};border-radius:4px;")
        self._diff_hl = DiffHighlighter(self.diff_view.document())
        lay.addWidget(self.diff_view, 1)
        return w

    def _build_commit_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setSpacing(8)
        top = QHBoxLayout()
        btn_status = QPushButton("⟳ Refresh changed files"); btn_status.clicked.connect(self.refresh_staged)
        top.addWidget(btn_status); top.addStretch()
        lay.addLayout(top)
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        lay.addWidget(self.file_list, 1)
        lay.addWidget(QLabel("Commit message:"))
        self.commit_msg = QLineEdit(); self.commit_msg.setPlaceholderText("feat: describe your change…")
        lay.addWidget(self.commit_msg)
        btn_row = QHBoxLayout()
        btn_stage_all = QPushButton("➕ Stage All"); btn_stage_all.clicked.connect(self.stage_all)
        btn_commit = QPushButton("✔ Commit"); btn_commit.setObjectName("success"); btn_commit.clicked.connect(self.do_commit)
        btn_push = QPushButton("🚀 Push"); btn_push.setObjectName("primary"); btn_push.clicked.connect(self.do_push)
        btn_row.addWidget(btn_stage_all); btn_row.addWidget(btn_commit); btn_row.addWidget(btn_push)
        lay.addLayout(btn_row)
        return w

    # ── helpers ─────────────────────────────

    def _cwd(self):
        idx = self.proj_combo.currentIndex()
        if 0 <= idx < len(self._projects):
            return self._projects[idx]["path"]
        return None

    def _run_git(self, cmd, callback=None):
        cwd = self._cwd()
        if not cwd: self.log.append_line("No project selected","error"); return
        self.log.append_line(f"$ {cmd}","cmd")
        self.progress.setVisible(True); self.progress.setRange(0,0)
        if self._worker and self._worker.isRunning(): self._worker.stop()
        self._worker = CommandWorker(cmd, cwd=cwd, shell_type="cmd")
        self._worker.output.connect(lambda l: self.log.append_line(l))
        def _done(c):
            self.progress.setVisible(False)
            self.log.append_line(f"Done ({c})", "success" if c==0 else "error")
            if callback: callback(c)
        self._worker.done.connect(_done); self._worker.start()

    def _run_git_capture(self, cmd, callback):
        """Run git, capture output, call callback(text)."""
        cwd = self._cwd()
        if not cwd: return
        try:
            r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0)
            callback((r.stdout + r.stderr).strip())
        except Exception as e:
            callback(f"[error] {e}")

    def _refresh_combo(self):
        self.proj_combo.clear()
        for p in self._projects:
            self.proj_combo.addItem(f"📁 {p['name']}")
        self._on_proj_combo(self.proj_combo.currentIndex())

    def _on_proj_combo(self, idx):
        if 0 <= idx < len(self._projects):
            p = self._projects[idx]
            self.proj_info_lbl.setText(f"Path: {p['path']}")
        else:
            self.proj_info_lbl.setText("No project selected")

    def _browse_add(self):
        d = QFileDialog.getExistingDirectory(self, "Select Git repo folder")
        if d:
            name = Path(d).name
            self._projects.append({"name": name, "path": d})
            self._save_projects(); self._refresh_combo()
            self.log.append_line(f"Added {name}","success")

    def _remove_proj(self):
        idx = self.proj_combo.currentIndex()
        if 0 <= idx < len(self._projects):
            self._projects.pop(idx); self._save_projects(); self._refresh_combo()

    def _do_clone_dialog(self):
        url, ok = QInputDialog.getText(self, "Clone Repo", "Repository URL:")
        if not ok or not url: return
        dest = QFileDialog.getExistingDirectory(self, "Clone into folder")
        if not dest: return
        self.log.append_line(f"Cloning {url}…","cmd")
        self.progress.setVisible(True); self.progress.setRange(0,0)
        if self._worker and self._worker.isRunning(): self._worker.stop()
        self._worker = CommandWorker(f"git clone {url}", cwd=dest, shell_type="cmd")
        self._worker.output.connect(lambda l: self.log.append_line(l))
        def _done(code):
            self.progress.setVisible(False)
            if code == 0:
                name = url.rstrip("/").split("/")[-1].replace(".git","")
                self._projects.append({"name":name,"path":str(Path(dest)/name)})
                self._save_projects(); self._refresh_combo()
                self.log.append_line("Clone complete.","success")
            else:
                self.log.append_line("Clone failed.","error")
        self._worker.done.connect(_done); self._worker.start()

    # ── git ops ─────────────────────────────

    def git_pull(self):   self._run_git("git pull")
    def git_fetch(self):  self._run_git("git fetch --all")
    def git_status(self): self._run_git("git status")
    def git_log(self):    self._run_git("git log --oneline -25")
    def run_custom(self):
        cmd = self.custom_cmd.text().strip()
        if cmd: self._run_git(cmd)

    # ── branches ────────────────────────────

    def refresh_branches(self):
        self._run_git_capture("git branch -a", self._populate_branches)

    def _populate_branches(self, text):
        self.branch_list.clear()
        for line in text.splitlines():
            self.branch_list.addItem(line.strip())

    def create_branch(self):
        name = self.new_branch_input.text().strip()
        if name: self._run_git(f"git checkout -b {name}", lambda _: self.refresh_branches())

    def switch_branch(self):
        item = self.branch_list.currentItem()
        if item:
            branch = item.text().lstrip("* ").split("/")[-1].strip()
            self._run_git(f"git checkout {branch}", lambda _: self.refresh_branches())

    def merge_branch(self):
        item = self.branch_list.currentItem()
        if item:
            branch = item.text().lstrip("* ").split("/")[-1].strip()
            self._run_git(f"git merge {branch}")

    def delete_branch(self):
        item = self.branch_list.currentItem()
        if not item: return
        branch = item.text().lstrip("* ").split("/")[-1].strip()
        if QMessageBox.question(self,"Delete branch",f"Delete branch '{branch}'?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self._run_git(f"git branch -d {branch}", lambda _: self.refresh_branches())

    # ── diff ────────────────────────────────

    def show_diff(self):
        sel = self.diff_selector.currentIndex()
        cmds = ["git diff","git diff --cached","git diff HEAD~1",""]
        if sel == 3:
            ref, ok = QInputDialog.getText(self,"Custom Diff","Enter git ref (e.g. main..HEAD):")
            if not ok: return
            cmd = f"git diff {ref}"
        else:
            cmd = cmds[sel]
        self._run_git_capture(cmd, lambda t: self.diff_view.setPlainText(t or "(no changes)"))

    # ── stage & commit ───────────────────────

    def refresh_staged(self):
        self._run_git_capture("git status --porcelain", self._populate_files)

    def _populate_files(self, text):
        self.file_list.clear()
        for line in text.splitlines():
            if line.strip():
                self.file_list.addItem(line)

    def stage_all(self): self._run_git("git add -A", lambda _: self.refresh_staged())

    def do_commit(self):
        msg = self.commit_msg.text().strip()
        if not msg: QMessageBox.warning(self,"No message","Enter a commit message."); return
        self._run_git(f'git commit -m "{msg}"')

    def do_push(self): self._run_git("git push")

    # ── persistence ─────────────────────────

    def _load_projects(self):
        try:
            with open(PROJECTS_FILE) as f: self._projects = json.load(f)
        except Exception: self._projects = []

    def _save_projects(self):
        try:
            with open(PROJECTS_FILE, "w") as f: json.dump(self._projects, f, indent=2)
        except Exception: pass


# ─────────────────────────────────────────────
#  GITHUB PANEL  (API explorer)
# ─────────────────────────────────────────────

class GitHubPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._worker = None; self._selected_repo = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(16,16,16,16); root.setSpacing(12)

        hdr = QHBoxLayout()
        t = QLabel("GitHub")
        t.setStyleSheet(f"font-size:18px;font-weight:bold;color:{THEME['text']};")
        hdr.addWidget(t); hdr.addStretch()
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("GitHub personal access token (ghp_…)")
        self.token_input.setMaximumWidth(300)
        self.token_input.setText(SETTINGS.get("github_token",""))
        self.token_input.textChanged.connect(lambda t: SETTINGS.set("github_token",t))
        btn_save_tok = QPushButton("Save Token"); btn_save_tok.clicked.connect(SETTINGS.save)
        hdr.addWidget(self.token_input); hdr.addWidget(btn_save_tok)
        root.addLayout(hdr)

        self.rate_lbl = QLabel("")
        self.rate_lbl.setStyleSheet(f"color:{THEME['text3']};font-size:11px;")
        root.addWidget(self.rate_lbl)

        tabs = QTabWidget()
        tabs.addTab(self._build_search_tab(),  "🔍  Search Repos")
        tabs.addTab(self._build_myrepos_tab(), "📋  My Repos")
        tabs.addTab(self._build_issues_tab(),  "🐛  Issues")
        tabs.addTab(self._build_prs_tab(),     "🔀  Pull Requests")
        root.addWidget(tabs, 1)

        self.log = LogView(); self.log.setMaximumHeight(120)
        root.addWidget(self.log)

    def _build_search_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setSpacing(8)
        top = QHBoxLayout()
        self.search_input = QLineEdit(); self.search_input.setPlaceholderText("language:python stars:>1000")
        self.search_input.returnPressed.connect(self.search_repos)
        btn = QPushButton("Search"); btn.setObjectName("primary"); btn.clicked.connect(self.search_repos)
        self.sort_combo = QComboBox(); self.sort_combo.addItems(["stars","forks","updated"])
        top.addWidget(self.search_input, 1); top.addWidget(self.sort_combo); top.addWidget(btn)
        lay.addLayout(top)
        self.search_tree = QTreeWidget()
        self.search_tree.setHeaderLabels(["Repo","Stars","Forks","Language","Description"])
        self.search_tree.setColumnWidth(0,200); self.search_tree.setColumnWidth(4,350)
        self.search_tree.itemDoubleClicked.connect(self._on_repo_dclick)
        lay.addWidget(self.search_tree, 1)
        btn_clone = QPushButton("⬇ Clone Selected into…"); btn_clone.clicked.connect(self._clone_selected_search)
        lay.addWidget(btn_clone)
        return w

    def _build_myrepos_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setSpacing(8)
        top = QHBoxLayout()
        btn = QPushButton("⟳ Load My Repos"); btn.setObjectName("primary"); btn.clicked.connect(self.load_my_repos)
        self.myrepo_filter = QLineEdit(); self.myrepo_filter.setPlaceholderText("Filter…")
        self.myrepo_filter.textChanged.connect(self._filter_my_repos)
        top.addWidget(btn); top.addWidget(self.myrepo_filter, 1)
        lay.addLayout(top)
        self.my_repo_tree = QTreeWidget()
        self.my_repo_tree.setHeaderLabels(["Name","Private","Stars","Language","Updated"])
        self.my_repo_tree.setColumnWidth(0,220)
        self.my_repo_tree.itemClicked.connect(self._on_myrepo_select)
        lay.addWidget(self.my_repo_tree, 1)
        btn_clone = QPushButton("⬇ Clone Selected into…"); btn_clone.clicked.connect(self._clone_selected_my)
        lay.addWidget(btn_clone)
        self._my_repos_data = []
        return w

    def _build_issues_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setSpacing(8)
        top = QHBoxLayout()
        self.issue_repo_input = QLineEdit(); self.issue_repo_input.setPlaceholderText("owner/repo")
        self.issue_state_combo = QComboBox(); self.issue_state_combo.addItems(["open","closed","all"])
        btn = QPushButton("Load Issues"); btn.setObjectName("primary"); btn.clicked.connect(self.load_issues)
        top.addWidget(QLabel("Repo:")); top.addWidget(self.issue_repo_input, 1)
        top.addWidget(self.issue_state_combo); top.addWidget(btn)
        lay.addLayout(top)
        self.issues_tree = QTreeWidget()
        self.issues_tree.setHeaderLabels(["#","Title","Author","Labels","Created"])
        self.issues_tree.setColumnWidth(1,300)
        lay.addWidget(self.issues_tree, 1)
        # create issue
        ci = QGroupBox("Create Issue")
        cl = QVBoxLayout(ci)
        self.new_issue_title = QLineEdit(); self.new_issue_title.setPlaceholderText("Issue title")
        self.new_issue_body  = QPlainTextEdit(); self.new_issue_body.setPlaceholderText("Description…")
        self.new_issue_body.setMaximumHeight(70)
        btn_create = QPushButton("Create Issue"); btn_create.setObjectName("success")
        btn_create.clicked.connect(self.create_issue)
        cl.addWidget(self.new_issue_title); cl.addWidget(self.new_issue_body); cl.addWidget(btn_create)
        lay.addWidget(ci)
        return w

    def _build_prs_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setSpacing(8)
        top = QHBoxLayout()
        self.pr_repo_input = QLineEdit(); self.pr_repo_input.setPlaceholderText("owner/repo")
        self.pr_state_combo = QComboBox(); self.pr_state_combo.addItems(["open","closed","all"])
        btn = QPushButton("Load PRs"); btn.setObjectName("primary"); btn.clicked.connect(self.load_prs)
        top.addWidget(QLabel("Repo:")); top.addWidget(self.pr_repo_input, 1)
        top.addWidget(self.pr_state_combo); top.addWidget(btn)
        lay.addLayout(top)
        self.prs_tree = QTreeWidget()
        self.prs_tree.setHeaderLabels(["#","Title","Author","Branch","Created"])
        self.prs_tree.setColumnWidth(1,300)
        lay.addWidget(self.prs_tree, 1)
        return w

    # ── actions ─────────────────────────────

    def _token(self): return self.token_input.text().strip()

    def _start_worker(self, endpoint, method="GET", body=None, callback=None, params=None):
        w = GitHubWorker(endpoint, method, body, self._token(), params)
        if callback: w.result.connect(callback)
        w.error.connect(lambda e: self.log.append_line(f"GitHub API: {e}","error"))
        w.start(); self._worker = w

    def search_repos(self):
        q = self.search_input.text().strip()
        if not q: return
        sort = self.sort_combo.currentText()
        self.log.append_line(f"Searching: {q}","cmd")
        self.search_tree.clear()
        self._start_worker("/search/repositories", params={"q":q,"sort":sort,"per_page":30},
                           callback=self._populate_search)

    def _populate_search(self, data):
        self.search_tree.clear()
        items = data.get("items",[])
        for r in items:
            item = QTreeWidgetItem([
                r.get("full_name",""), str(r.get("stargazers_count",0)),
                str(r.get("forks_count",0)), r.get("language","") or "",
                (r.get("description","") or "")[:80],
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, r)
            self.search_tree.addTopLevelItem(item)
        self.log.append_line(f"Found {len(items)} repos","success")

    def load_my_repos(self):
        self.log.append_line("Loading your repos…","cmd")
        self.my_repo_tree.clear(); self._my_repos_data = []
        self._start_worker("/user/repos", params={"per_page":100,"sort":"updated"},
                           callback=self._populate_my_repos)

    def _populate_my_repos(self, data):
        self._my_repos_data = data if isinstance(data,list) else []
        self._show_my_repos(self._my_repos_data)
        self.log.append_line(f"Loaded {len(self._my_repos_data)} repos","success")

    def _show_my_repos(self, repos):
        self.my_repo_tree.clear()
        for r in repos:
            item = QTreeWidgetItem([
                r.get("name",""), "🔒" if r.get("private") else "🌐",
                str(r.get("stargazers_count",0)),
                r.get("language","") or "",
                (r.get("updated_at","") or "")[:10],
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, r)
            self.my_repo_tree.addTopLevelItem(item)

    def _filter_my_repos(self, text):
        filtered = [r for r in self._my_repos_data
                    if text.lower() in r.get("name","").lower()]
        self._show_my_repos(filtered)

    def _on_myrepo_select(self, item, _):
        r = item.data(0, Qt.ItemDataRole.UserRole)
        if r: self._selected_repo = r.get("full_name")

    def _on_repo_dclick(self, item, _):
        r = item.data(0, Qt.ItemDataRole.UserRole)
        if r:
            self._selected_repo = r.get("full_name")
            self.issue_repo_input.setText(self._selected_repo)
            self.pr_repo_input.setText(self._selected_repo)

    def _clone_repo_url(self, url):
        if not url: return
        dest = QFileDialog.getExistingDirectory(self, "Clone into folder")
        if not dest: return
        self.log.append_line(f"Cloning {url}…","cmd")
        w = CommandWorker(f"git clone {url}", cwd=dest, shell_type="cmd")
        w.output.connect(lambda l: self.log.append_line(l))
        w.done.connect(lambda c: self.log.append_line("Clone done.","success") if c==0 else self.log.append_line("Failed.","error"))
        w.start(); self._worker = w

    def _clone_selected_search(self):
        item = self.search_tree.currentItem()
        if item:
            r = item.data(0, Qt.ItemDataRole.UserRole)
            if r: self._clone_repo_url(r.get("clone_url",""))

    def _clone_selected_my(self):
        item = self.my_repo_tree.currentItem()
        if item:
            r = item.data(0, Qt.ItemDataRole.UserRole)
            if r: self._clone_repo_url(r.get("clone_url",""))

    def load_issues(self):
        repo = self.issue_repo_input.text().strip()
        if not repo: return
        state = self.issue_state_combo.currentText()
        self.log.append_line(f"Loading issues for {repo}…","cmd")
        self.issues_tree.clear()
        self._start_worker(f"/repos/{repo}/issues",
                           params={"state":state,"per_page":50},
                           callback=self._populate_issues)

    def _populate_issues(self, data):
        self.issues_tree.clear()
        items = data if isinstance(data,list) else []
        for iss in items:
            labels = ",".join(l.get("name","") for l in iss.get("labels",[]))
            item = QTreeWidgetItem([
                str(iss.get("number","")),
                iss.get("title","")[:80],
                iss.get("user",{}).get("login",""),
                labels,
                (iss.get("created_at","") or "")[:10],
            ])
            self.issues_tree.addTopLevelItem(item)
        self.log.append_line(f"Loaded {len(items)} issues","success")

    def create_issue(self):
        repo  = self.issue_repo_input.text().strip()
        title = self.new_issue_title.text().strip()
        body  = self.new_issue_body.toPlainText().strip()
        if not repo or not title:
            QMessageBox.warning(self,"Missing","Repo and title are required."); return
        self.log.append_line(f"Creating issue on {repo}…","cmd")
        self._start_worker(f"/repos/{repo}/issues", method="POST",
                           body={"title":title,"body":body},
                           callback=lambda d: self.log.append_line(
                               f"Issue #{d.get('number')} created.","success"))

    def load_prs(self):
        repo = self.pr_repo_input.text().strip()
        if not repo: return
        state = self.pr_state_combo.currentText()
        self.log.append_line(f"Loading PRs for {repo}…","cmd")
        self.prs_tree.clear()
        self._start_worker(f"/repos/{repo}/pulls",
                           params={"state":state,"per_page":50},
                           callback=self._populate_prs)

    def _populate_prs(self, data):
        self.prs_tree.clear()
        items = data if isinstance(data,list) else []
        for pr in items:
            item = QTreeWidgetItem([
                str(pr.get("number","")),
                pr.get("title","")[:80],
                pr.get("user",{}).get("login",""),
                pr.get("head",{}).get("ref",""),
                (pr.get("created_at","") or "")[:10],
            ])
            self.prs_tree.addTopLevelItem(item)
        self.log.append_line(f"Loaded {len(items)} PRs","success")
