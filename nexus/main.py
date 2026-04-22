import sys
from PyQt6.QtWidgets import QApplication
from .app import MainWindow
from .core.style import STYLESHEET

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
