# NEXUS — AI Developer Hub & Local Workspace

<div align="center">

**A modular, dark-themed PyQt6 desktop application that unifies AI agents, LLM providers, developer tools, and project management into a single offline-first control panel.**

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-Desktop-green?logo=qt&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-Agent%20Engine-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

</div>

---

## Quick Start

### Windows
```
launch.bat
```

### Linux / macOS
```bash
chmod +x launch.sh && ./launch.sh
```

### Manual
```bash
pip install -r requirements.txt
python run_nexus.py
```

---

## Requirements

| Dependency | Required? | Install |
|---|---|---|
| Python 3.10+ | ✅ Yes | https://python.org |
| PyQt6 | ✅ Yes | `pip install PyQt6` |
| psutil | ✅ Yes | `pip install psutil` |
| requests | ✅ Yes | `pip install requests` |
| LangChain stack | For AI agents | `pip install langchain langchain-core langgraph` |
| Ollama | For local LLMs | https://ollama.com |
| Git | For Git panel | https://git-scm.com |

### Optional Provider Packages

```bash
pip install langchain-ollama         # Ollama (local)
pip install langchain-openai         # OpenAI / Together AI / OpenAI-compatible
pip install langchain-anthropic      # Anthropic Claude
pip install langchain-google-genai   # Google Gemini
pip install langchain-groq           # Groq
pip install langsmith                # LangSmith tracing
pip install duckduckgo-search        # Web search tool
```

---

## Architecture

```
nexus/
├── core/
│   ├── config.py           # Settings, project persistence, version
│   ├── engine.py           # WorkflowEngine — DAG execution engine
│   ├── langchain_agent.py  # LLM factory, tool registry, agent worker
│   ├── rag.py              # CodebaseRAG — local code indexing & search
│   ├── style.py            # Theme tokens & global stylesheet
│   └── workers.py          # QThread workers (command, git, workflow, ollama)
├── ui/
│   ├── widgets.py          # Shared UI components (NavButton, LogView, DiffHighlighter)
│   └── panels/
│       ├── dashboard.py          # ⬡  Status Dashboard
│       ├── ollama.py             # 🤖 Ollama Model Manager
│       ├── git_github.py         # 🌿 Git & 🐙 GitHub Panels
│       ├── agents.py             # 💬 Chat Agent & 🎭 Agent Studio
│       ├── langsmith_panel.py    # 🦜 LangSmith Observability
│       ├── integrations_panel.py # 🔌 Tool Integrations Hub
│       ├── projects.py           # 📁 Project Runner
│       ├── rag_panel.py          # 🔍 RAG Codebase Search
│       ├── prompts_panel.py      # 📝 Prompt Templates & Sandbox
│       ├── workflow.py           # ⛓  Visual Workflow Builder & Debugger
│       ├── terminal_system.py    # 🐚 Terminal & 📊 System Monitor
│       └── settings.py          # ⚙  Settings
└── app.py                  # MainWindow, sidebar navigation, panel lifecycle
```

- **QThread workers** stream subprocess and LLM output without blocking the UI
- **Panel hibernation** — panels call `activate()` / `deactivate()` to save resources when hidden
- **Modular design** — each panel is self-contained; partial failures don't crash the app
- **Offline-first** — everything runs locally; cloud APIs are optional

---

## Panels & Features

### ⬡ Status Dashboard
- Real-time system metrics: CPU, RAM, disk, GPU usage
- Active project summary and Ollama model count
- Quick-action cards for common tasks
- Auto-refreshes on a timer; pauses when hidden (hibernation)

### 🤖 Ollama Model Manager
- List all locally downloaded models with size
- Pull any model from the Ollama hub (llama3, mistral, phi3, gemma2, etc.)
- One-click Run (serve) and Chat dialog
- Delete models to free disk space
- GPU/CPU detection displayed

### 🌿 Git Panel
- **Diff Viewer** with syntax-highlighted diff (green/red/yellow) — unstaged, staged, last commit, or custom ref
- **Commit Builder** — stage files, write commit messages, commit & push
- **Branch Manager** — list/create/switch/delete branches, fetch/pull/push
- **Stash Manager** — save, pop, list, and drop stashes
- **Tag Manager** — create and list tags
- Log viewer with `git log --oneline --graph`

### 🐙 GitHub Panel
- List repositories for any GitHub user or organization
- Clone repos with a destination folder picker
- Star/unstar repos, view details (description, stars, forks, language)
- Search GitHub repos by query
- Create new repositories from the UI

### 💬 Chat Agent (AI Chat)
- Conversational AI chat with streaming token output
- Multi-provider support: Ollama, OpenAI, Anthropic, Google Gemini, Groq, Together AI, OpenAI-compatible endpoints
- System prompt customization
- Model and temperature selection
- Chat history with export capabilities
- Tool-use approval dialogs for safe agent execution

### 🎭 Agent Studio
- Build custom ReAct agents with LangGraph
- Choose provider, model, temperature, max iterations
- Enable/disable individual tools via checkboxes:
  - `shell` — Run shell commands
  - `read_file` / `write_file` / `list_dir` — File system access
  - `git` — Git operations
  - `python_repl` — Execute Python code
  - `web_search` — DuckDuckGo search
  - `code_search` — RAG-powered codebase search
  - `http_request` — Make HTTP GET/POST to any REST API
  - `json_transform` — Parse and query JSON with dot-path expressions
  - `regex_extract` — Extract data from text with regex patterns
  - `summarize_text` — Summarize long text using the active LLM
  - `langsmith_runs` / `langsmith_datasets` — Query LangSmith
- Tool approval dialogs — dangerous tools require user confirmation
- Streaming output with real-time token display

### 🦜 LangSmith Observability
- Connect to LangSmith with API key, endpoint, and project configuration
- View recent agent runs (status, duration, token usage)
- Browse and inspect datasets
- Toggle LangSmith tracing on/off for all agent runs

### 🔌 Tool Integrations Hub
- Categorized integration cards with live status detection:
  - **LLM Providers**: Ollama, OpenAI, Anthropic, Google Gemini, Groq, Together AI
  - **Developer Tools**: Docker, Node.js/npm, pip, uv, PostgreSQL, SQLite, Redis
  - **AI Frameworks**: LangChain, LangGraph, LangSmith, CrewAI, AutoGen
- Each card shows: name, connection status (🟢 / 🔴), version info
- "Test Connection" button for each integration
- Non-blocking async detection — cards update in background threads

### 📁 Project Runner
- Add and manage project folders
- One-click `git pull`, `git status`, `git log`, `git fetch`
- Custom command box for any shell command within a project
- Projects persisted to `~/.nexus_projects.json`

### 🔍 RAG Codebase Search
- Index an entire project's source code into a local vector store
- Multiple embedding providers: Ollama (`nomic-embed-text`), OpenAI, OpenAI-compatible
- Semantic search across your codebase with relevance scoring
- AI-powered Q&A — ask questions about your code and get contextual answers
- Streaming answer output with source file citations
- Progress bar and log during indexing

### 📝 Prompt Templates & Sandbox
- **Template Library**: Ships with built-in templates — Code Review, Bug Analysis, Documentation Writer, API Design, Unit Test Generator, Refactor Legacy Code, Security Audit
- **Custom Templates**: Create, edit, and delete your own templates with `{variable}` placeholders
- **Interactive Sandbox**:
  - Auto-detects `{variable}` placeholders and generates dynamic input forms
  - Multi-line input for code/error placeholders
  - Multi-provider model selector (Ollama auto-fetches local models)
  - Streaming completion output in a dark terminal
  - Real-time latency (seconds) and throughput (tokens/sec) metrics
- Templates saved to `~/.nexus_prompts.json`

### ⛓ Visual Workflow Builder & Debugger
- **Visual Flow Canvas** — drag-and-drop node graph editor
- Node types: Trigger, AI Task, Terminal Command, Git Operation, HTTP Request, Condition, Notify
- Connect nodes with edges to build automated pipelines
- Pre-built templates: Auto Commit & Push, AI Code Review, Git Pull & Notify
- **Step-by-Step Debugger**:
  - Toggle Debug Mode checkbox for step execution
  - Paused node highlighted with yellow border
  - "Step Next" button to advance one node at a time
  - **Runtime Variable Editing** — edit context variables (e.g. `last_output`) live in the Context Inspector table while paused
  - Modified variables are written directly back to the running engine
- Save/load workflows as JSON files

### 🐚 Terminal
- Shell selector: CMD / PowerShell / Git Bash (auto-detected on Windows)
- Working directory picker
- Command history (↑/↓ arrows)
- Quick-launch buttons (python, node, git, pip)
- Live streaming output with color-coded log

### 📊 System Monitor
- Real-time CPU %, RAM, disk, swap gauges
- Color transitions (green → yellow → red)
- Top 12 processes by CPU usage
- Auto-refreshes every 2 seconds; pauses when hidden

### ⚙ Settings
- **Ollama**: Host URL, default model, threads, GPU layers, context size
- **OpenAI**: API key, base URL, model
- **Anthropic**: API key, model
- **Google AI**: API key, model (Gemini)
- **Groq**: API key, model
- **Together AI**: API key, model
- **LangSmith**: API key, endpoint, project name, tracing toggle
- **RAG**: Embedding provider, model, chunk size
- **General**: Default working directory, theme preferences
- All settings persisted to `~/.nexus_settings.json`

---

## Supported LLM Providers

| Provider | Type | Package | Default Model |
|---|---|---|---|
| Ollama | Local | `langchain-ollama` | `llama3` |
| OpenAI | Cloud | `langchain-openai` | `gpt-4o-mini` |
| Anthropic | Cloud | `langchain-anthropic` | `claude-3-5-sonnet-20241022` |
| Google Gemini | Cloud | `langchain-google-genai` | `gemini-2.0-flash` |
| Groq | Cloud | `langchain-groq` | `llama-3.3-70b-versatile` |
| Together AI | Cloud | `langchain-openai` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` |
| OpenAI-compatible | Any | `langchain-openai` | Configurable |

All providers are hot-swappable — change provider mid-session in any agent panel.

---

## Open Source Models to Try

```bash
ollama pull llama3          # Meta Llama 3 8B
ollama pull mistral         # Mistral 7B
ollama pull phi3            # Microsoft Phi-3 Mini
ollama pull gemma2          # Google Gemma 2 9B
ollama pull codellama       # Code specialist
ollama pull qwen2           # Alibaba Qwen2 7B
ollama pull deepseek-coder  # DeepSeek Coder 6.7B
```

All models run 100% locally — no internet required after download, no telemetry, no API costs.

---

## Agent Tools Reference

The LangChain agent engine exposes these tools for autonomous task execution:

| Tool | Description | Requires Approval |
|---|---|---|
| `shell` | Run shell commands in the working directory | ✅ Yes |
| `read_file` | Read file contents (up to 6000 chars) | No |
| `write_file` | Write/create files with content | ✅ Yes |
| `list_dir` | List files and directories | No |
| `git` | Run git sub-commands in a repo | No |
| `python_repl` | Execute Python code | ✅ Yes |
| `web_search` | Search the web via DuckDuckGo | No |
| `code_search` | RAG-powered semantic codebase search | No |
| `http_request` | HTTP GET/POST to any REST API | ✅ Yes |
| `json_transform` | Parse and query JSON with dot-path | No |
| `regex_extract` | Extract data from text with regex | No |
| `summarize_text` | Summarize text using the active LLM provider | No |
| `langsmith_runs` | List recent LangSmith runs | No |
| `langsmith_datasets` | List LangSmith datasets | No |

---

## Building EXE

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed run_nexus.py
```

### With Custom Icon
```bash
python -m PyInstaller --onefile --windowed --icon=path/to/icon.ico run_nexus.py
```

---

## Changelog — Implemented Features & Modifications

### Core Engine
- [x] **Modular architecture** — refactored from single-file (600 lines) to multi-module package (`nexus/core/`, `nexus/ui/panels/`)
- [x] **Panel hibernation system** — `activate()` / `deactivate()` lifecycle on every panel to save resources
- [x] **QThread workers** — all subprocess, LLM, and network operations run in background threads (no UI freezing)
- [x] **WorkflowEngine** (`engine.py`) — DAG-based execution engine with step-by-step debug mode, pause/resume, and context variable tracking
- [x] **CodebaseRAG** (`rag.py`) — local vector store indexing with multi-provider embedding support
- [x] **LangChain Agent Engine** (`langchain_agent.py`) — multi-provider LLM factory, 14-tool registry, LangGraph ReAct agent
- [x] **Theme system** (`style.py`) — centralized dark theme tokens and global Qt stylesheet
- [x] **Settings persistence** (`config.py`) — all settings saved to `~/.nexus_settings.json`

### LLM Providers
- [x] Ollama (local) with auto-detection and model listing
- [x] OpenAI with configurable base URL
- [x] Anthropic Claude
- [x] Google Gemini (`langchain-google-genai`)
- [x] Groq
- [x] Together AI (OpenAI-compatible endpoint)
- [x] Generic OpenAI-compatible endpoints

### Agent Tools
- [x] `shell` — shell command execution with timeout and approval
- [x] `read_file` / `write_file` / `list_dir` — file system operations
- [x] `git` — git sub-command runner
- [x] `python_repl` — sandboxed Python code execution
- [x] `web_search` — DuckDuckGo search integration
- [x] `code_search` — RAG-powered semantic codebase search
- [x] `http_request` — HTTP GET/POST to any REST API with approval
- [x] `json_transform` — JSON parsing with dot-path traversal
- [x] `regex_extract` — regex pattern extraction
- [x] `summarize_text` — multi-provider text summarization (uses active LLM, falls back to Ollama)
- [x] `langsmith_runs` / `langsmith_datasets` — LangSmith query tools

### UI Panels
- [x] **Status Dashboard** — real-time system metrics with auto-refresh hibernation
- [x] **Ollama Manager** — model CRUD, pull, run, chat, GPU detection
- [x] **Git Panel** — diff viewer, commit builder, branch/stash/tag management
- [x] **GitHub Panel** — repo browser, clone, star, search, create
- [x] **Chat Agent** — streaming AI chat with multi-provider support
- [x] **Agent Studio** — custom ReAct agent builder with tool selection
- [x] **LangSmith Panel** — observability dashboard, run inspection, dataset browser
- [x] **Integrations Hub** — live detection of LLM providers, dev tools, AI frameworks
- [x] **Project Runner** — project management with git quick-actions
- [x] **RAG Search** — codebase indexing, semantic search, AI Q&A with source citations
- [x] **Prompt Templates & Sandbox** — template library, dynamic variable forms, streaming sandbox with metrics
- [x] **Visual Workflow Builder** — node graph editor with DAG execution engine
- [x] **Workflow Debugger** — step-by-step execution, pause/highlight, runtime variable editing
- [x] **Terminal** — multi-shell support with history and quick-launch buttons
- [x] **System Monitor** — CPU/RAM/disk/swap gauges with top processes
- [x] **Settings** — comprehensive configuration for all providers and features

### Bug Fixes & Stability
- [x] Fixed `RAGIndexerWorker` / `RAGQAWorker` missing `stop()` methods — prevented crash when switching panels during active operations
- [x] Fixed UI freezing during panel switches — all long-running operations moved to QThread workers
- [x] Fixed `summarize_text` tool hardcoded to Ollama — now uses the active LLM provider with graceful fallback
- [x] Added `blockSignals()` guard in workflow context table to prevent infinite loops during population
- [x] Made context variable keys read-only in the debugger table to prevent accidental key corruption

---

## License

MIT — free for personal & commercial use
