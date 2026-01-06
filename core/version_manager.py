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

# 导入日志工具
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.logger import get_logger


class VersionManager:
    """版本管理器"""

    # 当前版本号
    CURRENT_VERSION = "1.1.2"

    # GitHub Releases API 地址
    VERSION_INFO_URL = "https://api.github.com/repos/ZenoLeee/z-tools/releases/latest"

    # GitHub 用户名和仓库名
    GITHUB_OWNER = "ZenoLeee"
    GITHUB_REPO = "z-tools"

    # GitHub 加速镜像列表（按优先级排序）
    GITHUB_MIRRORS = [
        "https://ghfast.top/",  # ghproxy
        "https://gh-proxy.org/",  # gh-proxy 主节点
        "https://hk.gh-proxy.org/",  # 香港节点
        "https://cdn.gh-proxy.org/",  # CDN 节点
        "https://edgeone.gh-proxy.org/",  # EdgeOne 节点
        "",  # 官方地址
    ]

    def _get_proxy(self):
        """
        自动检测代理设置
        优先级：环境变量 > 系统代理设置
        """
        import os

        # 1. 检查环境变量
        proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        if proxy:
            self.logger.debug(f"使用环境变量代理: {proxy}")
            return proxy

        # 2. 检查 HTTPS 代理环境变量
        proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        if proxy:
            self.logger.debug(f"使用环境变量代理: {proxy}")
            return proxy
        return None

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
        self.logger = get_logger("version_manager")

    def get_current_version(self):
        """获取当前版本号"""
        return self.CURRENT_VERSION

    def check_for_updates(self, show_message_if_no_update=False):
        """
        检查更新

        Args:
            show_message_if_no_update: 如果没有更新是否显示提示

        Returns:
            tuple: (has_update, latest_version, changelog, force_update)
        """
        try:
            # 获取版本信息
            version_info = self._fetch_version_info()

            if not version_info:
                if show_message_if_no_update and self.parent_window:
                    messagebox.showwarning("检查更新", "无法获取版本信息，请检查网络连接")
                return (False, self.CURRENT_VERSION, "", False)

            # 解析版本信息
            self.latest_version = version_info.get('version', self.CURRENT_VERSION)
            self.download_url = version_info.get('download_url', '')
            self.changelog = version_info.get('changelog', '')
            min_version = version_info.get('min_version', None)
            force_update = version_info.get('force_update', False)

            # 判断是否需要强制更新（当前版本小于最小版本要求）
            need_force_update = False
            if min_version:
                if self._compare_versions(min_version, self.CURRENT_VERSION) > 0:
                    need_force_update = True

            # 如果配置了强制更新标记，也需要强制更新
            if force_update:
                need_force_update = True

            # 比较版本
            if self._compare_versions(self.latest_version, self.CURRENT_VERSION) > 0:
                # 有新版本
                return (True, self.latest_version, self.changelog, need_force_update)
            else:
                # 没有更新
                if show_message_if_no_update and self.parent_window:
                    messagebox.showinfo("检查更新", f"当前已是最新版本：{self.CURRENT_VERSION}")
                return (False, self.latest_version, self.changelog, False)

        except Exception as e:
            if show_message_if_no_update and self.parent_window:
                messagebox.showerror("检查更新", f"检查更新时出错：{str(e)}")
            return (False, self.CURRENT_VERSION, "", False)

    def _fetch_version_info(self):
        """从远程获取版本信息"""
        try:
            # 创建请求
            request = urllib.request.Request(
                self.VERSION_INFO_URL,
                headers={'User-Agent': 'z-tools'}  # GitHub API 需要 User-Agent
            )

            # 自动检测代理
            proxy = self._get_proxy()

            # 设置代理（如果检测到）
            if proxy:
                proxy_handler = urllib.request.ProxyHandler({'http': proxy, 'https': proxy})
                opener = urllib.request.build_opener(proxy_handler)
                response = opener.open(request, timeout=10)
            else:
                # 超时设置
                response = urllib.request.urlopen(request, timeout=10)

            data = response.read().decode('utf-8')
            release_data = json.loads(data)

            # 从 GitHub Releases API 响应中提取信息
            # tag_name 格式通常是 "v1.0.0"，需要去掉 "v" 前缀
            tag_name = release_data.get('tag_name', '')
            version = tag_name.lstrip('v') if tag_name else '0.0.0'

            # 获取更新日志（body 字段）
            changelog = release_data.get('body', '暂无更新日志')

            # 解析配置标记（支持两种格式）
            # 格式1: HTML 注释中 <!-- [config]...[/config] -->
            min_version = None
            force_update = False
            config_section = None
            config_start = -1
            config_end = -1

            # 先尝试从 HTML 注释中提取配置
            import re
            html_comment_pattern = r'<!--\s*\[config\].*?\[/config\]\s*-->'
            html_comment_match = re.search(html_comment_pattern, changelog, re.DOTALL)

            if html_comment_match:
                # 从 HTML 注释中提取配置内容（不包括 <!-- 和 -->）
                comment_content = html_comment_match.group(0)
                # 提取 [config]...[/config] 部分
                config_match = re.search(r'\[config\](.*?)\[/config\]', comment_content, re.DOTALL)
                if config_match:
                    config_section = config_match.group(1)

                # 从显示的 changelog 中完全移除 HTML 注释
                changelog = changelog[:html_comment_match.start()] + changelog[html_comment_match.end():]
                # 清理多余的空行
                changelog = re.sub(r'\n\s*\n', '\n\n', changelog).strip()
            else:
                # 直接在 changelog 中查找 [config] 标记
                config_start = changelog.find('[config]')
                if config_start != -1:
                    config_end = changelog.find('[/config]', config_start)
                    if config_end != -1:
                        config_end += len('[/config]')  # 包含结束标记
                        # 提取配置内容
                        config_section = changelog[config_start + 8:config_end - 10].strip()
                        # 从显示的 changelog 中移除配置部分
                        changelog = changelog[:config_start].strip() + changelog[config_end:].strip()
                        # 清理多余的空行
                        changelog = re.sub(r'\n\s*\n', '\n\n', changelog).strip()
                    else:
                        # 如果没有结束标记，取到文本末尾
                        config_section = changelog[config_start + 8:].strip()
                        changelog = changelog[:config_start].strip()

            # 如果找到配置，解析配置项
            if config_section:
                for line in config_section.split('\n'):
                    line = line.strip()
                    if line.startswith('min-version:'):
                        min_version = line.split(':', 1)[1].strip()
                    elif line.startswith('force-update:'):
                        value = line.split(':', 1)[1].strip().lower()
                        force_update = value in ['true', 'yes', '1']

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
                'changelog': changelog,
                'min_version': min_version,
                'force_update': force_update
            }

        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.logger.warning("未找到 Release，请确保已发布第一个版本")
            else:
                self.logger.error(f"HTTP 错误：{e.code}")
            return None
        except urllib.error.URLError as e:
            self.logger.error(f"网络错误：{e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析错误：{e}")
            return None
        except Exception as e:
            self.logger.error(f"获取版本信息失败：{e}")
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
                messagebox.showerror("更新失败", "未找到下载地址\n\n请确保GitHub Release已发布")
            return False

        self.logger.debug(f"下载URL: {self.download_url}")
        self.logger.debug(f"最新版本: {self.latest_version}")

        # 检测网络连接
        if progress_callback:
            progress_callback(0, "检测网络连接...")

        def test_connection():
            """测试是否能连接到 GitHub"""
            try:
                import socket
                socket.setdefaulttimeout(3)
                socket.gethostbyname("github.com")
                return True
            except:
                return False

        if not test_connection():
            if self.parent_window:
                result = messagebox.askyesno(
                    "网络连接失败",
                    f"无法连接到 GitHub 服务器，可能的原因：\n\n"
                    f"1. 网络未连接\n"
                    f"2. GitHub 访问受限\n\n"
                    f"最新版本：{self.latest_version}\n"
                    f"下载地址：\n{self.download_url}\n\n"
                    f"是否打开浏览器手动下载？"
                )
                if result:
                    import webbrowser
                    webbrowser.open(self.download_url)
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

            self.logger.debug(f"准备下载: {self.download_url}")
            self.logger.debug(f"保存到: {temp_file}")

            if progress_callback:
                progress_callback(0, "正在连接服务器...")

            # 下载文件
            def download_thread():
                try:
                    self.logger.debug("开始下载...")

                    # 尝试多个镜像源
                    download_success = False
                    last_error = None

                    for mirror in self.GITHUB_MIRRORS:
                        if mirror:
                            # 使用加速镜像
                            mirror_url = mirror + self.download_url
                            self.logger.debug(f"尝试镜像: {mirror}")
                            self.logger.debug(f"实际下载地址: {mirror_url}")
                        else:
                            # 使用官方地址
                            mirror_url = self.download_url
                            self.logger.info(f"使用官方地址: {mirror_url}")

                        try:
                            request = urllib.request.Request(
                                mirror_url,
                                headers={'User-Agent': 'Mozilla/5.0'}
                            )

                            # 自动检测代理
                            proxy = self._get_proxy()

                            # 设置代理（如果检测到）
                            if proxy:
                                self.logger.debug("检测到代理，将使用代理下载")
                                proxy_handler = urllib.request.ProxyHandler({'http': proxy, 'https': proxy})
                                opener = urllib.request.build_opener(proxy_handler)
                                urllib.request.install_opener(opener)

                            # 先尝试连接，获取响应头
                            if progress_callback:
                                progress_callback(5, "已连接，开始下载...")

                            with urllib.request.urlopen(request, timeout=10) as response:
                                self.logger.debug(f"连接成功，响应码: {response.status}")
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

                                # 下载成功
                                download_success = True
                                self.logger.info("下载成功")
                                break  # 跳出镜像循环

                        except Exception as e:
                            # 当前镜像失败，记录错误并尝试下一个
                            self.logger.warning(f"镜像失败: {str(e)}")
                            last_error = str(e)
                            continue  # 继续尝试下一个镜像

                    # 所有镜像都尝试完毕
                    if not download_success:
                        raise Exception(f"所有下载源都失败了\n最后一个错误: {last_error}")

                    if progress_callback:
                        progress_callback(100, "下载完成！")

                    if progress_callback:
                        progress_callback(100, "正在启动新版本...")

                    # 自动启动新版本并关闭当前程序
                    if self.parent_window:
                        messagebox.showinfo(
                            "更新完成",
                            f"新版本已下载到：\n{temp_file}\n\n正在启动新版本..."
                        )
                        # 启动新版本
                        subprocess.Popen(temp_file, shell=True)
                        # 关闭当前程序
                        self.parent_window.destroy()

                except Exception as e:
                    self.logger.error(f"下载异常: {type(e).__name__}: {str(e)}")
                    import traceback
                    self.logger.exception("")

                    # 如果是网络错误，提示手动下载
                    if "Connection" in str(e) or "Timeout" in str(e):
                        if self.parent_window:
                            result = messagebox.askyesno(
                                "下载失败",
                                f"自动下载失败，可能的原因：\n\n"
                                f"1. 网络连接超时\n"
                                f"2. GitHub 访问受限\n\n"
                                f"最新版本：{self.latest_version}\n\n"
                                f"是否打开浏览器手动下载？"
                            )
                            if result:
                                import webbrowser
                                webbrowser.open(self.download_url)
                    else:
                        if progress_callback:
                            progress_callback(0, f"下载失败：{str(e)}")
                        if self.parent_window:
                            messagebox.showerror("更新失败", f"下载失败：\n{str(e)}")

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

    def __init__(self, parent, version_manager, has_update, latest_version, changelog, force_update=False):
        """
        初始化更新对话框

        Args:
            parent: 父窗口
            version_manager: 版本管理器实例
            has_update: 是否有更新
            latest_version: 最新版本号
            changelog: 更新日志
            force_update: 是否强制更新
        """
        self.version_manager = version_manager
        self.has_update = has_update
        self.latest_version = latest_version
        self.changelog = changelog
        self.force_update = force_update

        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("版本更新")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)

        # 设置为模态对话框
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 如果是强制更新，禁用关闭按钮
        if self.force_update:
            self.dialog.protocol("WM_DELETE_WINDOW", self._on_force_close_attempt)

        self._create_ui()

        # 居中显示
        self._center_window()

    def _create_ui(self):
        """创建UI"""
        # 标题
        # 强制更新时使用红色背景，普通更新使用蓝色
        bg_color = '#E74C3C' if self.force_update else '#4A90E2'

        title_frame = tk.Frame(self.dialog, bg=bg_color, height=80)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        if self.has_update:
            if self.force_update:
                title_text = "⚠️ 强制更新"
                subtitle_text = f"当前版本：{self.version_manager.CURRENT_VERSION} → 最新版本：{self.latest_version}"
            else:
                title_text = "发现新版本！"
                subtitle_text = f"当前版本：{self.version_manager.CURRENT_VERSION} → 最新版本：{self.latest_version}"
        else:
            title_text = "当前已是最新版本"
            subtitle_text = f"版本号：{self.latest_version}"

        title_label = tk.Label(
            title_frame,
            text=title_text,
            font=('Microsoft YaHei UI', 16, 'bold'),
            bg=bg_color,
            fg='white'
        )
        title_label.pack(pady=(15, 5))

        subtitle_label = tk.Label(
            title_frame,
            text=subtitle_text,
            font=('Microsoft YaHei UI', 10),
            bg=bg_color,
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
            # 强制更新提示文本
            if self.force_update:
                warning_label = tk.Label(
                    content_frame,
                    text="⚠️ 此版本包含重要更新，必须更新后才能继续使用",
                    font=('Microsoft YaHei UI', 10, 'bold'),
                    fg='#E74C3C'
                )
                warning_label.pack(pady=(10, 0))

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

            # 如果不是强制更新，显示"稍后提醒"按钮
            if not self.force_update:
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

    def _on_force_close_attempt(self):
        """强制更新模式下尝试关闭窗口时的处理"""
        messagebox.showwarning(
            "强制更新",
            '此版本包含重要更新，必须更新后才能继续使用程序。\n\n请点击"立即更新"按钮完成更新。'
        )

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
