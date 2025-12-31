import os
from typing import List
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from core.shortcut_scanner import ShortcutInfo, UnifiedScannerThread
from utils.file_utils import try_delete_file

class ShortcutScannerTab(QWidget):
    """快捷方式扫描标签页"""

    def __init__(self):
        super().__init__()
        self.scanner_thread = None
        self.shortcuts: List[ShortcutInfo] = []
        self.is_scanning = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 顶部控制面板
        top_layout = QHBoxLayout()

        # 扫描按钮 - 调整到合适大小
        self.scan_btn = QPushButton("开始扫描所有磁盘的快捷方式")
        self.scan_btn.clicked.connect(self.start_scan)
        self.scan_btn.setMinimumHeight(40)  # 减小高度
        self.scan_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;  /* 减小字体 */
                font-weight: bold;
                padding: 8px;  /* 减小内边距 */
                background-color: #4CAF50;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        top_layout.addWidget(self.scan_btn)

        # 停止扫描按钮 - 调整到合适大小
        self.stop_btn = QPushButton("停止扫描")
        self.stop_btn.clicked.connect(self.stop_scan)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumHeight(40)  # 减小高度
        self.stop_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;  /* 减小字体 */
                padding: 8px;  /* 减小内边距 */
                background-color: #f44336;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        top_layout.addWidget(self.stop_btn)

        top_layout.addStretch()

        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索无效快捷方式...")
        self.search_edit.textChanged.connect(self.filter_shortcuts)
        self.search_edit.setMinimumWidth(200)
        top_layout.addWidget(QLabel("搜索:"))
        top_layout.addWidget(self.search_edit)

        layout.addLayout(top_layout)

        # 进度条区域
        progress_layout = QVBoxLayout()

        # 总进度条
        self.total_progress_label = QLabel("就绪")
        self.total_progress_label.setStyleSheet("font-weight: bold;")
        progress_layout.addWidget(self.total_progress_label)

        self.total_progress_bar = QProgressBar()
        self.total_progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.total_progress_bar)

        # 当前操作标签
        self.current_action_label = QLabel("等待开始扫描...")
        progress_layout.addWidget(self.current_action_label)

        layout.addLayout(progress_layout)

        # 统计信息
        stats_layout = QHBoxLayout()
        self.total_label = QLabel("无效快捷方式总数: 0")
        self.current_label = QLabel("当前显示: 0")
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.current_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # 表格显示
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["名称", "路径", "目标", "类型", "错误信息"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.setSortingEnabled(True)

        # 设置列宽
        self.table.setColumnWidth(0, 200)  # 名称列
        self.table.setColumnWidth(1, 250)  # 路径列
        self.table.setColumnWidth(2, 250)  # 目标列
        self.table.setColumnWidth(3, 80)  # 类型列（4个汉字宽度）
        self.table.setColumnWidth(4, 200)  # 错误信息列（10个汉字宽度）

        # 设置列宽调整模式
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)  # 名称列固定
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # 路径列自动拉伸
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # 目标列自动拉伸
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)  # 类型列固定
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)  # 错误信息列自动拉伸

        # 设置表格最小宽度，确保所有列都能显示
        self.table.setMinimumWidth(980)  # 所有列宽度之和加上一些边距

        layout.addWidget(self.table)

        # 底部操作按钮
        button_layout = QHBoxLayout()

        self.open_btn = QPushButton("打开所在文件夹")
        self.open_btn.clicked.connect(self.open_shortcut_folder)
        button_layout.addWidget(self.open_btn)

        self.run_btn = QPushButton("尝试运行")
        self.run_btn.clicked.connect(self.run_shortcut)
        button_layout.addWidget(self.run_btn)

        self.delete_btn = QPushButton("删除选中的")
        self.delete_btn.clicked.connect(self.delete_shortcut)
        self.delete_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
        button_layout.addWidget(self.delete_btn)

        self.delete_all_btn = QPushButton("删除全部")
        self.delete_all_btn.clicked.connect(self.delete_all_shortcuts)
        self.delete_all_btn.setStyleSheet("background-color: #ff4757; color: white;")
        button_layout.addWidget(self.delete_all_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 初始时禁用删除按钮
        self.set_delete_buttons_enabled(False)

    def set_delete_buttons_enabled(self, enabled: bool):
        """设置删除按钮的启用状态"""
        self.delete_btn.setEnabled(enabled)
        self.delete_all_btn.setEnabled(enabled)

    def start_scan(self):
        """开始扫描"""
        # 设置扫描状态
        self.is_scanning = True

        # 禁用开始扫描按钮，启用停止按钮
        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # 禁用删除按钮
        self.set_delete_buttons_enabled(False)

        # 清空之前的扫描结果
        self.table.setRowCount(0)
        self.shortcuts = []
        self.update_stats()

        # 创建并启动扫描线程
        self.scanner_thread = UnifiedScannerThread()
        self.scanner_thread.scan_progress.connect(self.update_progress)
        self.scanner_thread.invalid_shortcut_found.connect(self.add_invalid_shortcut)
        self.scanner_thread.scan_finished.connect(self.on_scan_finished)
        self.scanner_thread.start()

        self.total_progress_label.setText("正在扫描所有磁盘...")
        self.current_action_label.setText("正在初始化扫描...")

    def stop_scan(self):
        """停止扫描"""
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.scanner_thread.stop()
            self.scanner_thread.wait()
            self.total_progress_label.setText("扫描已停止")
            self.current_action_label.setText("扫描被用户停止")

        # 恢复按钮状态
        self.is_scanning = False
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        # 如果有结果，启用删除按钮
        if len(self.shortcuts) > 0:
            self.set_delete_buttons_enabled(True)

    def update_progress(self, current: int, total: int, action_text: str):
        """更新进度"""
        # 更新总进度
        progress_percent = int((current / total) * 100)
        self.total_progress_bar.setMaximum(100)
        self.total_progress_bar.setValue(progress_percent)

        # 更新标签
        self.total_progress_label.setText(f"总体进度: {progress_percent}%")
        self.current_action_label.setText(action_text)

    def add_invalid_shortcut(self, shortcut):
        """添加无效快捷方式到列表"""
        # 添加到列表
        self.shortcuts.append(shortcut)

        # 添加到表格
        row = self.table.rowCount()
        self.table.insertRow(row)

        # 名称 - 使用显示名称
        name_item = QTableWidgetItem(shortcut.display_name if shortcut.display_name else shortcut.name)
        self.table.setItem(row, 0, name_item)

        # 路径
        path_item = QTableWidgetItem(shortcut.path)
        path_item.setToolTip(shortcut.path)
        self.table.setItem(row, 1, path_item)

        # 目标
        target_item = QTableWidgetItem(shortcut.target_path[:100] if shortcut.target_path else "")
        target_item.setToolTip(shortcut.target_path)
        self.table.setItem(row, 2, target_item)

        # 类型
        type_text = self.get_type_display_name(shortcut.shortcut_type)
        type_item = QTableWidgetItem(type_text)
        self.table.setItem(row, 3, type_item)

        # 错误信息
        error_item = QTableWidgetItem(shortcut.error_message)
        error_item.setForeground(QColor("red"))
        self.table.setItem(row, 4, error_item)

        # 更新统计信息
        self.update_stats()

    def on_scan_finished(self):
        """扫描完成"""
        # 设置扫描状态
        self.is_scanning = False

        # 更新进度条
        self.total_progress_bar.setValue(100)
        self.total_progress_label.setText(f"扫描完成，共找到 {len(self.shortcuts)} 个无效快捷方式")
        self.current_action_label.setText("扫描完成")

        # 恢复按钮状态
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        # 如果有结果，启用删除按钮
        if len(self.shortcuts) > 0:
            self.set_delete_buttons_enabled(True)

        # 如果有结果，自动调整列宽
        if self.table.rowCount() > 0:
            # 自动调整列宽，但保持固定列的宽度不变
            self.table.resizeColumnToContents(1)  # 路径列
            self.table.resizeColumnToContents(2)  # 目标列
            self.table.resizeColumnToContents(4)  # 错误信息列

    def filter_shortcuts(self):
        """根据搜索框过滤快捷方式"""
        search_text = self.search_edit.text().lower()

        # 显示所有行
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, False)

        # 如果有搜索文本，隐藏不匹配的行
        if search_text:
            for row in range(self.table.rowCount()):
                match = False
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item and search_text in item.text().lower():
                        match = True
                        break
                self.table.setRowHidden(row, not match)

        # 更新显示数量
        self.update_stats()

    def get_type_display_name(self, shortcut_type: str) -> str:
        """获取类型显示名称"""
        type_map = {
            "start_menu": "开始菜单",
            "application": "应用程序",
            "document": "文档",
            "unknown": "未知"
        }
        return type_map.get(shortcut_type, shortcut_type)

    def update_stats(self):
        """更新统计信息"""
        total_invalid = len(self.shortcuts)

        # 计算当前显示的数量
        displayed = 0
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                displayed += 1

        self.total_label.setText(f"无效快捷方式总数: {total_invalid}")
        self.current_label.setText(f"当前显示: {displayed}")

    def open_shortcut_folder(self):
        """打开快捷方式所在文件夹"""
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个快捷方式")
            return

        row = selected_items[0].row()
        shortcut_path = self.table.item(row, 1).text()
        folder_path = os.path.dirname(shortcut_path)

        try:
            os.startfile(folder_path)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开文件夹: {e}")

    def run_shortcut(self):
        """运行选中的快捷方式"""
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个快捷方式")
            return

        row = selected_items[0].row()
        shortcut_path = self.table.item(row, 1).text()
        shortcut_name = self.table.item(row, 0).text()

        try:
            # 尝试运行快捷方式
            result = os.startfile(shortcut_path)

            # 如果运行成功，询问用户是否将其标记为有效
            reply = QMessageBox.question(
                self, "快捷方式运行成功",
                f"快捷方式 '{shortcut_name}' 运行成功！\n是否将其从无效列表中移除？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 从列表中移除
                self.table.removeRow(row)

                # 从原始列表中移除
                for i, shortcut in enumerate(self.shortcuts):
                    if shortcut.path == shortcut_path:
                        del self.shortcuts[i]
                        break

                self.update_stats()
                QMessageBox.information(self, "成功", "快捷方式已从列表中移除")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法运行快捷方式: {e}")

    def delete_shortcut(self):
        """删除选中的快捷方式"""
        # 检查是否正在扫描
        if self.is_scanning:
            QMessageBox.warning(self, "警告", "扫描正在进行中，请等待扫描完成后再删除")
            return

        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个快捷方式")
            return

        row = selected_items[0].row()
        shortcut_name = self.table.item(row, 0).text()
        shortcut_path = self.table.item(row, 1).text()

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除快捷方式 '{shortcut_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success, message = try_delete_file(shortcut_path)
            if success:
                # 从原始列表中移除
                self.shortcuts = [s for s in self.shortcuts if s.path != shortcut_path]

                # 从表格中移除
                self.table.removeRow(row)
                self.update_stats()
                QMessageBox.information(self, "成功", message)

                # 如果没有快捷方式了，禁用删除按钮
                if len(self.shortcuts) == 0:
                    self.set_delete_buttons_enabled(False)
            else:
                QMessageBox.critical(self, "删除失败", message)

    def delete_all_shortcuts(self):
        """删除所有无效快捷方式"""
        # 检查是否正在扫描
        if self.is_scanning:
            QMessageBox.warning(self, "警告", "扫描正在进行中，请等待扫描完成后再删除")
            return

        if not self.shortcuts:
            QMessageBox.warning(self, "警告", "没有可删除的快捷方式")
            return

        count = len(self.shortcuts)

        reply = QMessageBox.question(
            self, "确认删除所有",
            f"确定要删除所有 {count} 个无效快捷方式吗？\n此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            deleted_count = 0
            failed_count = 0
            error_messages = []

            # 创建进度对话框
            progress = QProgressDialog("正在删除快捷方式...", "取消", 0, count, self)
            progress.setWindowTitle("删除进度")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            for i, shortcut in enumerate(self.shortcuts[:]):  # 使用副本遍历
                if progress.wasCanceled():
                    break

                progress.setLabelText(f"正在删除: {shortcut.name}")
                progress.setValue(i)

                QApplication.processEvents()  # 保持UI响应

                success, message = try_delete_file(shortcut.path)

                if success:
                    self.shortcuts.remove(shortcut)
                    deleted_count += 1
                else:
                    failed_count += 1
                    error_messages.append(f"{shortcut.name}: {message}")

            progress.close()

            # 清空表格
            self.table.setRowCount(0)
            self.update_stats()

            # 禁用删除按钮
            self.set_delete_buttons_enabled(False)

            # 显示结果
            result_msg = f"删除完成:\n成功删除: {deleted_count} 个\n删除失败: {failed_count} 个"

            if error_messages:
                result_msg += "\n\n失败详情:\n" + "\n".join(error_messages[:10])
                if len(error_messages) > 10:
                    result_msg += f"\n...还有 {len(error_messages) - 10} 个错误"

            QMessageBox.information(self, "删除结果", result_msg)