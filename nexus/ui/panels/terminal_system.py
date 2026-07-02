import subprocess, sys, os, shutil, json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QGroupBox, QProgressBar, QListWidget, QComboBox, QFileDialog, QCheckBox, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, QEvent, QThread, pyqtSignal
from ...core.config import HAS_PSUTIL
from ...core.style import THEME
from ...core.workers import CommandWorker
from ..widgets import LogView

if HAS_PSUTIL:
    import psutil

class SystemMonitorWorker(QThread):
    stats_updated = pyqtSignal(dict)
    def run(self):
        if not HAS_PSUTIL: return
        try:
            import sys
            cpu  = psutil.cpu_percent(interval=None)
            vm   = psutil.virtual_memory()
            disk = psutil.disk_usage("/" if sys.platform!="win32" else "C:\\")
            swap = psutil.swap_memory()
            
            proc_list = []
            try:
                for p in psutil.process_iter(["name", "cpu_percent"]):
                    try:
                        cpu_p = p.info["cpu_percent"] or 0.0
                        proc_list.append((p.info["name"], cpu_p))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                proc_list = sorted(proc_list, key=lambda x: x[1], reverse=True)[:12]
            except Exception:
                pass
                
            net_io = None
            try:
                net_io = psutil.net_io_counters()
            except Exception:
                pass
                
            self.stats_updated.emit({
                "cpu": cpu,
                "ram_percent": vm.percent,
                "ram_used": vm.used,
                "ram_total": vm.total,
                "disk_percent": disk.percent,
                "disk_used": disk.used,
                "disk_total": disk.total,
                "swap_percent": swap.percent,
                "procs": proc_list,
                "net_io": net_io
            })
        except Exception:
            pass

PRESETS_FILE = Path.home() / ".nexus_cmd_presets.json"

class TerminalPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._worker  = None
        self._history = []
        self._hist_idx = -1
        self._presets = []
        self._load_presets()
        self._build_ui()
        self._populate_presets()

    def activate(self): pass
    def deactivate(self): pass

    def _load_presets(self):
        if PRESETS_FILE.exists():
            try:
                with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                    self._presets = json.load(f)
            except Exception:
                self._presets = []
        else:
            # Default presets
            self._presets = [
                {"label": "Node: dev server", "cmd": "npm run dev"},
                {"label": "Python: run tests", "cmd": "pytest"},
                {"label": "Docker: up", "cmd": "docker-compose up -d"},
                {"label": "Git: status", "cmd": "git status"},
            ]
            self._save_presets()

    def _save_presets(self):
        try:
            with open(PRESETS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._presets, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(16,16,16,16); root.setSpacing(10)
        
        # Header row
        hdr = QHBoxLayout()
        t = QLabel("Integrated Terminal")
        t.setStyleSheet(f"font-size:18px;font-weight:bold;color:{THEME['text']};")
        hdr.addWidget(t); hdr.addStretch()
        
        self.shell_combo = QComboBox()
        for s in self._detect_shells():
            self.shell_combo.addItem(s["label"], s["type"])
        hdr.addWidget(self.shell_combo)
        
        self.native_check = QCheckBox("Run in Native Window")
        self.native_check.setStyleSheet(f"color:{THEME['text']};")
        self.native_check.setCursor(Qt.CursorShape.PointingHandCursor)
        hdr.addWidget(self.native_check)

        btn_clear = QPushButton("Clear"); btn_clear.clicked.connect(lambda: self.output.clear_log())
        hdr.addWidget(btn_clear)
        root.addLayout(hdr)

        # Working directory row
        wd_row = QHBoxLayout()
        wd_row.addWidget(QLabel("Working dir:"))
        self.cwd_input = QLineEdit(str(Path.home()))
        btn_cwd = QPushButton("Browse"); btn_cwd.clicked.connect(self._browse_cwd)
        wd_row.addWidget(self.cwd_input); wd_row.addWidget(btn_cwd)
        root.addLayout(wd_row)

        # Splitter between Terminal Output and Presets Library
        main_split = QSplitter(Qt.Orientation.Horizontal)

        # LEFT SIDE: Terminal Output & Input
        term_container = QWidget(); term_layout = QVBoxLayout(term_container); term_layout.setContentsMargins(0,0,0,0); term_layout.setSpacing(8)
        
        self.output = LogView(); self.output.append_line("NEXUS Terminal ready.","system")
        term_layout.addWidget(self.output, 1)

        # Quick default commands
        quick = QHBoxLayout()
        for label, cmd in [
            ("python --version", "python --version"),
            ("node --version", "node --version"),
            ("git --version", "git --version"),
            ("pip list", "pip list"),
            ("dir" if sys.platform=="win32" else "ls", "dir" if sys.platform=="win32" else "ls"),
            ("ollama list", "ollama list")
        ]:
            b = QPushButton(label); b.setFixedHeight(26)
            b.setStyleSheet("font-size:11px;padding:2px 8px;")
            b.clicked.connect(lambda _, c=cmd: self._run(c))
            quick.addWidget(b)
        quick.addStretch()
        term_layout.addLayout(quick)

        # Terminal command input row
        inp_row = QHBoxLayout()
        lbl = QLabel("$"); lbl.setStyleSheet(f"color:{THEME['accent2']};font-weight:bold;")
        self.cmd_input = QLineEdit(); self.cmd_input.setPlaceholderText("Enter command…")
        self.cmd_input.returnPressed.connect(self._on_enter)
        self.cmd_input.installEventFilter(self)
        self.run_btn  = QPushButton("▶  Run"); self.run_btn.setObjectName("primary"); self.run_btn.clicked.connect(self._on_enter)
        self.stop_btn = QPushButton("⏹"); self.stop_btn.setFixedWidth(36); self.stop_btn.clicked.connect(self._stop)
        inp_row.addWidget(lbl); inp_row.addWidget(self.cmd_input)
        inp_row.addWidget(self.run_btn); inp_row.addWidget(self.stop_btn)
        term_layout.addLayout(inp_row)
        
        main_split.addWidget(term_container)

        # RIGHT SIDE: Presets Group Box
        presets_box = QGroupBox("Command Library")
        pbl = QVBoxLayout(presets_box); pbl.setSpacing(6)
        
        self.presets_list = QListWidget()
        self.presets_list.currentItemChanged.connect(self._on_preset_select)
        pbl.addWidget(self.presets_list, 1)
        
        pbl.addWidget(QLabel("Label:"))
        self.preset_label_input = QLineEdit()
        self.preset_label_input.setPlaceholderText("e.g. Run tests")
        pbl.addWidget(self.preset_label_input)
        
        pbl.addWidget(QLabel("Command:"))
        self.preset_cmd_input = QLineEdit()
        self.preset_cmd_input.setPlaceholderText("e.g. pytest")
        pbl.addWidget(self.preset_cmd_input)
        
        pbl_btn_row = QHBoxLayout()
        self.btn_run_preset = QPushButton("▶ Run"); self.btn_run_preset.setObjectName("success")
        self.btn_run_preset.clicked.connect(self._run_selected_preset)
        self.btn_save_preset = QPushButton("💾 Save")
        self.btn_save_preset.clicked.connect(self._save_custom_preset)
        self.btn_del_preset = QPushButton("🗑"); self.btn_del_preset.setObjectName("danger")
        self.btn_del_preset.clicked.connect(self._delete_selected_preset)
        pbl_btn_row.addWidget(self.btn_run_preset, 1)
        pbl_btn_row.addWidget(self.btn_save_preset)
        pbl_btn_row.addWidget(self.btn_del_preset)
        pbl.addLayout(pbl_btn_row)

        main_split.addWidget(presets_box)
        
        main_split.setSizes([600, 240])
        root.addWidget(main_split, 1)

    def _populate_presets(self):
        self.presets_list.clear()
        for p in self._presets:
            self.presets_list.addItem(p["label"])

    def _on_preset_select(self, current, previous):
        if not current:
            self.preset_label_input.clear()
            self.preset_cmd_input.clear()
            return
        idx = self.presets_list.row(current)
        if 0 <= idx < len(self._presets):
            p = self._presets[idx]
            self.preset_label_input.setText(p["label"])
            self.preset_cmd_input.setText(p["cmd"])

    def _run_selected_preset(self):
        cmd = self.preset_cmd_input.text().strip()
        if cmd:
            self._run(cmd)

    def _save_custom_preset(self):
        lbl = self.preset_label_input.text().strip()
        cmd = self.preset_cmd_input.text().strip()
        if not lbl or not cmd:
            QMessageBox.warning(self, "Invalid Preset", "Enter both preset label and command.")
            return
            
        # Check if updating or adding new
        current_item = self.presets_list.currentItem()
        if current_item:
            idx = self.presets_list.row(current_item)
            self._presets[idx] = {"label": lbl, "cmd": cmd}
        else:
            self._presets.append({"label": lbl, "cmd": cmd})
            
        self._save_presets()
        self._populate_presets()
        # Find and select the saved preset
        for i in range(self.presets_list.count()):
            if self.presets_list.item(i).text() == lbl:
                self.presets_list.setCurrentRow(i)
                break
        QMessageBox.information(self, "Saved", f"Preset '{lbl}' saved.")

    def _delete_selected_preset(self):
        current_item = self.presets_list.currentItem()
        if not current_item:
            return
        idx = self.presets_list.row(current_item)
        lbl = self._presets[idx]["label"]
        self._presets.pop(idx)
        self._save_presets()
        self._populate_presets()
        self.preset_label_input.clear()
        self.preset_cmd_input.clear()
        QMessageBox.information(self, "Deleted", f"Preset '{lbl}' deleted.")

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

        stripped = cmd.strip()
        if stripped.lower() == "cd" or stripped.lower().startswith("cd ") or stripped.lower().startswith("cd\t"):
            parts = stripped.split(None, 1)
            target = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else str(Path.home())
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
        self._monitor_worker = None
        # Activation handled by activate/deactivate (hibernation)

    def activate(self):
        self._update()
        self._timer.start(4000)

    def deactivate(self):
        self._timer.stop()
        if self._monitor_worker and self._monitor_worker.isRunning():
            self._monitor_worker.terminate()

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
        if self._monitor_worker and self._monitor_worker.isRunning():
            return # Let the current run finish
        
        self._monitor_worker = SystemMonitorWorker()
        self._monitor_worker.stats_updated.connect(self._on_stats_updated)
        self._monitor_worker.start()

    def _on_stats_updated(self, d):
        cpu = d["cpu"]
        self._bars["cpu"].setValue(int(cpu))
        self._labels["cpu"].setText(f"{cpu:.1f}%")
        
        rp = d["ram_percent"]
        self._bars["ram"].setValue(int(rp))
        self._labels["ram"].setText(f"{rp}% — {d['ram_used']//1024**3}/{d['ram_total']//1024**3} GB")
        
        dp = d["disk_percent"]
        self._bars["disk"].setValue(int(dp))
        self._labels["disk"].setText(f"{dp}% — {d['disk_used']//1024**3}/{d['disk_total']//1024**3} GB")
        
        sp = d["swap_percent"]
        self._bars["swap"].setValue(int(sp))
        self._labels["swap"].setText(f"{sp}%")
        
        for key, bar in self._bars.items():
            v = bar.value()
            c = THEME["success"] if v<60 else (THEME["warning"] if v<85 else THEME["error"])
            bar.setStyleSheet(f"QProgressBar::chunk{{background:{c};border-radius:4px;}}")
            
        net = d["net_io"]
        if net:
            if self._prev_net:
                s = net.bytes_sent - self._prev_net.bytes_sent
                r = net.bytes_recv - self._prev_net.bytes_recv
                self.net_lbl.setText(f"↑ {s//1024} KB/s  ↓ {r//1024} KB/s")
            self._prev_net = net
            
        self.proc_list.clear()
        for name, cpu_p in d["procs"]:
            self.proc_list.addItem(f" {name:<20} CPU:{cpu_p:>4.1f}%")
