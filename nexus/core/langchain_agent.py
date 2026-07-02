"""
nexus/core/langchain_agent.py
─────────────────────────────
LangChain-powered agent engine for NEXUS.

Provides:
  • build_llm()               — LLM factory (Ollama / OpenAI / Anthropic / compatible)
  • build_tools()             — LangChain tool registry
  • configure_langsmith()     — toggle LangSmith tracing env-vars
  • LangChainAgentWorker      — QThread that runs a LangGraph ReAct agent
  • HAS_LANGCHAIN / HAS_LANGSMITH — availability flags

Falls back gracefully when optional packages are absent.
"""

import os, sys, json, subprocess, threading
from pathlib import Path
from typing import Callable, List, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from .config import SETTINGS

# ── Availability flags ────────────────────────────────────────────────────────

try:
    import langchain  # noqa
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

try:
    import langsmith  # noqa
    HAS_LANGSMITH = True
except ImportError:
    HAS_LANGSMITH = False

try:
    from langgraph.prebuilt import create_react_agent
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False

# ── LLM Factory ───────────────────────────────────────────────────────────────

def build_llm(provider: str, model: str = "", host: str = "", api_key: str = "", temperature: float = 0.1):
    """Return a LangChain chat model based on provider string."""
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model or SETTINGS.get("default_model") or "llama3",
            base_url=host or SETTINGS.get("ollama_host"),
            temperature=temperature,
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or SETTINGS.get("openai_model", "gpt-4o-mini"),
            api_key=api_key or SETTINGS.get("openai_api_key") or "sk-placeholder",
            base_url=SETTINGS.get("openai_base_url", "https://api.openai.com/v1"),
            temperature=temperature,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model or SETTINGS.get("anthropic_model", "claude-3-5-sonnet-20241022"),
            api_key=api_key or SETTINGS.get("anthropic_api_key", ""),
            temperature=temperature,
        )
    elif provider == "openai_compatible":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or "llama3",
            api_key=api_key or "not-needed",
            base_url=host or SETTINGS.get("openai_base_url"),
            temperature=temperature,
        )
    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model or SETTINGS.get("google_model", "gemini-2.0-flash"),
            google_api_key=api_key or SETTINGS.get("google_api_key", ""),
            temperature=temperature,
        )
    elif provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=model or SETTINGS.get("groq_model", "llama-3.3-70b-versatile"),
            api_key=api_key or SETTINGS.get("groq_api_key", ""),
            temperature=temperature,
        )
    elif provider == "together":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or SETTINGS.get("together_model", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
            api_key=api_key or SETTINGS.get("together_api_key", ""),
            base_url="https://api.together.xyz/v1",
            temperature=temperature,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider!r}")


# ── Tool Registry ─────────────────────────────────────────────────────────────

ALL_TOOLS = [
    "shell", "read_file", "write_file", "list_dir",
    "git", "python_repl", "web_search",
    "langsmith_runs", "langsmith_datasets", "code_search",
    "http_request", "json_transform", "regex_extract", "summarize_text",
]

def build_tools(
    enabled: List[str],
    cwd: str = ".",
    approval_cb: Optional[Callable[[str, str], bool]] = None,
) -> list:
    """Build LangChain Tool objects from the list of enabled tool names."""
    from langchain_core.tools import tool as lc_tool

    _flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    def _approve(name: str, detail: str) -> bool:
        return approval_cb(name, detail) if approval_cb else True

    tools = []

    # ── shell ─────────────────────────────────────────────────────────────────
    if "shell" in enabled:
        @lc_tool
        def shell(command: str) -> str:
            """Run a shell command in the working directory. Returns stdout + stderr."""
            if not _approve("shell", command):
                return "[DENIED] Shell command rejected by user."
            try:
                r = subprocess.run(
                    command, cwd=cwd, shell=True,
                    capture_output=True, text=True, timeout=60,
                    encoding="utf-8", errors="replace", creationflags=_flags,
                )
                return (r.stdout + r.stderr).strip()[:4000] or f"[exit {r.returncode}]"
            except subprocess.TimeoutExpired:
                return "[ERROR] Timed out after 60 s"
            except Exception as e:
                return f"[ERROR] {e}"
        tools.append(shell)

    # ── read_file ─────────────────────────────────────────────────────────────
    if "read_file" in enabled:
        @lc_tool
        def read_file(path: str) -> str:
            """Read and return the text contents of a file (up to 6000 chars)."""
            try:
                p = Path(path) if Path(path).is_absolute() else Path(cwd) / path
                return p.read_text(errors="replace")[:6000]
            except Exception as e:
                return f"[ERROR] {e}"
        tools.append(read_file)

    # ── write_file ────────────────────────────────────────────────────────────
    if "write_file" in enabled:
        @lc_tool
        def write_file(path: str, content: str) -> str:
            """Write content to a file, creating parent directories if needed."""
            if not _approve("write_file", f"{path} ({len(content)} chars)"):
                return "[DENIED] Write operation rejected by user."
            try:
                p = Path(path) if Path(path).is_absolute() else Path(cwd) / path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content)
                return f"Wrote {len(content)} chars to {p}"
            except Exception as e:
                return f"[ERROR] {e}"
        tools.append(write_file)

    # ── list_dir ──────────────────────────────────────────────────────────────
    if "list_dir" in enabled:
        @lc_tool
        def list_dir(path: str = ".") -> str:
            """List files and directories at the given path."""
            try:
                p = Path(path) if Path(path).is_absolute() else Path(cwd) / path
                items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
                return "\n".join(f"{'📁' if i.is_dir() else '📄'} {i.name}" for i in items)
            except Exception as e:
                return f"[ERROR] {e}"
        tools.append(list_dir)

    # ── git ───────────────────────────────────────────────────────────────────
    if "git" in enabled:
        @lc_tool
        def git(command: str, repo: str = ".") -> str:
            """Run a git sub-command (without the 'git' prefix) in a repo path."""
            repo_path = repo if Path(repo).is_absolute() else str(Path(cwd) / repo)
            try:
                r = subprocess.run(
                    f"git {command}", cwd=repo_path, shell=True,
                    capture_output=True, text=True, timeout=30,
                    encoding="utf-8", errors="replace", creationflags=_flags,
                )
                return (r.stdout + r.stderr).strip()[:3000] or f"[exit {r.returncode}]"
            except Exception as e:
                return f"[ERROR] {e}"
        tools.append(git)

    # ── python_repl ───────────────────────────────────────────────────────────
    if "python_repl" in enabled:
        @lc_tool
        def python_repl(code: str) -> str:
            """Execute Python code and capture its output. Use print() to show values."""
            if not _approve("python_repl", code[:200]):
                return "[DENIED] Python execution rejected by user."
            import io, contextlib
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                    exec(code, {})  # noqa: S102
                return buf.getvalue()[:3000] or "[No output]"
            except Exception as e:
                return f"[ERROR] {type(e).__name__}: {e}"
        tools.append(python_repl)

    # ── web_search ────────────────────────────────────────────────────────────
    if "web_search" in enabled:
        try:
            from langchain_community.tools import DuckDuckGoSearchRun
            s = DuckDuckGoSearchRun()
            s.name = "web_search"
            s.description = "Search the web using DuckDuckGo. Input is a search query string."
            tools.append(s)
        except ImportError:
            @lc_tool
            def web_search(query: str) -> str:
                """Search the web (requires: pip install duckduckgo-search langchain-community)."""
                return "[ERROR] duckduckgo-search not installed."
            tools.append(web_search)

    # ── langsmith_runs ────────────────────────────────────────────────────────
    if "langsmith_runs" in enabled:
        @lc_tool
        def langsmith_runs(project: str = "", limit: int = 10) -> str:
            """List recent LangSmith runs for a project. Returns run IDs, status, names."""
            try:
                from langsmith import Client
                client = Client(
                    api_key=SETTINGS.get("langsmith_api_key"),
                    api_url=SETTINGS.get("langsmith_endpoint"),
                )
                proj = project or SETTINGS.get("langsmith_project", "nexus-default")
                runs = list(client.list_runs(project_name=proj, limit=limit))
                return "\n".join(
                    f"[{r.status}] {r.name} | {r.run_type} | {str(r.id)[:8]}" for r in runs
                )
            except Exception as e:
                return f"[ERROR] {e}"
        tools.append(langsmith_runs)

    # ── langsmith_datasets ────────────────────────────────────────────────────
    if "langsmith_datasets" in enabled:
        @lc_tool
        def langsmith_datasets(limit: int = 20) -> str:
            """List LangSmith datasets available in the configured project."""
            try:
                from langsmith import Client
                client = Client(
                    api_key=SETTINGS.get("langsmith_api_key"),
                    api_url=SETTINGS.get("langsmith_endpoint"),
                )
                datasets = list(client.list_datasets(limit=limit))
                return "\n".join(f"[{str(d.id)[:8]}] {d.name}" for d in datasets)
            except Exception as e:
                return f"[ERROR] {e}"
        tools.append(langsmith_datasets)

    # ── code_search ───────────────────────────────────────────────────────────
    if "code_search" in enabled:
        @lc_tool
        def code_search(query: str) -> str:
            """Semantic search the codebase for the given query to find relevant file snippets and functions."""
            try:
                from .rag import CodebaseRAG
                rag = CodebaseRAG(cwd)
                provider = SETTINGS.get("rag_embedding_provider", "ollama")
                model = SETTINGS.get("rag_embedding_model", "nomic-embed-text")
                host = SETTINGS.get("ollama_host", "http://localhost:11434")
                api_key = ""
                if provider == "openai":
                    api_key = SETTINGS.get("openai_api_key", "")
                elif provider == "openai_compatible":
                    api_key = "not-needed"
                    
                results = rag.search(query, top_k=5, provider=provider, model=model, host=host, api_key=api_key)
                if not results:
                    return f"No matching code snippets found for query: '{query}'"
                
                output = []
                for idx, r in enumerate(results):
                    output.append(
                        f"Result {idx+1}:\n"
                        f"File: {r['file']} (Lines {r['start_line']}-{r['end_line']})\n"
                        f"Relevance Score: {r['score']:.2f}\n"
                        f"Code:\n```\n{r['text']}\n```\n"
                    )
                return "\n\n".join(output)
            except Exception as e:
                return f"[ERROR] Code search failed: {e}"
        tools.append(code_search)

    # ── http_request ──────────────────────────────────────────────────────────
    if "http_request" in enabled:
        @lc_tool
        def http_request(url: str, method: str = "GET", body: str = "", headers_json: str = "{}") -> str:
            """Make an HTTP request to any URL. method: GET or POST. headers_json: JSON string of headers. body: request body for POST."""
            if not _approve("http_request", f"{method} {url}"):
                return "[DENIED] HTTP request rejected by user."
            import requests as _req
            try:
                hdrs = json.loads(headers_json) if headers_json else {}
                if method.upper() == "POST":
                    r = _req.post(url, data=body, headers=hdrs, timeout=30)
                else:
                    r = _req.get(url, headers=hdrs, timeout=30)
                return f"[{r.status_code}]\n{r.text[:4000]}"
            except Exception as e:
                return f"[ERROR] {e}"
        tools.append(http_request)

    # ── json_transform ────────────────────────────────────────────────────────
    if "json_transform" in enabled:
        @lc_tool
        def json_transform(json_str: str, path: str = "") -> str:
            """Parse a JSON string and extract data at a dot-separated path (e.g. 'data.items.0.name'). Empty path returns the whole parsed structure."""
            try:
                data = json.loads(json_str)
                if path:
                    for key in path.split("."):
                        if isinstance(data, list):
                            data = data[int(key)]
                        elif isinstance(data, dict):
                            data = data[key]
                        else:
                            return f"[ERROR] Cannot traverse into {type(data).__name__} with key '{key}'"
                return json.dumps(data, indent=2)[:4000]
            except Exception as e:
                return f"[ERROR] {e}"
        tools.append(json_transform)

    # ── regex_extract ─────────────────────────────────────────────────────────
    if "regex_extract" in enabled:
        @lc_tool
        def regex_extract(text: str, pattern: str) -> str:
            """Extract all matches of a regex pattern from text. Returns one match per line. Groups are pipe-separated."""
            import re
            try:
                matches = re.findall(pattern, text)
                if not matches:
                    return "No matches found."
                lines = []
                for m in matches[:50]:
                    if isinstance(m, tuple):
                        lines.append(" | ".join(m))
                    else:
                        lines.append(str(m))
                return "\n".join(lines)
            except Exception as e:
                return f"[ERROR] {e}"
        tools.append(regex_extract)

    # ── summarize_text ────────────────────────────────────────────────────────
    if "summarize_text" in enabled:
        @lc_tool
        def summarize_text(text: str, max_words: int = 150) -> str:
            """Summarize a long text into a concise version. Uses the active LLM."""
            try:
                from .config import SETTINGS
                provider = SETTINGS.get("agent_provider", "ollama")
                model = SETTINGS.get(f"{provider}_model") or SETTINGS.get("default_model") or "llama3"
                
                llm = build_llm(provider, model)
                from langchain_core.messages import SystemMessage, HumanMessage
                messages = [
                    SystemMessage(content=f"Summarize the following text concisely in under {max_words} words."),
                    HumanMessage(content=text[:8000])
                ]
                ans = llm.invoke(messages).content
                return ans
            except Exception as e:
                try:
                    import requests as _req
                    host_url = SETTINGS.get("ollama_host", "http://localhost:11434")
                    model_name = SETTINGS.get("default_model", "llama3")
                    body = {
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": f"Summarize the following text concisely in under {max_words} words."},
                            {"role": "user", "content": text[:8000]}
                        ],
                        "stream": False
                    }
                    r = _req.post(f"{host_url}/api/chat", json=body, timeout=60)
                    r.raise_for_status()
                    return r.json().get("message", {}).get("content", "[No response]")
                except Exception:
                    return f"[ERROR] {e}"
        tools.append(summarize_text)

    return tools


# ── LangSmith helpers ─────────────────────────────────────────────────────────

def configure_langsmith(enabled: bool = True):
    """Set or clear LangSmith tracing environment variables."""
    api_key  = SETTINGS.get("langsmith_api_key", "")
    project  = SETTINGS.get("langsmith_project", "nexus-default")
    endpoint = SETTINGS.get("langsmith_endpoint", "https://api.smith.langchain.com")
    if enabled and api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"]     = api_key
        os.environ["LANGCHAIN_PROJECT"]     = project
        os.environ["LANGCHAIN_ENDPOINT"]    = endpoint
    else:
        for k in ["LANGCHAIN_TRACING_V2", "LANGCHAIN_API_KEY",
                  "LANGCHAIN_PROJECT", "LANGCHAIN_ENDPOINT"]:
            os.environ.pop(k, None)


# ── QThread Worker ────────────────────────────────────────────────────────────

class LangChainAgentWorker(QThread):
    """
    Run a LangGraph ReAct agent in a background QThread.

    Signals
    -------
    step(kind, text)          — 'thought' | 'tool' | 'observation' | 'done' | 'error'
    finished(result_text)     — final agent answer
    approval_needed(tool, args, event_obj)  — emitted when user approval is required
    """
    step            = pyqtSignal(str, str)
    finished        = pyqtSignal(str)
    approval_needed = pyqtSignal(str, str, object)   # (tool_name, args_str, threading.Event)

    def __init__(
        self,
        provider: str,
        model: str,
        task: str,
        system_prompt: str = "",
        enabled_tools: Optional[List[str]] = None,
        cwd: str = ".",
        max_steps: int = 20,
        host: str = "",
        api_key: str = "",
        require_approval: bool = True,
    ):
        super().__init__()
        self.provider         = provider
        self.model            = model
        self.task             = task
        self.system_prompt    = system_prompt
        self.enabled_tools    = enabled_tools or ["shell", "read_file", "write_file", "list_dir", "git", "code_search"]
        self.cwd              = cwd
        self.max_steps        = max_steps
        self.host             = host
        self.api_key          = api_key
        self.require_approval = require_approval
        self._stop_flag       = False
        self._approval_result = False

    # ── tool approval ─────────────────────────────────────────────────────────

    def _approval_callback(self, tool_name: str, args_str: str) -> bool:
        """Block worker thread until the UI resolves the approval dialog."""
        if not self.require_approval or not SETTINGS.get("agent_tool_approval", True):
            return True
        event = threading.Event()
        self._approval_result = False
        self.approval_needed.emit(tool_name, args_str, event)
        granted = event.wait(timeout=120)
        return granted and self._approval_result

    def resolve_approval(self, approved: bool, event: threading.Event):
        """Called from the UI thread after the user clicks Yes/No."""
        self._approval_result = approved
        event.set()

    # ── main run loop ─────────────────────────────────────────────────────────

    def run(self):
        if not HAS_LANGCHAIN:
            self.step.emit("error", "LangChain not installed.\nRun: pip install -r requirements.txt")
            self.finished.emit("LangChain not installed.")
            return

        if SETTINGS.get("langchain_tracing", False):
            configure_langsmith(True)

        try:
            self.step.emit("thought", f"Initialising {self.provider} › {self.model or 'default'}…")

            llm = build_llm(
                provider=self.provider,
                model=self.model,
                host=self.host or SETTINGS.get("ollama_host"),
                api_key=self.api_key,
            )

            tools = build_tools(
                enabled=self.enabled_tools,
                cwd=self.cwd,
                approval_cb=self._approval_callback,
            )

            self.step.emit("thought", f"Tools: {[t.name for t in tools]}")

            from langchain_core.messages import SystemMessage, HumanMessage

            _sys = self.system_prompt or (
                "You are NEXUS Agent — a powerful autonomous AI assistant built into "
                "the NEXUS desktop development environment.\n"
                "You help developers with coding, file management, git, system tasks, and analysis.\n"
                "Think step by step. Be precise and verify your work after each action."
            )
            messages = [SystemMessage(content=_sys), HumanMessage(content=self.task)]

            if HAS_LANGGRAPH:
                self._run_langgraph(llm, tools, messages)
            else:
                self._run_executor(llm, tools, messages)

        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            self.step.emit("error", err)
            self.finished.emit(err)

    # ── LangGraph backend ─────────────────────────────────────────────────────

    def _run_langgraph(self, llm, tools, messages):
        from langgraph.prebuilt import create_react_agent

        agent  = create_react_agent(llm, tools)
        config = {"recursion_limit": self.max_steps}
        final  = ""

        for chunk in agent.stream({"messages": messages}, config=config):
            if self._stop_flag:
                self.step.emit("error", "Stopped by user.")
                self.finished.emit("Stopped.")
                return

            if "agent" in chunk:
                for msg in chunk["agent"].get("messages", []):
                    tool_calls = getattr(msg, "tool_calls", [])
                    content    = str(getattr(msg, "content", "") or "")
                    if tool_calls:
                        for tc in tool_calls:
                            self.step.emit("tool", f"{tc['name']}({json.dumps(tc.get('args', {}))})")
                    elif content:
                        self.step.emit("thought", content[:800])
                        final = content

            elif "tools" in chunk:
                for msg in chunk["tools"].get("messages", []):
                    obs = str(getattr(msg, "content", "") or "")
                    self.step.emit("observation", obs[:800])

        self.step.emit("done", final or "Task completed.")
        self.finished.emit(final or "Task completed.")

    # ── AgentExecutor fallback (no langgraph) ─────────────────────────────────

    def _run_executor(self, llm, tools, messages):
        from langchain.agents import AgentExecutor, create_react_agent as lc_react
        from langchain_core.prompts import ChatPromptTemplate

        # Minimal ReAct prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "{system}\n\nTools: {tool_names}\n\n{tools}"),
            ("human",  "{input}\n\n{agent_scratchpad}"),
        ])
        agent    = lc_react(llm, tools, prompt)
        executor = AgentExecutor(agent=agent, tools=tools, verbose=False,
                                 max_iterations=self.max_steps, return_intermediate_steps=True)

        sys_text = messages[0].content if messages else ""
        inp_text = messages[-1].content if len(messages) > 1 else self.task

        result = executor.invoke({
            "input": inp_text,
            "system": sys_text,
            "tool_names": ", ".join(t.name for t in tools),
        })

        for action, obs in result.get("intermediate_steps", []):
            self.step.emit("tool",        f"{action.tool}({action.tool_input})")
            self.step.emit("observation", str(obs)[:800])

        final = str(result.get("output", "Done."))
        self.step.emit("done", final)
        self.finished.emit(final)

    # ── stop ──────────────────────────────────────────────────────────────────

    def stop(self):
        self._stop_flag = True
        self.wait()
