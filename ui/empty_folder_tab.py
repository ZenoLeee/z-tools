import os
from typing import List
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.file_scanner import FolderInfo, EmptyFolderScannerThread
from utils.file_utils import try_delete_folder


class DeleteFolderThread(threading.Thread):
    """删除文件夹线程 - 使用多线程并发删除"""

    def __init__(self, folders_to_delete: List[tuple], max_workers: int = 8):
        """
        folders_to_delete: List[(item_id, folder_path), ...]
        max_workers: 最大并发线程数，默认8
        """
        super().__init__()
        self.folders_to_delete = folders_to_delete
        self.max_workers = max_workers
        self.running = True
        self.deleted_count = 0
        self.failed_count = 0
        self.error_messages = []
        self.lock = threading.Lock()  # 线程锁，保护共享变量

        # 回调函数
        self.progress_callback = None
        self.finished_callback = None

    def set_progress_callback(self, callback):
        self.progress_callback = callback

    def set_finished_callback(self, callback):
        self.finished_callback = callback

    def _delete_single_folder(self, item_id, folder_path):
        """删除单个文件夹（在线程池中执行）"""
        if not self.running:
            return None

        success, message = try_delete_folder(folder_path)

        with self.lock:
            if success:
                self.deleted_count += 1
            else:
                self.failed_count += 1
                self.error_messages.append(f"{os.path.basename(folder_path)}: {message}")

        return (item_id, folder_path, success, message)

    def run(self):
        """执行删除任务 - 使用线程池并发删除"""
        try:
            total = len(self.folders_to_delete)
            completed = 0

            # 使用线程池并发删除
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有删除任务
                future_to_folder = {
                    executor.submit(self._delete_single_folder, item_id, folder_path): (item_id, folder_path)
                    for item_id, folder_path in self.folders_to_delete
                }

                # 处理完成的任务
                for future in as_completed(future_to_folder):
                    if not self.running:
                        # 取消未完成的任务
                        for f in future_to_folder:
                            f.cancel()
                        break

                    result = future.result()
                    if result:
                        item_id, folder_path, success, message = result
                        completed += 1

                        # 通知主线程更新UI
                        if self.progress_callback:
                            self.progress_callback(item_id, folder_path, success, message)

            # 完成
            if self.finished_callback:
                self.finished_callback(self.deleted_count, self.failed_count, self.error_messages)

        except Exception as e:
            print(f"删除文件夹出错: {e}")
            import traceback
            traceback.print_exc()

            # 即使出错也要调用完成回调
            if self.finished_callback:
                self.finished_callback(self.deleted_count, self.failed_count, self.error_messages)

    def stop(self):
        """停止删除"""
        self.running = False


class EmptyFolderTab(tk.Frame):
    """空文件夹扫描标签页"""

    def __init__(self, parent):
        super().__init__(parent)
        self.scanner_thread = None
        self.folder_objects: List[FolderInfo] = []
        self.is_scanning = False
        self.scan_directories = []
        self.init_ui()

    def init_ui(self):
        # 主容器
        main_frame = tk.Frame(self, bg='#F8F9FA')
        main_frame.pack(expand=True, fill='both', padx=10, pady=10)

        # 顶部控制面板
        top_frame = tk.Frame(main_frame, bg='#F8F9FA')
        top_frame.pack(fill='x', pady=(0, 10))

        # 目录选择 - 使用只读Entry和浏览按钮
        tk.Label(top_frame, text="扫描目录:", bg='#F8F9FA', font=('Microsoft YaHei UI', 10)).pack(side='left', padx=5)
        self.dir_edit = tk.Entry(top_frame, width=50, state='readonly', font=('Microsoft YaHei UI', 9))
        self.dir_edit.pack(side='left', padx=5)

        self.browse_btn = tk.Button(
            top_frame, text="📁 浏览...",
            command=self.browse_directory,
            bg='#4A90E2', fg='white',
            font=('Microsoft YaHei UI', 9),
            relief='flat', cursor='hand2',
            borderwidth=0, pady=5, padx=15
        )
        self.browse_btn.pack(side='left', padx=5)

        self.scan_all_btn = tk.Button(
            top_frame, text="🖥️ 全电脑扫描",
            command=self.scan_all_computers,
            bg='#2ECC71', fg='white',
            font=('Microsoft YaHei UI', 9),
            relief='flat', cursor='hand2',
            borderwidth=0, pady=5, padx=15
        )
        self.scan_all_btn.pack(side='left', padx=5)

        self.clear_dirs_btn = tk.Button(
            top_frame, text="🗑️ 清除",
            command=self.clear_directories,
            bg='#E74C3C', fg='white',
            font=('Microsoft YaHei UI', 9),
            relief='flat', cursor='hand2',
            borderwidth=0, pady=5, padx=15
        )
        self.clear_dirs_btn.pack(side='left', padx=5)

        # 中间控制面板 - 选项
        middle_frame = tk.Frame(main_frame, bg='#F8F9FA')
        middle_frame.pack(fill='x', pady=(0, 10))

        # 排除系统目录
        self.exclude_system_var = tk.BooleanVar(value=True)
        self.exclude_system_check = tk.Checkbutton(
            middle_frame, text="排除系统目录", bg='#F8F9FA',
            variable=self.exclude_system_var
        )
        self.exclude_system_check.pack(side='left', padx=5)

        # 包含空的子目录
        self.include_empty_subdirs_var = tk.BooleanVar(value=True)
        self.include_empty_subdirs_check = tk.Checkbutton(
            middle_frame, text="包含空的子目录", bg='#F8F9FA',
            variable=self.include_empty_subdirs_var
        )
        self.include_empty_subdirs_check.pack(side='left', padx=5)

        # 扫描按钮区域
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(0, 10))

        self.scan_btn = tk.Button(
            button_frame, text="🔍 开始扫描",
            command=self.start_scan,
            bg='#2196F3', fg='white',
            font=('Microsoft YaHei UI', 9, 'bold'),
            relief='flat', cursor='hand2',
            padx=12, pady=6
        )
        self.scan_btn.pack(side='left', padx=3)

        self.stop_btn = tk.Button(
            button_frame, text="⏹ 停止",
            command=self.stop_scan,
            state='disabled',
            bg='#f44336', fg='white',
            font=('Microsoft YaHei UI', 9),
            relief='flat', cursor='hand2',
            padx=12, pady=6
        )
        self.stop_btn.pack(side='left', padx=3)

        # 进度条区域
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill='x', pady=(0, 10))

        self.progress_label = tk.Label(progress_frame, text="就绪")
        self.progress_label.pack(anchor='w')

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill='x', pady=(5, 0))

        self.current_folder_label = tk.Label(progress_frame, text="等待开始扫描...")
        self.current_folder_label.pack(anchor='w', pady=(5, 0))

        # 统计信息
        stats_frame = tk.Frame(main_frame)
        stats_frame.pack(fill='x', pady=(0, 10))

        self.total_folders_label = tk.Label(stats_frame, text="空文件夹数: 0")
        self.total_folders_label.pack(side='left', padx=5)

        # 表格显示
        table_frame = tk.Frame(main_frame)
        table_frame.pack(expand=True, fill='both')

        # 创建 Treeview
        columns = ("select", "foldername", "parent", "path", "modified", "files", "subdirs")
        self.table = ttk.Treeview(table_frame, columns=columns, show='headings', selectmode='extended')

        # 设置列标题
        self.table.heading("select", text="选择")
        self.table.heading("foldername", text="文件夹名称")
        self.table.heading("parent", text="父目录")
        self.table.heading("path", text="完整路径")
        self.table.heading("modified", text="修改时间")
        self.table.heading("files", text="文件数")
        self.table.heading("subdirs", text="子文件夹数")

        # 设置列宽
        self.table.column("select", width=50, minwidth=40)
        self.table.column("foldername", width=200, minwidth=150)
        self.table.column("parent", width=250, minwidth=200)
        self.table.column("path", width=350, minwidth=250)
        self.table.column("modified", width=150, minwidth=120)
        self.table.column("files", width=80, minwidth=60)
        self.table.column("subdirs", width=100, minwidth=80)

        # 添加滚动条
        table_scrollbar_y = tk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        table_scrollbar_x = tk.Scrollbar(table_frame, orient="horizontal", command=self.table.xview)

        self.table.configure(yscrollcommand=table_scrollbar_y.set, xscrollcommand=table_scrollbar_x.set)

        # 打包表格和滚动条
        self.table.grid(row=0, column=0, sticky='nsew')
        table_scrollbar_y.grid(row=0, column=1, sticky='ns')
        table_scrollbar_x.grid(row=1, column=0, sticky='ew')

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # 底部操作按钮
        bottom_button_frame = tk.Frame(main_frame)
        bottom_button_frame.pack(fill='x', pady=(10, 0))

        self.select_all_btn = tk.Button(
            bottom_button_frame, text="全选",
            command=self.select_all
        )
        self.select_all_btn.pack(side='left', padx=5)

        self.invert_selection_btn = tk.Button(
            bottom_button_frame, text="反选",
            command=self.invert_selection
        )
        self.invert_selection_btn.pack(side='left', padx=5)

        self.open_btn = tk.Button(
            bottom_button_frame, text="打开所在文件夹",
            command=self.open_folder_location
        )
        self.open_btn.pack(side='left', padx=5)

        self.delete_btn = tk.Button(
            bottom_button_frame, text="删除选中的文件夹",
            command=self.delete_selected_folders,
            bg='#ff6b6b', fg='white'
        )
        self.delete_btn.pack(side='left', padx=5)

        self.set_delete_buttons_enabled(False)

    def set_delete_buttons_enabled(self, enabled: bool):
        """设置删除按钮的启用状态"""
        state = 'normal' if enabled else 'disabled'
        self.delete_btn.config(state=state)
        self.select_all_btn.config(state=state)
        self.invert_selection_btn.config(state=state)

    def browse_directory(self):
        """浏览目录"""
        directory = filedialog.askdirectory(title="选择扫描目录")
        if directory:
            # 添加到扫描目录列表（避免重复）
            if directory not in self.scan_directories:
                self.scan_directories.append(directory)
            self.update_directory_display()

    def scan_all_computers(self):
        """全电脑扫描 - 扫描所有可用磁盘"""
        import string
        drives = []

        # 检测所有可用的磁盘
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                try:
                    # 测试磁盘是否可访问
                    os.listdir(drive)
                    drives.append(drive)
                except (PermissionError, OSError):
                    # 磁盘存在但无法访问，跳过
                    pass

        if drives:
            # 添加所有磁盘到扫描列表
            for drive in drives:
                if drive not in self.scan_directories:
                    self.scan_directories.append(drive)
            self.update_directory_display()

            drive_names = ", ".join(drives)
            messagebox.showinfo("全电脑扫描", f"已添加以下磁盘进行扫描:\n{drive_names}")
        else:
            messagebox.showwarning("警告", "未找到可用的磁盘")

    def clear_directories(self):
        """清除所有选中的目录"""
        self.scan_directories = []
        self.update_directory_display()

    def update_directory_display(self):
        """更新目录显示"""
        # 只读Entry需要先设置为normal状态才能修改
        self.dir_edit.config(state='normal')
        if self.scan_directories:
            # 显示所有目录，用逗号分隔
            display_text = " | ".join(self.scan_directories)
            # 如果太长，截断显示
            if len(display_text) > 60:
                display_text = display_text[:57] + "..."
            self.dir_edit.delete(0, tk.END)
            self.dir_edit.insert(0, display_text)
        else:
            self.dir_edit.delete(0, tk.END)
            self.dir_edit.insert(0, "未选择目录")
        self.dir_edit.config(state='readonly')

    def start_scan(self):
        """开始扫描"""
        # 检查是否选择了目录
        if not self.scan_directories:
            messagebox.showwarning("警告", "请先选择要扫描的目录\n\n可以点击:\n- '浏览' 添加单个目录\n- '全电脑扫描' 添加所有磁盘")
            return

        # 设置扫描状态
        self.is_scanning = True

        # 禁用开始扫描按钮，启用停止按钮
        self.scan_btn.config(state='disabled')
        self.stop_btn.config(state='normal')

        # 禁用删除按钮
        self.set_delete_buttons_enabled(False)

        # 清空之前的扫描结果
        for item in self.table.get_children():
            self.table.delete(item)
        self.folder_objects = []
        self.update_stats()

        # 重置进度条
        self.progress_bar['value'] = 0
        self.progress_label.config(text="正在准备扫描...")
        self.current_folder_label.config(text="正在初始化扫描...")

        # 获取参数
        exclude_system = self.exclude_system_var.get()
        include_empty_subdirs = self.include_empty_subdirs_var.get()

        # 创建并启动扫描线程
        self.scanner_thread = EmptyFolderScannerThread(
            directories=self.scan_directories,
            exclude_system=exclude_system,
            include_empty_subdirs=include_empty_subdirs
        )

        self.scanner_thread.set_progress_callback(self.update_scan_progress)
        self.scanner_thread.set_found_callback(self.add_empty_folder)
        self.scanner_thread.set_finished_callback(self.on_scan_finished)
        self.scanner_thread.start()

        self.progress_label.config(text="正在扫描目录...")
        self.current_folder_label.config(text="正在初始化扫描...")

    def stop_scan(self):
        """停止扫描"""
        # 先设置标志，阻止后续的文件夹添加
        self.is_scanning = False

        if self.scanner_thread and self.scanner_thread.is_alive():
            # 停止线程
            self.scanner_thread.stop()

            # 清除回调函数，防止线程继续调用
            self.scanner_thread.set_progress_callback(None)
            self.scanner_thread.set_found_callback(None)
            self.scanner_thread.set_finished_callback(None)

            self.progress_label.config(text="扫描已停止")
            self.current_folder_label.config(text="扫描被用户停止")

        # 恢复按钮状态
        self.scan_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

        # 如果有结果，启用删除按钮
        if len(self.folder_objects) > 0:
            self.set_delete_buttons_enabled(True)

    def update_scan_progress(self, current: int, total: int, text: str):
        """更新扫描进度"""
        # 如果已停止，不更新
        if not self.is_scanning:
            return

        progress = min(current, 100)
        self.progress_bar['value'] = progress

        if "扫描完成" in text or "完成" in text:
            self.progress_label.config(text=f"扫描完成")
        else:
            self.progress_label.config(text=f"扫描进度: {progress}%")

        self.current_folder_label.config(text=text)

    def add_empty_folder(self, folder_info: FolderInfo):
        """添加空文件夹到表格"""
        # 检查是否已停止扫描，如果停止则不再添加
        if not self.is_scanning:
            return

        # 添加到文件夹对象列表
        self.folder_objects.append(folder_info)

        # 插入数据
        item_id = self.table.insert('', 'end', values=(
            "☐",
            folder_info.folder_name,
            folder_info.parent_name if folder_info.parent_name else "根目录",
            folder_info.path,
            folder_info.modified_time.strftime("%Y-%m-%d %H:%M:%S"),
            str(folder_info.file_count),
            str(folder_info.folder_count)
        ))

        # 更新统计信息
        self.update_stats()

    def on_scan_finished(self, folder_objects, total_count):
        """扫描完成"""
        # 设置扫描状态
        self.is_scanning = False

        # 保存扫描结果
        self.folder_objects = folder_objects

        # 更新进度条
        self.progress_bar['value'] = 100
        self.progress_label.config(text=f"扫描完成")
        self.current_folder_label.config(text=f"找到 {total_count} 个空文件夹")

        # 恢复按钮状态
        self.scan_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

        # 如果有结果，启用删除按钮
        if total_count > 0:
            self.set_delete_buttons_enabled(True)

    def update_stats(self):
        """更新统计信息"""
        total_folders = len(self.folder_objects)
        self.total_folders_label.config(text=f"空文件夹数: {total_folders}")

    def select_all(self):
        """全选"""
        all_items = self.table.get_children()
        for item in all_items:
            self.table.selection_add(item)

    def invert_selection(self):
        """反选"""
        all_items = self.table.get_children()
        selected = set(self.table.selection())

        # 清除当前选择
        self.table.selection_remove(selected)

        # 选择之前未选中的项目
        for item in all_items:
            if item not in selected:
                self.table.selection_add(item)

    def open_folder_location(self):
        """打开文件夹所在位置"""
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个文件夹")
            return

        item = selected[0]
        values = self.table.item(item)['values']
        if len(values) >= 4:
            folder_path = values[3]  # 获取完整路径
            try:
                # 打开父目录
                parent_path = os.path.dirname(folder_path)
                if parent_path and os.path.exists(parent_path):
                    os.startfile(parent_path)
                else:
                    messagebox.showerror("错误", "无法找到父目录")
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件夹: {e}")

    def delete_selected_folders(self):
        """删除选中的文件夹"""
        # 检查是否正在扫描
        if self.is_scanning:
            messagebox.showwarning("警告", "扫描正在进行中，请等待扫描完成后再删除")
            return

        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的文件夹")
            return

        # 确认删除
        reply = messagebox.askyesno(
            "确认删除",
            f"确定要删除选中的 {len(selected)} 个空文件夹吗？\n\n注意：只能删除空的文件夹。"
        )

        if reply:
            # 准备要删除的文件夹列表
            folders_to_delete = []
            for item in selected:
                values = self.table.item(item)['values']
                if len(values) >= 4:
                    folder_path = values[3]  # 获取完整路径
                    folders_to_delete.append((item, folder_path))

            # 禁用删除按钮，显示正在删除
            self.set_delete_buttons_enabled(False)
            self.current_folder_label.config(text=f"正在删除 {len(folders_to_delete)} 个文件夹...")

            # 创建并启动删除线程
            self.delete_thread = DeleteFolderThread(folders_to_delete)
            self.delete_thread.set_progress_callback(self.on_delete_progress)
            self.delete_thread.set_finished_callback(self.on_delete_finished)
            self.delete_thread.start()

    def on_delete_progress(self, item_id, folder_path, success, message):
        """删除进度回调（在主线程中调用）"""
        # 计算删除进度
        total = len(self.folder_objects) + self.delete_thread.deleted_count + self.delete_thread.failed_count
        completed = self.delete_thread.deleted_count + self.delete_thread.failed_count
        if total > 0:
            progress = int((completed / total) * 100)
            self.current_folder_label.config(
                text=f"正在删除... {completed}/{total} ({progress}%) - 成功: {self.delete_thread.deleted_count}, 失败: {self.delete_thread.failed_count}"
            )

        if success:
            # 从表格中移除
            self.table.delete(item_id)

            # 从文件夹对象列表中移除
            self.folder_objects = [f for f in self.folder_objects if f.path != folder_path]

            # 更新统计信息
            self.update_stats()

    def on_delete_finished(self, deleted_count, failed_count, error_messages):
        """删除完成回调（在主线程中调用）"""
        # 如果没有文件夹了，禁用删除按钮
        if len(self.folder_objects) == 0:
            self.set_delete_buttons_enabled(False)
        else:
            # 如果还有文件夹，重新启用删除按钮
            self.set_delete_buttons_enabled(True)

        # 更新状态标签
        self.current_folder_label.config(text=f"删除完成: 成功 {deleted_count} 个, 失败 {failed_count} 个")

        # 显示结果
        result_msg = f"删除完成:\n成功删除: {deleted_count} 个文件夹\n删除失败: {failed_count} 个文件夹"

        if error_messages:
            result_msg += "\n\n失败详情:\n" + "\n".join(error_messages[:10])
            if len(error_messages) > 10:
                result_msg += f"\n...还有 {len(error_messages) - 10} 个错误"

        messagebox.showinfo("删除结果", result_msg)
