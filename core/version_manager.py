"""
版本管理模块
负责检查更新、下载新版本
"""
import os
import sys
import json
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import messagebox, ttk
from threading import Thread
import subprocess


class VersionManager:
    """版本管理器"""

    # 当前版本号
    CURRENT_VERSION = "1.1.2"

    # GitHub Releases API 地址
    VERSION_INFO_URL = "https://api.github.com/repos/ZenoLeee/z-tools/releases/latest"

    # GitHub 用户名和仓库名
    GITHUB_OWNER = "ZenoLeee"
    GITHUB_REPO = "z-tools"

    def __init__(self, parent_window=None):
        """
        初始化版本管理器

        Args:
            parent_window: 父窗口，用于显示对话框
        """
        self.parent_window = parent_window
        self.latest_version = None
        self.download_url = None
        self.changelog = None

    def get_current_version(self):
        """获取当前版本号"""
        return self.CURRENT_VERSION

    def check_for_updates(self, show_message_if_no_update=False):
        """
        检查更新

        Args:
            show_message_if_no_update: 如果没有更新是否显示提示

        Returns:
            tuple: (has_update, latest_version, changelog)
        """
        try:
            # 获取版本信息
            version_info = self._fetch_version_info()

            if not version_info:
                if show_message_if_no_update and self.parent_window:
                    messagebox.showwarning("检查更新", "无法获取版本信息，请检查网络连接")
                return (False, self.CURRENT_VERSION, "")

            # 解析版本信息
            self.latest_version = version_info.get('version', self.CURRENT_VERSION)
            self.download_url = version_info.get('download_url', '')
            self.changelog = version_info.get('changelog', '')

            # 比较版本
            if self._compare_versions(self.latest_version, self.CURRENT_VERSION) > 0:
                # 有新版本
                return (True, self.latest_version, self.changelog)
            else:
                # 没有更新
                if show_message_if_no_update and self.parent_window:
                    messagebox.showinfo("检查更新", f"当前已是最新版本：{self.CURRENT_VERSION}")
                return (False, self.latest_version, self.changelog)

        except Exception as e:
            if show_message_if_no_update and self.parent_window:
                messagebox.showerror("检查更新", f"检查更新时出错：{str(e)}")
            return (False, self.CURRENT_VERSION, "")

    def _fetch_version_info(self):
        """从远程获取版本信息"""
        try:
            # 创建请求
            request = urllib.request.Request(
                self.VERSION_INFO_URL,
                headers={'User-Agent': 'WindowsToolbox'}  # GitHub API 需要 User-Agent
            )

            # 超时设置
            with urllib.request.urlopen(request, timeout=10) as response:
                data = response.read().decode('utf-8')
                release_data = json.loads(data)

                # 从 GitHub Releases API 响应中提取信息
                # tag_name 格式通常是 "v1.0.0"，需要去掉 "v" 前缀
                tag_name = release_data.get('tag_name', '')
                version = tag_name.lstrip('v') if tag_name else '0.0.0'

                # 获取更新日志（body 字段）
                changelog = release_data.get('body', '暂无更新日志')

                download_url = ''
                assets = release_data.get('assets', [])
                for asset in assets:
                    asset_name = asset.get('name', '')
                    # 匹配 z-tools_v1.0.0.exe 或其他 z-tools 开头的 exe 文件
                    if asset_name.startswith('z-tools') and asset_name.endswith('.exe'):
                        download_url = asset.get('browser_download_url', '')
                        break

                # 如果没有找到 exe 文件，使用备用下载地址
                if not download_url and version:
                    download_url = f"https://github.com/{self.GITHUB_OWNER}/{self.GITHUB_REPO}/releases/download/v{version}/z-tools_v{version}.exe"

                return {
                    'version': version,
                    'download_url': download_url,
                    'changelog': changelog
                }

        except urllib.error.HTTPError as e:
            if e.code == 404:
                print("未找到 Release，请确保已发布第一个版本")
            else:
                print(f"HTTP 错误：{e.code}")
            return None
        except urllib.error.URLError as e:
            print(f"网络错误：{e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON解析错误：{e}")
            return None
        except Exception as e:
            print(f"获取版本信息失败：{e}")
            return None

    def _compare_versions(self, version1, version2):
        """
        比较两个版本号

        Args:
            version1: 版本号1（如 "1.2.3"）
            version2: 版本号2（如 "1.2.4"）

        Returns:
            int: 1表示version1较新，-1表示version2较新，0表示相同
        """
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]

        # 补齐长度
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))

        for v1, v2 in zip(v1_parts, v2_parts):
            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1

        return 0

    def download_and_update(self, progress_callback=None):
        """
        下载并更新程序

        Args:
            progress_callback: 进度回调函数，参数为(percent, status)

        Returns:
            bool: 是否成功
        """
        if not self.download_url:
            if self.parent_window:
                messagebox.showerror("更新失败", "未找到下载地址")
            return False

        try:
            # 下载文件到程序所在目录
            if getattr(sys, 'frozen', False):
                # 打包后的exe，下载到exe所在目录
                app_dir = os.path.dirname(sys.executable)
            else:
                # 开发环境，下载到当前目录
                app_dir = os.getcwd()

            # 使用版本号命名新文件
            new_filename = f"z-tools_v{self.latest_version}.exe"
            temp_file = os.path.join(app_dir, new_filename)

            if progress_callback:
                progress_callback(0, "正在连接服务器...")

            # 下载文件
            def download_thread():
                try:
                    request = urllib.request.Request(
                        self.download_url,
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )

                    with urllib.request.urlopen(request, timeout=30) as response:
                        total_size = int(response.headers.get('content-length', 0))
                        downloaded = 0
                        chunk_size = 8192

                        with open(temp_file, 'wb') as f:
                            while True:
                                chunk = response.read(chunk_size)
                                if not chunk:
                                    break
                                f.write(chunk)
                                downloaded += len(chunk)

                                if progress_callback and total_size > 0:
                                    percent = int(downloaded * 100 / total_size)
                                    progress_callback(percent, f"下载中... {percent}%")

                    if progress_callback:
                        progress_callback(100, "下载完成！")

                    # 获取当前程序路径
                    if getattr(sys, 'frozen', False):
                        # 打包后的exe路径
                        current_exe = sys.executable
                    else:
                        # 开发环境，不支持自动更新
                        if self.parent_window:
                            messagebox.showinfo("提示", f"新版本已下载到：\n{temp_file}\n\n请手动运行新版本")
                        if progress_callback:
                            progress_callback(100, "下载完成")
                        return

                    if progress_callback:
                        progress_callback(100, "正在启动新版本...")

                    # 通知用户下载完成
                    if self.parent_window:
                        result = messagebox.askyesno(
                            "下载完成",
                            f"新版本已下载到：\n{temp_file}\n\n是否立即启动新版本？"
                        )

                        if result:
                            # 启动新版本
                            subprocess.Popen(temp_file, shell=True)
                            # 关闭当前程序
                            self.parent_window.destroy()
                        else:
                            # 用户选择稍后手动启动
                            if progress_callback:
                                progress_callback(100, "您可以稍后手动运行新版本")

                except Exception as e:
                    if progress_callback:
                        progress_callback(0, f"下载失败：{str(e)}")
                    if self.parent_window:
                        messagebox.showerror("更新失败", f"下载失败：{str(e)}")

            # 在后台线程下载
            thread = Thread(target=download_thread, daemon=True)
            thread.start()

            return True

        except Exception as e:
            if self.parent_window:
                messagebox.showerror("更新失败", f"更新失败：{str(e)}")
            return False


class UpdateDialog:
    """更新对话框"""

    def __init__(self, parent, version_manager, has_update, latest_version, changelog):
        """
        初始化更新对话框

        Args:
            parent: 父窗口
            version_manager: 版本管理器实例
            has_update: 是否有更新
            latest_version: 最新版本号
            changelog: 更新日志
        """
        self.version_manager = version_manager
        self.has_update = has_update
        self.latest_version = latest_version
        self.changelog = changelog

        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("版本更新")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)

        # 设置为模态对话框
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_ui()

        # 居中显示
        self._center_window()

    def _create_ui(self):
        """创建UI"""
        # 标题
        title_frame = tk.Frame(self.dialog, bg='#4A90E2', height=80)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        if self.has_update:
            title_text = "发现新版本！"
            subtitle_text = f"当前版本：{self.version_manager.CURRENT_VERSION} → 最新版本：{self.latest_version}"
        else:
            title_text = "当前已是最新版本"
            subtitle_text = f"版本号：{self.latest_version}"

        title_label = tk.Label(
            title_frame,
            text=title_text,
            font=('Microsoft YaHei UI', 16, 'bold'),
            bg='#4A90E2',
            fg='white'
        )
        title_label.pack(pady=(15, 5))

        subtitle_label = tk.Label(
            title_frame,
            text=subtitle_text,
            font=('Microsoft YaHei UI', 10),
            bg='#4A90E2',
            fg='white'
        )
        subtitle_label.pack()

        # 内容区域
        content_frame = tk.Frame(self.dialog, padx=20, pady=20)
        content_frame.pack(fill='both', expand=True)

        # 更新日志标题
        tk.Label(
            content_frame,
            text="更新日志：",
            font=('Microsoft YaHei UI', 11, 'bold'),
            anchor='w'
        ).pack(fill='x', pady=(0, 10))

        # 更新日志内容
        changelog_text = tk.Text(
            content_frame,
            height=12,
            font=('Microsoft YaHei UI', 10),
            wrap='word',
            relief='flat',
            bg='#f5f5f5'
        )
        changelog_text.pack(fill='both', expand=True)

        # 添加滚动条
        scrollbar = tk.Scrollbar(changelog_text)
        scrollbar.pack(side='right', fill='y')
        changelog_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=changelog_text.yview)

        # 插入更新日志
        if self.changelog:
            changelog_text.insert('1.0', self.changelog)
        else:
            changelog_text.insert('1.0', "暂无更新日志")

        changelog_text.config(state='disabled')

        # 按钮区域
        button_frame = tk.Frame(self.dialog, pady=20)
        button_frame.pack(fill='x')

        if self.has_update:
            # 更新按钮
            update_btn = tk.Button(
                button_frame,
                text="立即更新",
                command=self._on_update_click,
                bg='#4A90E2',
                fg='white',
                font=('Microsoft YaHei UI', 11, 'bold'),
                relief='flat',
                cursor='hand2',
                padx=30,
                pady=10
            )
            update_btn.pack(side='left', padx=(20, 10))

            # 稍后提醒按钮
            later_btn = tk.Button(
                button_frame,
                text="稍后提醒",
                command=self.dialog.destroy,
                bg='#95A5A6',
                fg='white',
                font=('Microsoft YaHei UI', 10),
                relief='flat',
                cursor='hand2',
                padx=20,
                pady=10
            )
            later_btn.pack(side='left', padx=10)
        else:
            # 关闭按钮
            close_btn = tk.Button(
                button_frame,
                text="关闭",
                command=self.dialog.destroy,
                bg='#4A90E2',
                fg='white',
                font=('Microsoft YaHei UI', 10),
                relief='flat',
                cursor='hand2',
                padx=30,
                pady=10
            )
            close_btn.pack()

    def _center_window(self):
        """窗口居中"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')

    def _on_update_click(self):
        """更新按钮点击事件"""
        # 显示进度窗口
        progress_window = tk.Toplevel(self.dialog)
        progress_window.title("正在更新")
        progress_window.geometry("400x150")
        progress_window.resizable(False, False)

        # 进度标签
        status_label = tk.Label(
            progress_window,
            text="准备下载...",
            font=('Microsoft YaHei UI', 10)
        )
        status_label.pack(pady=20)

        # 进度条
        progress_bar = ttk.Progressbar(
            progress_window,
            length=350,
            mode='determinate'
        )
        progress_bar.pack(pady=10)

        # 提示标签
        tip_label = tk.Label(
            progress_window,
            text="更新过程中请勿关闭程序",
            font=('Microsoft YaHei UI', 9),
            fg='#7F8C8D'
        )
        tip_label.pack(pady=10)

        # 进度回调函数
        def progress_callback(percent, status):
            status_label.config(text=status)
            progress_bar['value'] = percent
            progress_window.update()

        # 开始下载
        self.version_manager.download_and_update(progress_callback)
