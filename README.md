# NEXUS — Local AI & Dev Workspace

A dark, minimal PyQt6 desktop app that unifies:

- 🤖 **Ollama** — pull, run, delete, and chat with local AI models
- 📁 **Git Projects** — clone repos and run git commands with one click
- ⌨ **Terminal** — integrated CMD / PowerShell / Git Bash with live output
- 📊 **System Monitor** — CPU, RAM, disk, swap, top processes (live)
- ⚙ **Settings** — configure Ollama host, threads, GPU layers, paths

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
pip install PyQt6 psutil
python nexus_app.py
```

---

## Requirements

| Tool | Required? | Install |
|------|-----------|---------|
| Python 3.10+ | ✅ Yes | https://python.org |
| PyQt6 | ✅ Yes | `pip install PyQt6` |
| psutil | ✅ Yes | `pip install psutil` |
| Ollama | For AI tab | https://ollama.com |
| Git | For Git tab | https://git-scm.com |
| Git Bash (Win) | Optional | https://git-scm.com |

---

## Features

### Ollama Tab
- Lists all locally downloaded models with size
- Pull any model from the Ollama hub (llama3, mistral, phi3, gemma2, etc.)
- One-click Run (serve) and Chat dialog
- Delete models to free disk space
- GPU/CPU detection displayed

### Git Projects Tab
- Clone any GitHub/GitLab/Bitbucket repo with a destination picker
- Add existing local repos to the project list (persisted across sessions)
- One-click: `git pull`, `git status`, `git log`, `git fetch`
- Custom command box for any git command
- Projects saved to `~/.nexus_projects.json`

### Terminal Tab
- Shell selector: CMD / PowerShell / Git Bash (auto-detected)
- Working directory picker
- Command history (↑/↓ arrows)
- Quick-launch buttons (python, node, git, pip)
- Live streaming output with color-coded log

### System Monitor
- Real-time CPU %, RAM, disk, swap
- Color transitions (green → yellow → red)
- Top 12 processes by CPU
- Auto-refreshes every 2 seconds

---

## Open Source Models to Try

```
ollama pull llama3          # Meta Llama 3 8B
ollama pull mistral         # Mistral 7B
ollama pull phi3            # Microsoft Phi-3 Mini
ollama pull gemma2          # Google Gemma 2 9B
ollama pull codellama       # Code specialist
ollama pull qwen2           # Alibaba Qwen2 7B
ollama pull deepseek-coder  # DeepSeek Coder 6.7B
```

All models run 100% locally — no internet required after download,
no telemetry, no API costs.

---

## Architecture

- Single Python file (~600 lines), zero C extensions
- QThread workers stream subprocess output without blocking the UI
- Projects stored as plain JSON in home directory
- Stateless design — restart safely at any time


## License

MIT — free for personal & commercial use


## License

MIT — free for personal & commercial use


## Building EXE
```
pip install pyinstaller
python -m PyInstaller --onefile --windowed run_nexus.py
```

## Running with Custom Icon (Optional)
```
pip install pyinstaller
python -m PyInstaller --onefile --windowed --icon=path/to/icon.ico run_nexus.py
```
