"""
注册表清理模块
提供安全的注册表扫描、清理和备份功能
"""
import winreg
import os
import datetime
import threading
from typing import List, Dict, Callable, Optional
import tempfile


class RegistryIssue:
    """注册表问题项"""

    def __init__(self, key_path: str, issue_type: str, description: str, value_name: str = ""):
        self.key_path = key_path
        self.issue_type = issue_type  # 'invalid_key', 'invalid_value', 'orphan', 'broken_software'
        self.description = description
        self.value_name = value_name
        self.safe_to_delete = True  # 默认安全

    def __repr__(self):
        return f"RegistryIssue({self.issue_type}, {self.key_path}, {self.description})"


class RegistryScanner:
    """注册表扫描器"""

    # 安全的扫描路径
    SAFE_SCAN_PATHS = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
    ]

    def __init__(self):
        self.issues: List[RegistryIssue] = []
        self.is_running = False
        self.should_stop = False
        self.progress_callback: Optional[Callable] = None
        self.found_callback: Optional[Callable] = None
        self.issue_batch_size = 50  # 批量回调，避免频繁调用UI更新

    def set_callbacks(self, progress: Callable = None, found: Callable = None):
        """设置回调函数"""
        self.progress_callback = progress
        self.found_callback = found

    def scan(self, scan_types: List[str] = None):
        """
        扫描注册表

        Args:
            scan_types: 扫描类型列表 ['invalid_software', 'startup_items', 'invalid_file_refs']
        """
        self.issues = []
        self.is_running = True
        self.should_stop = False

        if scan_types is None:
            scan_types = ['invalid_software', 'startup_items', 'invalid_file_refs']

        try:
            # 扫描无效的软件卸载项
            if 'invalid_software' in scan_types and not self.should_stop:
                self._scan_invalid_software()

            # 扫描启动项无效引用
            if 'startup_items' in scan_types and not self.should_stop:
                self._scan_startup_items()

            # 扫描无效的文件引用
            if 'invalid_file_refs' in scan_types and not self.should_stop:
                self._scan_invalid_file_refs()

            # 扫描完成，确保最后一次UI更新
            if self.found_callback and len(self.issues) > 0:
                self.found_callback(self.issues[-1])

        except Exception as e:
            print(f"扫描出错: {e}")

        finally:
            self.is_running = False

    def _scan_invalid_software(self):
        """扫描无效的软件卸载信息"""
        self._report_progress("正在扫描软件卸载信息...")

        uninstall_paths = self._get_uninstall_paths()
        total_paths = len(uninstall_paths)

        # 遍历卸载注册表项
        for idx, (hkey, subkey_path) in enumerate(uninstall_paths):
            if self.should_stop:
                break

            # 报告进度
            progress = int((idx + 1) / total_paths * 100) if total_paths > 0 else 0
            self._report_progress(f"正在扫描软件卸载信息... {progress}%")

            try:
                with winreg.OpenKey(hkey, subkey_path) as base_key:
                    subkey_count = winreg.QueryInfoKey(base_key)[0]

                    for i in range(subkey_count):
                        if self.should_stop:
                            break

                        try:
                            subkey_name = winreg.EnumKey(base_key, i)
                            subkey_full_path = f"{subkey_path}\\{subkey_name}"

                            with winreg.OpenKey(hkey, subkey_full_path) as subkey:
                                # 检查安装路径是否存在
                                install_location = self._get_reg_value(subkey, "InstallLocation")
                                uninstall_string = self._get_reg_value(subkey, "UninstallString")

                                # 检查安装路径
                                if install_location and not os.path.exists(install_location):
                                    issue = RegistryIssue(
                                        subkey_full_path,
                                        'invalid_software',
                                        f"软件可能已卸载但注册表残留: {subkey_name}"
                                    )
                                    self._add_issue(issue)

                                # 检查卸载程序
                                elif uninstall_string:
                                    # 提取卸载程序路径
                                    exe_path = self._extract_exe_path(uninstall_string)
                                    if exe_path and not os.path.exists(exe_path):
                                        issue = RegistryIssue(
                                            subkey_full_path,
                                            'invalid_software',
                                            f"卸载程序不存在: {subkey_name}"
                                        )
                                        self._add_issue(issue)

                        except WindowsError:
                            continue

            except WindowsError:
                continue

    def _scan_startup_items(self):
        """扫描启动项中的无效引用"""
        self._report_progress("正在扫描启动项...")

        startup_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
        ]

        total_paths = len(startup_paths)

        for idx, (hkey, subkey_path) in enumerate(startup_paths):
            if self.should_stop:
                break

            # 报告进度
            progress = int((idx + 1) / total_paths * 100) if total_paths > 0 else 0
            self._report_progress(f"正在扫描启动项... {progress}%")

            try:
                with winreg.OpenKey(hkey, subkey_path) as key:
                    value_count = winreg.QueryInfoKey(key)[1]

                    for i in range(value_count):
                        if self.should_stop:
                            break

                        try:
                            value_name, value_data, _ = winreg.EnumValue(key, i)

                            if isinstance(value_data, str):
                                # 提取文件路径
                                exe_path = self._extract_exe_path(value_data)
                                if exe_path and not os.path.exists(exe_path):
                                    issue = RegistryIssue(
                                        f"{subkey_path}\\{value_name}",
                                        'invalid_startup',
                                        f"启动项引用的文件不存在: {value_name}"
                                    )
                                    self._add_issue(issue)

                        except WindowsError:
                            continue

            except WindowsError:
                continue

    def _scan_invalid_file_refs(self):
        """扫描常见的无效文件引用（仅扫描特定安全区域）"""
        self._report_progress("正在扫描文件引用... 0%")

        # 扫描最近打开的文件记录（安全清理）
        recent_docs_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs"
        self._scan_recent_docs(winreg.HKEY_CURRENT_USER, recent_docs_path)
        self._report_progress(f"正在扫描文件引用... 50% (已发现 {len(self.issues)} 个问题)")

        # 扫描运行历史
        run_history_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\RunMRU"
        self._scan_run_mru(winreg.HKEY_CURRENT_USER, run_history_path)
        self._report_progress(f"扫描完成！共发现 {len(self.issues)} 个问题")

    def _scan_recent_docs(self, hkey, path):
        """扫描最近文档记录"""
        try:
            with winreg.OpenKey(hkey, path) as key:
                # 检查子项
                try:
                    subkey_count = winreg.QueryInfoKey(key)[0]
                    for i in range(subkey_count):
                        if self.should_stop:
                            break
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            subkey_path = f"{path}\\{subkey_name}"

                            with winreg.OpenKey(hkey, subkey_path) as subkey:
                                value_count = winreg.QueryInfoKey(subkey)[1]
                                for j in range(value_count):
                                    if self.should_stop:
                                        break
                                    try:
                                        value_name, value_data, _ = winreg.EnumValue(subkey, j)
                                        if isinstance(value_data, str):
                                            # 这些文件可能已经删除，批量添加不回调
                                            issue = RegistryIssue(
                                                subkey_path,  # 只存储键路径
                                                'recent_docs',
                                                f"最近文档记录: {value_name}",
                                                value_name=value_name  # 单独存储值名称
                                            )
                                            self.issues.append(issue)
                                    except WindowsError:
                                        continue
                        except WindowsError:
                            continue
                except WindowsError:
                    pass

        except WindowsError:
            pass

    def _scan_run_mru(self, hkey, path):
        """扫描运行历史"""
        try:
            with winreg.OpenKey(hkey, path) as key:
                value_count = winreg.QueryInfoKey(key)[1]
                for i in range(value_count):
                    if self.should_stop:
                        break
                    try:
                        value_name, value_data, _ = winreg.EnumValue(key, i)
                        if value_name != 'MRUList':
                            # 批量添加不回调
                            issue = RegistryIssue(
                                path,  # 只存储键路径
                                'run_history',
                                f"运行命令历史: {value_data}",
                                value_name=value_name  # 单独存储值名称
                            )
                            self.issues.append(issue)
                    except WindowsError:
                        continue
        except WindowsError:
            pass

    def _get_uninstall_paths(self):
        """获取卸载信息路径"""
        return [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

    def _get_reg_value(self, key, value_name: str) -> Optional[str]:
        """获取注册表值"""
        try:
            value, _ = winreg.QueryValueEx(key, value_name)
            if isinstance(value, str):
                return value
        except WindowsError:
            pass
        return None

    def _extract_exe_path(self, command: str) -> Optional[str]:
        """从命令字符串中提取exe路径"""
        import re
        # 匹配引号中的路径或可执行文件路径
        match = re.search(r'"([^"]+\.exe)"', command, re.IGNORECASE)
        if match:
            return match.group(1)

        # 匹配未加引号的路径（到第一个空格或结束）
        match = re.search(r'^([^\s]+\.exe)', command, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def _add_issue(self, issue: RegistryIssue):
        """添加问题项"""
        self.issues.append(issue)
        # 批量回调，避免频繁调用UI更新导致卡顿
        if self.found_callback and len(self.issues) % self.issue_batch_size == 0:
            self.found_callback(issue)

    def _report_progress(self, message: str):
        """报告进度"""
        if self.progress_callback:
            self.progress_callback(message)

    def stop(self):
        """停止扫描"""
        self.should_stop = True


class RegistryBackup:
    """注册表备份管理器"""

    @staticmethod
    def create_backup(issues: List[RegistryIssue]) -> str:
        """
        创建备份

        Args:
            issues: 要备份的注册表项列表

        Returns:
            备份文件路径
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(tempfile.gettempdir(), "RegistryCleaner_Backups")

        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        backup_file = os.path.join(backup_dir, f"registry_backup_{timestamp}.reg")

        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write("Windows Registry Editor Version 5.00\n")
                f.write("; 注册表清理备份 - 创建时间: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")

                for issue in issues:
                    f.write(f"; {issue.description}\n")
                    f.write(f"; 原始路径: {issue.key_path}\n")

                    # 导出注册表项
                    try:
                        # 解析键路径
                        key_info = RegistryBackup._parse_key_path(issue.key_path)
                        if key_info:
                            hkey, subkey = key_info
                            RegistryBackup._export_key(hkey, subkey, f)
                    except Exception as e:
                        f.write(f"; 导出失败: {e}\n")

                    f.write("\n")

            return backup_file

        except Exception as e:
            raise Exception(f"创建备份失败: {e}")

    @staticmethod
    def _parse_key_path(path: str):
        """解析键路径"""
        # 支持的根键
        root_keys = {
            'HKEY_LOCAL_MACHINE': winreg.HKEY_LOCAL_MACHINE,
            'HKLM': winreg.HKEY_LOCAL_MACHINE,
            'HKEY_CURRENT_USER': winreg.HKEY_CURRENT_USER,
            'HKCU': winreg.HKEY_CURRENT_USER,
        }

        parts = path.split('\\', 1)
        if len(parts) < 2:
            return None

        root, subkey = parts[0], parts[1]
        if root in root_keys:
            return (root_keys[root], subkey)

        return None

    @staticmethod
    def _export_key(hkey, subkey: str, file_handle):
        """导出注册表项到文件"""
        try:
            with winreg.OpenKey(hkey, subkey) as key:
                # 写入键路径
                key_name = winreg.QueryInfoKey(key)[0]
                root_key_name = "HKEY_LOCAL_MACHINE" if hkey == winreg.HKEY_LOCAL_MACHINE else "HKEY_CURRENT_USER"
                file_handle.write(f"\n[{root_key_name}\\{subkey}]\n")

                # 导出值
                value_count = winreg.QueryInfoKey(key)[1]
                for i in range(value_count):
                    try:
                        value_name, value_data, value_type = winreg.EnumValue(key, i)

                        if value_type == winreg.REG_SZ:
                            if isinstance(value_data, str):
                                file_handle.write(f'"{value_name}"="{value_data}"\n')

                        elif value_type == winreg.REG_DWORD:
                            if isinstance(value_data, int):
                                file_handle.write(f'"{value_name}"=dword:{value_data:08x}\n')

                        elif value_type == winreg.REG_EXPAND_SZ:
                            if isinstance(value_data, str):
                                file_handle.write(f'"{value_name}"=hex(2):{value_data.encode("utf-16-le").hex().upper()}\n')

                    except WindowsError:
                        continue

        except WindowsError:
            pass

    @staticmethod
    def restore_backup(backup_file: str) -> bool:
        """
        恢复备份

        Args:
            backup_file: 备份文件路径

        Returns:
            是否成功
        """
        try:
            import subprocess
            # 使用 reg import 命令恢复
            result = subprocess.run(['reg', 'import', backup_file], capture_output=True)
            return result.returncode == 0
        except Exception as e:
            print(f"恢复备份失败: {e}")
            return False

    @staticmethod
    def get_backup_files() -> List[Dict[str, str]]:
        """获取所有备份文件"""
        backup_dir = os.path.join(tempfile.gettempdir(), "RegistryCleaner_Backups")

        if not os.path.exists(backup_dir):
            return []

        backups = []
        for file in os.listdir(backup_dir):
            if file.endswith('.reg'):
                file_path = os.path.join(backup_dir, file)
                stat = os.stat(file_path)
                backups.append({
                    'name': file,
                    'path': file_path,
                    'size': stat.st_size,
                    'created': datetime.datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                })

        return sorted(backups, key=lambda x: x['created'], reverse=True)


class RegistryCleaner:
    """注册表清理器"""

    @staticmethod
    def clean_issue(issue: RegistryIssue) -> bool:
        """
        清理单个问题项

        Args:
            issue: 注册表问题项

        Returns:
            是否成功
        """
        try:
            key_info = RegistryBackup._parse_key_path(issue.key_path)
            if not key_info:
                print(f"无法解析键路径: {issue.key_path}")
                return False

            hkey, subkey_path = key_info

            # 如果是值级别的问题，删除值
            if issue.value_name:
                with winreg.OpenKey(hkey, subkey_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, issue.value_name)
                print(f"已删除值: {subkey_path}\\{issue.value_name}")
            else:
                # 删除整个键
                winreg.DeleteKey(hkey, subkey_path)
                print(f"已删除键: {subkey_path}")

            return True

        except Exception as e:
            print(f"清理失败 [{issue.description}]: {e}")
            return False

    @staticmethod
    def clean_issues(issues: List[RegistryIssue], progress_callback: Callable = None) -> int:
        """
        批量清理问题项

        Args:
            issues: 问题项列表
            progress_callback: 进度回调函数

        Returns:
            成功清理的数量
        """
        success_count = 0
        total = len(issues)

        for i, issue in enumerate(issues):
            if progress_callback:
                progress_callback(i, total, f"正在清理: {issue.description}")

            if RegistryCleaner.clean_issue(issue):
                success_count += 1

        return success_count


class RegistryScannerThread(threading.Thread):
    """注册表扫描线程"""

    def __init__(self, scanner: RegistryScanner, scan_types: List[str] = None):
        super().__init__()
        self.scanner = scanner
        self.scan_types = scan_types
        self.daemon = True

    def run(self):
        """运行扫描"""
        self.scanner.scan(self.scan_types)

    def stop(self):
        """停止扫描"""
        self.scanner.stop()
