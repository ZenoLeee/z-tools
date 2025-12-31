import os
from typing import List
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from core.file_scanner import FileInfo, LargeFileScannerThread
from utils.file_utils import try_delete_file


class LargeFileTab(QWidget):
    """大文件扫描标签页"""

    def __init__(self):
        super().__init__()
        self.scanner_thread = None
        self.large_files: List[FileInfo] = []
        self.is_scanning = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 顶部控制面板
        top_layout = QHBoxLayout()

        # 目录选择
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

        top_layout.addStretch()
        layout.addLayout(top_layout)

        # 中间控制面板
        middle_layout = QHBoxLayout()

        # 最小文件大小
        middle_layout.addWidget(QLabel("最小文件大小:"))
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setRange(10, 10240)
        self.min_size_spin.setValue(100)
        self.min_size_spin.setSuffix(" MB")
        middle_layout.addWidget(self.min_size_spin)

        # 最大结果数
        middle_layout.addWidget(QLabel("最大结果数:"))
        self.max_results_spin = QSpinBox()
        self.max_results_spin.setRange(10, 10000)
        self.max_results_spin.setValue(1000)
        self.max_results_spin.setSingleStep(100)
        middle_layout.addWidget(self.max_results_spin)

        # 排除系统文件
        self.exclude_system_check = QCheckBox("排除系统文件")
        self.exclude_system_check.setChecked(True)
        middle_layout.addWidget(self.exclude_system_check)

        middle_layout.addStretch()
        layout.addLayout(middle_layout)

        # 扫描按钮区域
        button_layout = QHBoxLayout()

        self.scan_btn = QPushButton("开始扫描大文件")
        self.scan_btn.clicked.connect(self.start_scan)
        self.scan_btn.setMinimumHeight(40)
        self.scan_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
                background-color: #9b59b6;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
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
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.current_dir_label = QLabel("等待开始扫描...")
        progress_layout.addWidget(self.current_dir_label)

        layout.addLayout(progress_layout)

        # 统计信息
        stats_layout = QHBoxLayout()
        self.total_files_label = QLabel("找到大文件: 0 个")
        self.total_size_label = QLabel("总大小: 0 MB")

        stats_layout.addWidget(self.total_files_label)
        stats_layout.addWidget(self.total_size_label)
        stats_layout.addStretch()

        layout.addLayout(stats_layout)

        # 表格显示
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["文件名", "路径", "大小", "修改时间", "类型"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.setSortingEnabled(True)

        # 设置列宽
        self.table.setColumnWidth(0, 200)
        self.table.setColumnWidth(1, 300)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 80)

        layout.addWidget(self.table)

        # 底部操作按钮
        button_layout2 = QHBoxLayout()

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
        self.set_delete_buttons_enabled(False)

    def set_delete_buttons_enabled(self, enabled: bool):
        """设置删除按钮的启用状态"""
        self.delete_btn.setEnabled(enabled)

    def browse_directory(self):
        """浏览目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择扫描目录")
        if directory:
            self.dir_edit.setText(directory)

    def start_scan(self):
        """开始扫描"""
        directory = self.dir_edit.text().strip()

        # 双重验证
        if not directory:
            QMessageBox.warning(self, "警告", "请先通过浏览按钮选择扫描目录")
            return

        if not os.path.exists(directory):
            QMessageBox.warning(self, "警告", "选择的目录不存在，请重新选择")
            self.dir_edit.clear()  # 清空输入框
            return

        # 设置扫描状态
        self.is_scanning = True

        # 禁用开始扫描按钮，启用停止按钮
        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # 重置进度条和标签
        self.progress_bar.setValue(0)
        self.progress_label.setText("正在准备扫描...")
        self.current_dir_label.setText("正在收集文件信息...")

        # 禁用删除按钮
        self.set_delete_buttons_enabled(False)

        # 清空之前的扫描结果
        self.table.setRowCount(0)
        self.large_files = []
        self.update_stats()

        # 获取参数
        min_size_mb = self.min_size_spin.value()
        max_results = self.max_results_spin.value()
        exclude_system = self.exclude_system_check.isChecked()

        # 创建并启动扫描线程
        self.scanner_thread = LargeFileScannerThread(
            [directory],
            min_size_mb,
            max_results,
            exclude_system
        )

        self.scanner_thread.scan_progress.connect(self.update_scan_progress)
        self.scanner_thread.large_file_found.connect(self.add_large_file)
        self.scanner_thread.scan_finished.connect(self.on_scan_finished)
        self.scanner_thread.start()

        self.progress_label.setText("正在扫描大文件...")
        self.current_dir_label.setText("正在扫描文件...")

    def stop_scan(self):
        """停止扫描"""
        if self.scanner_thread:
            try:
                self.scanner_thread.stop()
                # 使用非阻塞方式等待
                if not self.scanner_thread.wait(1000):  # 等待1秒
                    print("线程未在1秒内结束，强制终止")
                    self.scanner_thread.terminate()
                    self.scanner_thread.wait()
            except Exception as e:
                print(f"停止线程出错: {e}")

        # 恢复按钮状态
        self.is_scanning = False
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_label.setText("扫描已停止")
        self.current_dir_label.setText("扫描被用户停止")

    def update_scan_progress(self, progress: int, total: int, text: str):
        """更新扫描进度"""
        try:
            self.progress_bar.setValue(progress)
            self.progress_label.setText(f"扫描进度: {progress}%")
            self.current_dir_label.setText(text)

            QApplication.processEvents()
        except Exception as e:
            print(f"更新进度条出错: {e}")

    def add_large_file(self, file_info):
        """添加大文件到表格"""
        # 添加到文件列表
        self.large_files.append(file_info)

        # 添加到表格
        row = self.table.rowCount()
        self.table.insertRow(row)

        # 文件名
        filename_item = QTableWidgetItem(file_info.filename)
        self.table.setItem(row, 0, filename_item)

        # 路径
        path_item = QTableWidgetItem(file_info.directory)
        path_item.setToolTip(file_info.path)
        self.table.setItem(row, 1, path_item)

        # 文件大小
        size_mb = file_info.size / (1024 * 1024)
        size_item = QTableWidgetItem(f"{size_mb:.2f} MB")
        size_item.setData(Qt.UserRole, file_info.size)  # 存储原始大小用于排序
        self.table.setItem(row, 2, size_item)

        # 修改时间
        time_item = QTableWidgetItem(file_info.modified_time.strftime("%Y-%m-%d %H:%M:%S"))
        self.table.setItem(row, 3, time_item)

        # 文件类型
        _, ext = os.path.splitext(file_info.filename)
        type_item = QTableWidgetItem(ext.upper() if ext else "未知")
        self.table.setItem(row, 4, type_item)

        # 更新统计信息
        self.update_stats()

        # 刷新表格显示
        self.table.viewport().update()

    def on_scan_finished(self, file_objects, total_files, total_size_mb):
        """扫描完成"""
        # 设置扫描状态
        self.is_scanning = False

        # 更新进度条
        self.progress_bar.setValue(100)
        self.progress_label.setText(f"扫描完成，找到 {total_files} 个大文件")
        self.current_dir_label.setText(f"总大小: {total_size_mb} MB")

        # 恢复按钮状态
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        # 如果有结果，启用删除按钮
        if total_files > 0:
            self.set_delete_buttons_enabled(True)

    def update_stats(self):
        """更新统计信息"""
        total_files = len(self.large_files)

        # 计算总大小
        total_size = sum(f.size for f in self.large_files)
        total_size_mb = total_size / (1024 * 1024)

        self.total_files_label.setText(f"找到大文件: {total_files} 个")
        self.total_size_label.setText(f"总大小: {total_size_mb:.2f} MB")

    def select_all_files(self):
        """全选所有文件"""
        self.table.selectAll()

    def invert_selection(self):
        """反选"""
        selection_model = self.table.selectionModel()
        model = self.table.model()

        # 创建一个新的选择
        selection = QItemSelection()

        for row in range(self.table.rowCount()):
            # 获取行的索引
            index = model.index(row, 0)

            # 如果当前行没被选中，则选中它
            if not selection_model.isRowSelected(row, QModelIndex()):
                # 创建选择范围（整行）
                row_selection = QItemSelection(index, model.index(row, model.columnCount() - 1))
                selection.merge(row_selection, QItemSelectionModel.Select)

        # 清除原有选择并应用新的选择
        selection_model.select(selection, QItemSelectionModel.ClearAndSelect)

    def open_file_folder(self):
        """打开文件所在文件夹"""
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个文件")
            return

        row = selected_items[0].row()
        file_path_item = self.table.item(row, 1)
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

        # 计算选中文件的总大小
        total_size_mb = 0
        for row in selected_rows:
            size_item = self.table.item(row, 2)
            if size_item:
                size_text = size_item.text().replace(" MB", "")
                try:
                    total_size_mb += float(size_text)
                except:
                    pass

        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除选中的 {len(selected_rows)} 个文件吗？\n总大小: {total_size_mb:.2f} MB",
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
                path_item = self.table.item(row, 1)
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

                        # 从文件列表中移除
                        file_info_to_remove = None
                        for file_info in self.large_files:
                            if file_info.path == file_path:
                                file_info_to_remove = file_info
                                break

                        if file_info_to_remove:
                            self.large_files.remove(file_info_to_remove)

                        deleted_count += 1
                    else:
                        failed_count += 1
                        error_messages.append(f"{os.path.basename(file_path)}: {message}")

            progress.close()

            # 更新统计信息
            self.update_stats()

            # 如果没有文件了，禁用删除按钮
            if len(self.large_files) == 0:
                self.set_delete_buttons_enabled(False)

            # 显示结果
            result_msg = f"删除完成:\n成功删除: {deleted_count} 个文件\n释放空间: {total_size_mb:.2f} MB\n删除失败: {failed_count} 个文件"

            if error_messages:
                result_msg += "\n\n失败详情:\n" + "\n".join(error_messages[:10])
                if len(error_messages) > 10:
                    result_msg += f"\n...还有 {len(error_messages) - 10} 个错误"

            QMessageBox.information(self, "删除结果", result_msg)