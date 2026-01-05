import tkinter as tk
from tkinter import ttk
from ui.cleanup_tab import SystemCleanupTab
from ui.system_tab import SystemToolsTab
from ui.network_tab import NetworkToolsTab
from core.version_manager import VersionManager, UpdateDialog
from utils.platform import get_platform_name, get_supported_features


class WindowsToolbox(tk.Tk):
    """
    跨平台系统工具箱主窗口
    类名保持 WindowsToolbox 以向后兼容
    """

    def __init__(self):
        super().__init__()
        self.platform_name = get_platform_name()
        self.supported_features = get_supported_features()
        self.version_manager = VersionManager(self)
        self.init_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        # 启动时检查更新（后台）
        self._check_update_on_startup()

    def init_ui(self):
        # 根据平台设置窗口标题
        app_title = "Windows工具箱" if self.platform_name == "Windows" else f"{self.platform_name}工具箱"
        self.title(app_title)
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

        # 系统清理标签页（整合了4个清理功能）
        self.cleanup_tab = SystemCleanupTab(self.notebook)
        self.notebook.add(self.cleanup_tab, text="  🧹 系统清理  ")

        # 系统工具标签页
        self.system_tools_tab = SystemToolsTab(self.notebook)
        self.notebook.add(self.system_tools_tab, text="  ⚙️ 系统工具  ")

        # 网络工具标签页
        self.network_tools_tab = NetworkToolsTab(self.notebook)
        self.notebook.add(self.network_tools_tab, text="  🌐 网络工具  ")

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
        # 根据平台显示不同的功能列表
        features = [
            "• 重复文件查找与清理",
            "• 大文件查找与管理",
            "• 空文件夹清理",
            "• 网络工具"
        ]

        if self.supported_features.get('shortcut_cleanup'):
            features.append("• 无效快捷方式清理")

        if self.supported_features.get('registry_cleanup'):
            features.append("• 注册表清理")
            features.append("• 启动项管理")

        features_text = "\n".join(features)

        about_text = f"""
{self.platform_name}工具箱
版本：{self.version_manager.CURRENT_VERSION}
平台：{self.platform_name}

一款功能强大的跨平台系统工具箱

功能特性：
{features_text}

© 2025 WindowsToolbox
        """

        from tkinter import messagebox
        messagebox.showinfo("关于", about_text.strip())

    def on_closing(self):
        """关闭窗口事件"""
        # 停止清理标签页中的所有线程
        self.cleanup_tab.on_closing()

        # 停止Ping线程
        if hasattr(self.network_tools_tab, 'ping_thread') and self.network_tools_tab.ping_thread:
            if self.network_tools_tab.ping_thread.is_alive():
                self.network_tools_tab.ping_thread.stop()
                self.network_tools_tab.ping_thread.join(timeout=1)

        self.destroy()
