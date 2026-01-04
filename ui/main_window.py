import tkinter as tk
from tkinter import ttk
from ui.scanner_tab import ShortcutScannerTab
from ui.system_tab import SystemToolsTab
from ui.network_tab import NetworkToolsTab
from ui.duplicate_file_tab import DuplicateFileTab
from ui.large_file_tab import LargeFileTab
from ui.empty_folder_tab import EmptyFolderTab
from core.version_manager import VersionManager, UpdateDialog


class WindowsToolbox(tk.Tk):
    """Windows工具箱主窗口"""

    def __init__(self):
        super().__init__()
        self.version_manager = VersionManager(self)
        self.init_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        # 启动时检查更新（后台）
        self._check_update_on_startup()

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

        # 创建菜单栏
        self._create_menu_bar()

        # 创建状态栏
        self.status_bar = tk.Label(self, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="检查更新", command=self._check_update_manually)
        help_menu.add_separator()
        help_menu.add_command(label="关于", command=self._show_about)

    def _check_update_on_startup(self):
        """启动时后台检查更新"""
        import threading
        def check_in_background():
            import time
            time.sleep(2)  # 延迟2秒，等待窗口完全加载
            has_update, latest_version, changelog = self.version_manager.check_for_updates(show_message_if_no_update=False)
            if has_update:
                # 在主线程显示更新对话框
                self.after(0, lambda: UpdateDialog(self, self.version_manager, has_update, latest_version, changelog))

        thread = threading.Thread(target=check_in_background, daemon=True)
        thread.start()

    def _check_update_manually(self):
        """手动检查更新"""
        import threading
        def check():
            has_update, latest_version, changelog = self.version_manager.check_for_updates(show_message_if_no_update=True)
            if has_update:
                self.after(0, lambda: UpdateDialog(self, self.version_manager, has_update, latest_version, changelog))

        # 显示检查中提示
        self.status_bar.config(text="正在检查更新...")
        thread = threading.Thread(target=check, daemon=True)
        thread.start()

    def _show_about(self):
        """显示关于对话框"""
        about_text = f"""
Windows工具箱
版本：{self.version_manager.CURRENT_VERSION}

一款功能强大的Windows系统工具箱

功能特性：
• 无效快捷方式清理
• 重复文件查找与清理
• 大文件查找与管理
• 空文件夹清理
• 系统工具
• 网络工具

© 2025 WindowsToolbox
        """

        from tkinter import messagebox
        messagebox.showinfo("关于", about_text.strip())

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
