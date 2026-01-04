import subprocess
import tkinter as tk
from tkinter import ttk


class SystemToolsTab(tk.Frame):
    """系统工具标签页"""

    def __init__(self, parent):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        # 创建主容器
        main_frame = tk.Frame(self, bg='#F5F5F5')
        main_frame.pack(expand=True, fill='both', padx=20, pady=20)

        # 标题
        title_label = tk.Label(
            main_frame,
            text="Windows 系统工具",
            font=('Microsoft YaHei UI', 16, 'bold'),
            bg='#F5F5F5',
            fg='#333333'
        )
        title_label.pack(pady=(0, 20))

        # 创建按钮网格容器
        grid_container = tk.Frame(main_frame, bg='#F5F5F5')
        grid_container.pack(expand=True)

        # 按钮样式 - 固定宽度确保一致
        button_style = {
            'font': ('Microsoft YaHei UI', 11),
            'bg': '#FFFFFF',
            'fg': '#333333',
            'activebackground': '#4A90E2',
            'activeforeground': 'white',
            'relief': 'flat',
            'cursor': 'hand2',
            'borderwidth': 1,
            'highlightthickness': 1,
            'highlightbackground': '#E0E0E0',
            'highlightcolor': '#4A90E2',
            'pady': 15,
            'padx': 20,
            'width': 25  # 固定宽度，确保所有按钮长度一致
        }

        # 第一行
        row1 = tk.Frame(grid_container, bg='#F5F5F5')
        row1.pack(fill='x', pady=5)

        self.disk_clean_btn = tk.Button(
            row1, text="🗑️ 磁盘清理",
            command=self.run_disk_clean,
            **button_style
        )
        self.disk_clean_btn.pack(side='left', padx=5)

        self.system_info_btn = tk.Button(
            row1, text="ℹ️ 系统信息",
            command=self.show_system_info,
            **button_style
        )
        self.system_info_btn.pack(side='left', padx=5)

        # 第二行
        row2 = tk.Frame(grid_container, bg='#F5F5F5')
        row2.pack(fill='x', pady=5)

        self.services_btn = tk.Button(
            row2, text="⚙️ 服务管理",
            command=self.open_services,
            **button_style
        )
        self.services_btn.pack(side='left', padx=5)

        self.taskmgr_btn = tk.Button(
            row2, text="📊 任务管理器",
            command=self.open_task_manager,
            **button_style
        )
        self.taskmgr_btn.pack(side='left', padx=5)

        # 第三行
        row3 = tk.Frame(grid_container, bg='#F5F5F5')
        row3.pack(fill='x', pady=5)

        self.regedit_btn = tk.Button(
            row3, text="📝 注册表编辑器",
            command=self.open_regedit,
            **button_style
        )
        self.regedit_btn.pack(side='left', padx=5)

        self.control_panel_btn = tk.Button(
            row3, text="🎛️ 控制面板",
            command=self.open_control_panel,
            **button_style
        )
        self.control_panel_btn.pack(side='left', padx=5)

        # 第四行
        row4 = tk.Frame(grid_container, bg='#F5F5F5')
        row4.pack(fill='x', pady=5)

        self.device_mgr_btn = tk.Button(
            row4, text="🔧 设备管理器",
            command=self.open_device_manager,
            **button_style
        )
        self.device_mgr_btn.pack(side='left', padx=5)

        self.event_viewer_btn = tk.Button(
            row4, text="📋 事件查看器",
            command=self.open_event_viewer,
            **button_style
        )
        self.event_viewer_btn.pack(side='left', padx=5)

    def run_disk_clean(self):
        subprocess.Popen('cleanmgr', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)

    def show_system_info(self):
        subprocess.Popen('msinfo32', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)

    def open_services(self):
        subprocess.Popen('services.msc', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)

    def open_task_manager(self):
        subprocess.Popen('taskmgr', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)

    def open_regedit(self):
        subprocess.Popen('regedit', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)

    def open_control_panel(self):
        subprocess.Popen('control', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)

    def open_device_manager(self):
        subprocess.Popen('devmgmt.msc', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)

    def open_event_viewer(self):
        subprocess.Popen('eventvwr.msc', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
