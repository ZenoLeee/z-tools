import os
import sys
import string
import threading
from typing import List, Callable


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


class UnifiedScannerThread(threading.Thread):
    """统一扫描线程 - 同时扫描三种类型的快捷方式"""

    def __init__(self):
        super().__init__()
        self.shortcuts: List[ShortcutInfo] = []
        self.running = True
        self.scanned_files_count = 0
        self.total_files_estimate = 0

        # 回调函数
        self.progress_callback: Callable[[int, int, str], None] = None
        self.found_callback: Callable[[ShortcutInfo], None] = None
        self.finished_callback: Callable[[], None] = None

    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """设置进度回调"""
        self.progress_callback = callback

    def set_found_callback(self, callback: Callable[[ShortcutInfo], None]):
        """设置发现快捷方式回调"""
        self.found_callback = callback

    def set_finished_callback(self, callback: Callable[[], None]):
        """设置完成回调"""
        self.finished_callback = callback

    def run(self):
        """执行扫描任务"""
        try:
            # 先估算总文件数
            self.total_files_estimate = self.estimate_total_files()

            # 重置计数器
            self.scanned_files_count = 0
            self.shortcuts = []

            # 扫描开始菜单快捷方式
            self._emit_progress(0, 100, "正在初始化扫描...")
            self.scan_start_menu()

            if not self.running:
                return

            # 扫描应用程序快捷方式
            self._emit_progress(0, 100, "正在扫描应用程序...")
            self.scan_applications()

            if not self.running:
                return

            # 扫描文档快捷方式
            self._emit_progress(0, 100, "正在扫描文档...")
            self.scan_documents()

            # 扫描完成
            if self.running and self.finished_callback:
                self.finished_callback()

        except Exception as e:
            print(f"扫描出错: {e}")

    def _emit_progress(self, current: int, total: int, text: str):
        """发送进度信号"""
        if self.progress_callback:
            try:
                self.progress_callback(current, total, text)
            except Exception as e:
                print(f"进度回调失败: {e}")

    def _emit_found(self, shortcut: ShortcutInfo):
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

        return max(estimate, 100)  # 保证最小100

    def estimate_dir_files(self, directories: List[str]) -> int:
        """估算目录中的文件数量（快速估算，不深入扫描）"""
        total = 0
        for directory in directories:
            if os.path.exists(directory):
                try:
                    # 只扫描第一层和第二层目录进行快速估算
                    for root, dirs, files in os.walk(directory):
                        # 只统计.lnk文件
                        lnk_count = sum(1 for f in files if f.lower().endswith('.lnk'))
                        total += lnk_count

                        # 限制扫描深度为2层
                        level = root[len(directory):].count(os.sep)
                        if level >= 2:
                            # 停止深入，估算剩余文件
                            dirs[:] = []
                            total += lnk_count * 3  # 假设每层大约还有这么多
                            break
                except Exception as e:
                    # 如果统计失败，使用默认估算
                    total += 200
        return max(total, 200)  # 保证最小200

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
        self.scan_directories(directories, "start_menu", "开始菜单")

    def scan_applications(self):
        """扫描应用程序快捷方式"""
        directories = self.get_application_dirs()
        self.scan_directories(directories, "application", "应用程序")

    def scan_documents(self):
        """扫描文档快捷方式"""
        directories = self.get_document_dirs()
        self.scan_directories(directories, "document", "文档")

    def scan_directories(self, directories: List[str], shortcut_type: str, location_name: str):
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

                                # 更新进度（每处理一个文件都更新）
                                self.scanned_files_count += 1
                                progress = int((self.scanned_files_count / self.total_files_estimate) * 100)
                                progress = min(progress, 99)  # 限制最大99%

                                # 发送进度更新
                                self._emit_progress(progress, 100, f"正在扫描{location_name}: {os.path.basename(lnk_path)}")

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
                self._emit_found(shortcut)
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
                self._emit_found(shortcut)

        except Exception as e:
            print(f"处理快捷方式 {lnk_path} 出错: {e}")

    def stop(self):
        """停止扫描"""
        self.running = False


class ShortcutRecoveryThread(threading.Thread):
    """快捷方式恢复线程"""

    def __init__(self, broken_shortcuts: List[ShortcutInfo]):
        super().__init__()
        self.broken_shortcuts = broken_shortcuts
        self.running = True
        self.recovered_count = 0
        self.failed_count = 0
        self.recovery_results = []

        # 回调函数
        self.progress_callback: Callable[[int, int, str], None] = None
        self.found_callback: Callable[[dict], None] = None
        self.finished_callback: Callable[[int, int, List], None] = None

    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        self.progress_callback = callback

    def set_found_callback(self, callback: Callable[[dict], None]):
        self.found_callback = callback

    def set_finished_callback(self, callback: Callable[[int, int, List], None]):
        self.finished_callback = callback

    def _emit_progress(self, current: int, total: int, text: str):
        if self.progress_callback:
            try:
                self.progress_callback(current, total, text)
            except Exception as e:
                print(f"进度回调失败: {e}")

    def _emit_found(self, result: dict):
        if self.found_callback:
            try:
                self.found_callback(result)
            except Exception as e:
                print(f"发现回调失败: {e}")

    def run(self):
        """执行恢复任务"""
        try:
            total = len(self.broken_shortcuts)

            for idx, shortcut in enumerate(self.broken_shortcuts):
                if not self.running:
                    break

                progress = int((idx / total) * 100)
                self._emit_progress(progress, 100, f"正在尝试恢复: {shortcut.display_name}")

                # 尝试恢复快捷方式
                result = self.recover_shortcut(shortcut)
                self.recovery_results.append(result)

                if result['success']:
                    self.recovered_count += 1
                else:
                    self.failed_count += 1

                # 通知UI
                self._emit_found(result)

            # 完成
            if self.finished_callback:
                self.finished_callback(self.recovered_count, self.failed_count, self.recovery_results)

        except Exception as e:
            print(f"快捷方式恢复出错: {e}")
            import traceback
            traceback.print_exc()

    def recover_shortcut(self, shortcut: ShortcutInfo) -> dict:
        """尝试恢复单个快捷方式"""
        try:
            # 解析快捷方式获取详细信息
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            link = shell.CreateShortCut(shortcut.path)

            target_path = link.TargetPath if hasattr(link, 'TargetPath') else ""
            working_dir = link.WorkingDirectory if hasattr(link, 'WorkingDirectory') else ""

            # 提取目标文件名和文件夹名
            target_filename = os.path.basename(target_path) if target_path else ""

            # 如果没有目标路径，尝试从快捷方式名称推断
            if not target_filename:
                target_filename = os.path.splitext(shortcut.name)[0] + ".exe"

            # 提取原始文件夹名（从目标路径或工作目录）
            original_folder = ""

            if working_dir and os.path.exists(working_dir):
                # 工作目录存在，可能只是目标文件移动了
                original_folder = os.path.basename(working_dir.rstrip(os.sep))
            elif target_path:
                # 从目标路径提取文件夹名
                target_dir = os.path.dirname(target_path)
                if target_dir:
                    original_folder = os.path.basename(target_dir.rstrip(os.sep))

            # 尝试查找移动后的文件
            recovered_path = self.find_moved_file(target_filename, original_folder)

            if recovered_path:
                # 找到了，更新快捷方式
                return self.update_shortcut(shortcut, recovered_path)
            else:
                return {
                    'shortcut': shortcut,
                    'success': False,
                    'new_path': None,
                    'message': f'未找到匹配的文件: {target_filename}'
                }

        except Exception as e:
            return {
                'shortcut': shortcut,
                'success': False,
                'new_path': None,
                'message': f'恢复失败: {str(e)}'
            }

    def find_moved_file(self, target_filename: str, folder_name: str) -> str:
        """在所有磁盘中查找移动后的文件"""
        if not target_filename:
            return None

        # 获取所有可用磁盘
        import string
        drives = [f"{letter}:\\" for letter in string.ascii_uppercase if os.path.exists(f"{letter}:\\")]

        # 在所有磁盘中搜索匹配的文件夹和文件
        for drive in drives:
            if not self.running:
                return None

            try:
                # 搜索匹配的文件夹
                matching_dirs = self.find_matching_directories(drive, folder_name)

                for matching_dir in matching_dirs:
                    if not self.running:
                        return None

                    # 在匹配的文件夹中查找目标文件
                    target_path = os.path.join(matching_dir, target_filename)

                    if os.path.exists(target_path):
                        return target_path

                    # 也检查子目录（深度1-2层）
                    try:
                        for root, dirs, files in os.walk(matching_dir):
                            # 限制深度
                            level = root[len(matching_dir):].count(os.sep)
                            if level > 2:
                                dirs[:] = []  # 不再深入
                                continue

                            if target_filename in files:
                                return os.path.join(root, target_filename)
                    except (PermissionError, OSError):
                        continue

            except (PermissionError, OSError):
                continue

        return None

    def find_matching_directories(self, drive: str, folder_name: str) -> List[str]:
        """在驱动器中查找匹配的目录"""
        if not folder_name:
            return []

        matching_dirs = []

        try:
            # 遍历驱动器根目录和常见位置
            search_paths = [
                drive,
                os.path.join(drive, "Program Files"),
                os.path.join(drive, "Program Files (x86)"),
                os.path.join(drive, "Users"),
                os.path.join(drive, "Documents"),
                os.path.join(drive, "Software"),
            ]

            # 添加用户目录
            user_profile = os.path.expanduser("~")
            if user_profile not in search_paths:
                search_paths.append(user_profile)

            for search_path in search_paths:
                if not os.path.exists(search_path):
                    continue

                try:
                    # 只扫描前两层目录以提高速度
                    for root, dirs, files in os.walk(search_path):
                        # 限制深度
                        level = root[len(search_path):].count(os.sep)
                        if level > 1:
                            dirs[:] = []  # 不再深入
                            continue

                        # 检查当前目录是否匹配
                        if folder_name.lower() in [d.lower() for d in dirs]:
                            for dir_name in dirs:
                                if dir_name.lower() == folder_name.lower():
                                    matching_dirs.append(os.path.join(root, dir_name))

                except (PermissionError, OSError):
                    continue

        except Exception as e:
            print(f"查找匹配目录失败 {drive}: {e}")

        return matching_dirs

    def update_shortcut(self, shortcut: ShortcutInfo, new_target_path: str) -> dict:
        """更新快捷方式的目标路径"""
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            link = shell.CreateShortCut(shortcut.path)

            # 更新目标路径
            link.TargetPath = new_target_path

            # 更新工作目录
            new_working_dir = os.path.dirname(new_target_path)
            link.WorkingDirectory = new_working_dir

            # 保存快捷方式
            link.Save()

            return {
                'shortcut': shortcut,
                'success': True,
                'new_path': new_target_path,
                'message': f'已恢复到: {new_target_path}'
            }

        except Exception as e:
            return {
                'shortcut': shortcut,
                'success': False,
                'new_path': new_target_path,
                'message': f'保存失败: {str(e)}'
            }

    def stop(self):
        """停止恢复"""
        self.running = False
