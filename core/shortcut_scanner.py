import os
import sys
import string
from typing import List
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot

class ShortcutInfo:
    """快捷方式信息类"""

    def __init__(self, name: str, path: str, target_path: str = "",
                 is_valid: bool = False, error_message: str = "",
                 shortcut_type: str = "unknown", display_name: str = ""):
        self.name = name  # 原始文件名
        self.display_name = display_name  # 显示的名称
        self.path = path
        self.target_path = target_path
        self.is_valid = is_valid
        self.error_message = error_message
        self.shortcut_type = shortcut_type


class UnifiedScannerThread(QThread):
    """统一扫描线程 - 同时扫描三种类型的快捷方式"""
    scan_progress = pyqtSignal(int, int, str)  # 当前进度，总数，当前扫描类型
    invalid_shortcut_found = pyqtSignal(object)  # 发现无效快捷方式
    scan_finished = pyqtSignal()  # 扫描完成信号

    def __init__(self):
        super().__init__()
        self.shortcuts: List[ShortcutInfo] = []
        self.running = True
        self.scanned_files_count = 0
        self.total_files_estimate = 0

    def run(self):
        """执行扫描任务"""
        try:
            # 先估算总文件数
            self.total_files_estimate = self.estimate_total_files()

            # 重置计数器
            self.scanned_files_count = 0
            self.shortcuts = []

            # 扫描开始菜单快捷方式
            self.scan_progress.emit(1, 3, "正在扫描开始菜单...")
            self.scan_start_menu()

            if not self.running:
                return

            # 扫描应用程序快捷方式
            self.scan_progress.emit(2, 3, "正在扫描应用程序...")
            self.scan_applications()

            if not self.running:
                return

            # 扫描文档快捷方式
            self.scan_progress.emit(3, 3, "正在扫描文档...")
            self.scan_documents()

            # 扫描完成
            if self.running:
                self.scan_finished.emit()

        except Exception as e:
            print(f"扫描出错: {e}")

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

        return max(estimate, 100)  # 保证最小100

    def estimate_dir_files(self, directories: List[str]) -> int:
        """估算目录中的文件数量"""
        total = 0
        for directory in directories:
            if os.path.exists(directory):
                # 简单估算：每个目录大约100个文件
                total += 100
        return total

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

        # 获取所有本地磁盘
        for drive in string.ascii_uppercase:
            drive_path = f"{drive}:\\"
            if os.path.exists(drive_path):
                # 扫描常见的应用程序目录
                common_app_dirs = [
                    "Program Files",
                    "Program Files (x86)",
                    "Windows",
                    "Users",  # 用户目录下也可能有应用程序
                    "Programs",
                    "Applications",
                    "Software",
                    "Apps"
                ]

                for app_dir in common_app_dirs:
                    full_path = os.path.join(drive_path, app_dir)
                    if os.path.exists(full_path):
                        directories.append(full_path)

        return directories

    def get_document_dirs(self) -> List[str]:
        """获取文档目录"""
        directories = []

        # 获取所有本地磁盘
        for drive in string.ascii_uppercase:
            drive_path = f"{drive}:\\"
            if os.path.exists(drive_path):
                # 扫描常见的文档目录
                common_doc_dirs = [
                    "Users",  # 用户目录包含各种文档
                    "Documents",
                    "My Documents",
                    "Desktop",
                    "Downloads",
                    "数据",  # 中文目录
                    "文档",  # 中文目录
                    "文件",  # 中文目录
                    "资料"  # 中文目录
                ]

                for doc_dir in common_doc_dirs:
                    full_path = os.path.join(drive_path, doc_dir)
                    if os.path.exists(full_path):
                        directories.append(full_path)

        # 添加用户的特定文档目录
        user_dirs = [
            os.path.expandvars(r'%USERPROFILE%\Documents'),
            os.path.expandvars(r'%USERPROFILE%\Desktop'),
            os.path.expandvars(r'%USERPROFILE%\Downloads'),
            os.path.expandvars(r'%USERPROFILE%\OneDrive'),
        ]

        for user_dir in user_dirs:
            if os.path.exists(user_dir):
                directories.append(user_dir)

        return directories

    def is_system_shortcut(self, lnk_path: str) -> bool:
        """检查是否为系统快捷方式，如果是则跳过扫描"""
        try:
            lnk_path_lower = lnk_path.lower()
            file_name = os.path.basename(lnk_path)
            file_base = os.path.splitext(file_name)[0].lower()

            # 1. 检查是否在系统目录中
            system_dirs = [
                r"c:\windows",
                r"c:\windows\system32",
                r"c:\windows\syswow64",
                r"c:\programdata\microsoft\windows",
                r"c:\program files",
                r"c:\program files (x86)",
                os.environ.get('WINDIR', '').lower(),
                os.environ.get('SYSTEMROOT', '').lower(),
            ]

            # 添加系统开始菜单目录
            system_start_menu_dirs = [
                r"c:\programdata\microsoft\windows\start menu",
                r"c:\users\default\appdata\roaming\microsoft\windows\start menu",
                r"c:\users\public\desktop",
            ]

            all_system_dirs = system_dirs + system_start_menu_dirs

            # 检查是否在任何系统目录中
            for sys_dir in all_system_dirs:
                if sys_dir and lnk_path_lower.startswith(sys_dir):
                    # 在系统目录中，进一步检查文件名
                    return True

            # 2. 检查文件名是否为已知系统快捷方式
            system_file_names = {
                # 英文系统快捷方式
                "run": "运行",
                "control panel": "控制面板",
                "file explorer": "文件资源管理器",
                "this pc": "此电脑",
                "recycle bin": "回收站",
                "network": "网络",
                "settings": "设置",
                "task manager": "任务管理器",
                "command prompt": "命令提示符",
                "windows powershell": "Windows PowerShell",
                "notepad": "记事本",
                "calculator": "计算器",
                "paint": "画图",
                "registry editor": "注册表编辑器",
                "device manager": "设备管理器",
                "disk cleanup": "磁盘清理",
                "event viewer": "事件查看器",
                "services": "服务",

                # 中文系统快捷方式
                "显示桌面": "显示桌面",
                "在窗口之间切换": "在窗口之间切换",
                "切换窗口": "切换窗口",
                "桌面": "桌面",
                "任务视图": "任务视图",
                "搜索": "搜索",
                "开始": "开始",
                "所有程序": "所有程序",
                "最近添加": "最近添加",
                "管理工具": "管理工具",
                "系统工具": "系统工具",
                "附件": "附件",
                "游戏": "游戏",
                "维护": "维护",
                "轻松使用": "轻松使用",
            }

            # 检查文件名（不区分大小写）
            for sys_name in system_file_names:
                if sys_name in file_base or sys_name.replace(" ", "") in file_base:
                    return True

            # 3. 检查路径是否包含系统关键词
            system_keywords = [
                "system", "windows", "microsoft", "program", "admin",
                "公用", "公共", "默认", "default", "public",
                "开始菜单", "start menu", "启动", "启动菜单"
            ]

            for keyword in system_keywords:
                if keyword in lnk_path_lower:
                    return True

            # 4. 检查用户开始菜单目录中的系统快捷方式
            user_start_menu = os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu').lower()
            if lnk_path_lower.startswith(user_start_menu):
                # 在用户开始菜单中，检查是否为系统创建的快捷方式
                # 通常系统创建的快捷方式在特定子目录中
                system_subdirs = [
                    "programs\\system tools",
                    "programs\\accessories",
                    "programs\\maintenance",
                    "programs\\games",
                    "programs\\administrative tools",
                    "启动",
                    "startup"
                ]

                for subdir in system_subdirs:
                    if subdir in lnk_path_lower:
                        return True

            return False

        except Exception as e:
            print(f"检查系统快捷方式失败 {lnk_path}: {e}")
            # 如果检查失败，出于安全考虑，将其视为系统快捷方式
            return True

    def scan_start_menu(self):
        """扫描开始菜单快捷方式"""
        directories = self.get_start_menu_dirs()
        self.scan_directories(directories, "start_menu")

    def scan_applications(self):
        """扫描应用程序快捷方式"""
        directories = self.get_application_dirs()
        self.scan_directories(directories, "application")

    def scan_documents(self):
        """扫描文档快捷方式"""
        directories = self.get_document_dirs()
        self.scan_directories(directories, "document")

    def scan_directories(self, directories: List[str], shortcut_type: str):
        """扫描指定目录中的快捷方式"""
        for directory in directories:
            if not self.running:
                break

            if os.path.exists(directory):
                try:
                    # 使用os.walk扫描目录
                    for root, dirs, files in os.walk(directory):
                        if not self.running:
                            break

                        for file in files:
                            if not self.running:
                                break

                            if file.lower().endswith('.lnk'):
                                lnk_path = os.path.join(root, file)

                                # 检查是否为系统快捷方式，如果是则跳过
                                if self.is_system_shortcut(lnk_path):
                                    continue

                                self.process_shortcut(lnk_path, shortcut_type)

                                # 更新进度
                                self.scanned_files_count += 1
                                progress = int((self.scanned_files_count / self.total_files_estimate) * 100)
                                progress = min(progress, 99)  # 限制最大99%

                except Exception as e:
                    print(f"扫描目录 {directory} 出错: {e}")

    def file_exists(self, path: str) -> bool:
        """检查文件或目录是否存在，支持长路径"""
        if not path:
            return False

        # 处理长路径（Windows中超过260字符的路径）
        if len(path) > 260 and not path.startswith('\\\\?\\'):
            # 尝试添加长路径前缀
            long_path = '\\\\?\\' + path
            if os.path.exists(long_path):
                return True

        return os.path.exists(path)

    def is_in_system_path(self, executable: str) -> bool:
        """检查可执行文件是否在系统PATH中"""
        if not executable:
            return False

        # 获取文件名
        exe_name = os.path.basename(executable)

        # 获取系统PATH
        path_dirs = os.environ.get('PATH', '').split(os.pathsep)

        # 检查每个PATH目录
        for path_dir in path_dirs:
            full_path = os.path.join(path_dir, exe_name)
            if os.path.exists(full_path):
                return True

        return False

    def process_shortcut(self, lnk_path: str, shortcut_type: str):
        """处理单个快捷方式"""
        try:
            # 获取显示名称（先使用文件名）
            display_name = os.path.basename(lnk_path)

            # 尝试解析快捷方式
            try:
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                link = shell.CreateShortCut(lnk_path)

                # 尝试获取描述作为显示名称
                if hasattr(link, 'Description'):
                    description = link.Description or ""
                    if description and description.strip():
                        display_name = description

                # 获取其他属性
                target_path = link.TargetPath if hasattr(link, 'TargetPath') else ""
                arguments = link.Arguments if hasattr(link, 'Arguments') else ""
                working_dir = link.WorkingDirectory if hasattr(link, 'WorkingDirectory') else ""

            except Exception as e:
                # 解析失败，标记为无效
                print(f"解析快捷方式失败 {lnk_path}: {e}")
                is_valid = False
                actual_target_path = ""
                error_message = f"解析失败: {str(e)[:100]}"

                # 创建无效快捷方式对象并发射信号
                shortcut = ShortcutInfo(
                    name=os.path.basename(lnk_path),
                    path=lnk_path,
                    target_path=actual_target_path,
                    is_valid=is_valid,
                    error_message=error_message,
                    shortcut_type=shortcut_type,
                    display_name=display_name
                )
                self.invalid_shortcut_found.emit(shortcut)
                return

            # 验证快捷方式有效性
            is_valid = False
            error_message = ""
            actual_target_path = target_path

            if target_path:
                # 检查是否是URL或特殊协议
                if target_path.startswith(('http://', 'https://', 'ftp://', 'mailto:', 'shell:', 'appx:', 'ms-')):
                    is_valid = True
                # 检查文件是否存在
                elif os.path.exists(target_path):
                    is_valid = True
                # 检查环境变量扩展
                else:
                    expanded_path = os.path.expandvars(target_path)
                    if expanded_path != target_path and os.path.exists(expanded_path):
                        is_valid = True
                        actual_target_path = expanded_path
                    # 检查相对路径
                    elif working_dir and not os.path.isabs(target_path):
                        full_path = os.path.join(working_dir, target_path)
                        if os.path.exists(full_path):
                            is_valid = True
                            actual_target_path = full_path
                    # 检查PATH
                    elif self.is_in_system_path(target_path):
                        is_valid = True
                    else:
                        error_message = "目标文件不存在"
            else:
                # 没有目标路径
                error_message = "目标路径为空"

            # 创建快捷方式对象
            shortcut = ShortcutInfo(
                name=os.path.basename(lnk_path),
                path=lnk_path,
                target_path=actual_target_path,
                is_valid=is_valid,
                error_message=error_message,
                shortcut_type=shortcut_type,
                display_name=display_name
            )

            # 如果是无效快捷方式，立即发射信号
            if not is_valid:
                self.invalid_shortcut_found.emit(shortcut)

        except Exception as e:
            print(f"处理快捷方式 {lnk_path} 出错: {e}")

    def stop(self):
        """停止扫描"""
        self.running = False