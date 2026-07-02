from .config import SETTINGS

THEME = {
    "bg": "#121214", "bg2": "#1a1a1e", "bg3": "#24242b",
    "border": "#2e2e36",
    "accent":  SETTINGS.get("theme_accent", "#4f46e5"),
    "accent2": "#818cf8",
    "success": "#10b981", "warning": "#f59e0b", "error": "#ef4444",
    "text": "#f3f4f6", "text2": "#9ca3af", "text3": "#4b5563",
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color:{THEME['bg']}; color:{THEME['text']};
    font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size:13px;
}}
#sidebar {{
    background-color:{THEME['bg2']}; border-right:1px solid {THEME['border']};
}}
#nav_btn {{
    border:none; border-radius:4px; text-align:left; padding:8px 12px;
    margin:1px 8px; color:{THEME['text2']}; font-weight:normal;
}}
#nav_btn:hover {{ background-color:{THEME['bg3']}; color:{THEME['text']}; }}
#nav_btn_active {{
    background-color:{THEME['bg3']}; color:{THEME['accent2']};
    border-left:2px solid {THEME['accent']};
}}
QPushButton {{
    background-color:{THEME['bg3']}; border:1px solid {THEME['border']};
    border-radius:4px; padding:5px 12px; color:{THEME['text']};
    font-weight:normal;
}}
QPushButton:hover {{ background-color:{THEME['border']}; }}
QPushButton#primary {{ background-color:{THEME['accent']}; color:white; border:none; }}
QPushButton#primary:hover {{ background-color:{THEME['accent2']}; }}
QPushButton#success {{ border:1px solid {THEME['success']}; color:{THEME['success']}; }}
QPushButton#success:hover {{ background-color:{THEME['success']}; color:white; }}
QPushButton#warn    {{ border:1px solid {THEME['warning']}; color:{THEME['warning']}; }}
QPushButton#warn:hover {{ background-color:{THEME['warning']}; color:black; }}
QPushButton#danger  {{ border:1px solid {THEME['error']}; color:{THEME['error']}; }}
QPushButton#danger:hover {{ background-color:{THEME['error']}; color:white; }}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {{
    background-color:{THEME['bg2']}; border:1px solid {THEME['border']};
    border-radius:4px; padding:4px 8px; color:{THEME['text']}; selection-background-color:{THEME['accent']};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border:1px solid {THEME['accent']};
}}
QTextEdit, QPlainTextEdit, LogView, #logview {{
    font-family:"Consolas", "Courier New", monospace;
}}
QListWidget {{
    background-color:{THEME['bg2']}; border:1px solid {THEME['border']};
    border-radius:6px; outline:none; color:{THEME['text2']};
}}
QListWidget::item {{ padding:6px 8px; border-bottom:1px solid {THEME['bg']}; }}
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
    padding:6px 14px; border:1px solid {THEME['border']}; border-bottom:none;
}}
QTabBar::tab:selected {{ background:{THEME['bg']}; color:{THEME['accent2']}; border-bottom:1px solid {THEME['accent']}; }}
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
QGroupBox::title {{ subcontrol-origin:margin; left:10px; padding:0 4px; color:{THEME['text2']}; }}
QSplitter::handle {{ background:{THEME['border']}; }}
QSplitter::handle:horizontal {{ width:1px; }}
QSplitter::handle:vertical {{ height:1px; }}
QCheckBox {{ color:{THEME['text2']}; spacing:6px; }}
QCheckBox::indicator {{
    width:14px; height:14px; border:1px solid {THEME['border']};
    border-radius:3px; background:{THEME['bg3']};
}}
QCheckBox::indicator:checked {{ background:{THEME['accent']}; border-color:{THEME['accent']}; }}
QSpinBox {{ background:{THEME['bg3']}; border:1px solid {THEME['border']}; color:{THEME['text']}; padding:4px 8px; border-radius:4px; }}
QStatusBar {{ background:{THEME['bg2']}; color:{THEME['text3']}; border-top:1px solid {THEME['border']}; font-size:11px; }}
QGraphicsView {{ background:{THEME['bg']}; border:1px solid {THEME['border']}; border-radius:6px; }}
"""
