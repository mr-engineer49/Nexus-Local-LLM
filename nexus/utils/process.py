import os, sys, subprocess, shutil
from pathlib import Path

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

def kill_process_tree(pid, include_parent=True):
    """
    Recursively kill a process and all its children across platforms.
    Ensures no orphan processes (like npm workers) remain.
    """
    if not HAS_PSUTIL:
        # Fallback to simple termination if psutil is missing
        try:
            if sys.platform == "win32":
                subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)
            else:
                os.kill(pid, 9)
        except Exception: pass
        return

    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.kill()
            except Exception: pass
        if include_parent:
            try:
                parent.kill()
            except Exception: pass
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

def find_git_bash():
    """Locate git bash on Windows systems."""
    for c in [r"C:\Program Files\Git\bin\bash.exe",
              r"C:\Program Files (x86)\Git\bin\bash.exe",
              shutil.which("bash")]:
        if c and Path(c).exists(): return c
    return None
