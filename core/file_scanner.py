import os
import hashlib
import threading
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Callable


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


class DuplicateScannerThread(threading.Thread):
    """重复文件扫描线程"""

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

        # 回调函数
        self.scan_progress_callback: Callable[[int, int, str], None] = None
        self.file_progress_callback: Callable[[int, int, str], None] = None
        self.duplicate_callback: Callable[[FileInfo, int], None] = None
        self.finished_callback: Callable[[List, int, int, int], None] = None

    def set_scan_progress_callback(self, callback: Callable[[int, int, str], None]):
        self.scan_progress_callback = callback

    def set_file_progress_callback(self, callback: Callable[[int, int, str], None]):
        self.file_progress_callback = callback

    def set_duplicate_callback(self, callback: Callable[[FileInfo, int], None]):
        self.duplicate_callback = callback

    def set_finished_callback(self, callback: Callable[[List, int, int, int], None]):
        self.finished_callback = callback

    def _emit_scan_progress(self, current: int, total: int, text: str):
        if self.scan_progress_callback:
            self.scan_progress_callback(current, total, text)

    def _emit_file_progress(self, progress: int, total_files: int, text: str):
        if self.file_progress_callback:
            self.file_progress_callback(progress, total_files, text)

    def _emit_duplicate(self, file_info: FileInfo, group_id: int):
        if self.duplicate_callback:
            self.duplicate_callback(file_info, group_id)

    def _emit_finished(self, file_objects: List, total_files: int, duplicate_groups: int, duplicate_files: int):
        if self.finished_callback:
            self.finished_callback(file_objects, total_files, duplicate_groups, duplicate_files)

    def run(self):
        """执行扫描任务"""
        try:
            # 第一步：快速估算目标目录大小（不精确遍历，快速估算）
            self._emit_scan_progress(0, 100, "正在估算目录大小...")

            total_size_bytes = self.estimate_directory_size()

            if total_size_bytes == 0:
                total_size_bytes = 1024 * 1024 * 1024  # 默认1GB

            print(f"目标目录估算大小: {total_size_bytes / (1024 * 1024):.2f} MB")

            # 第二步：边扫描边判断重复（同步进行）
            scanned_size_bytes = 0
            all_files = []
            size_groups = {}  # 按大小分组的字典
            group_id = 1
            duplicate_count = 0
            file_count = 0
            last_progress = 0

            self._emit_scan_progress(0, 100, "开始扫描文件...")

            for directory in self.directories:
                if not self.running:
                    return

                # 遍历目录
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

                            # 更新已扫描的大小（用于进度条）
                            scanned_size_bytes += file_size
                            file_count += 1

                            # 计算进度
                            progress = min(int((scanned_size_bytes / total_size_bytes) * 100), 99)

                            # 只有进度变化时才更新（避免过于频繁）
                            if progress != last_progress and file_count % 10 == 0:
                                self._emit_scan_progress(progress, 100, f"正在扫描: {file_path}")
                                last_progress = progress

                            # 获取修改时间
                            modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))

                            # 创建FileInfo对象
                            file_info = FileInfo(
                                path=file_path,
                                size=file_size,
                                modified_time=modified_time,
                                md5_hash="",
                                is_duplicate=False,
                                duplicate_group=0,
                                keep=True
                            )

                            all_files.append(file_info)

                            # 按大小分组
                            if file_size not in size_groups:
                                size_groups[file_size] = []
                            size_groups[file_size].append(file_info)

                            # 如果该大小的文件超过1个，立即计算MD5判断是否重复
                            if len(size_groups[file_size]) > 1:
                                # 为这个大小的所有文件计算MD5
                                for fi in size_groups[file_size]:
                                    if not fi.md5_hash:  # 只计算未计算的
                                        fi.md5_hash = self.calculate_md5(fi.path)

                                # 按MD5分组
                                md5_groups = {}
                                for fi in size_groups[file_size]:
                                    if fi.md5_hash not in md5_groups:
                                        md5_groups[fi.md5_hash] = []
                                    md5_groups[fi.md5_hash].append(fi)

                                # 找出重复的文件组
                                for md5_hash, files_with_same_md5 in md5_groups.items():
                                    if len(files_with_same_md5) > 1 and md5_hash:  # 确实有重复且有MD5
                                        # 按修改时间排序，最新的排前面
                                        sorted_files = sorted(files_with_same_md5, key=lambda x: x.modified_time, reverse=True)

                                        # 检查是否已经分配过组ID
                                        if sorted_files[0].duplicate_group == 0:
                                            # 还没有组ID，需要分配
                                            for i, fi in enumerate(sorted_files):
                                                fi.is_duplicate = True
                                                fi.duplicate_group = group_id
                                                fi.keep = (i == 0)

                                                if i > 0:  # 标记为重复
                                                    self._emit_duplicate(fi, group_id)
                                                    duplicate_count += 1

                                            group_id += 1

                        except Exception as e:
                            print(f"处理文件失败 {file_path}: {e}")

            # 完成
            self._emit_scan_progress(100, 100, "扫描完成")

            # 统计重复组数
            duplicate_groups = len(set(f.duplicate_group for f in all_files if f.is_duplicate and f.duplicate_group > 0))

            self._emit_finished(
                all_files,
                len(all_files),
                duplicate_groups,
                duplicate_count
            )

        except Exception as e:
            print(f"重复文件扫描出错: {e}")
            import traceback
            traceback.print_exc()

    def estimate_directory_size(self) -> int:
        """快速估算目录总大小（使用采样估算，避免完全遍历）"""
        total_size = 0

        for directory in self.directories:
            if not self.running:
                return total_size

            if not os.path.exists(directory):
                continue

            # 无论是根目录还是子目录，都使用采样估算
            # 这样更准确，因为会应用相同的过滤规则
            try:
                sample_size = 0
                sample_count = 0
                max_depth = 3  # 只扫描前3层
                max_samples = 2000  # 最多采样2000个文件

                # 使用os.scandir()快速遍历（比os.walk快）
                dir_stack = [(directory, 0)]

                while dir_stack and self.running:
                    current_dir, depth = dir_stack.pop()

                    if depth > max_depth:
                        continue

                    try:
                        with os.scandir(current_dir) as entries:
                            for entry in entries:
                                if not self.running:
                                    break

                                # 达到采样数量限制就停止
                                if sample_count >= max_samples:
                                    break

                                try:
                                    if entry.is_dir(follow_symlinks=False):
                                        # 排除系统目录
                                        if self.exclude_system and self.is_system_path(entry.path):
                                            continue
                                        # 限制深度和采样数量
                                        if depth < max_depth and sample_count < max_samples:
                                            dir_stack.append((entry.path, depth + 1))
                                    elif entry.is_file(follow_symlinks=False):
                                        # 排除系统文件
                                        if self.exclude_system and self.is_system_path(entry.path):
                                            continue

                                        # 检查文件类型
                                        if not self.is_file_type_match(entry.path):
                                            continue

                                        try:
                                            file_size = entry.stat().st_size

                                            # 检查最小文件大小
                                            if file_size < self.min_size:
                                                continue

                                            sample_size += file_size
                                            sample_count += 1
                                        except (PermissionError, OSError):
                                            continue
                                except (PermissionError, OSError):
                                    continue
                    except (PermissionError, OSError):
                        continue

                # 基于样本估算总大小
                if sample_count > 0:
                    # 使用一个放大系数
                    # 3层采样通常只能扫描到10-30%的文件，所以乘以5-10倍
                    estimated_size = sample_size * 8  # 适中估算，乘以8
                    total_size += estimated_size
                    print(f"目录 {directory}，采样文件数: {sample_count}，采样大小: {sample_size / (1024**2):.2f} MB，估算总大小: {estimated_size / (1024**3):.2f} GB")
                else:
                    # 如果没有采样到文件，使用默认值
                    total_size += 1024 * 1024 * 1024  # 1GB
                    print(f"目录 {directory} 未采样到文件，使用默认值1GB")

            except Exception as e:
                print(f"估算目录大小失败 {directory}: {e}")
                # 降级方案：使用1GB默认值
                total_size += 1024 * 1024 * 1024

        return max(total_size, 1024 * 1024)  # 最小1MB

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


class LargeFileScannerThread(threading.Thread):
    """大文件扫描线程"""

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

        # 回调函数
        self.progress_callback: Callable[[int, int, str], None] = None
        self.found_callback: Callable[[FileInfo], None] = None
        self.finished_callback: Callable[[List, int, int], None] = None

    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        self.progress_callback = callback

    def set_found_callback(self, callback: Callable[[FileInfo], None]):
        self.found_callback = callback

    def set_finished_callback(self, callback: Callable[[List, int, int], None]):
        self.finished_callback = callback

    def _emit_progress(self, progress: int, total: int, text: str):
        if self.progress_callback:
            self.progress_callback(progress, total, text)

    def _emit_found(self, file_info: FileInfo):
        if self.found_callback:
            self.found_callback(file_info)

    def _emit_finished(self, file_objects: List, total_files: int, total_size_mb: int):
        if self.finished_callback:
            self.finished_callback(file_objects, total_files, total_size_mb)

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
            self._emit_progress(0, 100, "开始扫描大文件...")

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
            self._emit_progress(100, 100, "扫描完成")

            # 按文件大小排序
            self.large_files.sort(key=lambda x: x.size, reverse=True)

            # 计算总大小
            total_size_mb = sum(f.size for f in self.large_files) / (1024 * 1024)

            # 发送完成信号
            self._emit_finished(
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
                                            self._emit_progress(progress, 100, f"已扫描 {file_count} 个文件")
                                            last_progress_update = progress

                                # 检查是否为大文件
                                if file_size >= self.min_size_bytes:
                                    modified_time = datetime.fromtimestamp(os.path.getmtime(full_path))
                                    file_info = FileInfo(full_path, file_size, modified_time)
                                    self.large_files.append(file_info)
                                    self._emit_found(file_info)

                                    if len(self.large_files) >= self.max_results:
                                        return scanned_size_bytes

                            except (PermissionError, OSError):
                                pass

                    except (PermissionError, OSError):
                        pass

        except Exception as e:
            print(f"扫描目录出错 {directory}: {e}")

        return scanned_size_bytes

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


class FolderInfo:
    """文件夹信息类"""

    def __init__(self, path: str, file_count: int = 0, folder_count: int = 0,
                 modified_time: datetime = None, parent_path: str = ""):
        self.path = path  # 文件夹完整路径
        self.file_count = file_count  # 文件数量
        self.folder_count = folder_count  # 子文件夹数量
        self.modified_time = modified_time or datetime.now()  # 修改时间
        self.parent_path = parent_path  # 父目录
        self.folder_name = os.path.basename(path)  # 文件夹名称
        self.parent_name = os.path.basename(parent_path) if parent_path else ""  # 父文件夹名称


class EmptyFolderScannerThread(threading.Thread):
    """空文件夹扫描线程"""

    def __init__(self, directories: List[str], exclude_system: bool = True,
                 include_empty_subdirs: bool = True):
        super().__init__()
        self.directories = directories
        self.exclude_system = exclude_system  # 是否排除系统目录
        self.include_empty_subdirs = include_empty_subdirs  # 是否包含空的子目录
        self.running = True
        self.empty_folders = []

        # 系统目录排除列表
        self.system_dirs = [
            r"C:\Windows",
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            r"C:\ProgramData",
            r"$Recycle.Bin",
            r"System Volume Information"
        ]

        # 回调函数
        self.progress_callback: Callable[[int, int, str], None] = None
        self.found_callback: Callable[[FolderInfo], None] = None
        self.finished_callback: Callable[[List, int], None] = None

    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        self.progress_callback = callback

    def set_found_callback(self, callback: Callable[[FolderInfo], None]):
        self.found_callback = callback

    def set_finished_callback(self, callback: Callable[[List, int], None]):
        self.finished_callback = callback

    def _emit_progress(self, progress: int, total: int, text: str):
        if self.progress_callback:
            self.progress_callback(progress, total, text)

    def _emit_found(self, folder_info: FolderInfo):
        if self.found_callback:
            self.found_callback(folder_info)

    def _emit_finished(self, folder_objects: List, total_count: int):
        if self.finished_callback:
            self.finished_callback(folder_objects, total_count)

    def run(self):
        """执行扫描任务"""
        try:
            # 估算总目录数（用于进度条）
            self._emit_progress(0, 100, "开始扫描空文件夹...")

            total_dirs = 0
            for directory in self.directories:
                if not self.running:
                    return
                total_dirs += self.count_directories(directory)

            if total_dirs == 0:
                total_dirs = 100  # 默认值

            # 扫描空文件夹
            scanned_dirs = 0
            last_progress = 0

            for directory in self.directories:
                if not self.running:
                    return

                scanned_dirs = self.scan_directory(
                    directory,
                    total_dirs,
                    scanned_dirs,
                    last_progress
                )

            # 扫描完成
            self._emit_progress(100, 100, "扫描完成")
            self._emit_finished(self.empty_folders, len(self.empty_folders))

        except Exception as e:
            print(f"空文件夹扫描出错: {e}")
            import traceback
            traceback.print_exc()

    def count_directories(self, directory: str) -> int:
        """递归计算目录总数"""
        count = 0
        try:
            for root, dirs, files in os.walk(directory):
                if not self.running:
                    break

                # 排除系统目录
                if self.exclude_system:
                    dirs[:] = [d for d in dirs if not self.is_system_path(os.path.join(root, d))]

                count += len(dirs)
        except Exception as e:
            print(f"计算目录数量失败 {directory}: {e}")

        return max(count, 1)  # 至少返回1

    def scan_directory(self, directory: str, total_dirs: int,
                      scanned_count: int, last_progress: int) -> int:
        """扫描目录并查找空文件夹"""
        current_scanned = scanned_count

        try:
            for root, dirs, files in os.walk(directory):
                if not self.running:
                    break

                # 排除系统目录
                if self.exclude_system:
                    original_dirs = dirs[:]
                    dirs[:] = [d for d in dirs if not self.is_system_path(os.path.join(root, d))]
                    # 记录被排除的系统目录数量
                    current_scanned += len(original_dirs) - len(dirs)

                for dir_name in dirs:
                    if not self.running:
                        break

                    dir_path = os.path.join(root, dir_name)

                    # 检查是否为空文件夹
                    is_empty, file_count, folder_count = self.is_empty_folder(dir_path)

                    if is_empty:
                        # 获取修改时间
                        try:
                            modified_time = datetime.fromtimestamp(os.path.getmtime(dir_path))
                        except:
                            modified_time = datetime.now()

                        # 创建文件夹信息对象
                        folder_info = FolderInfo(
                            path=dir_path,
                            file_count=file_count,
                            folder_count=folder_count,
                            modified_time=modified_time,
                            parent_path=root
                        )

                        self.empty_folders.append(folder_info)
                        self._emit_found(folder_info)

                    # 更新进度
                    current_scanned += 1
                    if total_dirs > 0:
                        progress = min(int((current_scanned / total_dirs) * 100), 99)
                        if progress != last_progress and current_scanned % 10 == 0:
                            self._emit_progress(progress, 100, f"正在扫描: {dir_path}")
                            last_progress = progress

        except Exception as e:
            print(f"扫描目录出错 {directory}: {e}")

        return current_scanned

    def is_empty_folder(self, folder_path: str) -> tuple:
        """
        检查文件夹是否为空
        返回: (是否为空, 文件数量, 子文件夹数量)
        """
        try:
            entries = os.listdir(folder_path)

            if not entries:
                # 完全空的文件夹
                return True, 0, 0

            if not self.include_empty_subdirs:
                # 如果不包含空的子目录，只有完全空才算空
                return False, len([e for e in entries if os.path.isfile(os.path.join(folder_path, e))]), \
                       len([e for e in entries if os.path.isdir(os.path.join(folder_path, e))])

            # 检查是否只包含空的子文件夹
            file_count = 0
            folder_count = 0
            all_subdirs_empty = True

            for entry in entries:
                entry_path = os.path.join(folder_path, entry)

                if os.path.isfile(entry_path):
                    # 有文件，不算空
                    return False, 1, 0
                elif os.path.isdir(entry_path):
                    folder_count += 1
                    # 递归检查子目录是否为空
                    is_empty, _, _ = self.is_empty_folder(entry_path)
                    if not is_empty:
                        all_subdirs_empty = False

            # 如果所有子目录都是空的，则认为该目录为空
            if folder_count > 0 and all_subdirs_empty:
                return True, 0, folder_count

            return False, 0, folder_count

        except (PermissionError, OSError):
            # 无法访问的目录不视为空文件夹
            return False, 0, 0

    def is_system_path(self, path: str) -> bool:
        """检查是否为系统路径"""
        path_lower = path.lower()

        # 检查是否在系统目录中
        for system_dir in self.system_dirs:
            if system_dir.lower() in path_lower:
                return True

        return False

    def stop(self):
        """停止扫描"""
        self.running = False
