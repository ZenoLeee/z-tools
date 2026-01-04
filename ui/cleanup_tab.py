"""
整合的系统清理标签页
包含：无效快捷方式、重复文件、大文件、空文件夹、注册表清理
"""
import tkinter as tk
from tkinter import ttk
from ui.scanner_tab import ShortcutScannerTab
from ui.duplicate_file_tab import DuplicateFileTab
from ui.large_file_tab import LargeFileTab
from ui.empty_folder_tab import EmptyFolderTab
from ui.registry_tab import RegistryTab


class SystemCleanupTab(tk.Frame):
    """系统清理整合标签页"""

    def __init__(self, parent):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        # 创建主容器
        main_container = tk.Frame(self)
        main_container.pack(expand=True, fill='both', padx=5, pady=5)

        # 创建标题
        title_frame = tk.Frame(main_container, bg='#4A90E2', height=60)
        title_frame.pack(fill='x', pady=(0, 10))
        title_frame.pack_propagate(False)

        title_label = tk.Label(
            title_frame,
            text="🧹 系统清理工具",
            font=('Microsoft YaHei UI', 16, 'bold'),
            bg='#4A90E2',
            fg='white'
        )
        title_label.pack(expand=True)

        subtitle_label = tk.Label(
            title_frame,
            text="清理无效文件，释放磁盘空间 | 选择下方功能开始使用",
            font=('Microsoft YaHei UI', 9),
            bg='#4A90E2',
            fg='#E8F4F8'
        )
        subtitle_label.pack()

        # 创建子标签页（Notebook）
        self.notebook = ttk.Notebook(main_container)

        # 无效快捷方式清理
        self.shortcut_tab = ShortcutScannerTab(self.notebook)
        self.notebook.add(self.shortcut_tab, text="  🚫 无效快捷方式  ")

        # 重复文件清理
        self.duplicate_tab = DuplicateFileTab(self.notebook)
        self.notebook.add(self.duplicate_tab, text="  📑 重复文件  ")

        # 大文件清理
        self.large_file_tab = LargeFileTab(self.notebook)
        self.notebook.add(self.large_file_tab, text="  📦 大文件  ")

        # 空文件夹清理
        self.empty_folder_tab = EmptyFolderTab(self.notebook)
        self.notebook.add(self.empty_folder_tab, text="  📁 空文件夹  ")

        # 注册表清理
        self.registry_tab = RegistryTab(self.notebook)
        self.notebook.add(self.registry_tab, text="  🔍 注册表  ")

        self.notebook.pack(expand=True, fill='both')

        # 创建底部提示栏
        tip_frame = tk.Frame(main_container, bg='#F5F5F5', height=40)
        tip_frame.pack(fill='x', pady=(10, 0))
        tip_frame.pack_propagate(False)

        tip_label = tk.Label(
            tip_frame,
            text="💡 提示：建议先扫描再清理，清理前请仔细查看文件列表",
            font=('Microsoft YaHei UI', 9),
            bg='#F5F5F5',
            fg='#666'
        )
        tip_label.pack(expand=True)

    def on_closing(self):
        """关闭时的清理工作"""
        # 停止快捷方式扫描
        if hasattr(self.shortcut_tab, 'scanner_thread') and self.shortcut_tab.scanner_thread:
            if self.shortcut_tab.scanner_thread.is_alive():
                self.shortcut_tab.scanner_thread.stop()
                self.shortcut_tab.scanner_thread.join(timeout=1)

        # 停止快捷方式恢复
        if hasattr(self.shortcut_tab, 'recovery_thread') and self.shortcut_tab.recovery_thread:
            if self.shortcut_tab.recovery_thread.is_alive():
                self.shortcut_tab.recovery_thread.stop()
                self.shortcut_tab.recovery_thread.join(timeout=1)

        # 停止重复文件扫描
        if hasattr(self.duplicate_tab, 'scanner_thread') and self.duplicate_tab.scanner_thread:
            if self.duplicate_tab.scanner_thread.is_alive():
                self.duplicate_tab.scanner_thread.stop()
                self.duplicate_tab.scanner_thread.join(timeout=1)

        # 停止重复文件删除
        if hasattr(self.duplicate_tab, 'delete_thread') and self.duplicate_tab.delete_thread:
            if self.duplicate_tab.delete_thread.is_alive():
                self.duplicate_tab.delete_thread.stop()
                self.duplicate_tab.delete_thread.join(timeout=1)

        # 停止大文件扫描
        if hasattr(self.large_file_tab, 'scanner_thread') and self.large_file_tab.scanner_thread:
            if self.large_file_tab.scanner_thread.is_alive():
                self.large_file_tab.scanner_thread.stop()
                self.large_file_tab.scanner_thread.join(timeout=1)

        # 停止大文件删除
        if hasattr(self.large_file_tab, 'delete_thread') and self.large_file_tab.delete_thread:
            if self.large_file_tab.delete_thread.is_alive():
                self.large_file_tab.delete_thread.stop()
                self.large_file_tab.delete_thread.join(timeout=1)

        # 停止空文件夹扫描
        if hasattr(self.empty_folder_tab, 'scanner_thread') and self.empty_folder_tab.scanner_thread:
            if self.empty_folder_tab.scanner_thread.is_alive():
                self.empty_folder_tab.scanner_thread.stop()
                self.empty_folder_tab.scanner_thread.join(timeout=1)

        # 停止空文件夹删除
        if hasattr(self.empty_folder_tab, 'delete_thread') and self.empty_folder_tab.delete_thread:
            if self.empty_folder_tab.delete_thread.is_alive():
                self.empty_folder_tab.delete_thread.stop()
                self.empty_folder_tab.delete_thread.join(timeout=1)

        # 停止注册表扫描
        if hasattr(self.registry_tab, 'scanner_thread') and self.registry_tab.scanner_thread:
            if self.registry_tab.scanner_thread.is_alive():
                self.registry_tab.scanner_thread.stop()
                self.registry_tab.scanner_thread.join(timeout=1)
