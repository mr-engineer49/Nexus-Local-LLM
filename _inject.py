"""Inject _nexus_p5.py panels into nexus_app.py and update MainWindow."""
import sys

# ── Read source files ─────────────────────────────────────────────────────────
with open("nexus_app.py", encoding="utf-8") as f:
    content = f.read()

with open("_nexus_p5.py", encoding="utf-8-sig") as f:
    new_panels = f.read().strip()

# ── Step 1: Inject new panels before NavButton ───────────────────────────────
MARKER_WIN  = "# \u2500" * 22 + " " + "#  SIDEBAR NAV BUTTON"
# Simpler approach: find the exact string
MARKER = "#  SIDEBAR NAV BUTTON"
# find the full section header line + marker
idx = content.find(MARKER)
if idx == -1:
    print("ERROR: Could not find NavButton marker"); sys.exit(1)

# Walk back to find the start of the comment block (the dashes line)
line_start = content.rfind("\n", 0, idx)
block_start = content.rfind("\n", 0, line_start) + 1  # start of dashes line

content = content[:block_start] + new_panels + "\n\n\n" + content[block_start:]
print("OK: New panels injected before NavButton")

# ── Step 2: Update MainWindow pages/panels ───────────────────────────────────
OLD_TAG = "OllamaPanel(), GitHubPanel(), AgentPanel(),"
NEW_PAGES_BLOCK = '''        pages = [
            ("\U0001f916","Ollama"),("\U0001f4c1","Git"),("\U0001f419","GitHub"),
            ("\U0001f517","Agent"),("\U0001f3ac","Agent Studio"),("\U0001f680","Projects"),
            ("\u26a1","Workflows"),("\U0001f4e1","Status"),("\u2328","Terminal"),
            ("\U0001f4ca","System"),("\u2699","Settings"),
        ]
        panels = [
            OllamaPanel(), GitPanel(), GitHubPanel(),
            AgentPanel(), AgentStudioPanel(), ProjectRunnerPanel(),
            WorkflowPanel(), StatusDashboard(), TerminalPanel(),
            SystemPanel(), SettingsPanel(),
        ]'''

# Replace the whole pages + panels block
PAGES_START = '        pages = ['
PANELS_END_MARKER = 'panels.insert(1, GitPanel())'

if PAGES_START in content and PANELS_END_MARKER in content:
    ps = content.find(PAGES_START)
    pe = content.find(PANELS_END_MARKER) + len(PANELS_END_MARKER)
    content = content[:ps] + NEW_PAGES_BLOCK + content[pe:]
    print("OK: MainWindow pages/panels updated")
elif OLD_TAG in content:
    # fallback: just fix the panels line
    print("WARNING: Using fallback panel update")
else:
    print("WARNING: Could not find pages block, skipping")

# ── Step 3: Write result ──────────────────────────────────────────────────────
with open("nexus_app.py", "w", encoding="utf-8") as f:
    f.write(content)

total_lines = len(content.splitlines())
print(f"Done. nexus_app.py is now {total_lines} lines.")
