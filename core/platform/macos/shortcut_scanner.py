"""
macOS 平台快捷方式扫描模块
处理 .alias、.webloc 和 Dock 配置
"""
import os
import plistlib
import json
import threading
from typing import List, Callable, Dict, Any
import datetime

# 添加项目根目录到路径
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from core.shortcut_scanner import ShortcutInfo


class MacShortcutScanner:
    """macOS 快捷方式扫描器"""

    def __init__(self):
        self.running = True
        self.scanned_files_count = 0
        self.total_files_estimate = 0
        self.shortcuts = []

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
            self._emit_progress(0, 100, "正在初始化扫描...")

            # 扫描 .alias 文件
            self.scan_alias_files()

            if not self.running:
                return

            # 扫描 .webloc 文件
            self._emit_progress(30, 100, "正在扫描网页链接...")
            self.scan_webloc_files()

            if not self.running:
                return

            # 扫描 Dock 配置
            self._emit_progress(60, 100, "正在扫描 Dock 配置...")
            self.scan_dock_items()

            if not self.running:
                return

            # 扫描最近使用的项目
            self._emit_progress(80, 100, "正在扫描最近使用的项目...")
            self.scan_recent_items()

            # 扫描完成
            if self.running and self.finished_callback:
                self.finished_callback()

        except Exception as e:
            print(f"macOS 快捷方式扫描出错: {e}")
            import traceback
            traceback.print_exc()

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

    def scan_alias_files(self):
        """扫描 .alias 文件"""
        home = os.path.expanduser("~")

        # 常见的位置
        scan_paths = [
            os.path.join(home, "Desktop"),
            os.path.join(home, "Documents"),
            os.path.join(home, "Downloads"),
            os.path.join(home, "Applications"),
        ]

        total_paths = len(scan_paths)

        for idx, scan_path in enumerate(scan_paths):
            if not self.running:
                break

            if os.path.exists(scan_path):
                progress = 20 + int((idx + 1) / total_paths * 10)
                self._emit_progress(progress, 100, f"正在扫描 .alias 文件: {os.path.basename(scan_path)}")

                try:
                    for root, dirs, files in os.walk(scan_path):
                        if not self.running:
                            break

                        for file in files:
                            if not self.running:
                                break

                            if file.endswith('.alias'):
                                alias_path = os.path.join(root, file)
                                self.process_alias_file(alias_path)
                except Exception as e:
                    print(f"扫描目录 {scan_path} 出错: {e}")

    def process_alias_file(self, alias_path: str):
        """
        处理 .alias 文件
        .alias 文件是 macOS 的二进制格式，解析比较复杂
        我们使用基础的文件检查方法
        """
        try:
            # 读取 .alias 文件的目标路径（简化版）
            # 完整解析需要使用 Carbon APIs，这里使用简化方法

            # 尝试通过文件名推断目标
            alias_name = os.path.basename(alias_path)
            target_name = os.path.splitext(alias_name)[0]

            # 在常见位置查找目标文件
            target_path = self.find_alias_target(alias_path, target_name)

            is_valid = target_path is not None
            error_message = "" if is_valid else "目标文件不存在"

            shortcut = ShortcutInfo(
                name=alias_name,
                path=alias_path,
                target_path=target_path or "",
                is_valid=is_valid,
                error_message=error_message,
                shortcut_type="alias",
                display_name=alias_name
            )

            if not is_valid:
                self._emit_found(shortcut)

        except Exception as e:
            print(f"处理 .alias 文件 {alias_path} 出错: {e}")

    def find_alias_target(self, alias_path: str, target_name: str) -> str:
        """查找 alias 目标文件"""
        # 在父目录和常见位置查找
        search_dirs = [
            os.path.dirname(alias_path),
            os.path.expanduser("~/Applications"),
            "/Applications",
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Documents"),
        ]

        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                continue

            # 查找匹配的文件或目录
            try:
                for item in os.listdir(search_dir):
                    item_name = os.path.splitext(item)[0]
                    if item_name.lower() == target_name.lower():
                        return os.path.join(search_dir, item)
            except (PermissionError, OSError):
                continue

        return None

    def scan_webloc_files(self):
        """扫描 .webloc 文件（网页链接）"""
        home = os.path.expanduser("~")

        scan_paths = [
            os.path.join(home, "Desktop"),
            os.path.join(home, "Documents"),
            os.path.join(home, "Downloads"),
        ]

        for scan_path in scan_paths:
            if not self.running:
                break

            if os.path.exists(scan_path):
                try:
                    for root, dirs, files in os.walk(scan_path):
                        if not self.running:
                            break

                        for file in files:
                            if not self.running:
                                break

                            if file.endswith('.webloc'):
                                webloc_path = os.path.join(root, file)
                                self.process_webloc_file(webloc_path)
                except Exception as e:
                    print(f"扫描 .webloc 文件出错: {e}")

    def process_webloc_file(self, webloc_path: str):
        """处理 .webloc 文件"""
        try:
            # .webloc 文件是 XML 格式的 plist
            url = None

            try:
                with open(webloc_path, 'rb') as f:
                    plist = plistlib.load(f)
                    url = plist.get('URL', '')

                # 网页链接通常视为有效
                is_valid = bool(url)
                error_message = "" if is_valid else "无效的网页链接"

                shortcut = ShortcutInfo(
                    name=os.path.basename(webloc_path),
                    path=webloc_path,
                    target_path=url or "",
                    is_valid=is_valid,
                    error_message=error_message,
                    shortcut_type="webloc",
                    display_name=os.path.basename(webloc_path)
                )

                if not is_valid:
                    self._emit_found(shortcut)

            except Exception as e:
                print(f"解析 .webloc 文件失败 {webloc_path}: {e}")

        except Exception as e:
            print(f"处理 .webloc 文件 {webloc_path} 出错: {e}")

    def scan_dock_items(self):
        """扫描 Dock 配置中的项目"""
        dock_plist = os.path.expanduser("~/Library/Preferences/com.apple.dock.plist")

        if not os.path.exists(dock_plist):
            return

        try:
            with open(dock_plist, 'rb') as f:
                plist_data = plistlib.load(f)

            # 获取 Dock 中的应用列表
            persistent_apps = plist_data.get('persistent-apps', [])
            persistent_others = plist_data.get('persistent-others', [])

            # 检查应用
            for idx, app_item in enumerate(persistent_apps):
                if not self.running:
                    break

                try:
                    tile_data = app_item.get('tile-data', {})
                    file_data = tile_data.get('file-data', {})
                    app_path = file_data.get('_CFURLString', '')

                    if app_path:
                        is_valid = os.path.exists(app_path)
                        error_message = "" if is_valid else "应用不存在"

                        shortcut = ShortcutInfo(
                            name=os.path.basename(app_path),
                            path=f"Dock Item {idx}",
                            target_path=app_path,
                            is_valid=is_valid,
                            error_message=error_message,
                            shortcut_type="dock_app",
                            display_name=f"Dock: {os.path.basename(app_path)}"
                        )

                        if not is_valid:
                            self._emit_found(shortcut)

                except Exception as e:
                    print(f"处理 Dock 应用出错: {e}")

            # 检查其他项目（文件、文件夹等）
            for idx, other_item in enumerate(persistent_others):
                if not self.running:
                    break

                try:
                    tile_data = other_item.get('tile-data', '')
                    file_data = tile_data.get('file-data', {})
                    item_path = file_data.get('_CFURLString', '')

                    if item_path:
                        is_valid = os.path.exists(item_path)
                        error_message = "" if is_valid else "项目不存在"

                        shortcut = ShortcutInfo(
                            name=os.path.basename(item_path),
                            path=f"Dock Item (Other) {idx}",
                            target_path=item_path,
                            is_valid=is_valid,
                            error_message=error_message,
                            shortcut_type="dock_other",
                            display_name=f"Dock: {os.path.basename(item_path)}"
                        )

                        if not is_valid:
                            self._emit_found(shortcut)

                except Exception as e:
                    print(f"处理 Dock 其他项目出错: {e}")

        except Exception as e:
            print(f"解析 Dock 配置出错: {e}")

    def scan_recent_items(self):
        """扫描最近使用的项目"""
        recent_items_db = os.path.expanduser("~/Library/Application Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.ApplicationRecentDocuments")

        # 这个数据库格式复杂，这里只做简单的文件存在性检查
        # 实际实现可能需要更复杂的解析

        if not os.path.exists(recent_items_db):
            return

        try:
            # 简化的实现：检查最近项目文件夹
            pass
        except Exception as e:
            print(f"扫描最近项目出错: {e}")

    def stop(self):
        """停止扫描"""
        self.running = False
