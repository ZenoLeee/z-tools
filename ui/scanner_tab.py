import os
from typing import List
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from core.shortcut_scanner import ShortcutInfo, UnifiedScannerThread, ShortcutRecoveryThread
from utils.file_utils import try_delete_file


class ShortcutScannerTab(tk.Frame):
    """快捷方式扫描标签页"""

    def __init__(self, parent):
        super().__init__(parent)
        self.scanner_thread = None
        self.shortcuts: List[ShortcutInfo] = []
        self.is_scanning = False
        self.init_ui()

    def init_ui(self):
        # 主容器
        main_frame = tk.Frame(self)
        main_frame.pack(expand=True, fill='both', padx=10, pady=10)

        # 顶部控制面板
        top_frame = tk.Frame(main_frame)
        top_frame.pack(fill='x', pady=(0, 10))

        # 扫描按钮
        self.scan_btn = tk.Button(
            top_frame, text="开始扫描所有磁盘的快捷方式",
            command=self.start_scan,
            bg='#4CAF50', fg='white',
            font=('Arial', 12, 'bold'),
            height=2
        )
        self.scan_btn.pack(side='left', padx=5)

        # 停止扫描按钮
        self.stop_btn = tk.Button(
            top_frame, text="停止扫描",
            command=self.stop_scan,
            state='disabled',
            bg='#f44336', fg='white',
            font=('Arial', 12),
            height=2
        )
        self.stop_btn.pack(side='left', padx=5)

        # 搜索框
        tk.Label(top_frame, text="搜索:").pack(side='left', padx=(20, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_shortcuts)
        self.search_edit = tk.Entry(top_frame, textvariable=self.search_var, width=30)
        self.search_edit.pack(side='left', padx=5)

        # 进度条区域
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill='x', pady=(0, 10))

        # 总进度条
        self.total_progress_label = tk.Label(progress_frame, text="就绪", font=('Arial', 10, 'bold'))
        self.total_progress_label.pack(anchor='w')

        self.total_progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.total_progress_bar.pack(fill='x', pady=(5, 0))

        # 当前操作标签
        self.current_action_label = tk.Label(progress_frame, text="等待开始扫描...")
        self.current_action_label.pack(anchor='w', pady=(5, 0))

        # 统计信息
        stats_frame = tk.Frame(main_frame)
        stats_frame.pack(fill='x', pady=(0, 10))

        self.total_label = tk.Label(stats_frame, text="无效快捷方式总数: 0")
        self.total_label.pack(side='left', padx=5)

        self.current_label = tk.Label(stats_frame, text="当前显示: 0")
        self.current_label.pack(side='left', padx=5)

        # 表格显示
        table_frame = tk.Frame(main_frame)
        table_frame.pack(expand=True, fill='both')

        # 创建 Treeview
        columns = ("name", "path", "target", "type", "error")
        self.table = ttk.Treeview(table_frame, columns=columns, show='headings', selectmode='browse')

        # 设置列标题
        self.table.heading("name", text="名称")
        self.table.heading("path", text="路径")
        self.table.heading("target", text="目标")
        self.table.heading("type", text="类型")
        self.table.heading("error", text="错误信息")

        # 设置列宽
        self.table.column("name", width=200, minwidth=150)
        self.table.column("path", width=250, minwidth=200)
        self.table.column("target", width=250, minwidth=200)
        self.table.column("type", width=80, minwidth=60)
        self.table.column("error", width=200, minwidth=150)

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
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(10, 0))

        self.open_btn = tk.Button(button_frame, text="打开所在文件夹", command=self.open_shortcut_folder)
        self.open_btn.pack(side='left', padx=5)

        self.run_btn = tk.Button(button_frame, text="尝试运行", command=self.run_shortcut)
        self.run_btn.pack(side='left', padx=5)

        self.delete_btn = tk.Button(
            button_frame, text="删除选中的",
            command=self.delete_shortcut,
            bg='#ff6b6b', fg='white'
        )
        self.delete_btn.pack(side='left', padx=5)

        self.delete_all_btn = tk.Button(
            button_frame, text="删除全部",
            command=self.delete_all_shortcuts,
            bg='#ff4757', fg='white'
        )
        self.delete_all_btn.pack(side='left', padx=5)

        self.recover_selected_btn = tk.Button(
            button_frame, text="恢复选中",
            command=self.recover_selected_shortcuts,
            bg='#2196F3', fg='white'
        )
        self.recover_selected_btn.pack(side='left', padx=5)

        self.recover_all_btn = tk.Button(
            button_frame, text="尝试恢复全部",
            command=self.recover_all_shortcuts,
            bg='#3F51B5', fg='white'
        )
        self.recover_all_btn.pack(side='left', padx=5)

        # 初始时禁用删除按钮
        self.set_delete_buttons_enabled(False)

    def set_delete_buttons_enabled(self, enabled: bool):
        """设置删除按钮的启用状态"""
        state = 'normal' if enabled else 'disabled'
        self.delete_btn.config(state=state)
        self.delete_all_btn.config(state=state)
        self.recover_selected_btn.config(state=state)
        self.recover_all_btn.config(state=state)

    def start_scan(self):
        """开始扫描"""
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
        self.shortcuts = []
        self.update_stats()

        # 创建并启动扫描线程
        self.scanner_thread = UnifiedScannerThread()
        self.scanner_thread.set_progress_callback(self.update_progress)
        self.scanner_thread.set_found_callback(self.add_invalid_shortcut)
        self.scanner_thread.set_finished_callback(self.on_scan_finished)
        self.scanner_thread.start()

        self.total_progress_label.config(text="正在扫描所有磁盘...")
        self.current_action_label.config(text="正在初始化扫描...")

    def stop_scan(self):
        """停止扫描"""
        if self.scanner_thread and self.scanner_thread.is_alive():
            self.scanner_thread.stop()
            self.scanner_thread.join(timeout=1)
            self.total_progress_label.config(text="扫描已停止")
            self.current_action_label.config(text="扫描被用户停止")

        # 恢复按钮状态
        self.is_scanning = False
        self.scan_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

        # 如果有结果，启用删除按钮
        if len(self.shortcuts) > 0:
            self.set_delete_buttons_enabled(True)

    def update_progress(self, current: int, total: int, action_text: str):
        """更新进度"""
        # 更新总进度
        progress_percent = int((current / total) * 100)
        self.total_progress_bar['maximum'] = 100
        self.total_progress_bar['value'] = progress_percent

        # 更新标签
        self.total_progress_label.config(text=f"总体进度: {progress_percent}%")
        self.current_action_label.config(text=action_text)

    def add_invalid_shortcut(self, shortcut):
        """添加无效快捷方式到列表"""
        # 添加到列表
        self.shortcuts.append(shortcut)

        # 添加到表格
        name = shortcut.display_name if shortcut.display_name else shortcut.name

        # 插入数据
        self.table.insert('', 'end', values=(
            name,
            shortcut.path,
            shortcut.target_path[:100] if shortcut.target_path else "",
            self.get_type_display_name(shortcut.shortcut_type),
            shortcut.error_message
        ))

        # 更新统计信息
        self.update_stats()

    def on_scan_finished(self):
        """扫描完成"""
        # 设置扫描状态
        self.is_scanning = False

        # 更新进度条
        self.total_progress_bar['value'] = 100
        self.total_progress_label.config(text=f"扫描完成，共找到 {len(self.shortcuts)} 个无效快捷方式")
        self.current_action_label.config(text="扫描完成")

        # 恢复按钮状态
        self.scan_btn.config(state='normal')
        self.stop_btn.config(state='disabled')

        # 如果有结果，启用删除按钮
        if len(self.shortcuts) > 0:
            self.set_delete_buttons_enabled(True)

    def filter_shortcuts(self, *args):
        """根据搜索框过滤快捷方式"""
        search_text = self.search_var.get().lower()

        # 获取所有项目
        all_items = self.table.get_children()

        # 如果没有搜索文本，显示所有项目
        if not search_text:
            for item in all_items:
                self.table.item(item, tags='')
            self.update_stats()
            return

        # 隐藏不匹配的项目
        for item in all_items:
            values = self.table.item(item)['values']
            match = any(search_text in str(value).lower() for value in values)
            if match:
                self.table.item(item, tags='')
            else:
                self.table.item(item, tags='hidden')

        # 配置隐藏标签
        self.table.tag_configure('hidden', foreground='lightgray')

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
        search_text = self.search_var.get().lower()

        # 计算当前显示的数量
        if search_text:
            displayed = 0
            for item in self.table.get_children():
                tags = self.table.item(item).get('tags', [])
                if 'hidden' not in tags:
                    displayed += 1
        else:
            displayed = total_invalid

        self.total_label.config(text=f"无效快捷方式总数: {total_invalid}")
        self.current_label.config(text=f"当前显示: {displayed}")

    def open_shortcut_folder(self):
        """打开快捷方式所在文件夹"""
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个快捷方式")
            return

        item = selected[0]
        values = self.table.item(item)['values']
        shortcut_path = values[1]
        folder_path = os.path.dirname(shortcut_path)

        try:
            os.startfile(folder_path)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹: {e}")

    def run_shortcut(self):
        """运行选中的快捷方式"""
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个快捷方式")
            return

        item = selected[0]
        values = self.table.item(item)['values']
        shortcut_path = values[1]
        shortcut_name = values[0]

        try:
            # 尝试运行快捷方式
            os.startfile(shortcut_path)

            # 如果运行成功，询问用户是否将其标记为有效
            reply = messagebox.askyesno(
                "快捷方式运行成功",
                f"快捷方式 '{shortcut_name}' 运行成功！\n是否将其从无效列表中移除？"
            )

            if reply:
                # 从列表中移除
                self.table.delete(item)

                # 从原始列表中移除
                self.shortcuts = [s for s in self.shortcuts if s.path != shortcut_path]

                self.update_stats()
                messagebox.showinfo("成功", "快捷方式已从列表中移除")

        except Exception as e:
            messagebox.showerror("错误", f"无法运行快捷方式: {e}")

    def delete_shortcut(self):
        """删除选中的快捷方式"""
        # 检查是否正在扫描
        if self.is_scanning:
            messagebox.showwarning("警告", "扫描正在进行中，请等待扫描完成后再删除")
            return

        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个快捷方式")
            return

        item = selected[0]
        values = self.table.item(item)['values']
        shortcut_name = values[0]
        shortcut_path = values[1]

        reply = messagebox.askyesno(
            "确认删除",
            f"确定要删除快捷方式 '{shortcut_name}' 吗？"
        )

        if reply:
            success, message = try_delete_file(shortcut_path)
            if success:
                # 从原始列表中移除
                self.shortcuts = [s for s in self.shortcuts if s.path != shortcut_path]

                # 从表格中移除
                self.table.delete(item)
                self.update_stats()
                messagebox.showinfo("成功", message)

                # 如果没有快捷方式了，禁用删除按钮
                if len(self.shortcuts) == 0:
                    self.set_delete_buttons_enabled(False)
            else:
                messagebox.showerror("删除失败", message)

    def delete_all_shortcuts(self):
        """删除所有无效快捷方式"""
        # 检查是否正在扫描
        if self.is_scanning:
            messagebox.showwarning("警告", "扫描正在进行中，请等待扫描完成后再删除")
            return

        if not self.shortcuts:
            messagebox.showwarning("警告", "没有可删除的快捷方式")
            return

        count = len(self.shortcuts)

        reply = messagebox.askyesno(
            "确认删除所有",
            f"确定要删除所有 {count} 个无效快捷方式吗？\n此操作不可恢复！"
        )

        if reply:
            deleted_count = 0
            failed_count = 0
            error_messages = []

            # 使用 progress_var 和 update 模拟进度
            for i, shortcut in enumerate(self.shortcuts[:]):
                success, message = try_delete_file(shortcut.path)

                if success:
                    self.shortcuts.remove(shortcut)
                    deleted_count += 1
                else:
                    failed_count += 1
                    error_messages.append(f"{shortcut.name}: {message}")

                # 更新进度标签
                self.current_action_label.config(text=f"正在删除: {shortcut.name}")
                self.update()

            # 清空表格
            for item in self.table.get_children():
                self.table.delete(item)
            self.update_stats()

            # 禁用删除按钮
            self.set_delete_buttons_enabled(False)

            # 显示结果
            result_msg = f"删除完成:\n成功删除: {deleted_count} 个\n删除失败: {failed_count} 个"

            if error_messages:
                result_msg += "\n\n失败详情:\n" + "\n".join(error_messages[:10])
                if len(error_messages) > 10:
                    result_msg += f"\n...还有 {len(error_messages) - 10} 个错误"

            messagebox.showinfo("删除结果", result_msg)

    def recover_selected_shortcuts(self):
        """恢复选中的快捷方式"""
        # 检查是否正在扫描
        if self.is_scanning:
            messagebox.showwarning("警告", "扫描正在进行中，请等待扫描完成后再恢复")
            return

        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要恢复的快捷方式")
            return

        # 获取选中的快捷方式
        shortcuts_to_recover = []
        for item in selected:
            values = self.table.item(item)['values']
            shortcut_path = values[1]
            # 从列表中找到对应的快捷方式对象
            for shortcut in self.shortcuts:
                if shortcut.path == shortcut_path:
                    shortcuts_to_recover.append(shortcut)
                    break

        if not shortcuts_to_recover:
            messagebox.showwarning("警告", "未找到可恢复的快捷方式")
            return

        # 确认恢复
        reply = messagebox.askyesno(
            "确认恢复",
            f"确定要尝试恢复选中的 {len(shortcuts_to_recover)} 个快捷方式吗？\n\n系统将在所有磁盘中搜索匹配的文件并更新快捷方式。"
        )

        if reply:
            self.start_recovery(shortcuts_to_recover)

    def recover_all_shortcuts(self):
        """恢复所有快捷方式"""
        # 检查是否正在扫描
        if self.is_scanning:
            messagebox.showwarning("警告", "扫描正在进行中，请等待扫描完成后再恢复")
            return

        if not self.shortcuts:
            messagebox.showwarning("警告", "没有可恢复的快捷方式")
            return

        count = len(self.shortcuts)

        # 确认恢复
        reply = messagebox.askyesno(
            "确认恢复",
            f"确定要尝试恢复所有 {count} 个快捷方式吗？\n\n系统将在所有磁盘中搜索匹配的文件并更新快捷方式。\n这可能需要一些时间。"
        )

        if reply:
            self.start_recovery(self.shortcuts[:])

    def start_recovery(self, shortcuts_to_recover: List[ShortcutInfo]):
        """开始恢复快捷方式"""
        # 禁用所有操作按钮
        self.set_delete_buttons_enabled(False)
        self.scan_btn.config(state='disabled')

        # 创建并启动恢复线程
        self.recovery_thread = ShortcutRecoveryThread(shortcuts_to_recover)
        self.recovery_thread.set_progress_callback(self.update_recovery_progress)
        self.recovery_thread.set_found_callback(self.on_recovery_result)
        self.recovery_thread.set_finished_callback(self.on_recovery_finished)
        self.recovery_thread.start()

        self.total_progress_label.config(text="正在恢复快捷方式...")
        self.current_action_label.config(text="开始恢复...")

    def update_recovery_progress(self, current: int, total: int, text: str):
        """更新恢复进度"""
        progress_percent = int((current / total) * 100)
        self.total_progress_bar['maximum'] = 100
        self.total_progress_bar['value'] = progress_percent
        self.total_progress_label.config(text=f"恢复进度: {progress_percent}%")
        self.current_action_label.config(text=text)

    def on_recovery_result(self, result: dict):
        """处理单个恢复结果"""
        shortcut = result['shortcut']
        success = result['success']
        new_path = result.get('new_path', '')
        message = result.get('message', '')

        if success:
            # 从表格中找到对应的项并移除
            for item in self.table.get_children():
                values = self.table.item(item)['values']
                if values[1] == shortcut.path:
                    self.table.delete(item)
                    break

            # 从列表中移除
            self.shortcuts = [s for s in self.shortcuts if s.path != shortcut.path]

            # 更新统计
            self.update_stats()

    def on_recovery_finished(self, recovered_count: int, failed_count: int, results: List):
        """恢复完成"""
        # 恢复按钮状态
        self.scan_btn.config(state='normal')
        if len(self.shortcuts) > 0:
            self.set_delete_buttons_enabled(True)

        # 更新进度
        self.total_progress_bar['value'] = 100
        self.total_progress_label.config(text="恢复完成")
        self.current_action_label.config(text=f"成功: {recovered_count}, 失败: {failed_count}")

        # 显示结果
        result_msg = f"快捷方式恢复完成:\n成功恢复: {recovered_count} 个\n恢复失败: {failed_count} 个"

        # 显示失败详情
        failed_results = [r for r in results if not r['success']]
        if failed_results:
            result_msg += "\n\n失败详情:\n"
            for r in failed_results[:10]:
                shortcut_name = r['shortcut'].display_name or r['shortcut'].name
                result_msg += f"- {shortcut_name}: {r['message']}\n"
            if len(failed_results) > 10:
                result_msg += f"...还有 {len(failed_results) - 10} 个失败"

        messagebox.showinfo("恢复结果", result_msg)
