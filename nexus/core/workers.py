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

    def stop(self):
        self._stop = True
        self.wait()

class WorkflowWorker(QThread):
    step_info = pyqtSignal(str, str)
    highlight = pyqtSignal(int, bool)
    finished  = pyqtSignal()
    def __init__(self, data, host="http://localhost:11434"):
        super().__init__(); self.data=data; self.host=host; self._stop=False
    
    def run(self):
        nodes = self.data["nodes"]; edges = self.data["edges"]
        adj = [[] for _ in range(len(nodes))]
        in_degree = [0] * len(nodes)
        for e in edges:
            adj[e["from"]].append(e["to"])
            in_degree[e["to"]] += 1
            
        queue = [i for i, d in enumerate(in_degree) if d == 0]
        context = {"last_output": ""}

        while queue and not self._stop:
            idx = queue.pop(0)
            node_cfg = nodes[idx]
            ntype = node_cfg["type"]
            cfg = node_cfg.get("config", {})
            self.highlight.emit(idx, True)
            self.step_info.emit("cmd", f"Running: {ntype}")
            try:
                res = self._execute_node(ntype, cfg, context)
                if res is False:
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

    def stop(self):
        self._stop = True
        self.wait()

    def _execute_node(self, ntype, cfg, context):
        import subprocess, sys, json
        flags = subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0
        if ntype == "terminal":
            r = subprocess.run(cfg.get("cmd","echo ok"), cwd=cfg.get("cwd","."), shell=True, capture_output=True, text=True, timeout=60, creationflags=flags)
            out = (r.stdout + r.stderr).strip(); self.step_info.emit("info", out[:500] or "[done]"); return out
        elif ntype == "git":
            r = subprocess.run(cfg.get("cmd","git status"), cwd=cfg.get("repo","."), shell=True, capture_output=True, text=True, timeout=60, creationflags=flags)
            out = (r.stdout + r.stderr).strip(); self.step_info.emit("info", out[:300] or "[done]"); return out
        elif ntype == "ai":
            try:
                import requests as rq
                resp = rq.post(f"{self.host}/api/generate", json={"model":cfg.get("model") or "llama3","prompt":f"{cfg.get('prompt','Analyze this:')}\n\n{context.get('last_output','')}", "stream":False}, timeout=120)
                resp.raise_for_status(); ans = resp.json().get("response",""); self.step_info.emit("done", ans[:500]); return ans
            except Exception as e: self.step_info.emit("error", f"AI Node failed: {e}"); return False
        elif ntype == "condition":
            import re
            match = bool(re.search(cfg.get("pattern",""), context.get("last_output","")))
            if not match and cfg.get("on_false") == "stop": return False
            return context.get("last_output")
        elif ntype == "notify":
            self.step_info.emit("success", f"🔔 {cfg.get('message','Done')}"); return context.get("last_output")
        return True

