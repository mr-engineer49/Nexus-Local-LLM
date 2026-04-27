import subprocess, sys, os, shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QGroupBox, QProgressBar, QListWidget, QComboBox, QFileDialog, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, QEvent
from ...core.config import HAS_PSUTIL
from ...core.style import THEME
from ...core.workers import CommandWorker
from ..widgets import LogView

if HAS_PSUTIL:
    import psutil

class TerminalPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._worker  = None
        self._history = []
        self._hist_idx= -1
        self._build_ui()

    def activate(self): pass
    def deactivate(self): pass

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(16,16,16,16); root.setSpacing(10)
        hdr = QHBoxLayout()
        t = QLabel("Integrated Terminal")
        t.setStyleSheet(f"font-size:18px;font-weight:bold;color:{THEME['text']};")
        hdr.addWidget(t); hdr.addStretch()
        self.shell_combo = QComboBox()
        for s in self._detect_shells(): self.shell_combo.addItem(s["label"], s["type"])
        hdr.addWidget(self.shell_combo)
        
        self.native_check = QCheckBox("Run in Native Window")
        self.native_check.setStyleSheet(f"color:{THEME['text']};")
        self.native_check.setCursor(Qt.CursorShape.PointingHandCursor)
        hdr.addWidget(self.native_check)

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
        cwd = self.cwd_input.text().strip() or str(Path.home())
        shell_type = self.shell_combo.currentData() or "cmd"

        # --- Handle `cd` natively so directory changes persist ---
        stripped = cmd.strip()
        if stripped.lower() == "cd" or stripped.lower().startswith("cd ") or stripped.lower().startswith("cd\t"):
            parts = stripped.split(None, 1)
            target = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else str(Path.home())
            # Resolve relative or absolute path
            new_dir = Path(cwd) / target if not Path(target).is_absolute() else Path(target)
            try:
                resolved = new_dir.resolve()
                if resolved.is_dir():
                    self.cwd_input.setText(str(resolved))
                    self.output.append_line(f"$ {cmd}", "cmd")
                    self.output.append_line(f"→ Working directory changed to: {resolved}", "success")
                    self.output.append_line("[exit 0]", "success")
                else:
                    self.output.append_line(f"$ {cmd}", "cmd")
                    self.output.append_line(f"cd: The system cannot find the path specified: '{resolved}'", "error")
                    self.output.append_line("[exit 1]", "error")
            except Exception as e:
                self.output.append_line(f"$ {cmd}", "cmd")
                self.output.append_line(f"cd error: {e}", "error")
                self.output.append_line("[exit 1]", "error")
            return
        
        # Detect interactive commands that need a real TTY
        interactive_cmds = ["ollama run", "ollama launch", "python", "node", "powershell", "cmd"]
        is_interactive = any(x in cmd.lower() for x in interactive_cmds)
        
        if is_interactive and not self.native_check.isChecked():
            self.output.append_line("⚠️ Interactive command detected. Switching to Native Window for TTY support.", "warn")
            self.native_check.setChecked(True)

        self.output.append_line(f"$ {cmd}","cmd")
        
        if self.native_check.isChecked():
            self.output.append_line(f"Opening native {shell_type} window for: '{cmd}'", "system")
            cflags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            if shell_type == "powershell":
                full_cmd = ["powershell.exe", "-NoExit", "-Command", cmd]
            else:
                full_cmd = ["cmd.exe", "/K", cmd]
            try:
                subprocess.Popen(full_cmd, cwd=cwd, creationflags=cflags)
            except Exception as e:
                self.output.append_line(f"Failed to launch native terminal: {e}", "error")
            return
            
        if self._worker and self._worker.isRunning():
            self._worker.stop()
        
        self._worker = CommandWorker(cmd, cwd=cwd, shell_type=shell_type)
        self._worker.output.connect(self.output.append_line)
        self._worker.done.connect(lambda c: self.output.append_line(
            f"[exit {c}]","success" if c==0 else "error"))
        self._worker.start()

    def _stop(self):
        if self._worker:
            self._worker.stop()
            self.output.append_line("Terminated.","warn")

class SystemPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._timer = QTimer(self); self._timer.timeout.connect(self._update)
        # Activation handled by activate/deactivate (hibernation)

    def activate(self):
        self._update()
        self._timer.start(4000)

    def deactivate(self):
        self._timer.stop()

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
        self._labels["cpu"].setText(f"{cpu:.1f}%")
        rp = int(vm.percent); self._bars["ram"].setValue(rp)
        self._labels["ram"].setText(f"{rp}% — {vm.used//1024**3}/{vm.total//1024**3} GB")
        dp = int(disk.percent); self._bars["disk"].setValue(dp)
        self._labels["disk"].setText(f"{dp}% — {disk.used//1024**3}/{disk.total//1024**3} GB")
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
                self.net_lbl.setText(f"↑ {s//1024} KB/s  ↓ {r//1024} KB/s")
            self._prev_net = net
        except Exception: pass
        try:
            procs = sorted(psutil.process_iter(["pid","name","cpu_percent","memory_percent"]),
                           key=lambda p: p.info["cpu_percent"] or 0, reverse=True)[:12]
            self.proc_list.clear()
            for p in procs:
                self.proc_list.addItem(f" {p.info['name']:<20} CPU:{p.info['cpu_percent']:>4.1f}%")
        except Exception: pass
