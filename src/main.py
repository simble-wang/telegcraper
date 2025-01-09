import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 