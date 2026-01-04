"""
注册表清理标签页
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import List
from core.registry_cleaner import (
    RegistryIssue, RegistryScanner, RegistryScannerThread,
    RegistryBackup, RegistryCleaner
)


class RegistryTab(tk.Frame):
    """注册表清理标签页"""

    def __init__(self, parent):
        super().__init__(parent)
        self.scanner = RegistryScanner()
        self.scanner_thread = None
        self.issues: List[RegistryIssue] = []
        self.is_scanning = False
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        # 主容器
        main_frame = tk.Frame(self)
        main_frame.pack(expand=True, fill='both', padx=10, pady=10)

        # 顶部控制面板
        top_frame = tk.Frame(main_frame, relief=tk.RAISED, borderwidth=1)
        top_frame.pack(fill='x', pady=(0, 10))

        # 标题和说明
        title_frame = tk.Frame(top_frame, bg='#F0F8FF', pady=10)
        title_frame.pack(fill='x')

        tk.Label(
            title_frame,
            text="🔍 注册表清理工具",
            font=('Microsoft YaHei UI', 14, 'bold'),
            bg='#F0F8FF',
            fg='#2C3E50'
        ).pack()

        tk.Label(
            title_frame,
            text="扫描并清理无效的注册表项 | 所有操作都会自动备份",
            font=('Microsoft YaHei UI', 9),
            bg='#F0F8FF',
            fg='#7F8C8D'
        ).pack()

        # 扫描选项
        options_frame = tk.Frame(top_frame, pady=10)
        options_frame.pack(fill='x', padx=10)

        tk.Label(options_frame, text="扫描类型:", font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor='w')

        # 扫描选项容器（横向排列）
        scan_options_frame = tk.Frame(options_frame)
        scan_options_frame.pack(fill='x', pady=5)

        self.scan_vars = {
            'invalid_software': tk.BooleanVar(value=True),
            'startup_items': tk.BooleanVar(value=True),
            'invalid_file_refs': tk.BooleanVar(value=True),
        }

        options = [
            ('无效软件', 'invalid_software'),
            ('启动项', 'startup_items'),
            ('文件引用', 'invalid_file_refs'),
        ]

        for label, var_name in options:
            cb = tk.Checkbutton(
                scan_options_frame,
                text=label,
                variable=self.scan_vars[var_name],
                font=('Microsoft YaHei UI', 9)
            )
            cb.pack(side='left', padx=15)

        # 按钮区域
        button_frame = tk.Frame(top_frame, pady=8)
        button_frame.pack(fill='x', padx=10)

        self.scan_btn = tk.Button(
            button_frame,
            text="🔍 开始扫描",
            command=self.start_scan,
            bg='#4CAF50',
            fg='white',
            font=('Microsoft YaHei UI', 9, 'bold'),
            relief='flat',
            cursor='hand2',
            padx=12,
            pady=6
        )
        self.scan_btn.pack(side='left', padx=3)

        self.stop_btn = tk.Button(
            button_frame,
            text="⏹ 停止",
            command=self.stop_scan,
            state='disabled',
            bg='#f44336',
            fg='white',
            font=('Microsoft YaHei UI', 9),
            relief='flat',
            cursor='hand2',
            padx=12,
            pady=6
        )
        self.stop_btn.pack(side='left', padx=3)

        self.clean_btn = tk.Button(
            button_frame,
            text="🧹 清理选中",
            command=self.clean_selected,
            state='disabled',
            bg='#FF9800',
            fg='white',
            font=('Microsoft YaHei UI', 9),
            relief='flat',
            cursor='hand2',
            padx=12,
            pady=6
        )
        self.clean_btn.pack(side='left', padx=3)

        self.backup_btn = tk.Button(
            button_frame,
            text="💾 备份",
            command=self.show_backups,
            font=('Microsoft YaHei UI', 9),
            relief='flat',
            cursor='hand2',
            padx=12,
            pady=6
        )
        self.backup_btn.pack(side='left', padx=3)

        # 进度信息
        self.progress_frame = tk.Frame(top_frame)
        self.progress_frame.pack(fill='x', padx=10, pady=(0, 10))

        self.progress_label = tk.Label(
            self.progress_frame,
            text="",
            font=('Microsoft YaHei UI', 9),
            fg='#2196F3',
            anchor='w'
        )
        self.progress_label.pack(fill='x', pady=(0, 5))

        # 进度条（使用determinate模式显示实际进度）
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='determinate',
            length=400,
            maximum=100
        )
        self.progress_bar.pack(fill='x')

        # 结果区域
        result_frame = tk.Frame(main_frame)
        result_frame.pack(expand=True, fill='both', pady=(0, 10))

        # 结果标题和统计
        stats_frame = tk.Frame(result_frame, relief=tk.RAISED, borderwidth=1)
        stats_frame.pack(fill='x', pady=(0, 5))

        self.stats_label = tk.Label(
            stats_frame,
            text="📊 扫描结果: 0 个问题",
            font=('Microsoft YaHei UI', 10, 'bold'),
            bg='#ECF0F1',
            pady=5
        )
        self.stats_label.pack(fill='x')

        # 创建Treeview
        tree_frame = tk.Frame(result_frame)
        tree_frame.pack(expand=True, fill='both')

        # 滚动条
        scrollbar_y = tk.Scrollbar(tree_frame)
        scrollbar_y.pack(side='right', fill='y')

        scrollbar_x = tk.Scrollbar(tree_frame, orient='horizontal')
        scrollbar_x.pack(side='bottom', fill='x')

        # Treeview
        columns = ('type', 'path', 'description')
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='headings',
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        self.tree.heading('type', text='类型')
        self.tree.heading('path', text='注册表路径')
        self.tree.heading('description', text='描述')

        self.tree.column('type', width=120, anchor='w')
        self.tree.column('path', width=400, anchor='w')
        self.tree.column('description', width=300, anchor='w')

        self.tree.pack(expand=True, fill='both')

        scrollbar_y.config(command=self.tree.yview)
        scrollbar_x.config(command=self.tree.xview)

        # 绑定选择事件
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        # 表格下方的操作按钮区域
        table_button_frame = tk.Frame(result_frame, pady=8)
        table_button_frame.pack(fill='x')

        # 全选按钮
        self.select_all_btn = tk.Button(
            table_button_frame,
            text="✅ 全选",
            command=self.select_all,
            state='disabled',
            bg='#4CAF50',
            fg='white',
            font=('Microsoft YaHei UI', 9),
            relief='flat',
            cursor='hand2',
            padx=12,
            pady=6
        )
        self.select_all_btn.pack(side='left', padx=3)

        # 反选按钮
        self.invert_select_btn = tk.Button(
            table_button_frame,
            text="🔄 反选",
            command=self.invert_selection,
            state='disabled',
            bg='#64B5F6',
            fg='white',
            font=('Microsoft YaHei UI', 9),
            relief='flat',
            cursor='hand2',
            padx=12,
            pady=6
        )
        self.invert_select_btn.pack(side='left', padx=3)

        # 类型标签颜色映射
        self.type_colors = {
            'invalid_software': '#E74C3C',  # 红色
            'invalid_startup': '#E67E22',  # 橙色
            'recent_docs': '#3498DB',      # 蓝色
            'run_history': '#9B59B6',      # 紫色
        }

        self.type_names = {
            'invalid_software': '无效软件',
            'invalid_startup': '启动项',
            'recent_docs': '最近文档',
            'run_history': '运行历史',
        }

    def start_scan(self):
        """开始扫描"""
        if self.is_scanning:
            return

        # 获取选中的扫描类型
        scan_types = [key for key, var in self.scan_vars.items() if var.get()]

        if not scan_types:
            messagebox.showwarning("提示", "请至少选择一种扫描类型！")
            return

        # 清空结果
        self.issues = []
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 更新UI
        self.is_scanning = True
        self.scan_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.clean_btn.config(state='disabled')
        self.update_stats()

        # 重置进度条
        self.progress_bar['value'] = 0
        self.update_progress("正在初始化扫描...")

        # 设置扫描器回调
        self.scanner.issues = []

        # 创建一个线程安全的回调函数
        def safe_progress_callback(msg):
            def update():
                self.update_progress(msg)
            self.after(0, update)

        def safe_found_callback(issue):
            def update():
                self.add_issue_to_tree(issue)
            self.after(0, update)

        self.scanner.set_callbacks(
            progress=safe_progress_callback,
            found=safe_found_callback
        )

        # 启动扫描线程
        self.scanner_thread = RegistryScannerThread(self.scanner, scan_types)
        self.scanner_thread.start()

    def stop_scan(self):
        """停止扫描"""
        if self.scanner_thread and self.scanner_thread.is_alive():
            self.scanner_thread.stop()

        self.update_progress("正在停止...")
        self.after(1000, self.reset_ui)

    def reset_ui(self):
        """重置UI"""
        self.is_scanning = False
        self.scan_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

        # 设置进度条为100%表示完成
        self.progress_bar['value'] = 100

        if self.issues:
            self.progress_label.config(text=f"✓ 扫描完成！共发现 {len(self.issues)} 个问题")
            self.clean_btn.config(state='normal')
            self.select_all_btn.config(state='normal')
            self.invert_select_btn.config(state='normal')
        else:
            self.progress_label.config(text="✓ 扫描完成，未发现问题")

    def add_issue_to_tree(self, issue: RegistryIssue):
        """添加问题到树形列表"""
        # 直接从scanner获取最新的issues列表
        current_issues = self.scanner.issues.copy()
        self.issues = current_issues

        # 清空并重新填充（批量操作更高效）
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 批量插入所有问题
        for iss in current_issues:
            type_name = self.type_names.get(iss.issue_type, iss.issue_type)
            self.tree.insert('', 'end', values=(
                type_name,
                iss.key_path,
                iss.description
            ))

        self.update_stats()

        # 更新进度信息，显示实际数量
        if self.is_scanning:
            self.progress_label.config(text=f"⏳ 正在扫描... 已发现 {len(current_issues)} 个问题")

    def update_stats(self):
        """更新统计信息"""
        count = len(self.issues)
        self.stats_label.config(
            text=f"📊 扫描结果: {count} 个问题",
            bg='#FFF3CD' if count > 0 else '#ECF0F1'
        )

    def update_progress(self, message: str):
        """更新进度"""
        self.progress_label.config(text=f"⏳ {message}")

        # 从消息中提取进度百分比（如果有的话）
        # 格式：正在扫描xxx... 50%
        if '%' in message:
            try:
                # 提取百分比数字
                percent_str = message.split('%')[0].split(' ')[-1]
                percent = int(percent_str)
                self.progress_bar['value'] = percent
            except:
                # 如果提取失败，使用默认的小幅度增长
                current = self.progress_bar['value']
                if current < 90:
                    self.progress_bar['value'] = current + 5

        self.update()

    def select_all(self):
        """全选所有项目"""
        all_items = self.tree.get_children()
        for item in all_items:
            self.tree.selection_add(item)
        self.update_selection_count()

    def invert_selection(self):
        """反选：反转当前选择状态"""
        all_items = self.tree.get_children()
        selected_items = self.tree.selection()

        # 获取已选择的项的ID集合
        selected_set = set(selected_items)

        for item in all_items:
            if item in selected_set:
                self.tree.selection_remove(item)
            else:
                self.tree.selection_add(item)
        self.update_selection_count()

    def update_selection_count(self):
        """更新选中数量提示"""
        selected_count = len(self.tree.selection())
        if selected_count > 0:
            self.stats_label.config(
                text=f"📊 扫描结果: {len(self.issues)} 个问题 | 已选择: {selected_count} 个"
            )
        else:
            self.stats_label.config(
                text=f"📊 扫描结果: {len(self.issues)} 个问题"
            )

    def on_select(self, event):
        """选择事件"""
        self.update_selection_count()

    def clean_selected(self):
        """清理选中的项目"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("提示", "请先选择要清理的项目！\n\n您可以：\n• 点击'全选'选择所有项目\n• 手动勾选需要的项目\n• 点击'反选'反转选择")
            return

        # 确认对话框
        result = messagebox.askyesno(
            "确认清理",
            f"确定要清理选中的 {len(selected_items)} 个项目吗？\n\n"
            "程序会自动创建备份，清理后可以恢复。",
            icon='warning'
        )

        if not result:
            return

        # 收集要清理的问题项
        selected_issues = []
        for item_id in selected_items:
            index = self.tree.index(item_id)
            if index < len(self.issues):
                selected_issues.append(self.issues[index])

        # 创建备份
        try:
            backup_file = RegistryBackup.create_backup(selected_issues)
            self.update_progress(f"✅ 备份已创建: {backup_file}")
        except Exception as e:
            messagebox.showerror("备份失败", f"创建备份失败: {e}\n\n为安全起见，已取消清理操作。")
            return

        # 执行清理
        def clean_thread():
            success_count = RegistryCleaner.clean_issues(
                selected_issues,
                progress_callback=lambda i, total, msg: self.update_progress(msg)
            )

            self.after(0, lambda: self.clean_completed(success_count, len(selected_issues)))

        import threading
        thread = threading.Thread(target=clean_thread, daemon=True)
        thread.start()

    def clean_completed(self, success_count: int, total_count: int):
        """清理完成"""
        messagebox.showinfo(
            "清理完成",
            f"成功清理 {success_count}/{total_count} 个项目！\n\n"
            f"备份文件已保存，如需恢复请点击'查看备份'按钮。"
        )

        # 从列表中移除已清理的项目
        for item in self.tree.selection():
            self.tree.delete(item)

        self.issues = [issue for issue in self.issues if issue not in
                      [self.issues[self.tree.index(item)] for item in self.tree.selection()]]

        self.update_stats()
        self.clean_btn.config(state='disabled' if not self.issues else 'normal')

    def show_backups(self):
        """显示备份列表"""
        backups = RegistryBackup.get_backup_files()

        # 创建备份窗口
        backup_window = tk.Toplevel(self)
        backup_window.title("注册表备份")
        backup_window.geometry("700x400")
        backup_window.transient(self)
        backup_window.grab_set()

        # 标题
        title_frame = tk.Frame(backup_window, bg='#4A90E2', height=60)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        tk.Label(
            title_frame,
            text="💾 注册表备份列表",
            font=('Microsoft YaHei UI', 14, 'bold'),
            bg='#4A90E2',
            fg='white'
        ).pack(expand=True)

        # 备份列表
        list_frame = tk.Frame(backup_window)
        list_frame.pack(expand=True, fill='both', padx=10, pady=10)

        # Treeview
        columns = ('name', 'created', 'size')
        tree = ttk.Treeview(list_frame, columns=columns, show='headings')

        tree.heading('name', text='备份文件名')
        tree.heading('created', text='创建时间')
        tree.heading('size', text='大小')

        tree.column('name', width=300, anchor='w')
        tree.column('created', width=200, anchor='w')
        tree.column('size', width=100, anchor='w')

        tree.pack(expand=True, fill='both')

        # 填充数据
        for backup in backups:
            tree.insert('', 'end', values=(
                backup['name'],
                backup['created'],
                f"{backup['size'] / 1024:.2f} KB"
            ))

        # 按钮
        button_frame = tk.Frame(backup_window, pady=10)
        button_frame.pack(fill='x')

        if backups:
            tk.Button(
                button_frame,
                text="📥 恢复选中的备份",
                command=lambda: self.restore_backup(tree, backup_window),
                bg='#2196F3',
                fg='white',
                font=('Microsoft YaHei UI', 10),
                relief='flat',
                cursor='hand2',
                padx=15,
                pady=8
            ).pack(side='left', padx=10)

            tk.Button(
                button_frame,
                text="📂 打开备份文件夹",
                command=self.open_backup_folder,
                font=('Microsoft YaHei UI', 10),
                relief='flat',
                cursor='hand2',
                padx=15,
                pady=8
            ).pack(side='left', padx=10)

        tk.Button(
            button_frame,
            text="关闭",
            command=backup_window.destroy,
            font=('Microsoft YaHei UI', 10),
            relief='flat',
            cursor='hand2',
            padx=15,
            pady=8
        ).pack(side='right', padx=10)

        if not backups:
            tk.Label(
                list_frame,
                text="暂无备份文件",
                font=('Microsoft YaHei UI', 12),
                fg='#95A5A6'
            ).pack(expand=True)

    def restore_backup(self, tree, window):
        """恢复备份"""
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择要恢复的备份文件！")
            return

        item = tree.item(selected[0])
        filename = item['values'][0]

        # 查找完整路径
        backups = RegistryBackup.get_backup_files()
        backup_path = None
        for backup in backups:
            if backup['name'] == filename:
                backup_path = backup['path']
                break

        if not backup_path:
            messagebox.showerror("错误", "找不到备份文件！")
            return

        # 确认
        result = messagebox.askyesno(
            "确认恢复",
            f"确定要恢复备份 {filename} 吗？\n\n"
            "这将修改注册表，请确保备份文件可信。",
            icon='warning'
        )

        if result:
            import subprocess
            try:
                # 使用 reg import 恢复
                subprocess.run(['reg', 'import', backup_path], check=True)
                messagebox.showinfo("成功", "备份已恢复！\n\n建议重启计算机以使更改生效。")
                window.destroy()
            except subprocess.CalledProcessError as e:
                messagebox.showerror("失败", f"恢复备份失败: {e}")

    def open_backup_folder(self):
        """打开备份文件夹"""
        import subprocess
        import os
        import tempfile

        backup_dir = os.path.join(tempfile.gettempdir(), "RegistryCleaner_Backups")

        # 检查文件夹是否存在
        if not os.path.exists(backup_dir):
            try:
                # 如果不存在，创建它
                os.makedirs(backup_dir)
                messagebox.showinfo("提示", f"备份文件夹已创建：\n{backup_dir}")
            except Exception as e:
                messagebox.showerror("错误", f"无法创建备份文件夹：\n{e}")
                return

        # 尝试多种方式打开文件夹
        try:
            # 方法1：使用 os.startfile（Windows专用）
            os.startfile(backup_dir)
        except:
            try:
                # 方法2：使用 subprocess explorer
                subprocess.Popen(['explorer', backup_dir])
            except:
                try:
                    # 方法3：使用 cmd start
                    subprocess.Popen(['cmd', '/c', 'start', '', backup_dir], shell=True)
                except Exception as e:
                    messagebox.showerror("错误", f"无法打开文件夹：\n{e}\n\n文件夹路径：\n{backup_dir}")
