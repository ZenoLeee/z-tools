"""
启动项优化独立窗口
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List
from core.platform.windows.startup_manager import (
    WindowsStartupManager,
    WindowsStartupManagerThread,
    StartupItem,
    is_admin,
    run_as_admin
)
from utils.startup_scorer import StartupScorer


class StartupOptimizerWindow(tk.Toplevel):
    """启动项优化窗口"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("启动项优化")
        self.geometry("1100x750")
        self.transient(parent)
        self.grab_set()

        # 居中显示
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (1100 // 2)
        y = (self.winfo_screenheight() // 2) - (750 // 2)
        self.geometry(f"1100x750+{x}+{y}")

        self.manager = WindowsStartupManager()
        self.manager_thread = None
        self.startup_items: List[StartupItem] = []
        self.is_scanning = False

        self.init_ui()
        self.start_scan()

    def init_ui(self):
        """初始化UI"""
        # ============ 顶部标题区域 ============
        title_frame = tk.Frame(self, bg='#4A90E2', height=80)
        title_frame.pack(fill='x', padx=0, pady=0)
        title_frame.pack_propagate(False)

        tk.Label(
            title_frame,
            text="🚀 启动项优化",
            font=('Microsoft YaHei UI', 18, 'bold'),
            bg='#4A90E2',
            fg='white'
        ).pack(pady=(10, 5))

        tk.Label(
            title_frame,
            text="智能识别可优化的启动项，加速系统启动速度",
            font=('Microsoft YaHei UI', 10),
            bg='#4A90E2',
            fg='#E8F4F8'
        ).pack()

        # ============ 操作按钮区域 ============
        control_frame = tk.Frame(self, relief=tk.RAISED, borderwidth=1)
        control_frame.pack(fill='x', padx=10, pady=(10, 5))

        # 左侧按钮
        left_btn_frame = tk.Frame(control_frame)
        left_btn_frame.pack(side='left', padx=10, pady=10)

        self.scan_btn = tk.Button(
            left_btn_frame,
            text="🔍 重新扫描",
            command=self.start_scan,
            bg='#4CAF50',
            fg='white',
            font=('Microsoft YaHei UI', 10, 'bold'),
            relief='flat',
            cursor='hand2',
            padx=15,
            pady=8
        )
        self.scan_btn.pack(side='left', padx=3)

        self.stop_btn = tk.Button(
            left_btn_frame,
            text="⏹ 停止",
            command=self.stop_scan,
            state='disabled',
            bg='#f44336',
            fg='white',
            font=('Microsoft YaHei UI', 10),
            relief='flat',
            cursor='hand2',
            padx=15,
            pady=8
        )
        self.stop_btn.pack(side='left', padx=3)

        # 中间按钮
        middle_btn_frame = tk.Frame(control_frame)
        middle_btn_frame.pack(side='left', padx=20, pady=10)

        self.disable_btn = tk.Button(
            middle_btn_frame,
            text="⏸ 禁用选中",
            command=self.disable_selected,
            state='disabled',
            bg='#FF9800',
            fg='white',
            font=('Microsoft YaHei UI', 10, 'bold'),
            relief='flat',
            cursor='hand2',
            padx=15,
            pady=8
        )
        self.disable_btn.pack(side='left', padx=3)

        self.enable_btn = tk.Button(
            middle_btn_frame,
            text="▶️ 启用选中",
            command=self.enable_selected,
            state='disabled',
            bg='#2196F3',
            fg='white',
            font=('Microsoft YaHei UI', 10, 'bold'),
            relief='flat',
            cursor='hand2',
            padx=15,
            pady=8
        )
        self.enable_btn.pack(side='left', padx=3)

        self.delete_btn = tk.Button(
            middle_btn_frame,
            text="🗑️ 删除选中",
            command=self.delete_selected,
            state='disabled',
            bg='#E74C3C',
            fg='white',
            font=('Microsoft YaHei UI', 10, 'bold'),
            relief='flat',
            cursor='hand2',
            padx=15,
            pady=8
        )
        self.delete_btn.pack(side='left', padx=3)

        self.delay_btn = tk.Button(
            middle_btn_frame,
            text="⏱️ 延迟启动",
            command=self.set_delayed_startup,
            state='disabled',
            bg='#00BCD4',
            fg='white',
            font=('Microsoft YaHei UI', 10, 'bold'),
            relief='flat',
            cursor='hand2',
            padx=15,
            pady=8
        )
        self.delay_btn.pack(side='left', padx=3)

        # 右侧智能优化按钮
        right_btn_frame = tk.Frame(control_frame)
        right_btn_frame.pack(side='right', padx=10, pady=10)

        self.smart_optimize_btn = tk.Button(
            right_btn_frame,
            text="🤖 智能优化",
            command=self.smart_optimize,
            bg='#9C27B0',
            fg='white',
            font=('Microsoft YaHei UI', 11, 'bold'),
            relief='flat',
            cursor='hand2',
            padx=20,
            pady=8
        )
        self.smart_optimize_btn.pack(side='left', padx=3)

        # ============ 进度信息区域 ============
        progress_frame = tk.Frame(self)
        progress_frame.pack(fill='x', padx=10, pady=(5, 10))

        self.progress_label = tk.Label(
            progress_frame,
            text="",
            font=('Microsoft YaHei UI', 9),
            fg='#2196F3',
            anchor='w'
        )
        self.progress_label.pack(fill='x', pady=(0, 5))

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=400,
            maximum=100
        )
        self.progress_bar.pack(fill='x')

        # ============ 统计信息区域 ============
        stats_frame = tk.Frame(self, relief=tk.RAISED, borderwidth=1, bg='#ECF0F1')
        stats_frame.pack(fill='x', padx=10, pady=(0, 5))

        self.stats_label = tk.Label(
            stats_frame,
            text="📊 扫描结果: 0 个启动项",
            font=('Microsoft YaHei UI', 10, 'bold'),
            bg='#ECF0F1',
            fg='#2C3E50'
        )
        self.stats_label.pack(pady=8)

        # ============ 启动项列表区域 ============
        list_frame = tk.Frame(self)
        list_frame.pack(expand=True, fill='both', padx=10, pady=(0, 10))

        # 滚动条
        scrollbar_y = tk.Scrollbar(list_frame)
        scrollbar_y.pack(side='right', fill='y')

        scrollbar_x = tk.Scrollbar(list_frame, orient='horizontal')
        scrollbar_x.pack(side='bottom', fill='x')

        # Treeview
        columns = ('name', 'type', 'score', 'status', 'recommendation', 'location')
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show='headings',
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        self.tree.heading('name', text='启动项名称')
        self.tree.heading('type', text='类型')
        self.tree.heading('score', text='评分')
        self.tree.heading('status', text='状态')
        self.tree.heading('recommendation', text='优化建议')
        self.tree.heading('location', text='位置')

        self.tree.column('name', width=200, anchor='w')
        self.tree.column('type', width=100, anchor='center')
        self.tree.column('score', width=80, anchor='center')
        self.tree.column('status', width=100, anchor='center')
        self.tree.column('recommendation', width=300, anchor='w')
        self.tree.column('location', width=180, anchor='w')

        self.tree.pack(expand=True, fill='both')

        scrollbar_y.config(command=self.tree.yview)
        scrollbar_x.config(command=self.tree.xview)

        # 绑定选择事件
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        # ============ 底部提示区域 ============
        tip_frame = tk.Frame(self, bg='#FFF3CD', height=40)
        tip_frame.pack(fill='x', side='bottom')
        tip_frame.pack_propagate(False)

        tk.Label(
            tip_frame,
            text="💡 提示：禁用启动项前请仔细阅读优化建议，系统关键组件建议保留",
            font=('Microsoft YaHei UI', 9),
            bg='#FFF3CD',
            fg='#856404'
        ).pack(expand=True)

    def start_scan(self):
        """开始扫描"""
        # 清空列表
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.startup_items = []
        self.is_scanning = True

        # 更新按钮状态
        self.scan_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.disable_btn.config(state='disabled')
        self.enable_btn.config(state='disabled')
        self.delete_btn.config(state='disabled')
        self.delay_btn.config(state='disabled')
        self.smart_optimize_btn.config(state='disabled')

        # 设置进度
        self.progress_bar['value'] = 0
        self.update_progress("正在初始化扫描...")

        # 设置回调
        self.manager.startup_items = []

        def safe_progress(current, total, msg):
            def update():
                self.update_progress(msg)
                self.progress_bar['value'] = (current / total) * 100
            self.after(0, update)

        def safe_found(item):
            def update():
                self.add_item_to_tree(item)
            self.after(0, update)

        def safe_finished():
            def update():
                self.scan_finished()
            self.after(0, update)

        self.manager.set_progress_callback(safe_progress)
        self.manager.set_found_callback(safe_found)
        self.manager.set_finished_callback(safe_finished)

        # 启动扫描线程
        self.manager_thread = WindowsStartupManagerThread(self.manager)
        self.manager_thread.start()

    def stop_scan(self):
        """停止扫描"""
        if self.manager_thread and self.manager_thread.is_alive():
            self.manager_thread.stop()
        self.update_progress("正在停止...")
        self.after(1000, self.reset_ui)

    def reset_ui(self):
        """重置UI"""
        self.is_scanning = False
        self.scan_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.progress_bar['value'] = 100

    def add_item_to_tree(self, item: StartupItem):
        """添加启动项到列表"""
        self.startup_items.append(item)

        # 评分
        score, recommendation = StartupScorer.score_startup_item(
            item.name, item.command, item.is_valid
        )
        item.score = score
        item.recommendation = recommendation

        # 获取类型显示名称
        type_names = {
            'registry': '注册表',
            'folder': '启动文件夹',
            'task': '计划任务'
        }
        type_name = type_names.get(item.item_type, item.item_type)

        # 状态
        if not item.is_valid:
            status = "❌ 无效"
        elif item.is_enabled:
            status = "✅ 已启用"
        else:
            status = "⏸ 已禁用"

        # 评分等级显示
        if score <= 30:
            score_text = f"🟢 {score}"
        elif score <= 50:
            score_text = f"🟡 {score}"
        elif score <= 70:
            score_text = f"🟠 {score}"
        else:
            score_text = f"🔴 {score}"

        self.tree.insert('', 'end', values=(
            item.name,
            type_name,
            score_text,
            status,
            recommendation,
            item.location
        ))

        self.update_stats()

    def update_stats(self):
        """更新统计信息"""
        total = len(self.startup_items)
        enabled = sum(1 for item in self.startup_items if item.is_enabled)
        disabled = total - enabled
        invalid = sum(1 for item in self.startup_items if not item.is_valid)

        self.stats_label.config(
            text=f"📊 扫描结果: {total} 个启动项 | 已启用: {enabled} | 已禁用: {disabled} | 无效: {invalid}"
        )

    def update_progress(self, message: str):
        """更新进度"""
        self.progress_label.config(text=f"⏳ {message}")

    def scan_finished(self):
        """扫描完成"""
        self.is_scanning = False
        self.scan_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.progress_bar['value'] = 100

        count = len(self.startup_items)
        self.progress_label.config(text=f"✓ 扫描完成！共发现 {count} 个启动项")

        if count > 0:
            self.disable_btn.config(state='normal')
            self.enable_btn.config(state='normal')
            self.delete_btn.config(state='normal')
            self.delay_btn.config(state='normal')
            self.smart_optimize_btn.config(state='normal')

    def on_select(self, event):
        """选择事件"""
        pass

    def disable_selected(self):
        """禁用选中的启动项"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择要禁用的启动项！")
            return

        # 收集选中的启动项
        items_to_disable = []
        for item_id in selected:
            index = self.tree.index(item_id)
            if index < len(self.startup_items):
                items_to_disable.append(self.startup_items[index])

        # 确认
        result = messagebox.askyesno(
            "确认禁用",
            f"确定要禁用选中的 {len(items_to_disable)} 个启动项吗？\n\n"
            "禁用后这些程序将不会在开机时自动启动。",
            icon='warning'
        )

        if not result:
            return

        # 执行禁用
        success_count = 0
        permission_errors = []

        for item in items_to_disable:
            if self.manager.disable_startup_item(item):
                success_count += 1
                item.is_enabled = False
            else:
                # 检查是否是权限错误
                if "权限不足" in item.error_message or "拒绝访问" in item.error_message:
                    permission_errors.append((item.name, item.error_message))

        # 如果有权限错误，询问用户是否以管理员身份重启
        if permission_errors:
            perm_error_names = [name for name, _ in permission_errors[:3]]
            if len(permission_errors) > 3:
                perm_error_names.append(f"等{len(permission_errors)}个")

            if self._handle_permission_error(f"以下启动项需要管理员权限才能禁用：\n{', '.join(perm_error_names)}"):
                return  # 程序已重启

        messagebox.showinfo(
            "禁用完成",
            f"成功禁用 {success_count}/{len(items_to_disable)} 个启动项！"
        )

        # 重新扫描以更新状态
        self.start_scan()

    def enable_selected(self):
        """启用选中的启动项"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择要启用的启动项！")
            return

        # 收集选中的启动项
        items_to_enable = []
        for item_id in selected:
            index = self.tree.index(item_id)
            if index < len(self.startup_items):
                items_to_enable.append(self.startup_items[index])

        # 执行启用
        success_count = 0
        permission_errors = []

        for item in items_to_enable:
            if self.manager.enable_startup_item(item):
                success_count += 1
                item.is_enabled = True
            else:
                # 检查是否是权限错误
                if "权限不足" in item.error_message or "拒绝访问" in item.error_message:
                    permission_errors.append((item.name, item.error_message))

        # 如果有权限错误，询问用户是否以管理员身份重启
        if permission_errors:
            perm_error_names = [name for name, _ in permission_errors[:3]]
            if len(permission_errors) > 3:
                perm_error_names.append(f"等{len(permission_errors)}个")

            if self._handle_permission_error(f"以下启动项需要管理员权限才能启用：\n{', '.join(perm_error_names)}"):
                return  # 程序已重启

        messagebox.showinfo(
            "启用完成",
            f"成功启用 {success_count}/{len(items_to_enable)} 个启动项！"
        )

        # 重新扫描以更新状态
        self.start_scan()

    def delete_selected(self):
        """删除选中的启动项"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择要删除的启动项！")
            return

        # 收集选中的启动项
        items_to_delete = []
        for item_id in selected:
            index = self.tree.index(item_id)
            if index < len(self.startup_items):
                items_to_delete.append(self.startup_items[index])

        # 二次确认
        result = messagebox.askyesno(
            "确认删除",
            f"确定要删除选中的 {len(items_to_delete)} 个启动项吗？\n\n"
            "⚠️ 警告：删除操作不可恢复！\n"
            "建议先禁用，确认不需要后再删除。",
            icon='warning'
        )

        if not result:
            return

        # 最终确认
        result2 = messagebox.askyesno(
            "最终确认",
            "此操作将永久删除选中的启动项配置。\n\n"
            "您确定要继续吗？",
            icon='warning'
        )

        if not result2:
            return

        # 执行删除
        success_count = 0
        failed_items = []
        permission_errors = []

        for item in items_to_delete:
            if self.manager.delete_startup_item(item):
                success_count += 1
            else:
                error_msg = item.error_message
                failed_items.append((item.name, error_msg))
                # 检查是否是权限错误
                if "权限不足" in error_msg or "拒绝访问" in error_msg:
                    permission_errors.append((item.name, error_msg))

        # 如果有权限错误，询问用户是否以管理员身份重启
        if permission_errors:
            perm_error_names = [name for name, _ in permission_errors[:3]]
            if len(permission_errors) > 3:
                perm_error_names.append(f"等{len(permission_errors)}个")

            if self._handle_permission_error(f"以下启动项需要管理员权限才能删除：\n{', '.join(perm_error_names)}"):
                return  # 程序已重启

        # 构建结果消息
        if failed_items:
            failed_msg = "\n\n删除失败的启动项：\n"
            for name, error in failed_items[:5]:  # 最多显示5个
                failed_msg += f"• {name}: {error}\n"
            if len(failed_items) > 5:
                failed_msg += f"... 还有 {len(failed_items) - 5} 个失败项\n"

            messagebox.showwarning(
                "删除完成",
                f"成功删除 {success_count}/{len(items_to_delete)} 个启动项！{failed_msg}"
            )
        else:
            messagebox.showinfo(
                "删除完成",
                f"成功删除 {success_count}/{len(items_to_delete)} 个启动项！"
            )

        # 重新扫描以更新状态
        self.start_scan()

    def set_delayed_startup(self):
        """设置延时启动"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择要设置延时启动的启动项！")
            return

        # 只支持单个项目
        if len(selected) > 1:
            messagebox.showwarning("提示", "延时启动只能对单个启动项进行设置！")
            return

        index = self.tree.index(selected[0])
        if index >= len(self.startup_items):
            return

        item = self.startup_items[index]

        # 检查是否已禁用或无效
        if not item.is_enabled or not item.is_valid:
            messagebox.showwarning(
                "提示",
                "只能对已启用的有效启动项设置延时启动！\n"
                "请先启用该启动项。"
            )
            return

        # 检查是否已经是计划任务类型的启动项
        if item.item_type == 'task':
            messagebox.showwarning(
                "提示",
                "该启动项已经是计划任务类型，不支持延时启动设置。"
            )
            return

        # 创建延时选择对话框
        delay_window = tk.Toplevel(self)
        delay_window.title("设置延时启动")
        delay_window.geometry("480x500")
        delay_window.transient(self)
        delay_window.grab_set()
        delay_window.resizable(False, False)

        # 居中显示（相对于主窗口）
        self.update_idletasks()
        delay_window.update_idletasks()

        # 获取主窗口位置和大小
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_width = self.winfo_width()
        main_height = self.winfo_height()

        # 计算居中位置
        x = main_x + (main_width // 2) - 240
        y = main_y + (main_height // 2) - 250

        delay_window.geometry(f"480x500+{x}+{y}")

        # 标题
        tk.Label(
            delay_window,
            text="⏱️ 设置延时启动",
            font=('Microsoft YaHei UI', 14, 'bold'),
            fg='#2196F3'
        ).pack(pady=(20, 10))

        # 启动项名称
        tk.Label(
            delay_window,
            text=f"启动项: {item.name}",
            font=('Microsoft YaHei UI', 10),
            wraplength=350
        ).pack(pady=5)

        tk.Label(
            delay_window,
            text="选择延迟时间：",
            font=('Microsoft YaHei UI', 10, 'bold')
        ).pack(pady=(20, 10))

        # 延时时间选项
        delay_var = tk.IntVar(value=60)

        delay_options_frame = tk.Frame(delay_window)
        delay_options_frame.pack(pady=10)

        delay_options = [
            (30, "30秒 (推荐用于即时通讯软件)"),
            (60, "1分钟 (推荐用于浏览器)"),
            (120, "2分钟 (推荐用于办公软件)"),
            (180, "3分钟 (推荐用于媒体软件)"),
            (300, "5分钟 (推荐用于不常用工具)"),
        ]

        for i, (value, text) in enumerate(delay_options):
            rb = tk.Radiobutton(
                delay_options_frame,
                text=text,
                variable=delay_var,
                value=value,
                font=('Microsoft YaHei UI', 9),
                wraplength=350,
                justify='left',
                anchor='w'
            )
            rb.pack(fill='x', pady=2, padx=20)

        # 说明文字
        tk.Label(
            delay_window,
            text="💡 延迟启动后，该程序会在登录后指定时间再启动，\n不会影响开机速度。",
            font=('Microsoft YaHei UI', 9),
            fg='#666',
            justify='center'
        ).pack(pady=(15, 10))

        # 按钮区域
        btn_frame = tk.Frame(delay_window)
        btn_frame.pack(pady=10)

        def confirm():
            delay_seconds = delay_var.get()
            delay_window.destroy()

            # 执行延时启动设置
            if self.manager.set_delayed_startup(item, delay_seconds):
                result = messagebox.askyesno(
                    "设置成功",
                    f"已成功创建延迟启动任务！\n\n"
                    f"启动项: {item.name}\n"
                    f"延迟时间: {delay_seconds} 秒\n\n"
                    f"⚠️ 重要：还需要禁用原启动项，否则程序会启动两次！\n\n"
                    f"是否现在禁用原启动项？"
                )
                if result:
                    # 用户选择禁用原启动项
                    if self.manager.disable_startup_item(item):
                        messagebox.showinfo(
                            "完成",
                            f"✓ 已创建延迟启动任务\n"
                            f"✓ 已禁用原启动项\n\n"
                            f"下次登录时生效。"
                        )
                    else:
                        # 检查是否是权限错误
                        if "权限不足" in item.error_message or "拒绝访问" in item.error_message:
                            if self._handle_permission_error(f"禁用原启动项需要管理员权限：\n{item.name}"):
                                return
                        messagebox.showwarning(
                            "部分成功",
                            f"✓ 已创建延迟启动任务\n"
                            f"✗ 禁用原启动项失败（可能需要管理员权限）\n\n"
                            f"请手动禁用原启动项，否则程序会启动两次！"
                        )
                # 重新扫描
                self.start_scan()
            else:
                # 检查是否是权限错误
                if "权限不足" in item.error_message or "拒绝访问" in item.error_message:
                    if self._handle_permission_error(f"创建延迟启动任务需要管理员权限：\n{item.name}"):
                        return

                messagebox.showerror(
                    "设置失败",
                    f"设置延迟启动失败！\n\n"
                    f"错误: {item.error_message}\n\n"
                    f"可能的原因：\n"
                    f"• 权限不足（系统级启动项需要管理员权限）\n"
                    f"• 任务计划程序服务未运行\n"
                    f"• 命令格式不支持"
                )

        def cancel():
            delay_window.destroy()

        tk.Button(
            btn_frame,
            text="确定",
            command=confirm,
            bg='#4CAF50',
            fg='white',
            font=('Microsoft YaHei UI', 10, 'bold'),
            relief='flat',
            cursor='hand2',
            width=10
        ).pack(side='left', padx=5)

        tk.Button(
            btn_frame,
            text="取消",
            command=cancel,
            bg='#9E9E9E',
            fg='white',
            font=('Microsoft YaHei UI', 10, 'bold'),
            relief='flat',
            cursor='hand2',
            width=10
        ).pack(side='left', padx=5)

    def _handle_permission_error(self, error_msg: str = None) -> bool:
        """处理权限错误，询问用户是否以管理员身份重启

        Args:
            error_msg: 具体的错误消息

        Returns:
            True 如果用户选择以管理员身份重启（此时程序会退出）
            False 如果用户取消
        """
        msg = "权限不足：此操作需要管理员权限。\n\n"

        if error_msg:
            msg += f"错误详情：{error_msg}\n\n"

        msg += "是否以管理员身份重新运行程序？"

        result = messagebox.askyesno(
            "需要管理员权限",
            msg,
            icon='question'
        )

        if result:
            # 用户同意以管理员身份重启
            if run_as_admin():
                # 成功请求管理员权限，退出当前程序
                self.quit()
                return True
            else:
                messagebox.showerror(
                    "失败",
                    "无法请求管理员权限。\n\n"
                    "请手动右键程序，选择\"以管理员身份运行\"。"
                )
                return False
        return False

    def smart_optimize(self):
        """智能优化"""
        # 自动禁用评分低于40的启动项
        low_score_items = [item for item in self.startup_items
                          if item.score < 40 and item.is_enabled and item.is_valid]

        if not low_score_items:
            messagebox.showinfo("智能优化", "没有需要优化的启动项！")
            return

        # 确认对话框
        result = messagebox.askyesno(
            "智能优化",
            f"发现 {len(low_score_items)} 个可优化的启动项（评分<40分）\n\n"
            "是否一键禁用这些启动项？\n\n"
            "这些启动项通常是：\n"
            "• 更新服务\n"
            "• 非必要的软件助手\n"
            "• 很少使用的工具",
            icon='question'
        )

        if result:
            # 执行禁用操作
            success_count = 0
            permission_errors = []

            for item in low_score_items:
                if self.manager.disable_startup_item(item):
                    success_count += 1
                else:
                    # 检查是否是权限错误
                    if "权限不足" in item.error_message or "拒绝访问" in item.error_message:
                        permission_errors.append((item.name, item.error_message))

            # 如果有权限错误，询问用户是否以管理员身份重启
            if permission_errors:
                perm_error_names = [name for name, _ in permission_errors[:3]]
                if len(permission_errors) > 3:
                    perm_error_names.append(f"等{len(permission_errors)}个")

                if self._handle_permission_error(f"以下启动项需要管理员权限才能禁用：\n{', '.join(perm_error_names)}"):
                    return  # 程序已重启

            messagebox.showinfo(
                "优化完成",
                f"成功禁用 {success_count}/{len(low_score_items)} 个启动项！\n\n"
                f"建议重启电脑以查看效果。"
            )

            # 重新扫描
            self.start_scan()
