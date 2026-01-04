import os
from typing import List
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from core.file_scanner import FileInfo, LargeFileScannerThread
from utils.file_utils import try_delete_file


class DeleteLargeFileThread(threading.Thread):
    """删除大文件线程"""

    def __init__(self, files_to_delete: List[tuple]):
        """
        files_to_delete: List[(item_id, file_path), ...]
        """
        super().__init__()
        self.files_to_delete = files_to_delete
        self.running = True
        self.deleted_count = 0
        self.failed_count = 0
        self.error_messages = []

        # 回调函数
        self.progress_callback = None
        self.finished_callback = None

    def set_progress_callback(self, callback):
        self.progress_callback = callback

    def set_finished_callback(self, callback):
        self.finished_callback = callback

    def run(self):
        """执行删除任务"""
        try:
            for item_id, file_path in self.files_to_delete:
                if not self.running:
                    break

                success, message = try_delete_file(file_path)

                if success:
                    self.deleted_count += 1
                    # 通知主线程更新UI
                    if self.progress_callback:
                        self.progress_callback(item_id, file_path, True, message)
                else:
                    self.failed_count += 1
                    self.error_messages.append(f"{os.path.basename(file_path)}: {message}")
                    if self.progress_callback:
                        self.progress_callback(item_id, file_path, False, message)

            # 完成
            if self.finished_callback:
                self.finished_callback(self.deleted_count, self.failed_count, self.error_messages)

        except Exception as e:
            print(f"删除文件出错: {e}")
            import traceback
            traceback.print_exc()

    def stop(self):
        """停止删除"""
        self.running = False


class LargeFileTab(tk.Frame):
    """大文件扫描标签页"""

    def __init__(self, parent):
        super().__init__(parent)
        self.scanner_thread = None
        self.large_files: List[FileInfo] = []
        self.is_scanning = False
        self.scan_directories = []  # 存储所有要扫描的目录
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
            bg='#9B59B6', fg='white',
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

        # 中间控制面板
        middle_frame = tk.Frame(main_frame)
        middle_frame.pack(fill='x', pady=(0, 10))

        # 最小文件大小
        tk.Label(middle_frame, text="最小文件大小:").pack(side='left', padx=5)
        self.min_size_spin = tk.Spinbox(middle_frame, from_=10, to=10240, increment=10, width=10)
        self.min_size_spin.delete(0, tk.END)
        self.min_size_spin.insert(0, 100)
        self.min_size_spin.pack(side='left', padx=5)
        tk.Label(middle_frame, text="MB").pack(side='left', padx=0)

        # 最大结果数
        tk.Label(middle_frame, text="最大结果数:").pack(side='left', padx=(20, 5))
        self.max_results_spin = tk.Spinbox(middle_frame, from_=10, to=10000, increment=100, width=10)
        self.max_results_spin.delete(0, tk.END)
        self.max_results_spin.insert(0, 1000)
        self.max_results_spin.pack(side='left', padx=5)

        # 排除系统文件
        self.exclude_system_var = tk.BooleanVar(value=True)
        self.exclude_system_check = tk.Checkbutton(
            middle_frame, text="排除系统文件",
            variable=self.exclude_system_var
        )
        self.exclude_system_check.pack(side='left', padx=(20, 5))

        # 扫描按钮区域
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(0, 10))

        self.scan_btn = tk.Button(
            button_frame, text="开始扫描大文件",
            command=self.start_scan,
            bg='#9b59b6', fg='white',
            font=('Arial', 12, 'bold'),
            height=2
        )
        self.scan_btn.pack(side='left', padx=5)

        self.stop_btn = tk.Button(
            button_frame, text="停止扫描",
            command=self.stop_scan,
            state='disabled'
        )
        self.stop_btn.pack(side='left', padx=5)

        # 进度条区域
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill='x', pady=(0, 10))

        self.progress_label = tk.Label(progress_frame, text="就绪")
        self.progress_label.pack(anchor='w')

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill='x', pady=(5, 0))

        self.current_dir_label = tk.Label(progress_frame, text="等待开始扫描...")
        self.current_dir_label.pack(anchor='w', pady=(5, 0))

        # 统计信息
        stats_frame = tk.Frame(main_frame)
        stats_frame.pack(fill='x', pady=(0, 10))

        self.total_files_label = tk.Label(stats_frame, text="找到大文件: 0 个")
        self.total_files_label.pack(side='left', padx=5)

        self.total_size_label = tk.Label(stats_frame, text="总大小: 0 MB")
        self.total_size_label.pack(side='left', padx=5)

        # 表格显示
        table_frame = tk.Frame(main_frame)
        table_frame.pack(expand=True, fill='both')

        # 创建 Treeview
        columns = ("filename", "path", "size", "modified", "type")
        self.table = ttk.Treeview(table_frame, columns=columns, show='headings', selectmode='extended')

        # 设置列标题
        self.table.heading("filename", text="文件名")
        self.table.heading("path", text="路径")
        self.table.heading("size", text="大小")
        self.table.heading("modified", text="修改时间")
        self.table.heading("type", text="类型")

        # 设置列宽
        self.table.column("filename", width=200, minwidth=150)
        self.table.column("path", width=300, minwidth=200)
        self.table.column("size", width=100, minwidth=80)
        self.table.column("modified", width=120, minwidth=100)
        self.table.column("type", width=80, minwidth=60)

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

        self.open_btn = tk.Button(bottom_button_frame, text="打开所在文件夹", command=self.open_file_folder)
        self.open_btn.pack(side='left', padx=5)

        self.delete_btn = tk.Button(
            bottom_button_frame, text="删除选中的文件",
            command=self.delete_selected_files,
            bg='#ff6b6b', fg='white'
        )
        self.delete_btn.pack(side='left', padx=5)

        self.set_delete_buttons_enabled(False)

    def set_delete_buttons_enabled(self, enabled: bool):
        """设置删除按钮的启用状态"""
        state = 'normal' if enabled else 'disabled'
        self.delete_btn.config(state=state)

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

        # 重置进度条和标签
        self.progress_bar['value'] = 0
        self.progress_label.config(text="正在准备扫描...")
        self.current_dir_label.config(text="正在收集文件信息...")

        # 禁用删除按钮
        self.set_delete_buttons_enabled(False)

        # 清空之前的扫描结果
        for item in self.table.get_children():
            self.table.delete(item)
        self.large_files = []
        self.update_stats()

        # 获取参数
        try:
            min_size_mb = int(self.min_size_spin.get())
            max_results = int(self.max_results_spin.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            return

        exclude_system = self.exclude_system_var.get()

        # 创建并启动扫描线程（使用所有选中的目录）
        self.scanner_thread = LargeFileScannerThread(
            self.scan_directories,  # 使用目录列表
            min_size_mb,
            max_results,
            exclude_system
        )

        self.scanner_thread.set_progress_callback(self.update_scan_progress)
        self.scanner_thread.set_found_callback(self.add_large_file)
        self.scanner_thread.set_finished_callback(self.on_scan_finished)
        self.scanner_thread.start()

        self.progress_label.config(text="正在扫描大文件...")
        self.current_dir_label.config(text="正在扫描文件...")

    def stop_scan(self):
        """停止扫描"""
        # 先设置标志，阻止后续的文件添加
        self.is_scanning = False

        if self.scanner_thread:
            try:
                # 停止线程
                self.scanner_thread.stop()

                # 清除回调函数，防止线程继续调用
                self.scanner_thread.set_progress_callback(None)
                self.scanner_thread.set_found_callback(None)
                self.scanner_thread.set_finished_callback(None)

                if self.scanner_thread.is_alive():
                    self.scanner_thread.join(timeout=1)
            except Exception as e:
                print(f"停止线程出错: {e}")

        # 恢复按钮状态
        self.scan_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.progress_label.config(text="扫描已停止")
        self.current_dir_label.config(text="扫描被用户停止")

        # 如果有结果，启用删除按钮
        if len(self.large_files) > 0:
            self.set_delete_buttons_enabled(True)

    def update_scan_progress(self, progress: int, total: int, text: str):
        """更新扫描进度"""
        # 如果已停止，不更新
        if not self.is_scanning:
            return

        try:
            self.progress_bar['value'] = progress
            self.progress_label.config(text=f"扫描进度: {progress}%")
            self.current_dir_label.config(text=text)
            self.update()
        except Exception as e:
            print(f"更新进度条出错: {e}")

    def add_large_file(self, file_info):
        """添加大文件到表格"""
        # 检查是否已停止扫描，如果停止则不再添加
        if not self.is_scanning:
            return

        # 添加到文件列表
        self.large_files.append(file_info)

        # 获取文件类型
        _, ext = os.path.splitext(file_info.filename)
        file_type = ext.upper() if ext else "未知"

        # 文件大小
        size_mb = file_info.size / (1024 * 1024)

        # 插入数据
        self.table.insert('', 'end', values=(
            file_info.filename,
            file_info.directory,
            f"{size_mb:.2f} MB",
            file_info.modified_time.strftime("%Y-%m-%d %H:%M:%S"),
            file_type
        ))

        # 更新统计信息
        self.update_stats()

    def on_scan_finished(self, file_objects, total_files, total_size_mb):
        """扫描完成"""
        # 设置扫描状态
        self.is_scanning = False

        # 更新进度条
        self.progress_bar['value'] = 100
        self.progress_label.config(text=f"扫描完成，找到 {total_files} 个大文件")
        self.current_dir_label.config(text=f"总大小: {total_size_mb} MB")

        # 恢复按钮状态
        self.scan_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

        # 如果有结果，启用删除按钮
        if total_files > 0:
            self.set_delete_buttons_enabled(True)

    def update_stats(self):
        """更新统计信息"""
        total_files = len(self.large_files)

        # 计算总大小
        total_size = sum(f.size for f in self.large_files)
        total_size_mb = total_size / (1024 * 1024)

        self.total_files_label.config(text=f"找到大文件: {total_files} 个")
        self.total_size_label.config(text=f"总大小: {total_size_mb:.2f} MB")

    def open_file_folder(self):
        """打开文件所在文件夹"""
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个文件")
            return

        item = selected[0]
        values = self.table.item(item)['values']
        folder_path = values[1]
        try:
            os.startfile(folder_path)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹: {e}")

    def delete_selected_files(self):
        """删除选中的文件"""
        # 检查是否正在扫描
        if self.is_scanning:
            messagebox.showwarning("警告", "扫描正在进行中，请等待扫描完成后再删除")
            return

        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的文件")
            return

        # 获取要删除的文件信息
        files_to_delete = []
        total_size_mb = 0

        for item in selected:
            values = self.table.item(item)['values']
            file_path = values[1]
            size_text = values[2].replace(" MB", "")
            try:
                total_size_mb += float(size_text)
            except:
                pass
            files_to_delete.append((item, file_path))

        # 确认删除
        reply = messagebox.askyesno(
            "确认删除",
            f"确定要删除选中的 {len(files_to_delete)} 个文件吗？\n总大小: {total_size_mb:.2f} MB"
        )

        if reply:
            # 保存总大小以便在完成回调中使用
            self._total_size_to_delete = total_size_mb

            # 禁用删除按钮，显示正在删除
            self.set_delete_buttons_enabled(False)
            self.current_file_label.config(text=f"正在删除 {len(files_to_delete)} 个文件...")

            # 创建并启动删除线程
            self.delete_thread = DeleteLargeFileThread(files_to_delete)
            self.delete_thread.set_progress_callback(self.on_delete_progress)
            self.delete_thread.set_finished_callback(self.on_delete_finished)
            self.delete_thread.start()

    def on_delete_progress(self, item_id, file_path, success, message):
        """删除进度回调（在主线程中调用）"""
        if success:
            # 从表格中移除
            self.table.delete(item_id)

            # 从文件列表中移除
            self.large_files = [f for f in self.large_files if f.path != file_path]

            # 更新统计信息
            self.update_stats()

    def on_delete_finished(self, deleted_count, failed_count, error_messages):
        """删除完成回调（在主线程中调用）"""
        # 获取之前保存的总大小
        total_size_mb = getattr(self, '_total_size_to_delete', 0)

        # 如果没有文件了，禁用删除按钮
        if len(self.large_files) == 0:
            self.set_delete_buttons_enabled(False)
        else:
            # 如果还有文件，重新启用删除按钮
            self.set_delete_buttons_enabled(True)

        # 更新状态标签
        self.current_file_label.config(text=f"删除完成: 成功 {deleted_count} 个, 失败 {failed_count} 个")

        # 显示结果
        result_msg = f"删除完成:\n成功删除: {deleted_count} 个文件\n释放空间: {total_size_mb:.2f} MB\n删除失败: {failed_count} 个文件"

        if error_messages:
            result_msg += "\n\n失败详情:\n" + "\n".join(error_messages[:10])
            if len(error_messages) > 10:
                result_msg += f"\n...还有 {len(error_messages) - 10} 个错误"

        messagebox.showinfo("删除结果", result_msg)
