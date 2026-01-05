"""
快捷方式扫描模块（跨平台）
使用平台适配器自动加载对应平台的实现
"""
import os
import sys
import threading
from typing import List, Callable


class ShortcutInfo:
    """快捷方式信息类（跨平台）"""

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
    """
    统一扫描线程 - 跨平台快捷方式扫描
    自动根据平台使用对应的扫描器
    """

    def __init__(self):
        super().__init__()
        self.shortcuts: List[ShortcutInfo] = []
        self.running = True
        self.scanner_instance = None  # 平台特定的扫描器实例

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
        """执行扫描任务（跨平台）"""
        try:
            # 使用平台适配器获取扫描器
            from core.platform import get_shortcut_scanner
            ScannerClass = get_shortcut_scanner()

            if ScannerClass is None:
                from utils.platform import get_platform_name
                print(f"{get_platform_name()} 平台不支持快捷方式扫描")
                if self.finished_callback:
                    self.finished_callback()
                return

            # 创建平台特定的扫描器
            scanner = ScannerClass()
            self.scanner_instance = scanner

            # 设置回调
            if self.progress_callback:
                scanner.set_progress_callback(self.progress_callback)
            if self.found_callback:
                scanner.set_found_callback(self.found_callback)
            if self.finished_callback:
                scanner.set_finished_callback(self.finished_callback)

            # 运行扫描
            scanner.scan()

        except Exception as e:
            print(f"扫描出错: {e}")
            import traceback
            traceback.print_exc()

            # 如果出错，仍然调用完成回调
            if self.finished_callback:
                self.finished_callback()

    def stop(self):
        """停止扫描"""
        self.running = False
        # 同时停止底层的平台扫描器
        if self.scanner_instance and hasattr(self.scanner_instance, 'stop'):
            self.scanner_instance.stop()


class ShortcutRecoveryThread(threading.Thread):
    """
    快捷方式恢复线程（跨平台）
    目前仅 Windows 平台支持快捷方式恢复
    """

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

    def run(self):
        """执行恢复任务（仅 Windows）"""
        from utils.platform import is_windows

        if not is_windows():
            print("快捷方式恢复功能仅在 Windows 平台可用")
            if self.finished_callback:
                self.finished_callback(0, len(self.broken_shortcuts), [])
            return

        try:
            # Windows 平台的恢复逻辑
            import win32com.client

            total = len(self.broken_shortcuts)

            for idx, shortcut in enumerate(self.broken_shortcuts):
                if not self.running:
                    break

                if self.progress_callback:
                    progress = int((idx / total) * 100)
                    self.progress_callback(progress, 100, f"正在尝试恢复: {shortcut.display_name}")

                # 尝试恢复快捷方式
                result = self.recover_shortcut(shortcut)
                self.recovery_results.append(result)

                if result['success']:
                    self.recovered_count += 1
                else:
                    self.failed_count += 1

                # 通知UI
                if self.found_callback:
                    self.found_callback(result)

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
                original_folder = os.path.basename(working_dir.rstrip(os.sep))
            elif target_path:
                target_dir = os.path.dirname(target_path)
                if target_dir:
                    original_folder = os.path.basename(target_dir.rstrip(os.sep))

            # 尝试查找移动后的文件
            recovered_path = self.find_moved_file(target_filename, original_folder)

            if recovered_path:
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

        import string
        drives = [f"{letter}:\\" for letter in string.ascii_uppercase if os.path.exists(f"{letter}:\\")]

        for drive in drives:
            if not self.running:
                return None

            try:
                matching_dirs = self.find_matching_directories(drive, folder_name)

                for matching_dir in matching_dirs:
                    if not self.running:
                        return None

                    target_path = os.path.join(matching_dir, target_filename)

                    if os.path.exists(target_path):
                        return target_path

                    try:
                        for root, dirs, files in os.walk(matching_dir):
                            level = root[len(matching_dir):].count(os.sep)
                            if level > 2:
                                dirs[:] = []
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
            search_paths = [
                drive,
                os.path.join(drive, "Program Files"),
                os.path.join(drive, "Program Files (x86)"),
                os.path.join(drive, "Users"),
                os.path.join(drive, "Documents"),
                os.path.join(drive, "Software"),
            ]

            user_profile = os.path.expanduser("~")
            if user_profile not in search_paths:
                search_paths.append(user_profile)

            for search_path in search_paths:
                if not os.path.exists(search_path):
                    continue

                try:
                    for root, dirs, files in os.walk(search_path):
                        level = root[len(search_path):].count(os.sep)
                        if level > 1:
                            dirs[:] = []
                            continue

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

            link.TargetPath = new_target_path
            new_working_dir = os.path.dirname(new_target_path)
            link.WorkingDirectory = new_working_dir
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
