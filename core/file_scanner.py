import os
import hashlib
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from PyQt5.QtCore import QThread, pyqtSignal, QObject


class FileInfo:
    """文件信息类"""

    def __init__(self, path: str, size: int = 0, modified_time: datetime = None,
                 md5_hash: str = "", is_duplicate: bool = False,
                 duplicate_group: int = 0, keep: bool = True):
        self.path = path  # 文件完整路径
        self.size = size  # 文件大小（字节）
        self.modified_time = modified_time or datetime.now()  # 修改时间
        self.md5_hash = md5_hash  # MD5哈希值
        self.is_duplicate = is_duplicate  # 是否为重复文件
        self.duplicate_group = duplicate_group  # 重复文件组ID
        self.keep = keep  # 是否保留（默认保留最新的）
        self.filename = os.path.basename(path)  # 文件名
        self.directory = os.path.dirname(path)  # 目录


class DuplicateScannerThread(QThread):
    """重复文件扫描线程"""

    # 信号定义
    scan_progress = pyqtSignal(int, int, str)  # 当前进度，总数，当前文件
    file_processed = pyqtSignal(int, int, str)  # 已处理文件数，总数，当前文件
    duplicate_found = pyqtSignal(object, int)  # 发现重复文件，组ID
    scan_finished = pyqtSignal(list, int, int, int)  # 文件列表，总数，重复组数，重复文件数

    def __init__(self, directories: List[str], file_types: List[str] = None,
                 min_size: int = 0, exclude_system: bool = True):
        super().__init__()
        self.directories = directories
        self.file_types = file_types or ["*"]  # 默认所有文件类型
        self.min_size = min_size  # 最小文件大小（字节）
        self.exclude_system = exclude_system  # 是否排除系统文件
        self.running = True
        self.total_files = 0
        self.processed_files = 0

        # 系统目录排除列表
        self.system_dirs = [
            r"C:\Windows",
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            r"C:\ProgramData",
            r"$Recycle.Bin",
            r"System Volume Information"
        ]

    def run(self):
        """执行扫描任务"""
        try:
            # 第一步：扫描文件并分组（按大小快速分组）
            self.scan_progress.emit(0, 100, "正在扫描文件...")

            # 使用字典按文件大小分组
            size_groups = {}
            all_files = []
            scanned_count = 0

            for directory in self.directories:
                if not self.running:
                    return

                # 扫描目录，收集文件信息
                files = self.scan_directory(directory)

                for file_info in files:
                    if not self.running:
                        return

                    all_files.append(file_info)

                    # 按大小分组
                    if file_info.size not in size_groups:
                        size_groups[file_info.size] = []
                    size_groups[file_info.size].append(file_info)

                    scanned_count += 1

                    # 更新扫描进度（25%用于扫描）
                    progress = min(int((scanned_count / max(len(all_files), 1)) * 25), 25)
                    if scanned_count % 100 == 0:  # 每100个文件更新一次进度
                        self.scan_progress.emit(progress, 100, f"已扫描 {scanned_count} 个文件")

            if not self.running:
                return

            # 第二步：对大小相同的文件计算部分哈希（50%进度）
            partial_hash_groups = {}
            processed_count = 0
            total_to_process = sum(len(files) for files in size_groups.values() if len(files) > 1)

            # 只处理大小相同的文件（可能有重复）
            for size, files in size_groups.items():
                if len(files) > 1:
                    for file_info in files:
                        if not self.running:
                            return

                        # 计算快速哈希（使用文件开头）
                        quick_hash = self.calculate_quick_hash(file_info.path)
                        file_info.md5_hash = quick_hash

                        # 按快速哈希分组
                        if quick_hash not in partial_hash_groups:
                            partial_hash_groups[quick_hash] = []
                        partial_hash_groups[quick_hash].append(file_info)

                        processed_count += 1

                        # 更新进度（25-75%）
                        progress = 25 + int((processed_count / max(total_to_process, 1)) * 50)
                        if processed_count % 100 == 0:
                            self.scan_progress.emit(
                                min(progress, 75),
                                100,
                                f"正在计算哈希... ({processed_count}/{total_to_process})"
                            )

            if not self.running:
                return

            # 第三步：对部分哈希相同的文件计算完整MD5（75-100%进度）
            duplicate_groups = {}
            duplicate_count = 0
            group_id = 1
            full_hash_count = 0
            total_full_hash = sum(len(files) for files in partial_hash_groups.values() if len(files) > 1)

            for quick_hash, files in partial_hash_groups.items():
                if len(files) > 1:
                    # 按完整MD5分组
                    full_hash_dict = {}

                    for file_info in files:
                        if not self.running:
                            return

                        # 计算完整MD5
                        full_md5 = self.calculate_md5(file_info.path)
                        file_info.md5_hash = full_md5

                        if full_md5 not in full_hash_dict:
                            full_hash_dict[full_md5] = []
                        full_hash_dict[full_md5].append(file_info)

                        full_hash_count += 1

                        # 更新进度（75-100%）
                        progress = 75 + int((full_hash_count / max(total_full_hash, 1)) * 25)
                        self.scan_progress.emit(
                            min(progress, 99),
                            100,
                            f"正在验证重复... ({full_hash_count}/{total_full_hash})"
                        )

                    # 标记重复文件
                    for full_md5, duplicate_files in full_hash_dict.items():
                        if len(duplicate_files) > 1:
                            # 按修改时间排序，最新的排前面
                            sorted_files = sorted(duplicate_files, key=lambda x: x.modified_time, reverse=True)

                            # 标记第一个为保留（最新），其余为删除
                            for i, file_info in enumerate(sorted_files):
                                file_info.is_duplicate = True
                                file_info.duplicate_group = group_id
                                file_info.keep = (i == 0)  # 只保留最新的

                                if i > 0:
                                    self.duplicate_found.emit(file_info, group_id)
                                    duplicate_count += 1

                            duplicate_groups[group_id] = sorted_files
                            group_id += 1

            # 完成
            self.scan_progress.emit(100, 100, "扫描完成")
            self.scan_finished.emit(
                all_files,
                len(all_files),
                len(duplicate_groups),
                duplicate_count
            )

        except Exception as e:
            print(f"重复文件扫描出错: {e}")
            import traceback
            traceback.print_exc()

    def scan_directory(self, directory: str) -> List[FileInfo]:
        """扫描目录中的文件"""
        files = []

        try:
            for root, dirs, filenames in os.walk(directory):
                if not self.running:
                    break

                # 排除系统目录
                if self.exclude_system:
                    dirs[:] = [d for d in dirs if not self.is_system_path(os.path.join(root, d))]

                for filename in filenames:
                    if not self.running:
                        break

                    file_path = os.path.join(root, filename)

                    # 排除系统文件
                    if self.exclude_system and self.is_system_path(file_path):
                        continue

                    # 检查文件类型
                    if not self.is_file_type_match(file_path):
                        continue

                    try:
                        # 获取文件大小
                        file_size = os.path.getsize(file_path)

                        # 检查文件大小是否满足最小要求
                        if file_size < self.min_size:
                            continue

                        # 获取修改时间
                        modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))

                        # 创建FileInfo对象（暂时不计算MD5）
                        file_info = FileInfo(
                            path=file_path,
                            size=file_size,
                            modified_time=modified_time,
                            md5_hash="",  # 稍后计算
                            is_duplicate=False,
                            duplicate_group=0,
                            keep=True
                        )

                        files.append(file_info)

                    except Exception as e:
                        print(f"处理文件失败 {file_path}: {e}")

        except Exception as e:
            print(f"扫描目录出错 {directory}: {e}")

        return files

    def scan_and_hash_directory(self, directory: str, total_size_bytes: int, start_scanned_size: int,
                                md5_dict: dict, file_objects: list) -> tuple:
        """扫描目录，计算文件MD5并更新进度"""
        scanned_size_bytes = start_scanned_size
        file_count = 0

        # 使用栈而不是递归来处理目录遍历
        dir_stack = [directory]

        while dir_stack and self.running:
            current_dir = dir_stack.pop()

            try:
                entries = os.listdir(current_dir)
            except (PermissionError, OSError):
                continue

            for entry in entries:
                if not self.running:
                    return scanned_size_bytes, file_count

                full_path = os.path.join(current_dir, entry)

                # 排除系统文件/目录
                if self.exclude_system and self.is_system_path(full_path):
                    continue

                try:
                    if os.path.isdir(full_path):
                        # 将子目录加入栈中
                        dir_stack.append(full_path)
                    else:
                        # 检查文件类型
                        if not self.is_file_type_match(full_path):
                            continue

                        # 获取文件信息
                        try:
                            file_size = os.path.getsize(full_path)

                            # 检查文件大小是否满足最小要求
                            if file_size < self.min_size:
                                continue

                            # 更新已扫描的大小
                            scanned_size_bytes += file_size
                            file_count += 1

                            # 更新进度（按已扫描的文件大小）
                            if total_size_bytes > 0:
                                progress = min(int((scanned_size_bytes / total_size_bytes) * 100), 99)
                                self.scan_progress.emit(
                                    progress,
                                    len(self.directories),
                                    f"正在处理: {os.path.basename(full_path)}"
                                )

                            # 获取文件MD5
                            file_info = self.get_file_info(full_path)
                            if file_info and file_info.md5_hash:
                                file_objects.append(file_info)

                                # 按MD5分组
                                if file_info.md5_hash not in md5_dict:
                                    md5_dict[file_info.md5_hash] = []
                                md5_dict[file_info.md5_hash].append(file_info)

                        except Exception as e:
                            print(f"处理文件失败 {full_path}: {e}")

                except (PermissionError, OSError):
                    pass

        return scanned_size_bytes, file_count

    def is_system_path(self, path: str) -> bool:
        """检查是否为系统路径"""
        path_lower = path.lower()

        # 检查是否在系统目录中
        for system_dir in self.system_dirs:
            if system_dir.lower() in path_lower:
                return True

        # 检查是否为隐藏文件/系统文件
        if os.path.basename(path).startswith('.'):
            return True

        try:
            # 在Windows上检查文件属性
            import stat
            if os.name == 'nt':
                import win32api, win32con
                attrs = win32api.GetFileAttributes(path)
                if attrs & (win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM):
                    return True
            else:
                # Unix-like系统
                if os.stat(path).st_file_attributes & stat.UF_HIDDEN:
                    return True
        except:
            pass

        return False

    def is_file_type_match(self, file_path: str) -> bool:
        """检查文件类型是否匹配"""
        if "*" in self.file_types:
            return True

        ext = os.path.splitext(file_path)[1].lower()
        return any(ft.lower() == ext for ft in self.file_types)

    def get_file_info(self, file_path: str) -> Optional[FileInfo]:
        """获取文件信息并计算MD5"""
        try:
            # 获取文件大小和修改时间
            stat_info = os.stat(file_path)
            size = stat_info.st_size
            modified_time = datetime.fromtimestamp(stat_info.st_mtime)

            # 计算MD5（对于大文件，使用快速方法）
            md5_hash = ""
            if size < 50 * 1024 * 1024:  # 小于50MB的文件才计算完整MD5
                md5_hash = self.calculate_md5(file_path)
            else:
                # 对于大文件，使用快速哈希
                md5_hash = self.calculate_quick_hash(file_path)

            return FileInfo(file_path, size, modified_time, md5_hash)

        except Exception as e:
            print(f"获取文件信息失败 {file_path}: {e}")
            return None

    def calculate_md5(self, file_path: str, chunk_size: int = 8192) -> str:
        """计算文件的MD5哈希值"""
        md5_hash = hashlib.md5()

        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    if not self.running:
                        return ""
                    md5_hash.update(chunk)
        except:
            return ""

        return md5_hash.hexdigest()

    def calculate_quick_hash(self, file_path: str) -> str:
        """计算文件的快速哈希（用于大文件）"""
        try:
            stat_info = os.stat(file_path)
            size = stat_info.st_size

            # 使用文件大小+首尾各4KB内容计算哈希
            md5_hash = hashlib.md5()
            md5_hash.update(str(size).encode())

            with open(file_path, 'rb') as f:
                # 读取文件开头4KB
                head = f.read(4096)
                md5_hash.update(head)

                # 如果文件大于8KB，读取文件末尾4KB
                if size > 8192:
                    f.seek(size - 4096)
                    tail = f.read(4096)
                    md5_hash.update(tail)

            return md5_hash.hexdigest()
        except:
            return f"size_{size}"  # 回退到使用文件大小

    def stop(self):
        """停止扫描"""
        self.running = False


class LargeFileScannerThread(QThread):
    """大文件扫描线程"""

    # 信号定义
    scan_progress = pyqtSignal(int, int, str)  # 当前进度，总数，当前目录
    large_file_found = pyqtSignal(object)  # 发现大文件
    scan_finished = pyqtSignal(list, int, int)  # 文件列表，总数，总大小(MB)

    def __init__(self, directories: List[str], min_size_mb: int = 10,
                 max_results: int = 1000, exclude_system: bool = True):
        super().__init__()
        self.directories = directories
        self.min_size_mb = min_size_mb  # 最小文件大小（MB）
        self.min_size_bytes = min_size_mb * 1024 * 1024
        self.max_results = max_results  # 最大结果数
        self.exclude_system = exclude_system
        self.running = True
        self.large_files = []

        # 系统目录排除列表
        self.system_dirs = [
            r"C:\Windows",
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            r"C:\ProgramData",
            r"$Recycle.Bin",
            r"System Volume Information",
            r"C:\$Windows.~WS",  # Windows更新临时文件
            r"C:\$Windows.~BT"  # Windows更新备份
        ]

    def run(self):
        """执行扫描任务"""
        try:
            # 第一步：快速计算目标目录的总大小（使用psutil）
            total_size_bytes = 0

            for directory in self.directories:
                if not self.running:
                    return

                if os.path.exists(directory):
                    try:
                        # 使用psutil获取磁盘使用情况
                        import psutil

                        # 获取目录所在的驱动器
                        if os.path.ismount(directory) or len(directory) <= 3:  # 根目录
                            usage = psutil.disk_usage(directory)
                            total_size_bytes += usage.used  # 已使用的磁盘空间
                            print(f"磁盘 {directory} 已使用空间: {usage.used / (1024 * 1024 * 1024):.2f} GB")
                        else:
                            # 对于子目录，获取其所在的驱动器
                            drive = os.path.splitdrive(directory)[0] + "\\"
                            if os.path.exists(drive):
                                usage = psutil.disk_usage(drive)
                                # 估计该目录的大小（假设均匀分布）
                                # 这里简化处理：只使用磁盘已使用空间
                                total_size_bytes += usage.used
                                print(f"驱动器 {drive} 已使用空间: {usage.used / (1024 * 1024 * 1024):.2f} GB")
                    except ImportError:
                        # 如果psutil不可用，使用简化的估算
                        print("未安装psutil，使用简化的估算方法")
                        # 简化的估算：假设目录大小为1GB
                        total_size_bytes += 1024 * 1024 * 1024

            if total_size_bytes == 0:
                # 设置一个默认值避免除零错误
                total_size_bytes = 1024 * 1024 * 1024  # 1GB

            # 第二步：扫描大文件，按已扫描的文件大小更新进度
            scanned_size_bytes = 0

            # 发送初始进度（0%）
            self.scan_progress.emit(0, 100, "开始扫描大文件...")

            for directory in self.directories:
                if not self.running:
                    return

                if os.path.exists(directory):
                    # 扫描目录
                    scanned_size_bytes = self.scan_directory_with_progress(directory, total_size_bytes,
                                                                           scanned_size_bytes)

                    if len(self.large_files) >= self.max_results:
                        break

            # 扫描完成
            self.scan_progress.emit(100, 100, "扫描完成")

            # 按文件大小排序
            self.large_files.sort(key=lambda x: x.size, reverse=True)

            # 计算总大小
            total_size_mb = sum(f.size for f in self.large_files) / (1024 * 1024)

            # 发送完成信号
            self.scan_finished.emit(
                self.large_files,
                len(self.large_files),
                int(total_size_mb)
            )

        except Exception as e:
            print(f"大文件扫描出错: {e}")
            import traceback
            traceback.print_exc()

    def scan_directory_with_progress(self, directory: str, total_size_bytes: int, start_scanned_size: int) -> int:
        """扫描目录并更新进度（优化版，避免递归过深）"""
        scanned_size_bytes = start_scanned_size

        try:
            # 使用栈而不是递归来处理目录遍历，避免栈溢出
            dir_stack = [directory]
            file_count = 0
            last_progress_update = 0

            while dir_stack and self.running:
                current_dir = dir_stack.pop()

                try:
                    entries = os.listdir(current_dir)
                except (PermissionError, OSError):
                    continue

                for entry in entries:
                    if not self.running:
                        return scanned_size_bytes

                    full_path = os.path.join(current_dir, entry)

                    # 排除系统文件/目录
                    if self.exclude_system and self.is_system_path(full_path):
                        continue

                    try:
                        if os.path.isdir(full_path):
                            # 将子目录加入栈中（使用栈代替递归）
                            dir_stack.append(full_path)
                        else:
                            # 处理文件
                            try:
                                file_size = os.path.getsize(full_path)

                                # 更新已扫描的大小
                                scanned_size_bytes += file_size
                                file_count += 1

                                # 每扫描100个文件或每扫描1MB更新一次进度，避免过于频繁
                                if file_count % 100 == 0 or file_count == 1:
                                    if total_size_bytes > 0:
                                        progress = min(int((scanned_size_bytes / total_size_bytes) * 100), 99)
                                        # 只有进度有变化才发送信号
                                        if progress != last_progress_update:
                                            self.scan_progress.emit(progress, 100, f"已扫描 {file_count} 个文件")
                                            last_progress_update = progress

                                # 检查是否为大文件
                                if file_size >= self.min_size_bytes:
                                    modified_time = datetime.fromtimestamp(os.path.getmtime(full_path))
                                    file_info = FileInfo(full_path, file_size, modified_time)
                                    self.large_files.append(file_info)
                                    self.large_file_found.emit(file_info)

                                    if len(self.large_files) >= self.max_results:
                                        return scanned_size_bytes

                            except (PermissionError, OSError):
                                pass

                    except (PermissionError, OSError):
                        pass

        except Exception as e:
            print(f"扫描目录出错 {directory}: {e}")

        return scanned_size_bytes

    def calculate_directory_size(self, directory: str) -> int:
        """计算目录的总大小"""
        total_size = 0

        try:
            for root, dirs, files in os.walk(directory):
                # 排除系统目录
                if self.exclude_system:
                    dirs[:] = [d for d in dirs if not self.is_system_path(os.path.join(root, d))]

                for file in files:
                    file_path = os.path.join(root, file)

                    # 排除系统文件
                    if self.exclude_system and self.is_system_path(file_path):
                        continue

                    try:
                        total_size += os.path.getsize(file_path)
                    except:
                        pass
        except Exception as e:
            print(f"计算目录大小出错 {directory}: {e}")

        return total_size

    def scan_directory(self, directory: str):
        """扫描目录中的大文件"""
        if not os.path.exists(directory):
            return

        try:
            for root, dirs, files in os.walk(directory):
                if not self.running:
                    break

                # 排除系统目录
                if self.exclude_system:
                    dirs[:] = [d for d in dirs if not self.is_system_path(os.path.join(root, d))]

                for file in files:
                    if not self.running:
                        break

                    file_path = os.path.join(root, file)

                    # 排除系统文件
                    if self.exclude_system and self.is_system_path(file_path):
                        continue

                    try:
                        # 获取文件大小
                        file_size = os.path.getsize(file_path)

                        # 检查是否为大文件
                        if file_size >= self.min_size_bytes:
                            modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                            file_info = FileInfo(file_path, file_size, modified_time)
                            self.large_files.append(file_info)
                            self.large_file_found.emit(file_info)

                            if len(self.large_files) >= self.max_results:
                                return

                    except:
                        pass

        except Exception as e:
            print(f"扫描目录出错 {directory}: {e}")

    def is_system_path(self, path: str) -> bool:
        """检查是否为系统路径（简化版）"""
        try:
            path_lower = path.lower()

            # 检查是否在系统目录中
            for system_dir in self.system_dirs:
                if system_dir.lower() in path_lower:
                    return True

            # 检查是否为隐藏文件/系统文件
            if os.path.basename(path).startswith('.'):
                return True

            # 检查常见系统文件
            system_files = [
                "pagefile.sys",
                "hiberfil.sys",
                "swapfile.sys",
                "windows.edb"
            ]

            if os.path.basename(path).lower() in system_files:
                return True

            # 简化权限检查，避免复杂操作
            try:
                # 检查是否为隐藏文件（简化的Windows检查）
                if os.name == 'nt' and os.path.exists(path):
                    import ctypes
                    FILE_ATTRIBUTE_HIDDEN = 0x2
                    FILE_ATTRIBUTE_SYSTEM = 0x4
                    attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
                    if attrs != -1 and (attrs & (FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)):
                        return True
            except:
                pass

            return False

        except Exception:
            # 如果检查失败，出于安全考虑，将其视为系统文件
            return True

    def stop(self):
        """停止扫描"""
        self.running = False