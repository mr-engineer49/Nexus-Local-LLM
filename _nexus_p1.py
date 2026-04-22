#!/usr/bin/env python3
"""
NEXUS v2.0 — Local AI & Dev Workspace
• Ollama HTTP streaming  • GitHub API  • AI Agents  • Visual Automation Flows
Single-file PyQt6 desktop app
"""
import sys, os, json, subprocess, shutil, re, time, math
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

try:
    import requests as _req; HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import psutil; HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QLabel, QPushButton, QLineEdit, QTextEdit,
    QListWidget, QListWidgetItem, QComboBox, QFrame, QScrollArea,
    QProgressBar, QDialog, QMessageBox, QFileDialog, QSizePolicy,
    QStackedWidget, QGroupBox, QCheckBox, QSpinBox, QMenu,
    QGraphicsScene, QGraphicsView, QGraphicsItem, QGraphicsRectItem,
    QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsTextItem,
    QInputDialog, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QAbstractItemView, QPlainTextEdit, QStatusBar, QToolButton
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize, QRectF, QPointF, QRect, QEvent
)
from PyQt6.QtGui import (
    QFont, QColor, QTextCursor, QSyntaxHighlighter, QTextCharFormat,
    QPainter, QBrush, QPen, QFontDatabase, QPainterPath, QLinearGradient
)

APP_VERSION   = "2.0"
SETTINGS_FILE = Path.home() / ".nexus_settings.json"
PROJECTS_FILE = Path.home() / ".nexus_projects.json"
SESSIONS_DIR  = Path.home() / ".nexus_sessions"

# ─────────────────────────────────────────────
#  PERSISTENT SETTINGS
# ─────────────────────────────────────────────

class AppSettings:
    _defaults: Dict[str, Any] = {
        "ollama_host":    "http://localhost:11434",
        "ollama_threads": 4,
        "gpu_layers":     0,
        "default_model":  "",
        "github_token":   "",
        "clone_dir":      str(Path.home() / "Projects"),
        "agent_approve":  False,
        "agent_max_steps": 12,
        "autoscroll":     True,
        "timestamps":     True,
        "theme_accent":   "#6e56cf",
    }
    def __init__(self):
        self._data = dict(self._defaults); self.load()
    def load(self):
        try:
            with open(SETTINGS_FILE) as f: self._data.update(json.load(f))
        except Exception: pass
    def save(self):
        try:
            with open(SETTINGS_FILE, "w") as f: json.dump(self._data, f, indent=2)
        except Exception: pass
    def get(self, key, default=None):
        return self._data.get(key, self._defaults.get(key, default))
    def set(self, key, value):
        self._data[key] = value

SETTINGS = AppSettings()

# ─────────────────────────────────────────────
#  THEME  &  STYLESHEET
# ─────────────────────────────────────────────

THEME = {
    "bg": "#0d0d0f", "bg2": "#13131a", "bg3": "#1a1a24",
    "border": "#252535",
    "accent":  SETTINGS.get("theme_accent", "#6e56cf"),
    "accent2": "#9d7ff5",
    "success": "#3ecf8e", "warning": "#f7b731", "error": "#f04452",
    "text": "#e8e8f0", "text2": "#8888aa", "text3": "#555570",
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color:{THEME['bg']}; color:{THEME['text']};
    font-family:'Consolas','JetBrains Mono','Courier New',monospace; font-size:13px;
}}
#sidebar {{
    background-color:{THEME['bg2']}; border-right:1px solid {THEME['border']};
    min-width:200px; max-width:200px;
}}
#sidebar QPushButton {{
    background:transparent; border:none; color:{THEME['text2']};
    text-align:left; padding:10px 18px; font-size:13px; border-radius:0px;
}}
#sidebar QPushButton:hover {{ background-color:{THEME['bg3']}; color:{THEME['text']}; }}
#sidebar QPushButton[active="true"] {{
    background-color:{THEME['bg3']}; color:{THEME['accent2']};
    border-left:2px solid {THEME['accent']};
}}
QPushButton {{
    background-color:{THEME['bg3']}; border:1px solid {THEME['border']};
    color:{THEME['text']}; padding:7px 16px; border-radius:5px; font-size:12px;
}}
QPushButton:hover {{ border-color:{THEME['accent']}; color:{THEME['accent2']}; }}
QPushButton:pressed {{ background-color:{THEME['accent']}; color:white; }}
QPushButton#primary {{
    background-color:{THEME['accent']}; border:1px solid {THEME['accent2']};
    color:white; font-weight:bold;
}}
QPushButton#primary:hover {{ background-color:{THEME['accent2']}; }}
QPushButton#danger {{ background:transparent; border:1px solid {THEME['error']}; color:{THEME['error']}; }}
QPushButton#danger:hover {{ background:{THEME['error']}; color:white; }}
QPushButton#success {{ background:transparent; border:1px solid {THEME['success']}; color:{THEME['success']}; }}
QPushButton#success:hover {{ background:{THEME['success']}; color:{THEME['bg']}; }}
QPushButton#warn {{ background:transparent; border:1px solid {THEME['warning']}; color:{THEME['warning']}; }}
QPushButton#warn:hover {{ background:{THEME['warning']}; color:{THEME['bg']}; }}
QLineEdit, QTextEdit, QComboBox, QPlainTextEdit {{
    background-color:{THEME['bg3']}; border:1px solid {THEME['border']};
    color:{THEME['text']}; padding:7px 10px; border-radius:5px;
    selection-background-color:{THEME['accent']};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{ border-color:{THEME['accent']}; }}
QComboBox::drop-down {{ border:none; padding-right:8px; }}
QComboBox QAbstractItemView {{
    background-color:{THEME['bg3']}; border:1px solid {THEME['border']};
    color:{THEME['text']}; selection-background-color:{THEME['accent']};
}}
#logview {{
    background-color:#080810; border:1px solid {THEME['border']}; color:#b0ffb0;
    font-family:'Consolas','Courier New',monospace; font-size:12px;
    border-radius:6px; padding:6px;
}}
QListWidget {{
    background-color:{THEME['bg2']}; border:1px solid {THEME['border']};
    border-radius:6px; outline:none;
}}
QListWidget::item {{ padding:8px 12px; border-bottom:1px solid {THEME['border']}; color:{THEME['text2']}; }}
QListWidget::item:selected {{ background-color:{THEME['bg3']}; color:{THEME['accent2']}; border-left:2px solid {THEME['accent']}; }}
QListWidget::item:hover {{ background-color:{THEME['bg3']}; color:{THEME['text']}; }}
QTreeWidget {{
    background-color:{THEME['bg2']}; border:1px solid {THEME['border']};
    border-radius:6px; outline:none; color:{THEME['text2']};
}}
QTreeWidget::item:selected {{ background-color:{THEME['bg3']}; color:{THEME['accent2']}; }}
QTreeWidget::item:hover {{ background-color:{THEME['bg3']}; color:{THEME['text']}; }}
QHeaderView::section {{
    background-color:{THEME['bg3']}; border:none;
    border-bottom:1px solid {THEME['border']}; color:{THEME['text2']}; padding:4px 8px;
}}
QTabWidget::pane {{ border:1px solid {THEME['border']}; background:{THEME['bg']}; }}
QTabBar::tab {{
    background:{THEME['bg2']}; color:{THEME['text2']};
    padding:8px 18px; border:1px solid {THEME['border']}; border-bottom:none;
}}
QTabBar::tab:selected {{ background:{THEME['bg']}; color:{THEME['accent2']}; border-bottom:2px solid {THEME['accent']}; }}
QTabBar::tab:hover {{ color:{THEME['text']}; }}
QProgressBar {{
    background-color:{THEME['bg3']}; border:1px solid {THEME['border']};
    border-radius:4px; height:6px; text-align:center; color:transparent;
}}
QProgressBar::chunk {{ background-color:{THEME['accent']}; border-radius:4px; }}
QScrollBar:vertical {{ background:{THEME['bg2']}; width:6px; border:none; }}
QScrollBar::handle:vertical {{ background:{THEME['border']}; border-radius:3px; min-height:20px; }}
QScrollBar::handle:vertical:hover {{ background:{THEME['text3']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
QScrollBar:horizontal {{ background:{THEME['bg2']}; height:6px; border:none; }}
QScrollBar::handle:horizontal {{ background:{THEME['border']}; border-radius:3px; }}
QGroupBox {{
    border:1px solid {THEME['border']}; border-radius:6px; margin-top:10px;
    padding-top:8px; color:{THEME['text2']}; font-size:11px;
    text-transform:uppercase; letter-spacing:1px;
}}
QGroupBox::title {{ subcontrol-origin:margin; left:10px; padding:0 4px; color:{THEME['text3']}; }}
QSplitter::handle {{ background:{THEME['border']}; }}
QSplitter::handle:horizontal {{ width:1px; }}
QSplitter::handle:vertical {{ height:1px; }}
QCheckBox {{ color:{THEME['text2']}; spacing:6px; }}
QCheckBox::indicator {{
    width:14px; height:14px; border:1px solid {THEME['border']};
    border-radius:3px; background:{THEME['bg3']};
}}
QCheckBox::indicator:checked {{ background:{THEME['accent']}; border-color:{THEME['accent']}; }}
QSpinBox {{ background:{THEME['bg3']}; border:1px solid {THEME['border']}; color:{THEME['text']}; padding:5px 8px; border-radius:4px; }}
QStatusBar {{ background:{THEME['bg2']}; color:{THEME['text3']}; border-top:1px solid {THEME['border']}; font-size:11px; }}
QGraphicsView {{ background:{THEME['bg']}; border:1px solid {THEME['border']}; border-radius:6px; }}
"""

# ─────────────────────────────────────────────
#  WORKER THREADS
# ─────────────────────────────────────────────

class CommandWorker(QThread):
    """Run any shell command, stream output line by line."""
    output      = pyqtSignal(str)
    done        = pyqtSignal(int)
    started_sig = pyqtSignal()

    def __init__(self, cmd, cwd=None, shell_type="cmd", env=None):
        super().__init__()
        self.cmd=cmd; self.cwd=cwd; self.shell_type=shell_type
        self.env=env; self._proc=None; self._stop=False

    def run(self):
        self.started_sig.emit()
        try:
            if self.shell_type == "git_bash":
                bash = self._find_git_bash()
                full_cmd = [bash, "-c", self.cmd] if bash else self.cmd
            elif self.shell_type == "powershell":
                full_cmd = ["powershell", "-NoProfile", "-Command", self.cmd]
            else:
                full_cmd = self.cmd
            use_shell = isinstance(full_cmd, str)
            self._proc = subprocess.Popen(
                full_cmd, cwd=self.cwd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, shell=use_shell, env=self.env, bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0
            )
            for line in iter(self._proc.stdout.readline, ""):
                if self._stop: break
                self.output.emit(line.rstrip())
            self._proc.wait()
            self.done.emit(self._proc.returncode)
        except Exception as e:
            self.output.emit(f"[ERROR] {e}"); self.done.emit(-1)

    def stop(self):
        self._stop = True
        if self._proc:
            try: self._proc.terminate()
            except Exception: pass

    def _find_git_bash(self):
        for c in [r"C:\Program Files\Git\bin\bash.exe",
                  r"C:\Program Files (x86)\Git\bin\bash.exe",
                  shutil.which("bash")]:
            if c and Path(c).exists(): return c
        return None


class OllamaListWorker(QThread):
    result = pyqtSignal(list)
    error  = pyqtSignal(str)
    def run(self):
        try:
            proc = subprocess.run(["ollama","list"], capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0)
            models = []
            for line in proc.stdout.strip().splitlines()[1:]:
                parts = line.split()
                if parts:
                    models.append({"name":parts[0], "size":parts[2] if len(parts)>2 else "?", "raw":line})
            self.result.emit(models)
        except FileNotFoundError:
            self.error.emit("ollama not found — install from https://ollama.com")
        except Exception as e:
            self.error.emit(str(e))


class OllamaAPIWorker(QThread):
    """Stream chat tokens via Ollama /api/chat HTTP endpoint."""
    token = pyqtSignal(str)
    done  = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, host, model, messages, system=""):
        super().__init__()
        self.host=host; self.model=model
        self.messages=messages; self.system=system; self._stop=False

    def run(self):
        if not HAS_REQUESTS:
            self.error.emit("Install requests: pip install requests"); return
        try:
            import requests as rq
            payload = {"model": self.model, "messages": self.messages, "stream": True}
            if self.system:
                payload["system"] = self.system
            full = ""
            with rq.post(f"{self.host}/api/chat", json=payload,
                         stream=True, timeout=120) as resp:
                resp.raise_for_status()
                for raw in resp.iter_lines():
                    if self._stop: break
                    if not raw: continue
                    data  = json.loads(raw)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        self.token.emit(chunk); full += chunk
                    if data.get("done"): break
            self.done.emit(full)
        except Exception as e:
            self.error.emit(str(e))

    def stop(self): self._stop = True


class OllamaModelInfoWorker(QThread):
    result = pyqtSignal(dict)
    error  = pyqtSignal(str)
    def __init__(self, host, model):
        super().__init__(); self.host=host; self.model=model
    def run(self):
        if not HAS_REQUESTS:
            self.error.emit("requests not installed"); return
        try:
            import requests as rq
            r = rq.post(f"{self.host}/api/show", json={"name":self.model}, timeout=15)
            r.raise_for_status(); self.result.emit(r.json())
        except Exception as e:
            self.error.emit(str(e))


class GitHubWorker(QThread):
    """Call GitHub REST API v3."""
    result = pyqtSignal(object)
    error  = pyqtSignal(str)

    def __init__(self, endpoint, method="GET", body=None, token="", params=None):
        super().__init__()
        self.endpoint=endpoint; self.method=method
        self.body=body; self.token=token; self.params=params or {}

    def run(self):
        if not HAS_REQUESTS:
            self.error.emit("requests not installed"); return
        try:
            import requests as rq
            headers = {"Accept":"application/vnd.github+json",
                       "X-GitHub-Api-Version":"2022-11-28"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            url = "https://api.github.com" + self.endpoint
            if self.method == "POST":
                resp = rq.post(url, headers=headers, json=self.body, timeout=20)
            else:
                resp = rq.get(url, headers=headers, params=self.params, timeout=20)
            resp.raise_for_status()
            self.result.emit(resp.json())
        except Exception as e:
            self.error.emit(str(e))


class AgentWorker(QThread):
    """ReAct autonomous agent loop: Thought→Tool→Observation→repeat."""
    step     = pyqtSignal(str, str)  # (kind, text): thought|tool|observation|done|error
    finished = pyqtSignal(str)

    _SYSTEM = """You are NEXUS Agent — an autonomous AI assistant.
Complete the user's task step by step using tools.

To call a tool, respond EXACTLY:
THOUGHT: <your reasoning>
TOOL: <tool_name>
ARGS: {"key": "value", ...}

Available tools:
  read_file   — {"path":"..."}
  write_file  — {"path":"...","content":"..."}
  run_command — {"cmd":"...","cwd":"..."}
  list_dir    — {"path":"..."}
  git_command — {"cmd":"...","repo":"..."}

When done, respond EXACTLY:
THOUGHT: <summary>
DONE: <final answer>
"""

    def __init__(self, host, model, task, max_steps=12):
        super().__init__()
        self.host=host; self.model=model
        self.task=task; self.max_steps=max_steps; self._stop=False

    def run(self):
        if not HAS_REQUESTS:
            self.step.emit("error","requests not installed"); return
        import requests as rq
        msgs = [{"role":"system","content":self._SYSTEM},
                {"role":"user","content":self.task}]

        for _ in range(self.max_steps):
            if self._stop:
                self.step.emit("error","Stopped."); self.finished.emit("Stopped."); return
            try:
                resp = rq.post(f"{self.host}/api/chat",
                    json={"model":self.model,"messages":msgs,"stream":False}, timeout=120)
                resp.raise_for_status()
                content = resp.json()["message"]["content"].strip()
            except Exception as e:
                self.step.emit("error", str(e)); self.finished.emit(str(e)); return

            # Emit THOUGHT
            if "THOUGHT:" in content:
                thought = content.split("THOUGHT:",1)[1].split("\n")[0].strip()
                self.step.emit("thought", thought)

            # DONE?
            if "DONE:" in content:
                answer = content.split("DONE:",1)[1].strip()
                self.step.emit("done", answer); self.finished.emit(answer); return

            # TOOL call?
            if "TOOL:" in content and "ARGS:" in content:
                obs = self._exec_tool_call(content)
                self.step.emit("observation", obs[:1500])
                msgs.append({"role":"assistant","content":content})
                msgs.append({"role":"user","content":f"OBSERVATION:\n{obs[:1500]}"})
            else:
                # plain response — nudge
                self.step.emit("thought", content[:300])
                msgs.append({"role":"assistant","content":content})
                msgs.append({"role":"user","content":"Continue. Use a tool or respond with DONE."})

        self.step.emit("error", f"Max {self.max_steps} steps reached.")
        self.finished.emit("Max steps reached.")

    def _exec_tool_call(self, content: str) -> str:
        try:
            tool = content.split("TOOL:",1)[1].split("\n")[0].strip()
            args_raw = content.split("ARGS:",1)[1].strip()
            i = args_raw.index("{"); d=0
            for j,ch in enumerate(args_raw[i:],i):
                if ch=="{": d+=1
                elif ch=="}": d-=1
                if d==0: end=j; break
            args = json.loads(args_raw[i:end+1])
            self.step.emit("tool", f"{tool}({json.dumps(args)})")
            return self._run_tool(tool, args)
        except Exception as e:
            return f"[parse error] {e}"

    def _run_tool(self, tool: str, args: dict) -> str:
        try:
            if tool == "read_file":
                return Path(args["path"]).read_text(errors="replace")[:4000]
            elif tool == "write_file":
                p = Path(args["path"]); p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(args.get("content",""))
                return f"Wrote {len(args.get('content',''))} chars to {args['path']}"
            elif tool == "list_dir":
                items = sorted(Path(args["path"]).iterdir(), key=lambda x: (x.is_file(), x.name))
                return "\n".join(f"{'📁' if i.is_dir() else '📄'} {i.name}" for i in items)
            elif tool in ("run_command","git_command"):
                cwd = args.get("cwd") or args.get("repo",".")
                r = subprocess.run(args["cmd"], cwd=cwd, shell=True,
                    capture_output=True, text=True, timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0)
                return (r.stdout+r.stderr).strip()[:3000] or f"[exit {r.returncode}]"
            else:
                return f"Unknown tool: {tool}"
        except Exception as e:
            return f"[error] {e}"

    def stop(self): self._stop = True
