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
    QGraphicsLineItem, QInputDialog, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QAbstractItemView, QPlainTextEdit, QStatusBar, QToolButton
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize, QRectF, QPointF, QRect, QEvent, QLineF
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
        self.endpoint = endpoint
        self.method = method
        self.body = body
        self.token = token
        self.params = params or {}

    def run(self):
        if not HAS_REQUESTS:
            self.error.emit("requests not installed")
            return
        try:
            import requests as rq
            headers = {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
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


class WorkflowWorker(QThread):
    """Executes a workflow graph in a background thread."""
    step_info = pyqtSignal(str, str) # kind, text
    highlight = pyqtSignal(int, bool) # node_idx, active
    finished  = pyqtSignal()

    def __init__(self, data, host="http://localhost:11434"):
        super().__init__()
        self.data = data
        self.host = host
        self._stop = False

    def run(self):
        nodes = self.data.get("nodes", [])
        edges = self.data.get("edges", [])
        
        # Build adjacency
        adj = [[] for _ in range(len(nodes))]
        in_degree = [0] * len(nodes)
        for e in edges:
            adj[e["from"]].append(e["to"])
            in_degree[e["to"]] += 1
            
        # Topological Sort (Kahn's)
        queue = [i for i, d in enumerate(in_degree) if d == 0]
        executed_indices = []
        
        # Shared context for nodes
        context = {"last_output": ""}

        while queue and not self._stop:
            idx = queue.pop(0)
            executed_indices.append(idx)
            
            node_cfg = nodes[idx]
            ntype = node_cfg["type"]
            cfg = node_cfg.get("config", {})
            
            self.highlight.emit(idx, True)
            self.step_info.emit("cmd", f"Running: {ntype}")
            
            try:
                res = self._execute_node(ntype, cfg, context)
                if res is False: # Condition failed or error
                    self.step_info.emit("warn", f"Workflow stopped at {ntype}")
                    self.highlight.emit(idx, False)
                    break 
                context["last_output"] = str(res)
            except Exception as e:
                self.step_info.emit("error", f"Node {idx} failed: {e}")
                self.highlight.emit(idx, False)
                break
                
            self.highlight.emit(idx, False)
            
            for neighbor in adj[idx]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        self.finished.emit()

    def stop(self): self._stop = True

    def _execute_node(self, ntype, cfg, context):
        import subprocess, sys, json
        # Common subprocess flags
        flags = subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0
        
        if ntype == "terminal":
            cmd = cfg.get("cmd", "echo ok")
            cwd = cfg.get("cwd", ".") or "."
            r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=60, creationflags=flags)
            out = (r.stdout + r.stderr).strip()
            self.step_info.emit("info", out[:500] or "[done]")
            return out
            
        elif ntype == "git":
            cmd = cfg.get("cmd", "git status")
            repo = cfg.get("repo", ".") or "."
            r = subprocess.run(cmd, cwd=repo, shell=True, capture_output=True, text=True, timeout=60, creationflags=flags)
            out = (r.stdout + r.stderr).strip()
            self.step_info.emit("info", out[:300] or "[done]")
            return out
            
        elif ntype == "ai":
            model = cfg.get("model") or "llama3"
            prompt = cfg.get("prompt", "Analyze this:")
            input_text = context.get("last_output", "")
            full_prompt = f"{prompt}\n\nInput Context:\n{input_text}"
            
            self.step_info.emit("thought", f"Calling AI ({model})...")
            try:
                import requests as rq
                resp = rq.post(f"{self.host}/api/generate", 
                             json={"model": model, "prompt": full_prompt, "stream": False}, 
                             timeout=120)
                resp.raise_for_status()
                ans = resp.json().get("response", "")
                self.step_info.emit("done", ans[:500])
                return ans
            except Exception as e:
                self.step_info.emit("error", f"AI Node failed: {e}")
                return False
                
        elif ntype == "condition":
            pattern = cfg.get("pattern", "")
            input_text = context.get("last_output", "")
            import re
            match = bool(re.search(pattern, input_text)) if pattern else True
            self.step_info.emit("info", f"Condition '{pattern}': {'MATCH' if match else 'NO MATCH'}")
            if not match and cfg.get("on_false") == "stop":
                return False
            return input_text
            
        elif ntype == "notify":
            msg = cfg.get("message", "Workflow step complete")
            self.step_info.emit("success", f"🔔 {msg}")
            return context.get("last_output")
            
        return True


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


# ─────────────────────────────────────────────
#  LOG WIDGET  +  DIFF HIGHLIGHTER
# ─────────────────────────────────────────────

class LogView(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setObjectName("logview"); self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.document().setMaximumBlockCount(2000)
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
        
        def _on_clone_done(code):
            if code == 0:
                self.log.append_line("Clone complete.","success")
                name = url.rstrip("/").split("/")[-1].replace(".git","")
                path = str(Path(dest) / name)
                # Auto-add to projects
                try:
                    projs = []
                    if PROJECTS_FILE.exists():
                        with open(PROJECTS_FILE) as f: projs = json.load(f)
                    if not any(p["path"] == path for p in projs):
                        projs.append({"name": name, "path": path})
                        with open(PROJECTS_FILE, "w") as f: json.dump(projs, f, indent=2)
                        self.log.append_line(f"Registered project: {name}","success")
                        # Trigger global refresh if main window exists
                        mw = QApplication.activeWindow()
                        if hasattr(mw, "refresh_all_projects"): mw.refresh_all_projects()
                except Exception as e:
                    self.log.append_line(f"Failed to auto-register: {e}","error")
            else:
                self.log.append_line("Clone failed.","error")
                
        w.done.connect(_on_clone_done)
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

    def set_highlight(self, active: bool):
        pen = self.pen()
        if active:
            pen.setWidth(3); pen.setColor(QColor(THEME["accent2"]))
        else:
            info = self.TYPES.get(self.node_type, self.TYPES["terminal"])
            pen.setWidth(1); pen.setColor(QColor(info["border"]))
        self.setPen(pen)

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
        self._temp_edge: Optional[QGraphicsLineItem] = None

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
        pos = event.scenePos()
        items = self.items(pos)
        
        # 1. Detection for port-based dragging
        for item in items:
            if isinstance(item, QGraphicsEllipseItem) and isinstance(item.parentItem(), FlowNode):
                node = item.parentItem()
                if item == node._out_port:
                    self._pending_src = node
                    self._temp_edge = QGraphicsLineItem(QLineF(node.out_port_scene_pos(), pos))
                    pen = QPen(QColor(THEME["accent2"]), 2, Qt.PenStyle.DashLine)
                    self._temp_edge.setPen(pen)
                    self.addItem(self._temp_edge)
                    return

        # 2. Search for clicked node for context/other events
        clicked_node = None
        for item in items:
            if isinstance(item, FlowNode):
                clicked_node = item; break

        if event.button() == Qt.MouseButton.RightButton and clicked_node:
            self._show_node_context_menu(clicked_node, event.screenPos())
            return
            
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._temp_edge:
            line = self._temp_edge.line()
            line.setP2(event.scenePos())
            self._temp_edge.setLine(line)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._temp_edge:
            pos = event.scenePos()
            items = self.items(pos)
            dst_node = None
            for item in items:
                if isinstance(item, QGraphicsEllipseItem) and isinstance(item.parentItem(), FlowNode):
                    node = item.parentItem()
                    if item == node._in_port and node != self._pending_src:
                        dst_node = node; break
                elif isinstance(item, FlowNode): # Allow dropping on node itself
                    if item != self._pending_src:
                        dst_node = item; break
            
            if dst_node:
                # Check for existing edge
                exists = any(e.src == self._pending_src and e.dst == dst_node for e in self._pending_src._edges_out)
                if not exists:
                    self.connect_nodes(self._pending_src, dst_node)
            
            self.removeItem(self._temp_edge)
            self._temp_edge = None
            self._pending_src = None
            return
        super().mouseReleaseEvent(event)

    def _show_node_context_menu(self, node: FlowNode, screen_pos):
        menu = QMenu()
        menu.setStyleSheet(STYLESHEET)
        act_cfg = menu.addAction("⚙ Configure")
        act_del = menu.addAction("🗑 Delete")
        
        # Convert QPointF (screen) to QPoint (integer) for exec
        action = menu.exec(screen_pos.toPoint())
        if action == act_cfg:
            self._configure_node(node)
        elif action == act_del:
            for e in node._edges_out[:] + node._edges_in[:]: e.remove()
            self._nodes.remove(node)
            self.removeItem(node)

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
        self.log.append_line("=== Starting workflow execution ===","cmd")
        data = self.canvas.to_dict()
        if not data["nodes"]:
            self.log.append_line("No nodes to execute.","warn"); return
            
        self._worker = WorkflowWorker(data, host=SETTINGS.get("ollama_host"))
        self._worker.step_info.connect(self.log.append_line)
        self._worker.highlight.connect(self._highlight_node)
        self._worker.finished.connect(lambda: self.log.append_line("=== Workflow complete ===","success"))
        
        # Disable buttons
        # (Add UI state management if needed)
        self._worker.start()

    def _highlight_node(self, idx, active):
        if 0 <= idx < len(self.canvas._nodes):
            self.canvas._nodes[idx].set_highlight(active)

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
        self._timer.start(4000); self._update()

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
        if not HAS_PSUTIL or not self.isVisible(): return
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
        self.btn_term = QPushButton("🐚  Open in Terminal"); self.btn_term.clicked.connect(self._open_terminal)
        for b in [self.btn_install,self.btn_run,self.btn_dev,self.btn_test,self.btn_stop,self.btn_term]:
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

    def _open_terminal(self):
        path = self.proj_combo.itemData(self.proj_combo.currentIndex())
        if not path: return
        mw = QApplication.activeWindow()
        if hasattr(mw, "_switch"):
            # Switch to Terminal panel (index 8 based on MainWindow pages)
            for i, btn in enumerate(mw._nav_btns):
                if "Terminal" in btn.text():
                    mw._switch(i)
                    term_panel = mw._stack.widget(i)
                    if hasattr(term_panel, "cwd_input"):
                        term_panel.cwd_input.setText(path)
                    break

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


# ─────────────────────────────────────────────
#  STATUS DASHBOARD
# ─────────────────────────────────────────────

class StatusDashboard(QWidget):
    """Live overview: Ollama status, active models, agent sessions, system resources."""

    def __init__(self):
        super().__init__()
        self._last_sess_count = -1
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
        # 1. Ollama status (Background thread already good)
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

        # 2. Lazy Sessions refresh
        if SESSIONS_DIR.exists():
            files = sorted(SESSIONS_DIR.glob("*.json"), reverse=True)
            if len(files) == self._last_sess_count and not self.underMouse(): 
                # Skip expensive UI rebuild if count hasn't changed unless user is interacting
                pass
            else:
                self._last_sess_count = len(files)
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
            ("🤖","Ollama"),("📁","Git"),("🐙","GitHub"),
            ("🔗","Agent"),("🎬","Agent Studio"),("🚀","Projects"),
            ("⚡","Workflows"),("📡","Status"),("⌨","Terminal"),
            ("📊","System"),("⚙","Settings"),
        ]
        panels = [
            OllamaPanel(), GitPanel(), GitHubPanel(),
            AgentPanel(), AgentStudioPanel(), ProjectRunnerPanel(),
            WorkflowPanel(), StatusDashboard(), TerminalPanel(),
            SystemPanel(), SettingsPanel(),
        ]

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

    def refresh_all_projects(self):
        """Broadcast project list refresh to all relevant panels."""
        for i in range(self._stack.count()):
            panel = self._stack.widget(i)
            if hasattr(panel, "_refresh_list"):
                panel._refresh_list()
            elif hasattr(panel, "_refresh_combo"):
                panel._refresh_combo()
            elif hasattr(panel, "refresh_models"): # some panels use this
                pass

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
