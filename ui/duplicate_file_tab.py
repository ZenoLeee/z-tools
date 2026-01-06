import os
from typing import List
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from core.file_scanner import FileInfo, DuplicateScannerThread
from utils.file_utils import try_delete_file


class DeleteFileThread(threading.Thread):
    """删除文件线程"""

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


class DuplicateFileTab(tk.Frame):
    """重复文件扫描标签页"""

    def __init__(self, parent):
        super().__init__(parent)
        self.scanner_thread = None
        self.file_objects: List[FileInfo] = []
        self.duplicate_groups = {}
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
            top_frame, text="📁 浏览",
            command=self.browse_directory,
            bg='#4A90E2', fg='white',
            font=('Microsoft YaHei UI', 9),
            relief='flat', cursor='hand2',
            padx=12, pady=6
        )
        self.browse_btn.pack(side='left', padx=3)

        self.scan_all_btn = tk.Button(
            top_frame, text="🖥 全电脑",
            command=self.scan_all_computers,
            bg='#2ECC71', fg='white',
            font=('Microsoft YaHei UI', 9),
            relief='flat', cursor='hand2',
            padx=12, pady=6
        )
        self.scan_all_btn.pack(side='left', padx=3)

        self.clear_dirs_btn = tk.Button(
            top_frame, text="🗑 清除",
            command=self.clear_directories,
            bg='#E74C3C', fg='white',
            font=('Microsoft YaHei UI', 9),
            relief='flat', cursor='hand2',
            padx=12, pady=6
        )
        self.clear_dirs_btn.pack(side='left', padx=3)

        # 文件类型过滤
        tk.Label(top_frame, text="文件类型:").pack(side='left', padx=(20, 5))
        self.filetype_combo = ttk.Combobox(
            top_frame,
            values=["所有文件", "图片文件", "文档文件", "视频文件", "音频文件", "自定义"],
            state='readonly',
            width=12
        )
        self.filetype_combo.current(0)
        self.filetype_combo.bind('<<ComboboxSelected>>', self.on_filetype_changed)
        self.filetype_combo.pack(side='left', padx=5)

        self.custom_filetype_edit = tk.Entry(top_frame, width=20)
        self.custom_filetype_edit.pack(side='left', padx=5)

        # 中间控制面板
        middle_frame = tk.Frame(main_frame)
        middle_frame.pack(fill='x', pady=(0, 10))

        # 最小文件大小
        tk.Label(middle_frame, text="最小文件大小:").pack(side='left', padx=5)
        self.min_size_spin = tk.Spinbox(middle_frame, from_=0, to=10240, increment=10, width=10)
        self.min_size_spin.delete(0, tk.END)
        self.min_size_spin.insert(0, 100)
        self.min_size_spin.pack(side='left', padx=5)
        tk.Label(middle_frame, text="KB").pack(side='left', padx=0)

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
            button_frame, text="🔍 开始扫描",
            command=self.start_scan,
            bg='#4CAF50', fg='white',
            font=('Microsoft YaHei UI', 9, 'bold'),
            relief='flat', cursor='hand2',
            padx=12, pady=6
        )
        self.scan_btn.pack(side='left', padx=5)

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

        self.current_file_label = tk.Label(progress_frame, text="等待开始扫描...")
        self.current_file_label.pack(anchor='w', pady=(5, 0))

        # 统计信息
        stats_frame = tk.Frame(main_frame)
        stats_frame.pack(fill='x', pady=(0, 10))

        self.total_files_label = tk.Label(stats_frame, text="总文件数: 0")
        self.total_files_label.pack(side='left', padx=5)

        self.duplicate_groups_label = tk.Label(stats_frame, text="重复组数: 0")
        self.duplicate_groups_label.pack(side='left', padx=5)

        self.duplicate_files_label = tk.Label(stats_frame, text="重复文件数: 0")
        self.duplicate_files_label.pack(side='left', padx=5)

        self.reclaimable_label = tk.Label(stats_frame, text="可回收空间: 0 MB")
        self.reclaimable_label.pack(side='left', padx=5)

        # 表格显示
        table_frame = tk.Frame(main_frame)
        table_frame.pack(expand=True, fill='both')

        # 创建 Treeview
        columns = ("keep", "filename", "path", "size", "modified", "md5", "group")
        self.table = ttk.Treeview(table_frame, columns=columns, show='headings', selectmode='extended')

        # 设置列标题
        self.table.heading("keep", text="保留")
        self.table.heading("filename", text="文件名")
        self.table.heading("path", text="路径")
        self.table.heading("size", text="大小")
        self.table.heading("modified", text="修改时间")
        self.table.heading("md5", text="MD5")
        self.table.heading("group", text="重复组")

        # 设置列宽
        self.table.column("keep", width=50, minwidth=40)
        self.table.column("filename", width=200, minwidth=150)
        self.table.column("path", width=300, minwidth=200)
        self.table.column("size", width=80, minwidth=60)
        self.table.column("modified", width=120, minwidth=100)
        self.table.column("md5", width=150, minwidth=100)
        self.table.column("group", width=80, minwidth=60)

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

        self.smart_select_btn = tk.Button(
            bottom_button_frame, text="智能选择",
            command=self.smart_select_duplicates
        )
        self.smart_select_btn.pack(side='left', padx=5)

        self.invert_selection_btn = tk.Button(
            bottom_button_frame, text="反选",
            command=self.invert_selection
        )
        self.invert_selection_btn.pack(side='left', padx=5)

        self.open_btn = tk.Button(
            bottom_button_frame, text="打开所在文件夹",
            command=self.open_file_folder
        )
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
        self.smart_select_btn.config(state=state)
        self.invert_selection_btn.config(state=state)

    def on_filetype_changed(self, event=None):
        """文件类型选择变化"""
        filetype = self.filetype_combo.get()
        if filetype == "自定义":
            self.custom_filetype_edit.config(state='normal')
        else:
            self.custom_filetype_edit.config(state='disabled')

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

    def get_file_types(self):
        """获取选中的文件类型"""
        filetype = self.filetype_combo.get()

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
            text = self.custom_filetype_edit.get().strip()
            if text:
                return [ext.strip() for ext in text.split(",")]

        return ["*"]

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
        self.file_objects = []
        self.duplicate_groups = {}
        self.update_stats()

        # 重置进度条
        self.progress_bar['value'] = 0
        self.progress_label.config(text="正在准备扫描...")
        self.current_file_label.config(text="正在初始化扫描...")

        # 获取参数
        file_types = self.get_file_types()

        # 获取最小文件大小
        min_size_text = self.min_size_spin.get()
        try:
            min_size_kb = int(min_size_text)
        except ValueError:
            min_size_kb = 100

        min_size_bytes = min_size_kb * 1024

        # 排除系统文件
        exclude_system = self.exclude_system_var.get()

        # 创建并启动扫描线程（使用所有选中的目录）
        self.scanner_thread = DuplicateScannerThread(
            directories=self.scan_directories,  # 使用目录列表
            file_types=file_types,
            min_size=min_size_bytes,
            exclude_system=exclude_system
        )

        self.scanner_thread.set_scan_progress_callback(self.update_scan_progress)
        self.scanner_thread.set_file_progress_callback(self.update_file_progress)
        self.scanner_thread.set_duplicate_callback(self.add_duplicate_file)
        self.scanner_thread.set_finished_callback(self.on_scan_finished)
        self.scanner_thread.start()

        self.progress_label.config(text="正在扫描目录...")
        self.current_file_label.config(text="正在初始化扫描...")

    def stop_scan(self):
        """停止扫描"""
        # 先设置标志，阻止后续的文件添加
        self.is_scanning = False

        if self.scanner_thread and self.scanner_thread.is_alive():
            # 停止线程
            self.scanner_thread.stop()

            # 清除回调函数，防止线程继续调用
            self.scanner_thread.set_scan_progress_callback(None)
            self.scanner_thread.set_file_progress_callback(None)
            self.scanner_thread.set_duplicate_callback(None)
            self.scanner_thread.set_finished_callback(None)

            self.progress_label.config(text="扫描已停止")
            self.current_file_label.config(text="扫描被用户停止")

        # 恢复按钮状态
        self.scan_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

        # 如果有结果，启用删除按钮
        if len(self.file_objects) > 0:
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

        self.current_file_label.config(text=text)

    def update_file_progress(self, progress: int, total_files: int, text: str):
        """更新文件处理进度"""
        # 如果已停止，不更新
        if not self.is_scanning:
            return

        adjusted_progress = 50 + int(progress / 2)
        adjusted_progress = min(adjusted_progress, 100)

        self.progress_bar['value'] = adjusted_progress
        self.progress_label.config(text=f"文件处理进度: {progress}%")
        self.current_file_label.config(text=f"{text} (已处理 {total_files} 个文件)")

    def add_duplicate_file(self, file_info, group_id):
        """添加重复文件到表格"""
        # 检查是否已停止扫描，如果停止则不再添加
        if not self.is_scanning:
            return

        # 添加到文件对象列表
        self.file_objects.append(file_info)

        # 添加到重复组字典
        if group_id not in self.duplicate_groups:
            self.duplicate_groups[group_id] = []
        self.duplicate_groups[group_id].append(file_info)

        # 文件大小
        size_mb = file_info.size / (1024 * 1024)

        # MD5（只显示前8位）
        md5_short = file_info.md5_hash[:8] + "..." if len(file_info.md5_hash) > 8 else file_info.md5_hash

        # 插入数据
        item_id = self.table.insert('', 'end', values=(
            "✓" if file_info.keep else "✗",
            file_info.filename,
            file_info.directory,
            f"{size_mb:.2f} MB",
            file_info.modified_time.strftime("%Y-%m-%d %H:%M:%S"),
            md5_short,
            str(file_info.duplicate_group)
        ))

        # 如果不是保留文件，设置红色背景
        if not file_info.keep:
            self.table.item(item_id, tags='duplicate')
            self.table.tag_configure('duplicate', background='#ffc8c8')

        # 更新统计信息
        self.update_stats()

    def on_scan_finished(self, file_objects, total_files, duplicate_groups, duplicate_files):
        """扫描完成"""
        # 保存扫描结果
        self.file_objects = file_objects

        # 构建重复组字典
        self.duplicate_groups = {}
        for file_info in file_objects:
            if file_info.is_duplicate and file_info.duplicate_group > 0:
                if file_info.duplicate_group not in self.duplicate_groups:
                    self.duplicate_groups[file_info.duplicate_group] = []
                self.duplicate_groups[file_info.duplicate_group].append(file_info)

        # 清空表格
        for item in self.table.get_children():
            self.table.delete(item)

        # 将所有文件添加到表格中
        # 注意：此时不要设置 is_scanning = False，否则 add_duplicate_file 会直接返回
        for file_info in file_objects:
            # 临时绕过 is_scanning 检查，直接插入数据
            if file_info.is_duplicate and file_info.duplicate_group > 0:
                # 添加到表格
                size_mb = file_info.size / (1024 * 1024)
                md5_short = file_info.md5_hash[:8] + "..." if len(file_info.md5_hash) > 8 else file_info.md5_hash

                item_id = self.table.insert('', 'end', values=(
                    "✓" if file_info.keep else "✗",
                    file_info.filename,
                    file_info.directory,
                    f"{size_mb:.2f} MB",
                    file_info.modified_time.strftime("%Y-%m-%d %H:%M:%S"),
                    md5_short,
                    str(file_info.duplicate_group)
                ))

                # 如果不是保留文件，设置红色背景
                if not file_info.keep:
                    self.table.item(item_id, tags='duplicate')
                    self.table.tag_configure('duplicate', background='#ffc8c8')

        # 现在可以安全地设置扫描状态为 False
        self.is_scanning = False

        # 更新进度条
        self.progress_bar['value'] = 100
        self.progress_label.config(text=f"扫描完成")
        self.current_file_label.config(text=f"找到 {duplicate_files} 个重复文件，{duplicate_groups} 个重复组")

        # 恢复按钮状态
        self.scan_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

        # 如果有结果，启用删除按钮
        if duplicate_files > 0:
            self.set_delete_buttons_enabled(True)

        # 计算可回收空间
        total_reclaimable = 0
        for file_info in file_objects:
            if file_info.is_duplicate and not file_info.keep:
                total_reclaimable += file_info.size

        self.reclaimable_label.config(text=f"可回收空间: {total_reclaimable / (1024 * 1024):.2f} MB")

    def update_stats(self):
        """更新统计信息"""
        total_files = len(self.file_objects)
        duplicate_files = sum(1 for f in self.file_objects if f.is_duplicate and not f.keep)
        duplicate_groups = len(set(f.duplicate_group for f in self.file_objects if f.is_duplicate))

        self.total_files_label.config(text=f"总文件数: {total_files}")
        self.duplicate_files_label.config(text=f"重复文件数: {duplicate_files}")
        self.duplicate_groups_label.config(text=f"重复组数: {duplicate_groups}")

    def smart_select_duplicates(self):
        """智能选择 - 选择所有重复文件中较旧的文件（保留最新的）"""
        # 清空当前选择
        self.table.selection_remove(self.table.selection())

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
                        for item in self.table.get_children():
                            values = self.table.item(item)['values']
                            if len(values) >= 3 and values[2] == file_info.path:
                                self.table.selection_add(item)
                                selected_count += 1
                                break

        if selected_count > 0:
            self.current_file_label.config(text=f"智能选择了 {selected_count} 个较旧的文件")
        else:
            self.current_file_label.config(text="没有找到需要选择的重复文件")

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

    def open_file_folder(self):
        """打开文件所在文件夹"""
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个文件")
            return

        item = selected[0]
        values = self.table.item(item)['values']
        if len(values) >= 3:
            folder_path = values[2]
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

        # 确认删除
        reply = messagebox.askyesno(
            "确认删除",
            f"确定要删除选中的 {len(selected)} 个文件吗？"
        )

        if reply:
            # 准备要删除的文件列表
            files_to_delete = []
            for item in selected:
                values = self.table.item(item)['values']
                if len(values) >= 3:
                    file_path = values[2]  # 获取完整路径（在路径列中）
                    files_to_delete.append((item, file_path))

            # 禁用删除按钮，显示正在删除
            self.set_delete_buttons_enabled(False)
            self.current_file_label.config(text=f"正在删除 {len(files_to_delete)} 个文件...")

            # 创建并启动删除线程
            self.delete_thread = DeleteFileThread(files_to_delete)
            self.delete_thread.set_progress_callback(self.on_delete_progress)
            self.delete_thread.set_finished_callback(self.on_delete_finished)
            self.delete_thread.start()

    def on_delete_progress(self, item_id, file_path, success, message):
        """删除进度回调（在主线程中调用）"""
        if success:
            # 从表格中移除
            self.table.delete(item_id)

            # 从文件对象列表中移除
            self.file_objects = [f for f in self.file_objects if f.path != file_path]

            # 更新统计信息
            self.update_stats()

    def on_delete_finished(self, deleted_count, failed_count, error_messages):
        """删除完成回调（在主线程中调用）"""
        # 如果没有文件了，禁用删除按钮
        if len(self.file_objects) == 0:
            self.set_delete_buttons_enabled(False)
        else:
            # 如果还有文件，重新启用删除按钮
            self.set_delete_buttons_enabled(True)

        # 更新状态标签
        self.current_file_label.config(text=f"删除完成: 成功 {deleted_count} 个, 失败 {failed_count} 个")

        # 显示结果
        result_msg = f"删除完成:\n成功删除: {deleted_count} 个文件\n删除失败: {failed_count} 个文件"

        if error_messages:
            result_msg += "\n\n失败详情:\n" + "\n".join(error_messages[:10])
            if len(error_messages) > 10:
                result_msg += f"\n...还有 {len(error_messages) - 10} 个错误"

        messagebox.showinfo("删除结果", result_msg)
