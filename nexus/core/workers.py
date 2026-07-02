import subprocess, sys, json, re, time, requests
from datetime import datetime
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from .config import SETTINGS, SESSIONS_DIR
from ..utils.process import kill_process_tree, find_git_bash

try:
    import requests as rq
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

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
                bash = find_git_bash()
                full_cmd = [bash, "-c", self.cmd] if bash else self.cmd
            elif self.shell_type == "powershell":
                full_cmd = ["powershell", "-NoProfile", "-Command", self.cmd]
            else:
                full_cmd = self.cmd
            
            use_shell = isinstance(full_cmd, str)
            self._proc = subprocess.Popen(
                full_cmd, cwd=self.cwd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", 
                shell=use_shell, env=self.env, bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0
            )
            for line in iter(self._proc.stdout.readline, ""):
                if self._stop: break
                self.output.emit(line.rstrip())
            self._proc.wait()
            self.done.emit(self._proc.returncode if self._proc else 0)
        except Exception as e:
            self.output.emit(f"[ERROR] {e}"); self.done.emit(-1)

    def stop(self):
        self._stop = True
        if self._proc:
            try:
                kill_process_tree(self._proc.pid)
            except Exception:
                pass
        self.wait() # Wait for the thread to actually finish

class OllamaListWorker(QThread):
    result = pyqtSignal(list)
    def run(self):
        if not HAS_REQUESTS: return
        try:
            r = rq.get(f"{SETTINGS.get('ollama_host')}/api/tags", timeout=5)
            r.raise_for_status()
            self.result.emit(r.json().get("models", []))
        except Exception: self.result.emit([])

class OllamaAPIWorker(QThread):
    token = pyqtSignal(str)
    done  = pyqtSignal(str)
    error = pyqtSignal(str)
    def __init__(self, host, model, messages, system=""):
        super().__init__()
        self.host=host; self.model=model; self.messages=messages; self.system=system; self._stop=False
    def run(self):
        if not HAS_REQUESTS: self.error.emit("requests not installed"); return
        try:
            body = {"model":self.model, "messages":self.messages, "stream":True}
            if self.system: body["system"] = self.system
            
            # Use timeout=None so large prompts don't time out while model loads to VRAM locally
            r = rq.post(f"{self.host}/api/chat", json=body, stream=True, timeout=None)
            r.raise_for_status(); full = ""
            for line in r.iter_lines():
                if self._stop: break
                if line:
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        self.token.emit(chunk); full += chunk
                    if data.get("done"): break
            self.done.emit(full)
        except Exception as e: self.error.emit(str(e))
    def stop(self):
        self._stop = True
        self.wait()

class OllamaModelInfoWorker(QThread):
    result = pyqtSignal(dict)
    error  = pyqtSignal(str)
    def __init__(self, host, model):
        super().__init__(); self.host=host; self.model=model
    def run(self):
        if not HAS_REQUESTS: self.error.emit("requests not installed"); return
        try:
            r = rq.post(f"{self.host}/api/show", json={"name":self.model}, timeout=15)
            r.raise_for_status(); self.result.emit(r.json())
        except Exception as e: self.error.emit(str(e))

class GitHubWorker(QThread):
    result = pyqtSignal(object)
    error  = pyqtSignal(str)
    def __init__(self, endpoint, method="GET", body=None, token="", params=None):
        super().__init__()
        self.endpoint=endpoint; self.method=method; self.body=body; self.token=token; self.params=params or {}
    def run(self):
        if not HAS_REQUESTS: self.error.emit("requests not installed"); return
        try:
            headers = {"Accept":"application/vnd.github+json", "X-GitHub-Api-Version":"2022-11-28"}
            if self.token: headers["Authorization"] = f"Bearer {self.token}"
            url = "https://api.github.com" + self.endpoint
            if self.method == "POST":
                resp = rq.post(url, headers=headers, json=self.body, timeout=20)
            else:
                resp = rq.get(url, headers=headers, params=self.params, timeout=20)
            resp.raise_for_status(); self.result.emit(resp.json())
        except Exception as e: self.error.emit(str(e))

class AgentWorker(QThread):
    """ReAct autonomous agent loop wrapper."""
    step     = pyqtSignal(str, str)  # (kind, text): thought|tool|observation|done|error
    finished = pyqtSignal(str)

    def __init__(self, host, model, task, max_steps=12):
        super().__init__()
        from .engine import AgentEngine
        self.engine = AgentEngine(host, model, task, max_steps)

    def run(self):
        for event in self.engine.execute():
            self.step.emit(event.level, event.message)
            if event.level in ("error", "done"):
                self.finished.emit(event.message)
                break
        
        # If it finished without emitting error or done, it reached max steps
        if self.engine._stop is False and event.level not in ("error", "done"):
            self.finished.emit("Max steps reached.")

    def stop(self):
        self.engine.stop()
        self.wait()

class WorkflowWorker(QThread):
    step_info = pyqtSignal(str, str)
    highlight = pyqtSignal(int, bool)
    paused    = pyqtSignal(int)
    context_updated = pyqtSignal(dict)
    finished  = pyqtSignal()
    
    def __init__(self, data, host="http://localhost:11434", step_mode=False):
        super().__init__()
        from .engine import WorkflowEngine
        self.engine = WorkflowEngine(data, host, step_mode=step_mode)
    
    def step(self):
        self.engine.step()

    def run(self):
        for event in self.engine.execute():
            if event.level == "highlight":
                self.highlight.emit(event.node_idx, event.is_active)
            elif event.level == "paused":
                self.paused.emit(event.node_idx)
            elif event.level == "context":
                try:
                    self.context_updated.emit(json.loads(event.message))
                except Exception:
                    pass
            else:
                self.step_info.emit(event.level, event.message)
        self.finished.emit()

    def stop(self):
        self.engine.stop()
        self.wait()

