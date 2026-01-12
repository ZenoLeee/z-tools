import tkinter as tk
from tkinter import ttk
from ui.cleanup_tab import SystemCleanupTab
from ui.system_tab import SystemToolsTab
from ui.network_tab import NetworkToolsTab
from ui.system_tray import SystemTrayManager
from core.version_manager import VersionManager, UpdateDialog
from utils.platform import get_platform_name, get_supported_features


class WindowsToolbox(tk.Tk):
    """
    跨平台系统工具箱主窗口
    类名保持 WindowsToolbox 以向后兼容
    """

    def __init__(self):
        super().__init__()

        # 先隐藏窗口，避免显示初始化过程
        self.withdraw()

        self.platform_name = get_platform_name()
        self.supported_features = get_supported_features()
        self.version_manager = VersionManager(self)

        # 初始化系统托盘（先设置为None）
        self.tray_manager = None

        self.init_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 绑定窗口最小化事件
        self.bind('<Unmap>', self._on_window_minimize)

        # 启动时检查更新（后台）
        self._check_update_on_startup()

        # 现在显示窗口
        self.deiconify()
        self.update()

    def init_ui(self):
        # 设置窗口图标
        self._set_window_icon()

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
            has_update, latest_version, changelog, force_update = self.version_manager.check_for_updates(show_message_if_no_update=False)
            if has_update:
                # 在主线程显示更新对话框
                self.after(0, lambda: UpdateDialog(self, self.version_manager, has_update, latest_version, changelog, force_update))

        thread = threading.Thread(target=check_in_background, daemon=True)
        thread.start()

    def _check_update_manually(self):
        """手动检查更新"""
        import threading
        def check():
            has_update, latest_version, changelog, force_update = self.version_manager.check_for_updates(show_message_if_no_update=True)
            if has_update:
                self.after(0, lambda: UpdateDialog(self, self.version_manager, has_update, latest_version, changelog, force_update))

        # 显示检查中提示
        self.status_bar.config(text="正在检查更新...")
        thread = threading.Thread(target=check, daemon=True)
        thread.start()

    def _set_window_icon(self):
        """设置窗口图标"""
        import os
        import sys

        # 获取资源目录路径
        if getattr(sys, 'frozen', False):
            # 打包后的exe，资源在exe所在目录
            base_path = os.path.dirname(sys.executable)
        else:
            # 开发环境
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        icon_path = os.path.join(base_path, 'resources', 'icon.ico')

        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as e:
                print(f"设置窗口图标失败: {e}")

    def _init_system_tray(self):
        """初始化系统托盘"""
        try:
            self.tray_manager = SystemTrayManager(
                window=self,
                show_window_callback=self._show_window_from_tray,
                quit_callback=self._quit_from_tray
            )
            self.tray_manager.create_tray_icon()

            # 在后台线程中运行托盘图标
            import threading
            self._tray_thread = threading.Thread(
                target=self.tray_manager.icon.run,
                daemon=True
            )
            self._tray_thread.start()
        except Exception as e:
            print(f"系统托盘初始化失败: {e}")
            self.tray_manager = None

    def _show_window_from_tray(self):
        """从托盘显示窗口"""
        # 停止托盘图标
        if self.tray_manager:
            self.tray_manager.stop()
            self.tray_manager = None

        # 显示窗口
        self.deiconify()
        self.lift()
        self.focus_force()

    def _quit_from_tray(self):
        """从托盘退出程序"""
        self._cleanup_and_quit()

    def _on_window_minimize(self, event):
        """
        窗口最小化事件处理
        当窗口最小化时，自动隐藏到托盘
        """
        # 检查窗口是否被最小化
        if self.state() == 'iconic':
            # 延迟隐藏，确保最小化动画完成
            self.after(100, self._hide_to_tray)

    def _hide_to_tray(self):
        """隐藏窗口到托盘"""
        # 每次最小化时都创建托盘图标
        if self.tray_manager is None:
            self._init_system_tray()

        if self.tray_manager:
            self.withdraw()  # 隐藏窗口

    def _cleanup_and_quit(self):
        """清理资源并退出"""
        # 停止清理标签页中的所有线程
        self.cleanup_tab.on_closing()

        # 停止Ping线程
        if hasattr(self.network_tools_tab, 'ping_thread') and self.network_tools_tab.ping_thread:
            if self.network_tools_tab.ping_thread.is_alive():
                self.network_tools_tab.ping_thread.stop()
                self.network_tools_tab.ping_thread.join(timeout=1)

        # 停止托盘图标
        if self.tray_manager:
            self.tray_manager.stop()

        # 销毁窗口
        self.destroy()

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
        """关闭窗口事件 - 直接退出程序"""
        self._cleanup_and_quit()
