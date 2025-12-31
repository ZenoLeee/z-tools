from PyQt5.QtWidgets import *
from ui.scanner_tab import ShortcutScannerTab
from ui.system_tab import SystemToolsTab
from ui.network_tab import NetworkToolsTab
from ui.duplicate_file_tab import DuplicateFileTab
from ui.large_file_tab import LargeFileTab

class WindowsToolbox(QMainWindow):
    """Windows工具箱主窗口"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Windows工具箱")
        self.setGeometry(100, 100, 1200, 800)

        # 设置应用样式
        QApplication.instance().setStyle("Fusion")

        # 创建标签页
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setMovable(False)

        # 快捷方式扫描标签页
        self.scanner_tab = ShortcutScannerTab()
        self.tabs.addTab(self.scanner_tab, "无效快捷方式清理")

        # 重复文件扫描标签页
        self.duplicate_file_tab = DuplicateFileTab()
        self.tabs.addTab(self.duplicate_file_tab, "重复文件清理")

        # 大文件扫描标签页
        self.large_file_tab = LargeFileTab()
        self.tabs.addTab(self.large_file_tab, "大文件清理")

        # 系统工具标签页
        self.system_tools_tab = SystemToolsTab()
        self.tabs.addTab(self.system_tools_tab, "系统工具")

        # 网络工具标签页
        self.network_tools_tab = NetworkToolsTab()
        self.tabs.addTab(self.network_tools_tab, "网络工具")

        self.setCentralWidget(self.tabs)

        # 创建状态栏
        self.statusBar().showMessage("就绪")

    def closeEvent(self, event):
        """关闭窗口事件"""
        # 停止快捷方式扫描线程
        if hasattr(self.scanner_tab, 'scanner_thread') and self.scanner_tab.scanner_thread:
            self.scanner_tab.scanner_thread.stop()
            self.scanner_tab.scanner_thread.wait()

        # 停止重复文件扫描线程
        if hasattr(self.duplicate_file_tab, 'scanner_thread') and self.duplicate_file_tab.scanner_thread:
            self.duplicate_file_tab.scanner_thread.stop()
            self.duplicate_file_tab.scanner_thread.wait()

        # 停止大文件扫描线程
        if hasattr(self.large_file_tab, 'scanner_thread') and self.large_file_tab.scanner_thread:
            self.large_file_tab.scanner_thread.stop()
            self.large_file_tab.scanner_thread.wait()

        # 停止Ping线程
        if hasattr(self.network_tools_tab, 'ping_thread') and self.network_tools_tab.ping_thread:
            self.network_tools_tab.ping_thread.stop()
            self.network_tools_tab.ping_thread.wait()

        event.accept()