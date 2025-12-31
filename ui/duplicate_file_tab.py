import os
from typing import List
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from core.file_scanner import FileInfo, DuplicateScannerThread
from utils.file_utils import try_delete_file


class DuplicateFileTab(QWidget):
    """重复文件扫描标签页"""

    def __init__(self):
        super().__init__()
        self.scanner_thread = None
        self.file_objects: List[FileInfo] = []
        self.duplicate_groups = {}
        self.is_scanning = False
        self.shortcuts = []  # 添加这行
        self.current_action_label = QLabel()  # 添加这行
        self.init_ui()

    def init_ui(self):

        layout = QVBoxLayout()

        # 顶部控制面板
        top_layout = QHBoxLayout()

        # 目录选择 - 设置为只读，只能通过浏览选择
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("请选择要扫描的目录...")
        self.dir_edit.setMinimumWidth(300)
        self.dir_edit.setReadOnly(True)  # 设置为只读，禁止手动输入
        self.dir_edit.setStyleSheet("""
            QLineEdit:read-only {
                background-color: #f5f5f5;
                color: #666666;
                border: 1px solid #cccccc;
            }
        """)
        top_layout.addWidget(QLabel("扫描目录:"))
        top_layout.addWidget(self.dir_edit)

        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_directory)
        top_layout.addWidget(self.browse_btn)

        # 全盘扫描按钮
        self.scan_all_disks_btn = QPushButton("全盘扫描")
        self.scan_all_disks_btn.clicked.connect(self.scan_all_disks)
        self.scan_all_disks_btn.setToolTip("扫描电脑上的所有硬盘")
        self.scan_all_disks_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                padding: 5px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        top_layout.addWidget(self.scan_all_disks_btn)

        # 文件类型过滤
        top_layout.addWidget(QLabel("文件类型:"))
        self.filetype_combo = QComboBox()
        self.filetype_combo.addItems(["所有文件", "图片文件", "文档文件", "视频文件", "音频文件", "自定义"])
        self.filetype_combo.currentTextChanged.connect(self.on_filetype_changed)
        top_layout.addWidget(self.filetype_combo)

        self.custom_filetype_edit = QLineEdit()
        self.custom_filetype_edit.setPlaceholderText("例如: .txt,.jpg,.mp4")
        self.custom_filetype_edit.setVisible(False)
        top_layout.addWidget(self.custom_filetype_edit)

        layout.addLayout(top_layout)

        # 中间控制面板
        middle_layout = QHBoxLayout()

        # 最小文件大小
        middle_layout.addWidget(QLabel("最小文件大小:"))
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setRange(0, 10240)
        self.min_size_spin.setValue(100)
        self.min_size_spin.setSuffix(" KB")
        middle_layout.addWidget(self.min_size_spin)

        # 排除系统文件
        self.exclude_system_check = QCheckBox("排除系统文件")
        self.exclude_system_check.setChecked(True)
        middle_layout.addWidget(self.exclude_system_check)

        middle_layout.addStretch()

        layout.addLayout(middle_layout)

        # 扫描按钮区域
        button_layout = QHBoxLayout()

        self.scan_btn = QPushButton("开始扫描重复文件")
        self.scan_btn.clicked.connect(self.start_scan)
        self.scan_btn.setMinimumHeight(40)
        self.scan_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
                background-color: #3498db;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        button_layout.addWidget(self.scan_btn)

        self.stop_btn = QPushButton("停止扫描")
        self.stop_btn.clicked.connect(self.stop_scan)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)

        button_layout.addStretch()

        layout.addLayout(button_layout)

        # 进度条区域
        progress_layout = QVBoxLayout()

        self.progress_label = QLabel("就绪")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)

        self.current_file_label = QLabel("等待开始扫描...")
        progress_layout.addWidget(self.current_file_label)

        layout.addLayout(progress_layout)

        # 统计信息
        stats_layout = QHBoxLayout()
        self.total_files_label = QLabel("总文件数: 0")
        self.duplicate_groups_label = QLabel("重复组数: 0")
        self.duplicate_files_label = QLabel("重复文件数: 0")
        self.reclaimable_label = QLabel("可回收空间: 0 MB")

        stats_layout.addWidget(self.total_files_label)
        stats_layout.addWidget(self.duplicate_groups_label)
        stats_layout.addWidget(self.duplicate_files_label)
        stats_layout.addWidget(self.reclaimable_label)
        stats_layout.addStretch()

        layout.addLayout(stats_layout)

        # 表格显示
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["保留", "文件名", "路径", "大小", "修改时间", "MD5", "重复组"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.setSortingEnabled(True)

        # 设置多选模式
        self.table.setSelectionMode(QAbstractItemView.MultiSelection)

        # 设置复选框委托
        self.table.setItemDelegateForColumn(0, CheckBoxDelegate())

        # 设置列宽
        self.table.setColumnWidth(0, 50)  # 保留列
        self.table.setColumnWidth(1, 200)  # 文件名列
        self.table.setColumnWidth(2, 300)  # 路径列
        self.table.setColumnWidth(3, 80)  # 大小列
        self.table.setColumnWidth(4, 120)  # 修改时间列
        self.table.setColumnWidth(5, 150)  # MD5列
        self.table.setColumnWidth(6, 80)  # 重复组列

        layout.addWidget(self.table)

        # 底部操作按钮
        button_layout2 = QHBoxLayout()

        # 修改按钮文本和功能
        self.smart_select_btn = QPushButton("智能选择")
        self.smart_select_btn.clicked.connect(self.smart_select_duplicates)
        self.smart_select_btn.setToolTip("自动选择所有重复文件中较旧的文件（保留最新的）")
        button_layout2.addWidget(self.smart_select_btn)

        self.invert_selection_btn = QPushButton("反选")
        self.invert_selection_btn.clicked.connect(self.invert_selection)
        button_layout2.addWidget(self.invert_selection_btn)

        self.open_btn = QPushButton("打开所在文件夹")
        self.open_btn.clicked.connect(self.open_file_folder)
        button_layout2.addWidget(self.open_btn)

        self.delete_btn = QPushButton("删除选中的文件")
        self.delete_btn.clicked.connect(self.delete_selected_files)
        self.delete_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
        button_layout2.addWidget(self.delete_btn)

        button_layout2.addStretch()
        layout.addLayout(button_layout2)

        self.setLayout(layout)

    def smart_select_duplicates(self):
        """智能选择 - 选择所有重复文件中较旧的文件（保留最新的）"""
        # 清空当前选择
        self.table.clearSelection()

        selected_count = 0

        # 遍历所有重复组
        for group_id, files in self.duplicate_groups.items():
            if len(files) > 1:
                # 按修改时间排序，最新的在最前面
                sorted_files = sorted(files, key=lambda x: x.modified_time, reverse=True)

                # 选择除了最新文件外的所有文件
                for i, file_info in enumerate(sorted_files):
                    if i > 0:  # 跳过第一个（最新的）
                        # 在表格中找到对应的行
                        for row in range(self.table.rowCount()):
                            path_item = self.table.item(row, 2)
                            if path_item and path_item.toolTip() == file_info.path:
                                self.table.selectRow(row)
                                selected_count += 1
                                break

        if selected_count > 0:
            self.current_action_label.setText(f"智能选择了 {selected_count} 个较旧的文件")
        else:
            self.current_action_label.setText("没有找到需要选择的重复文件")

    def set_delete_buttons_enabled(self, enabled: bool):
        """设置删除按钮的启用状态"""
        self.delete_btn.setEnabled(enabled)
        self.smart_select_btn.setEnabled(enabled)
        self.invert_selection_btn.setEnabled(enabled)

    def on_filetype_changed(self, text: str):
        """文件类型选择变化"""
        self.custom_filetype_edit.setVisible(text == "自定义")

    def browse_directory(self):
        """浏览目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择扫描目录")
        if directory:
            self.dir_edit.setText(directory)

    def get_file_types(self):
        """获取选中的文件类型"""
        filetype = self.filetype_combo.currentText()

        if filetype == "所有文件":
            return ["*"]
        elif filetype == "图片文件":
            return [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"]
        elif filetype == "文档文件":
            return [".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]
        elif filetype == "视频文件":
            return [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".rmvb"]
        elif filetype == "音频文件":
            return [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma"]
        elif filetype == "自定义":
            text = self.custom_filetype_edit.text().strip()
            if text:
                return [ext.strip() for ext in text.split(",")]

        return ["*"]

    def scan_all_disks(self):
        """全盘扫描 - 扫描电脑上的所有硬盘"""
        if self.is_scanning:
            QMessageBox.warning(self, "警告", "扫描正在进行中，请等待当前扫描完成")
            return

        # 给用户提示
        reply = QMessageBox.information(
            self, "全盘扫描说明",
            "全盘扫描说明：\n\n"
            "1. 扫描会跳过系统文件和权限不足的文件\n"
            "2. 扫描过程中不会请求管理员权限\n"
            "3. 扫描时间取决于硬盘大小和文件数量\n"
            "4. 可以随时点击'停止扫描'按钮中断\n\n"
            "点击确定开始扫描",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            # 获取所有硬盘分区
            all_disks = self.get_all_disks()

            if not all_disks:
                QMessageBox.warning(self, "警告", "未找到可用的硬盘分区")
                return

            # 显示全盘扫描信息
            disk_info = "\n".join(all_disks)
            QMessageBox.information(self, "全盘扫描", f"将扫描以下硬盘分区:\n\n{disk_info}")

            # 设置全盘扫描状态
            self.is_scanning = True

            # 禁用开始扫描按钮，启用停止按钮
            self.scan_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.scan_all_disks_btn.setEnabled(False)  # 禁用全盘扫描按钮

            # 禁用删除按钮
            self.set_delete_buttons_enabled(False)

            # 清空之前的扫描结果
            self.table.setRowCount(0)
            self.file_objects = []
            self.duplicate_groups = {}
            self.shortcuts = []
            self.update_stats()

            # 重置进度条
            self.progress_bar.setValue(0)
            self.progress_label.setText("正在准备全盘扫描...")
            self.current_file_label.setText("正在获取硬盘信息...")

            # 获取参数
            file_types = self.get_file_types()
            min_size_kb = self.min_size_spin.value()
            min_size_bytes = min_size_kb * 1024  # 转换为字节
            exclude_system = self.exclude_system_check.isChecked()

            # 创建并启动扫描线程
            self.scanner_thread = DuplicateScannerThread(
                directories=all_disks,  # 传入所有硬盘分区
                file_types=file_types,
                min_size=min_size_bytes,
                exclude_system=exclude_system
            )

            # 连接信号
            self.scanner_thread.scan_progress.connect(self.update_scan_progress)
            self.scanner_thread.file_processed.connect(self.update_file_progress)
            self.scanner_thread.duplicate_found.connect(self.add_duplicate_file)
            self.scanner_thread.scan_finished.connect(self.on_scan_finished)

            self.scanner_thread.start()

            self.progress_label.setText("正在进行全盘扫描...")
            self.current_file_label.setText(f"正在扫描 {len(all_disks)} 个硬盘分区...")

    def get_all_disks(self):
        """获取电脑上的所有硬盘分区"""
        import os
        import sys

        disks = []

        if sys.platform == 'win32':  # Windows系统
            import ctypes
            import string

            # 获取逻辑驱动器列表
            drives = []
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()

            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drive = f"{letter}:\\"
                    drives.append(drive)
                bitmask >>= 1

            # 检查每个驱动器是否可用
            for drive in drives:
                try:
                    # 检查驱动器类型和可用性
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)

                    # DRIVE_FIXED = 3 (本地硬盘)
                    # DRIVE_REMOVABLE = 2 (可移动磁盘)
                    # DRIVE_REMOTE = 4 (网络驱动器)
                    # DRIVE_CDROM = 5 (光盘)
                    # DRIVE_RAMDISK = 6 (RAM磁盘)

                    # 只扫描本地硬盘和可移动磁盘（不包括光盘、网络驱动器等）
                    if drive_type in [2, 3, 6]:  # 可移动磁盘、本地硬盘、RAM磁盘
                        # 检查驱动器是否就绪
                        if os.path.exists(drive):
                            # 获取驱动器信息
                            try:
                                import psutil
                                usage = psutil.disk_usage(drive)
                                total_gb = usage.total / (1024 * 1024 * 1024)
                                free_gb = usage.free / (1024 * 1024 * 1024)
                                used_gb = usage.used / (1024 * 1024 * 1024)

                                # 只添加有足够空间的驱动器（避免扫描CD-ROM等）
                                if total_gb > 0.1:  # 大于100MB的驱动器
                                    disks.append(drive)
                                    print(
                                        f"找到驱动器: {drive} (总空间: {total_gb:.1f}GB, 已用: {used_gb:.1f}GB, 可用: {free_gb:.1f}GB)")
                            except ImportError:
                                # 如果没有psutil，简单检查
                                if os.path.isdir(drive):
                                    disks.append(drive)
                                    print(f"找到驱动器: {drive}")
                except Exception as e:
                    print(f"检查驱动器 {drive} 失败: {e}")

        elif sys.platform == 'darwin':  # macOS
            # macOS的挂载点通常在 /Volumes
            volumes_path = "/Volumes"
            if os.path.exists(volumes_path):
                for item in os.listdir(volumes_path):
                    volume_path = os.path.join(volumes_path, item)
                    if os.path.isdir(volume_path):
                        disks.append(volume_path)
                        print(f"找到卷: {volume_path}")

            # 添加根目录
            disks.append("/")

        else:  # Linux/Unix
            # 检查常见的挂载点
            import subprocess

            try:
                # 使用df命令获取挂载点
                result = subprocess.run(['df', '-h'], capture_output=True, text=True)
                lines = result.stdout.strip().split('\n')

                for line in lines[1:]:  # 跳过标题行
                    parts = line.split()
                    if len(parts) >= 6:
                        mount_point = parts[5]
                        # 排除系统目录，只扫描数据目录
                        if mount_point and mount_point != '/' and not mount_point.startswith('/boot'):
                            disks.append(mount_point)
                            print(f"找到挂载点: {mount_point}")

                # 添加根目录
                disks.append("/")
            except:
                # 如果df命令失败，使用常见目录
                common_dirs = ['/', '/home', '/mnt', '/media']
                for dir_path in common_dirs:
                    if os.path.exists(dir_path):
                        disks.append(dir_path)

        # 如果没有找到任何磁盘，添加一个默认目录
        if not disks:
            if sys.platform == 'win32':
                disks = ['C:\\']
            else:
                disks = ['/']

        return disks

    def start_scan(self):
        """开始扫描"""
        directory = self.dir_edit.text().strip()

        # 双重验证：不仅检查是否存在，还要检查是否是通过浏览选择的
        if not directory:
            QMessageBox.warning(self, "警告", "请先通过浏览按钮选择扫描目录")
            return

        if not os.path.exists(directory):
            QMessageBox.warning(self, "警告", "选择的目录不存在，请重新选择")
            self.dir_edit.clear()  # 清空输入框
            return

        print(f"开始扫描目录: {directory}")

        # 设置扫描状态
        self.is_scanning = True

        # 禁用开始扫描按钮，启用停止按钮
        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # 禁用删除按钮
        self.set_delete_buttons_enabled(False)

        # 清空之前的扫描结果
        self.table.setRowCount(0)
        self.file_objects = []
        self.duplicate_groups = {}
        self.shortcuts = []
        self.update_stats()

        # 重置进度条
        self.progress_bar.setValue(0)
        self.progress_label.setText("正在准备扫描...")
        self.current_file_label.setText("正在初始化扫描...")

        # 获取参数
        file_types = self.get_file_types()
        min_size_kb = self.min_size_spin.value()
        min_size_bytes = min_size_kb * 1024  # 转换为字节
        exclude_system = self.exclude_system_check.isChecked()

        # 创建并启动扫描线程
        self.scanner_thread = DuplicateScannerThread(
            directories=[directory],
            file_types=file_types,
            min_size=min_size_bytes,
            exclude_system=exclude_system
        )

        # 连接信号
        self.scanner_thread.scan_progress.connect(self.update_scan_progress)
        self.scanner_thread.file_processed.connect(self.update_file_progress)
        self.scanner_thread.duplicate_found.connect(self.add_duplicate_file)
        self.scanner_thread.scan_finished.connect(self.on_scan_finished)

        self.scanner_thread.start()

        self.progress_label.setText("正在扫描目录...")
        self.current_file_label.setText("正在初始化扫描...")

    def stop_scan(self):
        """停止扫描"""
        print("尝试停止扫描...")

        if self.scanner_thread:
            print(f"停止线程: {self.scanner_thread}")

            # 先设置停止标志
            self.scanner_thread.stop()

            # 等待一小段时间让线程响应
            if not self.scanner_thread.wait(500):  # 等待500ms
                print("线程没有及时响应，尝试强制终止")
                # 强制终止线程
                self.scanner_thread.terminate()
                if not self.scanner_thread.wait(2000):  # 再等待2秒
                    print("无法终止线程")

            print("线程已停止")

        # 恢复按钮状态
        self.is_scanning = False
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.scan_all_disks_btn.setEnabled(True)  # 重新启用全盘扫描按钮

        # 更新界面状态
        self.progress_label.setText("扫描已停止")
        self.current_file_label.setText("用户取消了扫描")

    def update_scan_progress(self, current: int, total: int, text: str):
        """更新扫描进度"""
        # 这里 current 应该是已扫描大小的百分比
        progress = min(current, 100)  # 确保不超过100%
        self.progress_bar.setValue(progress)

        # 更新标签文本
        if text.startswith("扫描:"):
            # 只显示文件名部分，去掉"扫描:"前缀
            filename = text[3:] if len(text) > 3 else text
            self.current_file_label.setText(f"正在扫描: {filename}")
            self.progress_label.setText(f"扫描进度: {progress}%")
        elif "计算:" in text:
            filename = text.split("计算:")[1] if "计算:" in text else text
            self.current_file_label.setText(f"正在计算: {filename}")
            self.progress_label.setText(f"计算进度: {progress}%")
        elif "扫描完成" in text:
            self.progress_label.setText("扫描完成")
            self.current_file_label.setText(text)
        else:
            self.progress_label.setText(text)
            self.current_file_label.setText(text)

    def update_file_progress(self, progress: int, total_files: int, text: str):
        """更新文件处理进度（按文件大小）"""
        # 这里的 progress 应该是已扫描大小的百分比
        progress = min(progress, 100)
        self.progress_bar.setValue(progress)

        if "完成" in text:
            self.progress_label.setText("扫描完成")
        else:
            self.progress_label.setText(f"扫描进度: {progress}%")

        self.current_file_label.setText(text)

    def add_duplicate_file(self, file_info, group_id):
        """添加重复文件到表格"""
        # 添加到文件对象列表
        self.file_objects.append(file_info)

        # 添加到重复组字典
        if group_id not in self.duplicate_groups:
            self.duplicate_groups[group_id] = []
        self.duplicate_groups[group_id].append(file_info)

        # 添加到表格
        row = self.table.rowCount()
        self.table.insertRow(row)

        # 保留复选框
        keep_item = QTableWidgetItem()
        keep_item.setCheckState(Qt.Checked if file_info.keep else Qt.Unchecked)
        keep_item.setFlags(keep_item.flags() | Qt.ItemIsUserCheckable)
        keep_item.setData(Qt.UserRole, file_info.path)  # 存储文件路径
        self.table.setItem(row, 0, keep_item)

        # 文件名
        filename_item = QTableWidgetItem(file_info.filename)
        self.table.setItem(row, 1, filename_item)

        # 路径
        path_item = QTableWidgetItem(file_info.directory)
        path_item.setToolTip(file_info.path)
        self.table.setItem(row, 2, path_item)

        # 文件大小
        size_mb = file_info.size / (1024 * 1024)
        size_item = QTableWidgetItem(f"{size_mb:.2f} MB")
        size_item.setData(Qt.UserRole, file_info.size)  # 存储原始大小用于排序
        self.table.setItem(row, 3, size_item)

        # 修改时间
        time_item = QTableWidgetItem(file_info.modified_time.strftime("%Y-%m-%d %H:%M:%S"))
        self.table.setItem(row, 4, time_item)

        # MD5（只显示前8位）
        md5_short = file_info.md5_hash[:8] + "..." if len(file_info.md5_hash) > 8 else file_info.md5_hash
        md5_item = QTableWidgetItem(md5_short)
        md5_item.setToolTip(file_info.md5_hash)
        self.table.setItem(row, 5, md5_item)

        # 重复组
        group_item = QTableWidgetItem(str(file_info.duplicate_group))
        self.table.setItem(row, 6, group_item)

        # 如果不是保留文件，设置为红色背景
        if not file_info.keep:
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QColor(255, 200, 200))

        # 更新统计信息
        self.update_stats()

    def on_scan_finished(self, file_objects, total_files, duplicate_groups, duplicate_files):
        """扫描完成"""
        print(
            f"收到 scan_finished 信号: total_files={total_files}, duplicate_groups={duplicate_groups}, duplicate_files={duplicate_files}")

        # 设置扫描状态
        self.is_scanning = False

        print(f"扫描完成，找到 {len(file_objects)} 个文件")

        # 保存扫描结果
        self.file_objects = file_objects

        # 构建重复组字典
        self.duplicate_groups = {}
        duplicate_file_list = []

        for file_info in file_objects:
            if file_info.is_duplicate and file_info.duplicate_group > 0:
                if file_info.duplicate_group not in self.duplicate_groups:
                    self.duplicate_groups[file_info.duplicate_group] = []
                self.duplicate_groups[file_info.duplicate_group].append(file_info)
                duplicate_file_list.append(file_info)

        print(f"找到 {len(duplicate_file_list)} 个重复文件，{len(self.duplicate_groups)} 个重复组")

        # 清空表格
        self.table.setRowCount(0)

        # 只添加重复文件到表格
        for file_info in duplicate_file_list:
            self.add_duplicate_file(file_info, file_info.duplicate_group)

        # 更新进度条
        self.progress_bar.setValue(100)
        self.progress_label.setText(f"扫描完成")
        self.current_file_label.setText(f"找到 {duplicate_files} 个重复文件，{duplicate_groups} 个重复组")

        # 恢复按钮状态
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.scan_all_disks_btn.setEnabled(True)  # 重新启用全盘扫描按钮

        # 如果有结果，启用删除按钮
        if duplicate_files > 0:
            self.set_delete_buttons_enabled(True)

        # 计算可回收空间
        total_reclaimable = 0
        for file_info in file_objects:
            if file_info.is_duplicate and not file_info.keep:
                total_reclaimable += file_info.size

        self.reclaimable_label.setText(f"可回收空间: {total_reclaimable / (1024 * 1024):.2f} MB")

    def update_stats(self):
        """更新统计信息"""
        total_files = len(self.file_objects)
        duplicate_files = sum(1 for f in self.file_objects if f.is_duplicate and not f.keep)
        duplicate_groups = len(set(f.duplicate_group for f in self.file_objects if f.is_duplicate))

        self.total_files_label.setText(f"总文件数: {total_files}")
        self.duplicate_files_label.setText(f"重复文件数: {duplicate_files}")
        self.duplicate_groups_label.setText(f"重复组数: {duplicate_groups}")

    def select_all_duplicates(self):
        """智能选择 - 选择所有重复文件中较旧的文件（保留最新的）"""
        self.table.clearSelection()

        # 按重复组分组
        groups = {}
        for file_info in self.file_objects:
            if file_info.is_duplicate:
                group_id = file_info.duplicate_group
                if group_id not in groups:
                    groups[group_id] = []
                groups[group_id].append(file_info)

        selected_count = 0

        # 选择每个组中除最新文件外的所有文件
        for group_id, files in groups.items():
            if len(files) > 1:
                # 按修改时间排序，最新的在最前面
                sorted_files = sorted(files, key=lambda x: x.modified_time, reverse=True)

                # 选择除了最新文件外的所有文件
                for i, file_info in enumerate(sorted_files):
                    if i > 0:  # 跳过第一个（最新的）
                        for row in range(self.table.rowCount()):
                            path_item = self.table.item(row, 2)
                            if path_item and path_item.toolTip() == file_info.path:
                                self.table.selectRow(row)
                                selected_count += 1
                                break

        if selected_count > 0:
            self.current_action_label.setText(f"智能选择了 {selected_count} 个较旧的文件")
        else:
            self.current_action_label.setText("没有找到需要选择的重复文件")

    def invert_selection(self):
        """反选 - 修复闪退问题"""
        try:
            selection_model = self.table.selectionModel()
            model = self.table.model()

            # 创建一个新的选择
            selection = QItemSelection()

            for row in range(self.table.rowCount()):
                # 获取行的索引
                index = model.index(row, 0)

                # 如果当前行被选中，则取消选中；如果没选中，则选中
                if selection_model.isRowSelected(row, QModelIndex()):
                    # 该行当前是选中的，反选时应该取消选中
                    # 这里我们不做任何操作，因为我们要选中所有没被选中的行
                    pass
                else:
                    # 该行当前没被选中，反选时应该选中
                    # 创建选择范围（整行）
                    row_selection = QItemSelection(index, model.index(row, model.columnCount() - 1))
                    selection.merge(row_selection, QItemSelectionModel.Select)

            # 应用新的选择
            selection_model.select(selection, QItemSelectionModel.ClearAndSelect)

        except Exception as e:
            print(f"反选时出错: {e}")
            QMessageBox.warning(self, "错误", f"反选时出错: {e}")

    def open_file_folder(self):
        """打开文件所在文件夹"""
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个文件")
            return

        row = selected_items[0].row()
        file_path_item = self.table.item(row, 2)
        if file_path_item:
            folder_path = file_path_item.text()
            try:
                os.startfile(folder_path)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法打开文件夹: {e}")

    def delete_selected_files(self):
        """删除选中的文件"""
        # 检查是否正在扫描
        if self.is_scanning:
            QMessageBox.warning(self, "警告", "扫描正在进行中，请等待扫描完成后再删除")
            return

        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的文件")
            return

        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除选中的 {len(selected_rows)} 个文件吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            deleted_count = 0
            failed_count = 0
            error_messages = []

            # 按行号倒序排列，以便从后往前删除
            rows_to_delete = sorted(selected_rows, reverse=True)

            # 创建进度对话框
            progress = QProgressDialog("正在删除文件...", "取消", 0, len(rows_to_delete), self)
            progress.setWindowTitle("删除进度")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            for i, row in enumerate(rows_to_delete):
                if progress.wasCanceled():
                    break

                # 获取文件路径
                path_item = self.table.item(row, 2)
                if path_item:
                    file_path = path_item.toolTip()
                    progress.setLabelText(f"正在删除: {os.path.basename(file_path)}")
                    progress.setValue(i)

                    QApplication.processEvents()  # 保持UI响应

                    # 尝试删除文件
                    success, message = try_delete_file(file_path)

                    if success:
                        # 从表格中移除行
                        self.table.removeRow(row)

                        # 从文件对象列表中移除
                        self.file_objects = [f for f in self.file_objects if f.path != file_path]

                        deleted_count += 1
                    else:
                        failed_count += 1
                        error_messages.append(f"{os.path.basename(file_path)}: {message}")

            progress.close()

            # 更新统计信息
            self.update_stats()

            # 如果没有文件了，禁用删除按钮
            if len(self.file_objects) == 0:
                self.set_delete_buttons_enabled(False)

            # 显示结果
            result_msg = f"删除完成:\n成功删除: {deleted_count} 个文件\n删除失败: {failed_count} 个文件"

            if error_messages:
                result_msg += "\n\n失败详情:\n" + "\n".join(error_messages[:10])
                if len(error_messages) > 10:
                    result_msg += f"\n...还有 {len(error_messages) - 10} 个错误"

            QMessageBox.information(self, "删除结果", result_msg)


class CheckBoxDelegate(QStyledItemDelegate):
    """复选框委托类"""

    def createEditor(self, parent, option, index):
        return None  # 禁用编辑

    def paint(self, painter, option, index):
        """绘制复选框"""
        if index.column() == 0:  # 只在第一列绘制复选框
            # 获取复选框状态
            checked = index.data(Qt.CheckStateRole) == Qt.Checked

            # 绘制复选框样式
            checkbox_style = QStyleOptionButton()
            checkbox_style.rect = option.rect
            checkbox_style.state = QStyle.State_Enabled
            checkbox_style.state |= QStyle.State_Active

            if checked:
                checkbox_style.state |= QStyle.State_On
            else:
                checkbox_style.state |= QStyle.State_Off

            # 居中绘制
            checkbox_style.rect.moveCenter(option.rect.center())

            QApplication.style().drawControl(QStyle.CE_CheckBox, checkbox_style, painter)
        else:
            super().paint(painter, option, index)

    def editorEvent(self, event, model, option, index):
        """处理复选框点击事件"""
        if index.column() == 0 and event.type() == QEvent.MouseButtonRelease:
            # 切换复选框状态
            checked = index.data(Qt.CheckStateRole) == Qt.Checked
            model.setData(index, Qt.Unchecked if checked else Qt.Checked, Qt.CheckStateRole)
            return True
        return False