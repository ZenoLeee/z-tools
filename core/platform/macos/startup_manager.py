"""
macOS 平台启动项管理模块
管理 LaunchAgents 和 LaunchDaemons
"""
import os
import plistlib
import threading
from typing import List, Callable, Dict, Any
import datetime

# 添加项目根目录到路径
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


class StartupItem:
    """启动项信息类"""

    def __init__(self, name: str, path: str, label: str = "",
                 is_valid: bool = False, is_enabled: bool = False,
                 error_message: str = "", item_type: str = "unknown"):
        self.name = name
        self.path = path
        self.label = label
        self.is_valid = is_valid
        self.is_enabled = is_enabled
        self.error_message = error_message
        self.item_type = item_type  # 'launch_agent', 'launch_daemon', 'login_item'

    def __repr__(self):
        return f"StartupItem({self.label}, {self.item_type}, valid={self.is_valid})"


class MacStartupManager:
    """macOS 启动项管理器"""

    def __init__(self):
        self.running = True
        self.startup_items = []

        # 回调函数
        self.progress_callback: Callable[[int, int, str], None] = None
        self.found_callback: Callable[[StartupItem], None] = None
        self.finished_callback: Callable = None

    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """设置进度回调"""
        self.progress_callback = callback

    def set_found_callback(self, callback: Callable[[StartupItem], None]):
        """设置发现启动项回调"""
        self.found_callback = callback

    def set_finished_callback(self, callback: Callable):
        """设置完成回调"""
        self.finished_callback = callback

    def scan(self):
        """扫描启动项"""
        try:
            self._emit_progress(0, 100, "正在初始化扫描...")

            # 扫描用户 LaunchAgents
            self._emit_progress(10, 100, "正在扫描用户 LaunchAgents...")
            self.scan_launch_agents(
                os.path.expanduser("~/Library/LaunchAgents"),
                "user_launch_agent"
            )

            if not self.running:
                return

            # 扫描全局 LaunchAgents
            self._emit_progress(40, 100, "正在扫描全局 LaunchAgents...")
            self.scan_launch_agents(
                "/Library/LaunchAgents",
                "global_launch_agent"
            )

            if not self.running:
                return

            # 扫描 LaunchDaemons（系统级）
            self._emit_progress(70, 100, "正在扫描 LaunchDaemons...")
            self.scan_launch_agents(
                "/Library/LaunchDaemons",
                "launch_daemon"
            )

            if not self.running:
                return

            # 扫描登录项
            self._emit_progress(90, 100, "正在扫描登录项...")
            self.scan_login_items()

            # 扫描完成
            if self.running and self.finished_callback:
                self.finished_callback()

        except Exception as e:
            print(f"macOS 启动项扫描出错: {e}")
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

    def scan_launch_agents(self, directory: str, item_type: str):
        """扫描 LaunchAgents/LaunchDaemons 目录"""
        if not os.path.exists(directory):
            return

        try:
            plist_files = [f for f in os.listdir(directory) if f.endswith('.plist')]

            for idx, plist_file in enumerate(plist_files):
                if not self.running:
                    break

                plist_path = os.path.join(directory, plist_file)
                self.process_launch_item(plist_path, item_type)

                # 更新进度
                if item_type == "user_launch_agent":
                    progress = 10 + int((idx + 1) / len(plist_files) * 30)
                elif item_type == "global_launch_agent":
                    progress = 40 + int((idx + 1) / len(plist_files) * 30)
                else:
                    progress = 70 + int((idx + 1) / len(plist_files) * 20)

                self._emit_progress(progress, 100, f"正在扫描: {plist_file}")

        except (PermissionError, OSError) as e:
            print(f"无法访问目录 {directory}: {e}")
        except Exception as e:
            print(f"扫描目录 {directory} 出错: {e}")

    def process_launch_item(self, plist_path: str, item_type: str):
        """处理单个 LaunchAgent/LaunchDaemon 配置文件"""
        try:
            with open(plist_path, 'rb') as f:
                plist_data = plistlib.load(f)

            # 获取 Label（启动项标识）
            label = plist_data.get('Label', os.path.basename(plist_path))

            # 获取程序路径
            program_path = None
            if 'Program' in plist_data:
                program_path = plist_data['Program']
            elif 'ProgramArguments' in plist_data and plist_data['ProgramArguments']:
                program_path = plist_data['ProgramArguments'][0]

            # 检查是否存在
            is_valid = True
            error_message = ""

            if program_path:
                # 展开环境变量
                program_path = os.path.expandvars(program_path)

                if not os.path.exists(program_path):
                    is_valid = False
                    error_message = f"程序不存在: {program_path}"
            else:
                # 没有 Program 键，可能是其他类型的启动项
                # 标记为有效但不检查程序路径
                pass

            # 检查是否启用（通过检查是否已加载）
            is_enabled = self.is_launch_item_loaded(label)

            # 创建启动项对象
            item = StartupItem(
                name=os.path.basename(plist_path),
                path=plist_path,
                label=label,
                is_valid=is_valid,
                is_enabled=is_enabled,
                error_message=error_message,
                item_type=item_type
            )

            # 总是发射信号（包括有效的和无效的）
            self._emit_found(item)

        except Exception as e:
            print(f"处理 LaunchItem {plist_path} 出错: {e}")

            # 创建无效项
            item = StartupItem(
                name=os.path.basename(plist_path),
                path=plist_path,
                label="",
                is_valid=False,
                is_enabled=False,
                error_message=f"解析失败: {str(e)}",
                item_type=item_type
            )
            self._emit_found(item)

    def is_launch_item_loaded(self, label: str) -> bool:
        """检查启动项是否已加载"""
        try:
            import subprocess
            result = subprocess.run(
                ['launchctl', 'list', label],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def scan_login_items(self):
        """扫描登录项（通过用户偏好设置）"""
        # macOS 的登录项存储在多个位置
        # 1. 旧版本：com.apple.loginitems.plist
        # 2. 新版本：com.apple.loginitems.plist (使用新格式)

        login_items_plist = os.path.expanduser(
            "~/Library/Preferences/com.apple.loginitems.plist"
        )

        if not os.path.exists(login_items_plist):
            return

        try:
            with open(login_items_plist, 'rb') as f:
                plist_data = plistlib.load(f)

            # 旧格式：AutoLaunchItems
            if 'AutoLaunchItems' in plist_data:
                auto_launch_items = plist_data['AutoLaunchItems']
                for item in auto_launch_items:
                    if not self.running:
                        break

                    self.process_login_item(item, "old_login_item")

            # 新格式：SessionItems
            if 'SessionItems' in plist_data:
                session_items = plist_data['SessionItems'].get('CustomListItems', [])
                for item in session_items:
                    if not self.running:
                        break

                    self.process_login_item(item, "new_login_item")

        except Exception as e:
            print(f"扫描登录项出错: {e}")

    def process_login_item(self, item_data: Dict[str, Any], item_type: str):
        """处理单个登录项"""
        try:
            # 获取别名数据（AliasData）
            alias_data = item_data.get('Alias', {})

            # 简化处理：尝试获取名称
            name = item_data.get('Name', 'Unknown')

            # 从别名数据中提取路径（复杂，这里简化处理）
            # 实际需要解析 AliasData 的二进制格式

            # 创建登录项对象（简化版）
            item = StartupItem(
                name=name,
                path="Login Item",
                label=name,
                is_valid=True,  # 默认有效，因为路径解析复杂
                is_enabled=True,
                error_message="",
                item_type=item_type
            )

            self._emit_found(item)

        except Exception as e:
            print(f"处理登录项出错: {e}")

    def enable_startup_item(self, item: StartupItem) -> bool:
        """启用启动项"""
        try:
            import subprocess

            if item.item_type in ['user_launch_agent', 'global_launch_agent']:
                # 使用 launchctl 加载
                result = subprocess.run(
                    ['launchctl', 'load', item.path],
                    capture_output=True,
                    timeout=10
                )
                return result.returncode == 0
            elif item.item_type == 'launch_daemon':
                # 需要管理员权限
                result = subprocess.run(
                    ['sudo', 'launchctl', 'load', item.path],
                    capture_output=True,
                    timeout=10
                )
                return result.returncode == 0
            else:
                return False

        except Exception as e:
            print(f"启用启动项失败: {e}")
            return False

    def disable_startup_item(self, item: StartupItem) -> bool:
        """禁用启动项"""
        try:
            import subprocess

            if item.item_type in ['user_launch_agent', 'global_launch_agent']:
                # 使用 launchctl 卸载
                result = subprocess.run(
                    ['launchctl', 'unload', item.path],
                    capture_output=True,
                    timeout=10
                )
                return result.returncode == 0
            elif item.item_type == 'launch_daemon':
                # 需要管理员权限
                result = subprocess.run(
                    ['sudo', 'launchctl', 'unload', item.path],
                    capture_output=True,
                    timeout=10
                )
                return result.returncode == 0
            else:
                return False

        except Exception as e:
            print(f"禁用启动项失败: {e}")
            return False

    def delete_startup_item(self, item: StartupItem) -> bool:
        """删除启动项配置文件"""
        try:
            # 先禁用
            self.disable_startup_item(item)

            # 删除配置文件
            if os.path.exists(item.path):
                os.remove(item.path)
                return True

            return False

        except Exception as e:
            print(f"删除启动项失败: {e}")
            return False

    def stop(self):
        """停止扫描"""
        self.running = False


class MacStartupManagerThread(threading.Thread):
    """macOS 启动项扫描线程"""

    def __init__(self, manager: MacStartupManager):
        super().__init__()
        self.manager = manager
        self.daemon = True

    def run(self):
        """运行扫描"""
        self.manager.scan()

    def stop(self):
        """停止扫描"""
        self.manager.stop()
