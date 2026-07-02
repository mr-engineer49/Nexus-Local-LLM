"""
nexus/core/engine.py
─────────────────────────────
Headless execution engine for NEXUS.
Unifies Workflow DAG execution and Agent ReAct loops, decoupling them from PyQt threads.
"""

import sys, subprocess, tempfile, os, json, re, threading, time
from typing import Iterator, Dict, Any, List

class ExecutionEvent:
    def __init__(self, level: str, message: str, node_idx: int = -1, is_active: bool = False):
        self.level = level         # "info", "warn", "error", "success", "done", "cmd", "thought", "tool", "observation"
        self.message = message
        self.node_idx = node_idx
        self.is_active = is_active # Used for highlight signals in workflows

class WorkflowEngine:
    def __init__(self, data: Dict[str, Any], host: str = "http://localhost:11434", step_mode: bool = False):
        self.data = data
        self.host = host
        self._stop = False
        self.step_mode = step_mode
        self._step_event = threading.Event()
        self.context = {"last_output": ""}

    def stop(self):
        self._stop = True
        self._step_event.set()

    def step(self):
        self._step_event.set()

    def execute(self) -> Iterator[ExecutionEvent]:
        nodes = self.data.get("nodes", [])
        edges = self.data.get("edges", [])
        
        if not nodes:
            return

        adj = [[] for _ in range(len(nodes))]
        in_degree = [0] * len(nodes)
        for e in edges:
            adj[e["from"]].append(e["to"])
            in_degree[e["to"]] += 1
            
        queue = [i for i, d in enumerate(in_degree) if d == 0]

        while queue and not self._stop:
            idx = queue.pop(0)
            node_cfg = nodes[idx]
            ntype = node_cfg.get("type")
            cfg = node_cfg.get("config", {})
            
            if self.step_mode:
                yield ExecutionEvent("paused", f"Paused before {ntype}", idx, True)
                self._step_event.clear()
                while not self._step_event.is_set() and not self._stop:
                    time.sleep(0.05)
                if self._stop:
                    break

            yield ExecutionEvent("highlight", "", idx, True)
            yield ExecutionEvent("cmd", f"Running: {ntype}", idx, True)
            
            try:
                res, evt = self._execute_node(ntype, cfg, self.context)
                if evt: yield ExecutionEvent(evt[0], evt[1], idx, True)
                
                if res is False:
                    yield ExecutionEvent("warn", f"Workflow stopped at {ntype}", idx, False)
                    yield ExecutionEvent("highlight", "", idx, False)
                    break 
                self.context["last_output"] = str(res)
                yield ExecutionEvent("context", json.dumps(self.context), idx, True)
            except Exception as e:
                yield ExecutionEvent("error", f"Node {idx} failed: {e}", idx, False)
                yield ExecutionEvent("highlight", "", idx, False)
                break
                
            yield ExecutionEvent("highlight", "", idx, False)
            
            for neighbor in adj[idx]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    
        yield ExecutionEvent("done", "Workflow Execution Complete", -1, False)

    def _execute_node(self, ntype: str, cfg: dict, context: dict):
        flags = subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0
        from .config import SETTINGS
        default_cwd = SETTINGS.get("clone_dir", ".")
        
        if ntype == "terminal":
            cmd = cfg.get("cmd", "echo ok")
            cwd = cfg.get("cwd") or default_cwd
            timeout = int(cfg.get("timeout", 60))
            r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=timeout, creationflags=flags)
            out = (r.stdout + r.stderr).strip()
            return out, ("info", out[:500] or "[done]")
        
        elif ntype == "git":
            cwd = cfg.get("repo") or default_cwd
            r = subprocess.run(cfg.get("cmd","git status"), cwd=cwd, shell=True, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=60, creationflags=flags)
            out = (r.stdout + r.stderr).strip()
            return out, ("info", out[:300] or "[done]")
            
        elif ntype == "python":
            script = cfg.get("script", "print('ok')")
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
                f.write(script)
                tmp = f.name
            try:
                r = subprocess.run([sys.executable, tmp], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=120, creationflags=flags)
                out = (r.stdout + r.stderr).strip()
                return out, ("info", out[:500] or "[done]")
            finally:
                os.unlink(tmp)
                
        elif ntype == "ai":
            try:
                from .config import SETTINGS
                from .langchain_agent import build_llm, HAS_LANGCHAIN
                provider = SETTINGS.get("agent_provider", "ollama")
                model = cfg.get("model") or SETTINGS.get(f"{provider}_model") or "llama3"
                prompt_text = f"{cfg.get('prompt','Analyze this:')}\n\n{context.get('last_output','')}"
                
                if HAS_LANGCHAIN:
                    llm = build_llm(provider, model)
                    ans = llm.invoke(prompt_text).content
                    return ans, ("done", ans[:500])
                else:
                    import requests as rq
                    resp = rq.post(f"{self.host}/api/generate", json={"model":model,"prompt":prompt_text, "stream":False}, timeout=120)
                    resp.raise_for_status()
                    ans = resp.json().get("response","")
                    return ans, ("done", ans[:500])
            except Exception as e:
                return False, ("error", f"AI Node failed: {e}")
                
        elif ntype == "condition":
            match = bool(re.search(cfg.get("pattern",""), context.get("last_output","")))
            if not match and cfg.get("on_false") == "stop":
                return False, None
            return context.get("last_output"), None
            
        elif ntype == "notify":
            return context.get("last_output"), ("success", f"🔔 {cfg.get('message','Done')}")
            
        return True, None


class AgentEngine:
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

    def __init__(self, host: str, model: str, task: str, max_steps: int = 12):
        self.host = host
        self.model = model
        self.task = task
        self.max_steps = max_steps
        self._stop = False

    def stop(self):
        self._stop = True

    def execute(self) -> Iterator[ExecutionEvent]:
        try:
            import requests as rq
        except ImportError:
            yield ExecutionEvent("error", "requests not installed")
            return

        msgs = [{"role":"system","content":self._SYSTEM},
                {"role":"user","content":self.task}]

        for _ in range(self.max_steps):
            if self._stop:
                yield ExecutionEvent("error", "Stopped.")
                return

            try:
                resp = rq.post(f"{self.host}/api/chat",
                    json={"model":self.model,"messages":msgs,"stream":False}, timeout=120)
                resp.raise_for_status()
                content = resp.json()["message"]["content"].strip()
            except Exception as e:
                yield ExecutionEvent("error", str(e))
                return

            if "THOUGHT:" in content:
                thought = content.split("THOUGHT:",1)[1].split("\n")[0].strip()
                yield ExecutionEvent("thought", thought)

            if "DONE:" in content:
                answer = content.split("DONE:",1)[1].strip()
                yield ExecutionEvent("done", answer)
                return

            if "TOOL:" in content and "ARGS:" in content:
                try:
                    tool = content.split("TOOL:",1)[1].split("\n")[0].strip()
                    args_raw = content.split("ARGS:",1)[1].strip()
                    i = args_raw.index("{"); d = 0
                    for j,ch in enumerate(args_raw[i:],i):
                        if ch=="{": d+=1
                        elif ch=="}": d-=1
                        if d==0: end=j; break
                    args = json.loads(args_raw[i:end+1])
                    yield ExecutionEvent("tool", f"{tool}({json.dumps(args)})")
                    obs = self._run_tool(tool, args)
                    yield ExecutionEvent("observation", obs[:1500])
                    msgs.append({"role":"assistant","content":content})
                    msgs.append({"role":"user","content":f"OBSERVATION:\n{obs[:1500]}"})
                except Exception as e:
                    yield ExecutionEvent("observation", f"[parse error] {e}")
                    msgs.append({"role":"assistant","content":content})
                    msgs.append({"role":"user","content":f"OBSERVATION:\n[parse error] {e}"})
            else:
                yield ExecutionEvent("thought", content[:300])
                msgs.append({"role":"assistant","content":content})
                msgs.append({"role":"user","content":"Continue. Use a tool or respond with DONE."})

        yield ExecutionEvent("error", f"Max {self.max_steps} steps reached.")

    def _run_tool(self, tool: str, args: dict) -> str:
        try:
            from pathlib import Path
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
                flags = subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0
                r = subprocess.run(args["cmd"], cwd=cwd, shell=True,
                    capture_output=True, text=True, timeout=30,
                    encoding="utf-8", errors="replace",
                    creationflags=flags)
                return (r.stdout+r.stderr).strip()[:3000] or f"[exit {r.returncode}]"
            else:
                return f"Unknown tool: {tool}"
        except Exception as e:
            return f"[error] {e}"
