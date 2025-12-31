import os
from PyQt5.QtWidgets import *

class SystemToolsTab(QWidget):
    """系统工具标签页"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 创建按钮网格
        grid_layout = QGridLayout()

        # 第一行
        self.disk_clean_btn = QPushButton("磁盘清理")
        self.disk_clean_btn.clicked.connect(self.run_disk_clean)
        grid_layout.addWidget(self.disk_clean_btn, 0, 0)

        self.system_info_btn = QPushButton("系统信息")
        self.system_info_btn.clicked.connect(self.show_system_info)
        grid_layout.addWidget(self.system_info_btn, 0, 1)

        # 第二行
        self.services_btn = QPushButton("服务管理")
        self.services_btn.clicked.connect(self.open_services)
        grid_layout.addWidget(self.services_btn, 1, 0)

        self.taskmgr_btn = QPushButton("任务管理器")
        self.taskmgr_btn.clicked.connect(self.open_task_manager)
        grid_layout.addWidget(self.taskmgr_btn, 1, 1)

        # 第三行
        self.regedit_btn = QPushButton("注册表编辑器")
        self.regedit_btn.clicked.connect(self.open_regedit)
        grid_layout.addWidget(self.regedit_btn, 2, 0)

        self.control_panel_btn = QPushButton("控制面板")
        self.control_panel_btn.clicked.connect(self.open_control_panel)
        grid_layout.addWidget(self.control_panel_btn, 2, 1)

        # 第四行
        self.device_mgr_btn = QPushButton("设备管理器")
        self.device_mgr_btn.clicked.connect(self.open_device_manager)
        grid_layout.addWidget(self.device_mgr_btn, 3, 0)

        self.event_viewer_btn = QPushButton("事件查看器")
        self.event_viewer_btn.clicked.connect(self.open_event_viewer)
        grid_layout.addWidget(self.event_viewer_btn, 3, 1)

        layout.addLayout(grid_layout)
        layout.addStretch()
        self.setLayout(layout)

    def run_disk_clean(self):
        os.system("cleanmgr")

    def show_system_info(self):
        os.system("msinfo32")

    def open_services(self):
        os.system("services.msc")

    def open_task_manager(self):
        os.system("taskmgr")

    def open_regedit(self):
        os.system("regedit")

    def open_control_panel(self):
        os.system("control")

    def open_device_manager(self):
        os.system("devmgmt.msc")

    def open_event_viewer(self):
        os.system("eventvwr.msc")