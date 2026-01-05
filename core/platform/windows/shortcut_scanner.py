"""
Windows 平台快捷方式扫描模块
"""
import os
import sys
import string
import threading
from typing import List, Callable

# 添加项目根目录到路径，以便导入 ShortcutInfo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


class WindowsShortcutScanner:
    """Windows 快捷方式扫描器"""

    def __init__(self):
        self.running = True
        self.scanned_files_count = 0
        self.total_files_estimate = 0

        # 回调函数
        self.progress_callback: Callable[[int, int, str], None] = None
        self.found_callback: Callable = None
        self.finished_callback: Callable = None

    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """设置进度回调"""
        self.progress_callback = callback

    def set_found_callback(self, callback: Callable):
        """设置发现快捷方式回调"""
        self.found_callback = callback

    def set_finished_callback(self, callback: Callable):
        """设置完成回调"""
        self.finished_callback = callback

    def scan(self):
        """执行扫描任务"""
        try:
            # 导入 ShortcutInfo（延迟导入避免循环依赖）
            from core.shortcut_scanner import ShortcutInfo

            # 先估算总文件数
            self.total_files_estimate = self.estimate_total_files()

            # 重置计数器
            self.scanned_files_count = 0

            # 扫描开始
            self._emit_progress(0, 100, "正在初始化扫描...")
            self.scan_start_menu()

            if not self.running:
                return

            self._emit_progress(0, 100, "正在扫描应用程序...")
            self.scan_applications()

            if not self.running:
                return

            self._emit_progress(0, 100, "正在扫描文档...")
            self.scan_documents()

            # 扫描完成
            if self.running and self.finished_callback:
                self.finished_callback()

        except Exception as e:
            print(f"Windows 快捷方式扫描出错: {e}")

    def _emit_progress(self, current: int, total: int, text: str):
        """发送进度信号"""
        if self.progress_callback:
            try:
                self.progress_callback(current, total, text)
            except Exception as e:
                print(f"进度回调失败: {e}")

    def _emit_found(self, shortcut):
        """发送发现快捷方式信号"""
        if self.found_callback:
            try:
                self.found_callback(shortcut)
            except Exception as e:
                print(f"发现回调失败: {e}")

    def estimate_total_files(self) -> int:
        """估算总文件数量"""
        estimate = 0

        # 估算开始菜单文件
        start_menu_dirs = self.get_start_menu_dirs()
        estimate += self.estimate_dir_files(start_menu_dirs)

        # 估算应用程序目录文件
        app_dirs = self.get_application_dirs()
        estimate += self.estimate_dir_files(app_dirs)

        # 估算文档目录文件
        doc_dirs = self.get_document_dirs()
        estimate += self.estimate_dir_files(doc_dirs)

        return max(estimate, 100)

    def estimate_dir_files(self, directories: List[str]) -> int:
        """估算目录中的文件数量"""
        total = 0
        for directory in directories:
            if os.path.exists(directory):
                try:
                    for root, dirs, files in os.walk(directory):
                        lnk_count = sum(1 for f in files if f.lower().endswith('.lnk'))
                        total += lnk_count

                        level = root[len(directory):].count(os.sep)
                        if level >= 2:
                            dirs[:] = []
                            total += lnk_count * 3
                            break
                except Exception:
                    total += 200
        return max(total, 200)

    def get_start_menu_dirs(self) -> List[str]:
        """获取开始菜单目录"""
        directories = []
        user_start_menu = os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu')
        common_start_menu = os.path.expandvars(r'%PROGRAMDATA%\Microsoft\Windows\Start Menu')

        for path in [user_start_menu, common_start_menu]:
            if os.path.exists(path):
                directories.append(path)

        return directories

    def get_application_dirs(self) -> List[str]:
        """获取应用程序目录"""
        directories = []

        for drive in string.ascii_uppercase:
            drive_path = f"{drive}:\\"
            if os.path.exists(drive_path):
                common_app_dirs = [
                    "Program Files",
                    "Program Files (x86)",
                    "Windows",
                    "Users",
                    "Programs",
                ]

                for app_dir in common_app_dirs:
                    full_path = os.path.join(drive_path, app_dir)
                    if os.path.exists(full_path):
                        directories.append(full_path)

        return directories

    def get_document_dirs(self) -> List[str]:
        """获取文档目录"""
        directories = []

        for drive in string.ascii_uppercase:
            drive_path = f"{drive}:\\"
            if os.path.exists(drive_path):
                common_doc_dirs = ["Users", "Documents", "Desktop", "Downloads"]

                for doc_dir in common_doc_dirs:
                    full_path = os.path.join(drive_path, doc_dir)
                    if os.path.exists(full_path):
                        directories.append(full_path)

        user_dirs = [
            os.path.expandvars(r'%USERPROFILE%\Documents'),
            os.path.expandvars(r'%USERPROFILE%\Desktop'),
            os.path.expandvars(r'%USERPROFILE%\Downloads'),
        ]

        for user_dir in user_dirs:
            if os.path.exists(user_dir):
                directories.append(user_dir)

        return directories

    def is_system_shortcut(self, lnk_path: str) -> bool:
        """检查是否为系统快捷方式"""
        try:
            lnk_path_lower = lnk_path.lower()

            system_dirs = [
                r"c:\windows",
                r"c:\windows\system32",
                r"c:\programdata\microsoft\windows",
            ]

            for sys_dir in system_dirs:
                if sys_dir and lnk_path_lower.startswith(sys_dir):
                    return True

            return False

        except Exception:
            return True

    def scan_start_menu(self):
        """扫描开始菜单快捷方式"""
        from core.shortcut_scanner import ShortcutInfo
        directories = self.get_start_menu_dirs()
        self.scan_directories(directories, "start_menu", "开始菜单")

    def scan_applications(self):
        """扫描应用程序快捷方式"""
        from core.shortcut_scanner import ShortcutInfo
        directories = self.get_application_dirs()
        self.scan_directories(directories, "application", "应用程序")

    def scan_documents(self):
        """扫描文档快捷方式"""
        from core.shortcut_scanner import ShortcutInfo
        directories = self.get_document_dirs()
        self.scan_directories(directories, "document", "文档")

    def scan_directories(self, directories: List[str], shortcut_type: str, location_name: str):
        """扫描指定目录中的快捷方式"""
        from core.shortcut_scanner import ShortcutInfo

        for directory in directories:
            if not self.running:
                break

            if os.path.exists(directory):
                try:
                    for root, dirs, files in os.walk(directory):
                        if not self.running:
                            break

                        for file in files:
                            if not self.running:
                                break

                            if file.lower().endswith('.lnk'):
                                lnk_path = os.path.join(root, file)

                                if self.is_system_shortcut(lnk_path):
                                    continue

                                self.process_shortcut(lnk_path, shortcut_type)

                                self.scanned_files_count += 1
                                progress = int((self.scanned_files_count / self.total_files_estimate) * 100)
                                progress = min(progress, 99)

                                self._emit_progress(progress, 100, f"正在扫描{location_name}: {os.path.basename(lnk_path)}")

                except Exception as e:
                    print(f"扫描目录 {directory} 出错: {e}")

    def process_shortcut(self, lnk_path: str, shortcut_type: str):
        """处理单个快捷方式"""
        from core.shortcut_scanner import ShortcutInfo

        try:
            display_name = os.path.basename(lnk_path)

            try:
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                link = shell.CreateShortCut(lnk_path)

                if hasattr(link, 'Description'):
                    description = link.Description or ""
                    if description and description.strip():
                        display_name = description

                target_path = link.TargetPath if hasattr(link, 'TargetPath') else ""
                working_dir = link.WorkingDirectory if hasattr(link, 'WorkingDirectory') else ""

            except Exception as e:
                print(f"解析快捷方式失败 {lnk_path}: {e}")
                shortcut = ShortcutInfo(
                    name=os.path.basename(lnk_path),
                    path=lnk_path,
                    target_path="",
                    is_valid=False,
                    error_message=f"解析失败: {str(e)[:100]}",
                    shortcut_type=shortcut_type,
                    display_name=display_name
                )
                self._emit_found(shortcut)
                return

            is_valid = False
            error_message = ""
            actual_target_path = target_path

            if target_path:
                if target_path.startswith(('http://', 'https://', 'ftp://', 'mailto:', 'shell:', 'appx:', 'ms-')):
                    is_valid = True
                elif os.path.exists(target_path):
                    is_valid = True
                else:
                    expanded_path = os.path.expandvars(target_path)
                    if expanded_path != target_path and os.path.exists(expanded_path):
                        is_valid = True
                        actual_target_path = expanded_path
                    elif working_dir and not os.path.isabs(target_path):
                        full_path = os.path.join(working_dir, target_path)
                        if os.path.exists(full_path):
                            is_valid = True
                            actual_target_path = full_path
                    else:
                        error_message = "目标文件不存在"
            else:
                error_message = "目标路径为空"

            shortcut = ShortcutInfo(
                name=os.path.basename(lnk_path),
                path=lnk_path,
                target_path=actual_target_path,
                is_valid=is_valid,
                error_message=error_message,
                shortcut_type=shortcut_type,
                display_name=display_name
            )

            if not is_valid:
                self._emit_found(shortcut)

        except Exception as e:
            print(f"处理快捷方式 {lnk_path} 出错: {e}")

    def stop(self):
        """停止扫描"""
        self.running = False
