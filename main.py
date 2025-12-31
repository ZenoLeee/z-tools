import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import WindowsToolbox

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    toolbox = WindowsToolbox()
    toolbox.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()