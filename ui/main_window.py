import tkinter as tk
from tkinter import ttk
from ui.scanner_tab import ShortcutScannerTab
from ui.system_tab import SystemToolsTab
from ui.network_tab import NetworkToolsTab
from ui.duplicate_file_tab import DuplicateFileTab
from ui.large_file_tab import LargeFileTab
from ui.empty_folder_tab import EmptyFolderTab


class WindowsToolbox(tk.Tk):
    """Windows工具箱主窗口"""

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def init_ui(self):
        self.title("Windows工具箱")
        self.geometry("1200x800")
        self.minsize(900, 600)

        # 设置样式
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # 自定义按钮样式
        self.button_style = {
            'font': ('Microsoft YaHei UI', 10),
            'relief': 'flat',
            'cursor': 'hand2',
            'borderwidth': 0,
            'pady': 8,
            'padx': 20
        }

        # 主按钮样式
        self.primary_button_style = {
            'bg': '#4A90E2',
            'fg': 'white',
            'activebackground': '#357ABD',
            'activeforeground': 'white',
            'font': ('Microsoft YaHei UI', 11, 'bold'),
            'relief': 'flat',
            'cursor': 'hand2',
            'borderwidth': 0,
            'pady': 10,
            'padx': 25
        }

        # 危险按钮样式
        self.danger_button_style = {
            'bg': '#E74C3C',
            'fg': 'white',
            'activebackground': '#C0392B',
            'activeforeground': 'white',
            'font': ('Microsoft YaHei UI', 10),
            'relief': 'flat',
            'cursor': 'hand2',
            'borderwidth': 0,
            'pady': 8,
            'padx': 20
        }

        # 成功按钮样式
        self.success_button_style = {
            'bg': '#2ECC71',
            'fg': 'white',
            'activebackground': '#27AE60',
            'activeforeground': 'white',
            'font': ('Microsoft YaHei UI', 10),
            'relief': 'flat',
            'cursor': 'hand2',
            'borderwidth': 0,
            'pady': 8,
            'padx': 20
        }

        # 创建Notebook（标签页控件）
        self.notebook = ttk.Notebook(self)

        # 快捷方式扫描标签页
        self.scanner_tab = ShortcutScannerTab(self.notebook)
        self.notebook.add(self.scanner_tab, text="无效快捷方式清理")

        # 重复文件扫描标签页
        self.duplicate_file_tab = DuplicateFileTab(self.notebook)
        self.notebook.add(self.duplicate_file_tab, text="重复文件清理")

        # 大文件扫描标签页
        self.large_file_tab = LargeFileTab(self.notebook)
        self.notebook.add(self.large_file_tab, text="大文件清理")

        # 空文件夹扫描标签页
        self.empty_folder_tab = EmptyFolderTab(self.notebook)
        self.notebook.add(self.empty_folder_tab, text="空文件夹清理")

        # 系统工具标签页
        self.system_tools_tab = SystemToolsTab(self.notebook)
        self.notebook.add(self.system_tools_tab, text="系统工具")

        # 网络工具标签页
        self.network_tools_tab = NetworkToolsTab(self.notebook)
        self.notebook.add(self.network_tools_tab, text="网络工具")

        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)

        # 创建状态栏
        self.status_bar = tk.Label(self, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def on_closing(self):
        """关闭窗口事件"""
        # 停止快捷方式扫描线程
        if hasattr(self.scanner_tab, 'scanner_thread') and self.scanner_tab.scanner_thread:
            if self.scanner_tab.scanner_thread.is_alive():
                self.scanner_tab.scanner_thread.stop()
                self.scanner_tab.scanner_thread.join(timeout=1)

        # 停止快捷方式恢复线程
        if hasattr(self.scanner_tab, 'recovery_thread') and self.scanner_tab.recovery_thread:
            if self.scanner_tab.recovery_thread.is_alive():
                self.scanner_tab.recovery_thread.stop()
                self.scanner_tab.recovery_thread.join(timeout=1)

        # 停止重复文件扫描线程
        if hasattr(self.duplicate_file_tab, 'scanner_thread') and self.duplicate_file_tab.scanner_thread:
            if self.duplicate_file_tab.scanner_thread.is_alive():
                self.duplicate_file_tab.scanner_thread.stop()
                self.duplicate_file_tab.scanner_thread.join(timeout=1)

        # 停止重复文件删除线程
        if hasattr(self.duplicate_file_tab, 'delete_thread') and self.duplicate_file_tab.delete_thread:
            if self.duplicate_file_tab.delete_thread.is_alive():
                self.duplicate_file_tab.delete_thread.stop()
                self.duplicate_file_tab.delete_thread.join(timeout=1)

        # 停止大文件扫描线程
        if hasattr(self.large_file_tab, 'scanner_thread') and self.large_file_tab.scanner_thread:
            if self.large_file_tab.scanner_thread.is_alive():
                self.large_file_tab.scanner_thread.stop()
                self.large_file_tab.scanner_thread.join(timeout=1)

        # 停止大文件删除线程
        if hasattr(self.large_file_tab, 'delete_thread') and self.large_file_tab.delete_thread:
            if self.large_file_tab.delete_thread.is_alive():
                self.large_file_tab.delete_thread.stop()
                self.large_file_tab.delete_thread.join(timeout=1)

        # 停止空文件夹扫描线程
        if hasattr(self.empty_folder_tab, 'scanner_thread') and self.empty_folder_tab.scanner_thread:
            if self.empty_folder_tab.scanner_thread.is_alive():
                self.empty_folder_tab.scanner_thread.stop()
                self.empty_folder_tab.scanner_thread.join(timeout=1)

        # 停止空文件夹删除线程
        if hasattr(self.empty_folder_tab, 'delete_thread') and self.empty_folder_tab.delete_thread:
            if self.empty_folder_tab.delete_thread.is_alive():
                self.empty_folder_tab.delete_thread.stop()
                self.empty_folder_tab.delete_thread.join(timeout=1)

        # 停止Ping线程
        if hasattr(self.network_tools_tab, 'ping_thread') and self.network_tools_tab.ping_thread:
            if self.network_tools_tab.ping_thread.is_alive():
                self.network_tools_tab.ping_thread.stop()
                self.network_tools_tab.ping_thread.join(timeout=1)

        self.destroy()
