import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from core.network_tools import PingThread


class NetworkToolsTab(tk.Frame):
    """网络工具标签页"""

    def __init__(self, parent):
        super().__init__(parent)
        self.ping_thread = None
        self.init_ui()

    def init_ui(self):
        # 创建主容器
        main_container = tk.Frame(self, bg='#F5F7FA')
        main_container.pack(expand=True, fill='both', padx=10, pady=10)

        # 顶部控制区域 - Ping测试
        ping_frame = tk.LabelFrame(
            main_container,
            text=" 网络连接测试 ",
            bg='#F5F7FA',
            font=('Microsoft YaHei UI', 11, 'bold'),
            fg='#333333',
            padx=15, pady=15
        )
        ping_frame.pack(fill='x', pady=(0, 10))

        # IP地址输入行
        input_row = tk.Frame(ping_frame, bg='#F5F7FA')
        input_row.pack(fill='x', pady=(0, 10))

        tk.Label(
            input_row, text="目标地址:",
            bg='#F5F7FA', font=('Microsoft YaHei UI', 10)
        ).pack(side='left', padx=(0, 8))

        self.ip_edit = tk.Entry(
            input_row, font=('Microsoft YaHei UI', 10),
            relief='solid', borderwidth=1
        )
        self.ip_edit.insert(0, "8.8.8.8")
        self.ip_edit.pack(side='left', fill='x', expand=True, padx=(0, 10))

        tk.Label(
            input_row, text="次数:",
            bg='#F5F7FA', font=('Microsoft YaHei UI', 10)
        ).pack(side='left', padx=(0, 8))

        self.ping_count_combo = ttk.Combobox(
            input_row, values=["1", "4", "8", "16"],
            width=5, state='readonly', font=('Microsoft YaHei UI', 9)
        )
        self.ping_count_combo.current(1)
        self.ping_count_combo.pack(side='left')

        # 快速测试按钮
        quick_test_row = tk.Frame(ping_frame, bg='#F5F7FA')
        quick_test_row.pack(fill='x', pady=(0, 10))

        tk.Label(
            quick_test_row, text="快速测试:",
            bg='#F5F7FA', font=('Microsoft YaHei UI', 10)
        ).pack(side='left', padx=(0, 10))

        quick_buttons = [
            ("🏠 本地", "127.0.0.1"),
            ("🌐 谷歌DNS", "8.8.8.8"),
            ("🔍 百度", "www.baidu.com"),
            ("🐧 腾讯", "www.qq.com"),
            ("📡 网关", "192.168.1.1")
        ]

        for name, ip in quick_buttons:
            btn = tk.Button(
                quick_test_row, text=name,
                command=lambda i=ip: self.set_ip_address(i),
                bg='#E3F2FD', fg='#1976D2',
                font=('Microsoft YaHei UI', 9),
                relief='flat', cursor='hand2',
                borderwidth=0, pady=5, padx=12
            )
            btn.pack(side='left', padx=3)

        # 操作按钮行
        action_row = tk.Frame(ping_frame, bg='#F5F7FA')
        action_row.pack(fill='x')

        self.ping_btn = tk.Button(
            action_row, text="🚀 开始Ping测试",
            command=self.start_ping,
            bg='#4CAF50', fg='white',
            font=('Microsoft YaHei UI', 10, 'bold'),
            relief='flat', cursor='hand2',
            borderwidth=0, pady=8, padx=20
        )
        self.ping_btn.pack(side='left', padx=(0, 10))

        self.stop_ping_btn = tk.Button(
            action_row, text="⏹ 停止",
            command=self.stop_ping,
            state='disabled',
            bg='#f44336', fg='white',
            font=('Microsoft YaHei UI', 10),
            relief='flat', cursor='hand2',
            borderwidth=0, pady=8, padx=15
        )
        self.stop_ping_btn.pack(side='left')

        # 网络诊断工具区域
        diag_frame = tk.LabelFrame(
            main_container,
            text=" 网络诊断工具 ",
            bg='#F5F7FA',
            font=('Microsoft YaHei UI', 11, 'bold'),
            fg='#333333',
            padx=15, pady=15
        )
        diag_frame.pack(fill='x', pady=(0, 10))

        # 工具按钮网格
        tools_grid = tk.Frame(diag_frame, bg='#F5F7FA')
        tools_grid.pack(fill='x')

        # 第一行工具按钮
        row1 = tk.Frame(tools_grid, bg='#F5F7FA')
        row1.pack(fill='x', pady=3)

        self.network_info_btn = tk.Button(
            row1, text="📊 网络连接信息",
            command=self.show_network_info,
            bg='#FFFFFF', fg='#333333',
            font=('Microsoft YaHei UI', 9),
            relief='solid', borderwidth=1, cursor='hand2',
            pady=6, padx=15
        )
        self.network_info_btn.pack(side='left', fill='x', expand=True, padx=3)

        self.flush_dns_btn = tk.Button(
            row1, text="🔄 刷新DNS缓存",
            command=self.flush_dns,
            bg='#FFFFFF', fg='#333333',
            font=('Microsoft YaHei UI', 9),
            relief='solid', borderwidth=1, cursor='hand2',
            pady=6, padx=15
        )
        self.flush_dns_btn.pack(side='left', fill='x', expand=True, padx=3)

        self.arp_cache_btn = tk.Button(
            row1, text="🔍 查看ARP缓存",
            command=self.show_arp_cache,
            bg='#FFFFFF', fg='#333333',
            font=('Microsoft YaHei UI', 9),
            relief='solid', borderwidth=1, cursor='hand2',
            pady=6, padx=15
        )
        self.arp_cache_btn.pack(side='left', fill='x', expand=True, padx=3)

        # 第二行工具按钮
        row2 = tk.Frame(tools_grid, bg='#F5F7FA')
        row2.pack(fill='x', pady=3)

        self.release_ip_btn = tk.Button(
            row2, text="⬇️ 释放IP地址",
            command=self.release_ip,
            bg='#FFFFFF', fg='#333333',
            font=('Microsoft YaHei UI', 9),
            relief='solid', borderwidth=1, cursor='hand2',
            pady=6, padx=15
        )
        self.release_ip_btn.pack(side='left', fill='x', expand=True, padx=3)

        self.renew_ip_btn = tk.Button(
            row2, text="⬆️ 续约IP地址",
            command=self.renew_ip,
            bg='#FFFFFF', fg='#333333',
            font=('Microsoft YaHei UI', 9),
            relief='solid', borderwidth=1, cursor='hand2',
            pady=6, padx=15
        )
        self.renew_ip_btn.pack(side='left', fill='x', expand=True, padx=3)

        self.route_table_btn = tk.Button(
            row2, text="📋 查看路由表",
            command=self.show_route_table,
            bg='#FFFFFF', fg='#333333',
            font=('Microsoft YaHei UI', 9),
            relief='solid', borderwidth=1, cursor='hand2',
            pady=6, padx=15
        )
        self.route_table_btn.pack(side='left', fill='x', expand=True, padx=3)

        # 输出区域
        output_container = tk.Frame(main_container, bg='#F5F7FA')
        output_container.pack(fill='both', expand=True, pady=(10, 0))

        # 输出控制按钮
        output_controls = tk.Frame(output_container, bg='#F5F7FA')
        output_controls.pack(fill='x', pady=(0, 8))

        self.clear_output_btn = tk.Button(
            output_controls, text="🗑️ 清空输出",
            command=self.clear_output,
            bg='#FF9800', fg='white',
            font=('Microsoft YaHei UI', 9),
            relief='flat', cursor='hand2',
            borderwidth=0, pady=5, padx=15
        )
        self.clear_output_btn.pack(side='left', padx=(0, 8))

        self.copy_output_btn = tk.Button(
            output_controls, text="📄 复制内容",
            command=self.copy_output,
            bg='#607D8B', fg='white',
            font=('Microsoft YaHei UI', 9),
            relief='flat', cursor='hand2',
            borderwidth=0, pady=5, padx=15
        )
        self.copy_output_btn.pack(side='left')

        # 输出文本框
        output_frame = tk.Frame(output_container, bg='white', relief='solid', borderwidth=1)
        output_frame.pack(fill='both', expand=True)

        self.output_text = tk.Text(
            output_frame,
            height=12,
            font=('Consolas', 9),
            wrap=tk.WORD,
            bg='#282C34',
            fg='#ABB2BF',
            insertbackground='white',
            relief='flat',
            borderwidth=0
        )
        self.output_text.pack(side='left', fill='both', expand=True, padx=(5, 0), pady=5)

        # 添加滚动条
        output_scrollbar = tk.Scrollbar(output_frame, command=self.output_text.yview)
        output_scrollbar.pack(side='right', fill='y', pady=5, padx=(0, 5))
        self.output_text.config(yscrollcommand=output_scrollbar.set)

    def set_ip_address(self, ip: str):
        """设置IP地址到输入框"""
        self.ip_edit.delete(0, tk.END)
        self.ip_edit.insert(0, ip)

    def start_ping(self):
        """开始Ping测试"""
        ip = self.ip_edit.get().strip()
        if not ip:
            messagebox.showwarning("警告", "请输入IP地址或域名")
            return

        # 禁用按钮，启用停止按钮
        self.ping_btn.config(state='disabled')
        self.stop_ping_btn.config(state='normal')

        # 清空输出
        self.output_text.delete(1.0, tk.END)

        # 获取Ping次数
        count = int(self.ping_count_combo.get())

        # 创建并启动Ping线程
        self.ping_thread = PingThread(ip, count)
        self.ping_thread.set_output_callback(self.append_ping_output)
        self.ping_thread.set_finished_callback(self.on_ping_finished)
        self.ping_thread.start()

    def stop_ping(self):
        """停止Ping测试"""
        if self.ping_thread and self.ping_thread.is_alive():
            self.ping_thread.stop()
            self.append_ping_output("Ping测试已停止")

        self.ping_btn.config(state='normal')
        self.stop_ping_btn.config(state='disabled')

    def append_ping_output(self, text: str):
        """添加Ping输出到文本区域"""
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)

    def on_ping_finished(self, success: bool, summary: str):
        """Ping测试完成"""
        self.append_ping_output("=" * 50)
        self.append_ping_output(summary)

        # 恢复按钮状态
        self.ping_btn.config(state='normal')
        self.stop_ping_btn.config(state='disabled')

    def show_network_info(self):
        """显示网络连接信息"""
        try:
            result = subprocess.run(
                ["ipconfig", "/all"],
                capture_output=True,
                text=True,
                encoding='gbk'
            )
            self.output_text.delete(1.0, tk.END)
            self.append_ping_output("网络连接信息:\n" + "=" * 50 + "\n")
            self.append_ping_output(result.stdout)
        except Exception as e:
            self.output_text.delete(1.0, tk.END)
            self.append_ping_output(f"错误: {e}")

    def release_ip(self):
        """释放IP地址"""
        try:
            result = subprocess.run(
                ["ipconfig", "/release"],
                capture_output=True,
                text=True,
                encoding='gbk'
            )
            self.output_text.delete(1.0, tk.END)
            self.append_ping_output("IP地址释放结果:\n" + "=" * 50 + "\n")
            self.append_ping_output(result.stdout)
        except Exception as e:
            self.output_text.delete(1.0, tk.END)
            self.append_ping_output(f"错误: {e}")

    def renew_ip(self):
        """续约IP地址"""
        try:
            result = subprocess.run(
                ["ipconfig", "/renew"],
                capture_output=True,
                text=True,
                encoding='gbk'
            )
            self.output_text.delete(1.0, tk.END)
            self.append_ping_output("IP地址续约结果:\n" + "=" * 50 + "\n")
            self.append_ping_output(result.stdout)
        except Exception as e:
            self.output_text.delete(1.0, tk.END)
            self.append_ping_output(f"错误: {e}")

    def flush_dns(self):
        """刷新DNS缓存"""
        try:
            result = subprocess.run(
                ["ipconfig", "/flushdns"],
                capture_output=True,
                text=True,
                encoding='gbk'
            )
            self.output_text.delete(1.0, tk.END)
            self.append_ping_output("DNS缓存刷新结果:\n" + "=" * 50 + "\n")
            self.append_ping_output(result.stdout)
        except Exception as e:
            self.output_text.delete(1.0, tk.END)
            self.append_ping_output(f"错误: {e}")

    def show_arp_cache(self):
        """查看ARP缓存"""
        try:
            result = subprocess.run(
                ["arp", "-a"],
                capture_output=True,
                text=True,
                encoding='gbk'
            )
            self.output_text.delete(1.0, tk.END)
            self.append_ping_output("ARP缓存:\n" + "=" * 50 + "\n")
            self.append_ping_output(result.stdout)
        except Exception as e:
            self.output_text.delete(1.0, tk.END)
            self.append_ping_output(f"错误: {e}")

    def show_route_table(self):
        """查看路由表"""
        try:
            result = subprocess.run(
                ["route", "print"],
                capture_output=True,
                text=True,
                encoding='gbk'
            )
            self.output_text.delete(1.0, tk.END)
            self.append_ping_output("路由表:\n" + "=" * 50 + "\n")
            self.append_ping_output(result.stdout)
        except Exception as e:
            self.output_text.delete(1.0, tk.END)
            self.append_ping_output(f"错误: {e}")

    def clear_output(self):
        """清空输出区域"""
        self.output_text.delete(1.0, tk.END)

    def copy_output(self):
        """复制输出内容到剪贴板"""
        text = self.output_text.get(1.0, tk.END)
        if text.strip():
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("成功", "内容已复制到剪贴板")
