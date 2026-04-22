import re
from datetime import datetime
from PyQt6.QtWidgets import (
    QPushButton, QTextEdit, QAbstractItemView
)
from PyQt6.QtGui import (
    QColor, QTextCursor, QSyntaxHighlighter, QTextCharFormat,
    QFont, QPen
)
from PyQt6.QtCore import Qt
from ..core.style import THEME

class NavButton(QPushButton):
    def __init__(self, text, icon=""):
        super().__init__(f" {icon}  {text}")
        self.setObjectName("nav_btn")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(42)

    def set_active(self, active):
        self.setObjectName("nav_btn_active" if active else "nav_btn")
        self.setChecked(active)
        self.style().unpolish(self)
        self.style().polish(self)

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
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def append_line(self, text: str, level="info"):
        text = self._ansi_escape.sub('', text)
        color = self._colors.get(level, self._colors["info"])
        ts    = datetime.now().strftime("%H:%M:%S")
        html  = (f'<span style="color:#444466;">[{ts}]</span> '
                 f'<span style="color:{color};">{self._esc(text)}</span>')
        self.append(html)
        self.moveCursor(QTextCursor.MoveOperation.End)

    def append_token(self, tok: str):
        cur = self.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cur)
        
        # Use insertText with formatting to perfectly preserve whitespace (HTML strips spaces)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#d0d0ff"))
        cur.setCharFormat(fmt)
        cur.insertText(tok)
        
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
            fmt.setForeground(QColor(THEME["text3"]))
        self.setFormat(0, len(text), fmt)
