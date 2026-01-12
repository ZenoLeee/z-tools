"""
Windows 平台启动项管理模块
管理注册表启动项、启动文件夹、计划任务
"""
import winreg
import os
import sys
import threading
import subprocess
import ctypes
from typing import List, Callable, Optional
import tempfile
import shutil


def is_admin():
    """检查是否具有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    """以管理员权限重新运行当前程序

    Returns:
        bool: 如果成功请求管理员权限返回True，否则返回False
    """
    try:
        # 获取当前脚本路径
        if getattr(sys, 'frozen', False):
            # 如果是打包的exe
            script = sys.executable
        else:
            # 如果是Python脚本
            script = sys.argv[0]
            # 使用当前Python解释器
            script = f'"{sys.executable}" "{script}"'

        # 获取参数
        params = ' '.join([f'"{arg}"' if ' ' in arg else arg for arg in sys.argv[1:]])

        # 请求管理员权限重新运行
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",  # 请求提升权限
            sys.executable if not getattr(sys, 'frozen', False) else script,
            f'"{script}" {params}' if not getattr(sys, 'frozen', False) else params,
            None,
            1  # SW_SHOWNORMAL
        )

        return ret > 32  # 返回值 > 32 表示成功

    except Exception as e:
        print(f"请求管理员权限失败: {e}")
        return False


class StartupItem:
    """启动项信息类"""

    def __init__(self, name: str, path: str, label: str = "",
                 is_valid: bool = False, is_enabled: bool = False,
                 error_message: str = "", item_type: str = "unknown",
                 command: str = "", location: str = ""):
        self.name = name
        self.path = path
        self.label = label
        self.is_valid = is_valid
        self.is_enabled = is_enabled
        self.error_message = error_message
        self.item_type = item_type  # 'registry', 'folder', 'task'
        self.command = command
        self.location = location
        self.score = 50  # 评分，由外部设置
        self.recommendation = ""  # 优化建议

    def __repr__(self):
        return f"StartupItem({self.label}, {self.item_type}, valid={self.is_valid})"


class WindowsStartupManager:
    """Windows 启动项管理器"""

    # 注册表启动项路径
    REGISTRY_STARTUP_PATHS = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
    ]

    # 启动文件夹
    STARTUP_FOLDERS = [
        os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup'),
        os.path.expandvars(r'%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\Startup'),
    ]

    # 备份文件夹
    BACKUP_FOLDER = os.path.join(tempfile.gettempdir(), 'WindowsToolbox', 'StartupBackup')

    def __init__(self):
        self.running = True
        self.startup_items: List[StartupItem] = []
        self.progress_callback: Optional[Callable] = None
        self.found_callback: Optional[Callable] = None
        self.finished_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable):
        """设置进度回调"""
        self.progress_callback = callback

    def set_found_callback(self, callback: Callable):
        """设置发现启动项回调"""
        self.found_callback = callback

    def set_finished_callback(self, callback: Callable):
        """设置完成回调"""
        self.finished_callback = callback

    def scan(self):
        """扫描所有启动项"""
        try:
            self._emit_progress(0, 100, "正在初始化扫描...")

            # 扫描注册表启动项
            self._emit_progress(10, 100, "正在扫描注册表启动项...")
            self._scan_registry_startup()

            if not self.running:
                return

            # 扫描启动文件夹
            self._emit_progress(50, 100, "正在扫描启动文件夹...")
            self._scan_startup_folder()

            if not self.running:
                return

            # 扫描计划任务
            self._emit_progress(80, 100, "正在扫描计划任务...")
            self._scan_scheduled_tasks()

            # 扫描完成
            self._emit_progress(100, 100, "扫描完成")
            if self.running and self.finished_callback:
                self.finished_callback()

        except Exception as e:
            print(f"Windows 启动项扫描出错: {e}")
            import traceback
            traceback.print_exc()

    def _emit_progress(self, current: int, total: int, text: str):
        """发送进度信号"""
        if self.progress_callback:
            try:
                self.progress_callback(current, total, text)
            except Exception as e:
                print(f"进度回调失败: {e}")

    def _emit_found(self, item: StartupItem):
        """发送发现启动项信号"""
        if self.found_callback:
            try:
                self.found_callback(item)
            except Exception as e:
                print(f"发现回调失败: {e}")

    def _scan_registry_startup(self):
        """扫描注册表启动项"""
        total = len(self.REGISTRY_STARTUP_PATHS)

        for idx, (hkey, subkey_path) in enumerate(self.REGISTRY_STARTUP_PATHS):
            if not self.running:
                break

            try:
                with winreg.OpenKey(hkey, subkey_path) as key:
                    value_count = winreg.QueryInfoKey(key)[1]

                    for i in range(value_count):
                        if not self.running:
                            break

                        try:
                            value_name, value_data, _ = winreg.EnumValue(key, i)

                            # 提取文件路径
                            exe_path = self._extract_exe_path(value_data) if isinstance(value_data, str) else ""
                            is_valid = os.path.exists(exe_path) if exe_path else True

                            # 确定作用域
                            scope = "系统级" if hkey == winreg.HKEY_LOCAL_MACHINE else "用户级"
                            # 添加路径前缀以便后续解析
                            path_prefix = "HKLM\\" if hkey == winreg.HKEY_LOCAL_MACHINE else "HKCU\\"

                            item = StartupItem(
                                name=value_name,
                                path=f"{path_prefix}{subkey_path}\\{value_name}",
                                label=value_name,
                                is_valid=is_valid,
                                is_enabled=True,
                                item_type='registry',
                                command=value_data,
                                location=f"注册表 ({scope})"
                            )

                            self._emit_found(item)

                        except WindowsError:
                            continue

                    # 更新进度
                    progress = 10 + int((idx + 1) / total * 40)
                    self._emit_progress(progress, 100, f"正在扫描注册表: {subkey_path}")

            except WindowsError:
                continue

    def _scan_startup_folder(self):
        """扫描启动文件夹"""
        total = len(self.STARTUP_FOLDERS)

        for idx, folder in enumerate(self.STARTUP_FOLDERS):
            if not self.running or not os.path.exists(folder):
                continue

            try:
                lnk_files = [f for f in os.listdir(folder) if f.lower().endswith('.lnk')]

                for lnk_file in lnk_files:
                    if not self.running:
                        break

                    lnk_path = os.path.join(folder, lnk_file)
                    self._process_shortcut(lnk_path)

                # 更新进度
                progress = 50 + int((idx + 1) / total * 30)
                scope = "用户" if "APPDATA" in folder else "公共"
                self._emit_progress(progress, 100, f"正在扫描{scope}启动文件夹")

            except (PermissionError, OSError) as e:
                print(f"无法访问启动文件夹 {folder}: {e}")

    def _process_shortcut(self, lnk_path: str):
        """处理快捷方式文件"""
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(lnk_path)

            target_path = shortcut.TargetPath
            command = target_path
            if shortcut.Arguments:
                command += f" {shortcut.Arguments}"

            is_valid = os.path.exists(target_path) if target_path else False

            item = StartupItem(
                name=os.path.basename(lnk_path).replace('.lnk', ''),
                path=lnk_path,
                label=os.path.basename(lnk_path),
                is_valid=is_valid,
                is_enabled=True,
                item_type='folder',
                command=command,
                location=f"启动文件夹: {os.path.basename(os.path.dirname(lnk_path))}"
            )

            self._emit_found(item)

        except Exception as e:
            print(f"解析快捷方式失败 {lnk_path}: {e}")

    def _scan_scheduled_tasks(self):
        """扫描计划任务"""
        try:
            # 使用schtasks命令查询
            result = subprocess.run(
                ['schtasks', '/query', '/fo', 'list', '/v'],
                capture_output=True,
                text=True,
                timeout=30,
                encoding='gbk',
                errors='ignore'
            )

            if result.returncode != 0:
                return

            # 解析输出
            lines = result.stdout.split('\n')
            task_name = ""
            trigger = ""
            status = ""

            for line in lines:
                if not self.running:
                    break

                line = line.strip()
                if line.startswith("任务名:"):
                    task_name = line.split(":", 1)[1].strip()
                elif line.startswith("触发器:"):
                    trigger = line.lower()
                elif line.startswith("状态:"):
                    status = line.split(":", 1)[1].strip()

                # 当收集到完整信息时
                if task_name and trigger and "任务名:" not in line:
                    # 筛选启动时/登录时运行的任务
                    if any(keyword in trigger for keyword in ['logon', 'startup', 'at logon', 'at startup', '登录', '启动']):
                        item = StartupItem(
                            name=task_name,
                            path=f"Task: {task_name}",
                            label=task_name,
                            is_valid=True,
                            is_enabled=('启用' in status or 'Enabled' in status or 'ready' in status.lower()),
                            item_type='task',
                            location="计划任务"
                        )

                        self._emit_found(item)

                    # 重置
                    task_name = ""
                    trigger = ""
                    status = ""

            self._emit_progress(95, 100, "正在扫描计划任务...")

        except Exception as e:
            print(f"扫描计划任务失败: {e}")

    def _extract_exe_path(self, command: str) -> str:
        """从命令行中提取可执行文件路径"""
        if not command:
            return ""

        # 移除前后引号
        command = command.strip()

        # 如果有引号，提取引号内的内容
        if command.startswith('"'):
            end = command.find('"', 1)
            if end > 0:
                return command[1:end]

        # 否则按空格分割
        parts = command.split()
        if parts:
            return parts[0]

        return ""

    def enable_startup_item(self, item: StartupItem) -> bool:
        """启用启动项"""
        try:
            if item.item_type == 'registry':
                # 从备份恢复注册表值
                return self._restore_registry_item(item)
            elif item.item_type == 'folder':
                # 从备份恢复快捷方式
                return self._restore_shortcut_item(item)
            elif item.item_type == 'task':
                # 启用计划任务
                result = subprocess.run(
                    ['schtasks', '/change', '/tn', item.name, '/enable'],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode != 0:
                    error_output = result.stderr.decode('gbk', errors='ignore')
                    item.error_message = f"启用计划任务失败: {error_output}"
                return result.returncode == 0
            return False
        except PermissionError as e:
            error_msg = f"权限不足：{e}"
            print(f"启用启动项失败: {error_msg}")
            item.error_message = error_msg
            return False
        except Exception as e:
            error_msg = str(e)
            print(f"启用启动项失败: {error_msg}")
            item.error_message = error_msg
            return False

    def disable_startup_item(self, item: StartupItem) -> bool:
        """禁用启动项"""
        try:
            if item.item_type == 'registry':
                # 备份并删除注册表值
                return self._backup_and_disable_registry_item(item)
            elif item.item_type == 'folder':
                # 移动快捷方式到备份文件夹
                return self._backup_shortcut_item(item)
            elif item.item_type == 'task':
                # 禁用计划任务
                result = subprocess.run(
                    ['schtasks', '/change', '/tn', item.name, '/disable'],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode != 0:
                    error_output = result.stderr.decode('gbk', errors='ignore')
                    item.error_message = f"禁用计划任务失败: {error_output}"
                return result.returncode == 0
            return False
        except PermissionError as e:
            error_msg = f"权限不足：{e}"
            print(f"禁用启动项失败: {error_msg}")
            item.error_message = error_msg
            return False
        except Exception as e:
            error_msg = str(e)
            print(f"禁用启动项失败: {error_msg}")
            item.error_message = error_msg
            return False

    def delete_startup_item(self, item: StartupItem) -> bool:
        """删除启动项"""
        try:
            if item.item_type == 'registry':
                # 删除注册表值
                result = self._parse_registry_path(item.path)
                if result is None:
                    print(f"无法解析注册表路径: {item.path}")
                    return False
                hkey, subkey_path = result

                # 检查是否为系统级注册表项
                if hkey == winreg.HKEY_LOCAL_MACHINE and not is_admin():
                    error_msg = "权限不足：删除系统级启动项需要管理员权限。请以管理员身份运行程序。"
                    print(f"删除启动项失败: {error_msg}")
                    item.error_message = error_msg
                    return False

                value_name = item.label
                with winreg.OpenKey(hkey, subkey_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, value_name)
                return True
            elif item.item_type == 'folder':
                # 删除快捷方式文件
                if os.path.exists(item.path):
                    os.remove(item.path)
                    return True
            elif item.item_type == 'task':
                # 删除计划任务
                result = subprocess.run(
                    ['schtasks', '/delete', '/tn', item.name, '/f'],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode != 0:
                    error_output = result.stderr.decode('gbk', errors='ignore')
                    print(f"删除计划任务失败: {error_output}")
                return result.returncode == 0
            return False
        except PermissionError as e:
            error_msg = f"权限不足：{e}"
            print(f"删除启动项失败: {error_msg}")
            item.error_message = error_msg
            return False
        except Exception as e:
            print(f"删除启动项失败: {e}")
            item.error_message = str(e)
            return False

    def set_delayed_startup(self, item: StartupItem, delay_seconds: int) -> bool:
        """设置延时启动

        Args:
            item: 启动项
            delay_seconds: 延迟秒数（30秒-10分钟）

        Returns:
            是否成功
        """
        try:
            # 检查权限（针对系统级注册表启动项）
            if item.item_type == 'registry':
                result = self._parse_registry_path(item.path)
                if result and result[0] == winreg.HKEY_LOCAL_MACHINE and not is_admin():
                    error_msg = "权限不足：设置系统级启动项的延迟启动需要管理员权限。请以管理员身份运行程序。"
                    print(f"设置延迟启动失败: {error_msg}")
                    item.error_message = error_msg
                    return False

            # 使用任务计划程序创建延迟启动任务
            task_name = f"z-tools延迟启动_{item.name}"
            # 清理可能存在的旧任务
            subprocess.run(
                ['schtasks', '/delete', '/tn', task_name, '/f'],
                capture_output=True,
                timeout=10
            )

            # 创建新任务
            command = item.command if item.command else item.path

            # 构建schtasks命令
            # /sc: schedule类型 (onlogon)
            # /delay: 延迟时间
            # /rl: 权限级别 (limited: 普通用户权限，避免UAC弹窗)
            cmd = [
                'schtasks', '/create',
                '/tn', task_name,
                '/tr', f'"{command}"',
                '/sc', 'onlogon',
                '/delay', f'0:00:{delay_seconds:02d}',
                '/rl', 'limited',
                '/f'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=10
            )

            if result.returncode != 0:
                error_output = result.stderr.decode('gbk', errors='ignore')
                print(f"创建延迟任务失败: {error_output}")
                item.error_message = f"创建延迟任务失败: {error_output}"
                return False

            print(f"成功设置延迟启动: {item.name}, 延迟 {delay_seconds} 秒")
            return True

        except Exception as e:
            print(f"设置延迟启动失败: {e}")
            item.error_message = str(e)
            return False

    def _parse_registry_path(self, path: str):
        """解析注册表路径

        Args:
            path: 路径格式可能是：
                1. "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run\\ValueName"
                2. "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run\\ValueName"
                3. "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run\\ValueName" (旧格式)

        Returns:
            (hkey, subkey_path) 或 None
        """
        if not path:
            return None

        # 处理带前缀的格式
        if path.startswith('HKLM\\') or path.startswith('HKEY_LOCAL_MACHINE\\'):
            prefix = 'HKLM\\' if path.startswith('HKLM\\') else 'HKEY_LOCAL_MACHINE\\'
            remaining = path[len(prefix):]
            # 查找匹配的注册表路径
            for reg_path in self.REGISTRY_STARTUP_PATHS:
                if reg_path[0] == winreg.HKEY_LOCAL_MACHINE and remaining.startswith(reg_path[1]):
                    # 返回 (hkey, subkey_path)，value_name 会在调用方从 item.label 获取
                    return reg_path
            return None

        elif path.startswith('HKCU\\') or path.startswith('HKEY_CURRENT_USER\\'):
            prefix = 'HKCU\\' if path.startswith('HKCU\\') else 'HKEY_CURRENT_USER\\'
            remaining = path[len(prefix):]
            for reg_path in self.REGISTRY_STARTUP_PATHS:
                if reg_path[0] == winreg.HKEY_CURRENT_USER and remaining.startswith(reg_path[1]):
                    return reg_path
            return None

        # 处理旧格式（没有前缀），尝试匹配
        for reg_path in self.REGISTRY_STARTUP_PATHS:
            if path.startswith(reg_path[1]):
                return reg_path

        return None

    def _backup_and_disable_registry_item(self, item: StartupItem) -> bool:
        """备份并禁用注册表启动项"""
        try:
            result = self._parse_registry_path(item.path)
            if result is None:
                error_msg = f"无法解析注册表路径: {item.path}"
                print(error_msg)
                item.error_message = error_msg
                return False
            hkey, subkey_path = result

            value_name = item.label

            # 读取当前值
            with winreg.OpenKey(hkey, subkey_path) as key:
                value_data, _ = winreg.QueryValueEx(key, value_name)

            # 创建备份键
            backup_key_path = subkey_path + "_Disabled"
            try:
                with winreg.CreateKey(hkey, backup_key_path) as backup_key:
                    winreg.SetValueEx(backup_key, value_name, 0, winreg.REG_SZ, value_data)
            except:
                pass

            # 删除原值
            with winreg.OpenKey(hkey, subkey_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, value_name)

            return True
        except PermissionError as e:
            error_msg = f"权限不足：无法禁用注册表项（{e}）"
            print(error_msg)
            item.error_message = error_msg
            return False
        except Exception as e:
            error_msg = f"备份注册表项失败: {e}"
            print(error_msg)
            item.error_message = error_msg
            return False

    def _restore_registry_item(self, item: StartupItem) -> bool:
        """从备份恢复注册表启动项"""
        try:
            result = self._parse_registry_path(item.path)
            if result is None:
                error_msg = f"无法解析注册表路径: {item.path}"
                print(error_msg)
                item.error_message = error_msg
                return False
            hkey, subkey_path = result

            value_name = item.label

            # 从备份键读取
            backup_key_path = subkey_path + "_Disabled"
            try:
                with winreg.OpenKey(hkey, backup_key_path) as backup_key:
                    value_data, _ = winreg.QueryValueEx(backup_key, value_name)

                # 恢复到原位置
                with winreg.CreateKey(hkey, subkey_path) as key:
                    winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, value_data)

                # 从备份键删除
                with winreg.OpenKey(hkey, backup_key_path, 0, winreg.KEY_SET_VALUE) as backup_key:
                    winreg.DeleteValue(backup_key, value_name)

                return True
            except FileNotFoundError:
                return False
        except PermissionError as e:
            error_msg = f"权限不足：无法恢复注册表项（{e}）"
            print(error_msg)
            item.error_message = error_msg
            return False
        except Exception as e:
            error_msg = f"恢复注册表项失败: {e}"
            print(error_msg)
            item.error_message = error_msg
            return False

    def _backup_shortcut_item(self, item: StartupItem) -> bool:
        """备份启动文件夹快捷方式"""
        try:
            # 创建备份文件夹
            os.makedirs(self.BACKUP_FOLDER, exist_ok=True)

            # 移动文件到备份文件夹
            backup_path = os.path.join(self.BACKUP_FOLDER, os.path.basename(item.path))
            shutil.move(item.path, backup_path)
            return True
        except PermissionError as e:
            error_msg = f"权限不足：无法备份快捷方式（{e}）"
            print(error_msg)
            item.error_message = error_msg
            return False
        except Exception as e:
            error_msg = f"备份快捷方式失败: {e}"
            print(error_msg)
            item.error_message = error_msg
            return False

    def _restore_shortcut_item(self, item: StartupItem) -> bool:
        """从备份恢复快捷方式"""
        try:
            # 找到备份文件
            backup_path = os.path.join(self.BACKUP_FOLDER, os.path.basename(item.path))

            if os.path.exists(backup_path):
                # 确定原始位置
                if "APPDATA" in item.path:
                    original_folder = self.STARTUP_FOLDERS[0]
                else:
                    original_folder = self.STARTUP_FOLDERS[1]

                # 移回原位置
                original_path = os.path.join(original_folder, os.path.basename(item.path))
                shutil.move(backup_path, original_path)
                return True
            return False
        except PermissionError as e:
            error_msg = f"权限不足：无法恢复快捷方式（{e}）"
            print(error_msg)
            item.error_message = error_msg
            return False
        except Exception as e:
            error_msg = f"恢复快捷方式失败: {e}"
            print(error_msg)
            item.error_message = error_msg
            return False

    def stop(self):
        """停止扫描"""
        self.running = False


class WindowsStartupManagerThread(threading.Thread):
    """Windows 启动项扫描线程"""

    def __init__(self, manager: WindowsStartupManager):
        super().__init__()
        self.manager = manager
        self.daemon = True

    def run(self):
        """运行扫描"""
        self.manager.scan()

    def stop(self):
        """停止扫描"""
        self.manager.stop()
