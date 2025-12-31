import os
import hashlib
import time
from datetime import datetime
from typing import List, Optional
from PyQt5.QtCore import QThread, pyqtSignal

import psutil


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

        """执行扫描任务 - 添加调试信息"""
        try:
            print("重复文件扫描线程开始运行")
            start_time = time.time()

            # 发送初始进度
            self.scan_progress.emit(0, 100, "正在计算目录大小...")

            # 第一阶段：计算目标目录的总大小
            total_size_bytes = 0

            for directory in self.directories:
                if not self.running:
                    print("扫描被用户停止")
                    return

                print(f"开始处理目录: {directory}")
                dir_start_time = time.time()

                if os.path.exists(directory):
                    drive = os.path.splitdrive(directory)[0] + "\\"
                    if os.path.exists(drive):
                        try:
                            usage = psutil.disk_usage(drive)
                            total_size_bytes += usage.used
                            print(f"驱动器 {drive} 大小获取完成，用时: {time.time() - dir_start_time:.2f}秒")
                        except Exception as e:
                            print(f"使用psutil失败，使用估算: {e}")
                            total_size_bytes += 500 * 1024 * 1024  # 估算500MB

            print(
                f"总扫描大小计算完成: {total_size_bytes / (1024 * 1024 * 1024):.2f} GB, 总用时: {time.time() - start_time:.2f}秒")

            # 第二阶段：扫描文件（快速扫描，不计算MD5）
            scanned_size_bytes = 0
            file_objects = []  # FileInfo对象列表

            # 发送初始进度
            self.scan_progress.emit(0, 100, "开始扫描文件...")

            for directory in self.directories:
                if not self.running:
                    return

                print(f"扫描目录: {directory}")

                if os.path.exists(directory):
                    # 快速扫描目录（不计算MD5）
                    try:
                        scanned_size_bytes, scanned_files = self.fast_scan_directory(
                            directory, total_size_bytes, scanned_size_bytes, file_objects
                        )
                    except Exception as e:
                        print(f"扫描目录 {directory} 时出错: {e}")
                        # 继续扫描其他目录
                        continue
                else:
                    print(f"目录不存在: {directory}")

            if not self.running:
                return

            print(f"快速扫描完成，共找到 {len(file_objects)} 个文件")

            # 如果文件太多，警告用户
            if len(file_objects) > 100000:
                print(f"警告：扫描到大量文件 ({len(file_objects)})，可能需要较长时间")
                self.scan_progress.emit(50, 100, f"找到 {len(file_objects)} 个文件，正在分析...")

            # 第三阶段：计算MD5并实时发现重复文件（50-100%）
            self.scan_progress.emit(50, 100, "正在计算文件哈希值...")

            # 按大小分组，先处理可能重复的文件
            size_groups = {}
            for file_info in file_objects:
                if file_info.size not in size_groups:
                    size_groups[file_info.size] = []
                size_groups[file_info.size].append(file_info)

            # 只处理大小相同的文件组（可能重复）
            processed_files = 0
            total_files_to_hash = sum(len(files) for files in size_groups.values() if len(files) > 1)

            if total_files_to_hash == 0:
                # 没有可能重复的文件，直接完成
                self.scan_progress.emit(100, 100, "扫描完成，没有重复文件")
                self.scan_finished.emit(file_objects, len(file_objects), 0, 0)
                return

            print(f"需要计算 {total_files_to_hash} 个文件的哈希值")

            # 存储每个MD5对应的文件
            md5_dict = {}
            duplicate_groups = {}
            duplicate_count = 0
            current_group_id = 1

            # 存储已经分配了组ID的MD5
            md5_to_group_id = {}

            for size, files in size_groups.items():
                if not self.running:
                    return

                if len(files) > 1:  # 只处理可能重复的文件
                    # 为这个大小的所有文件计算MD5
                    for file_info in files:
                        if not self.running:
                            return

                        try:
                            # 再次检查文件是否存在
                            if not os.path.exists(file_info.path):
                                print(f"文件在扫描后已被删除: {file_info.path}")
                                continue

                            # 计算MD5
                            md5_hash = self.calculate_md5(file_info.path)

                            if not md5_hash:  # 如果计算MD5失败
                                print(f"计算MD5失败: {file_info.path}")
                                continue

                            file_info.md5_hash = md5_hash

                            # 检查这个MD5是否已经存在
                            if md5_hash in md5_dict:
                                # 发现重复文件！
                                existing_files = md5_dict[md5_hash]

                                # 获取这个MD5对应的组ID
                                group_id = md5_to_group_id.get(md5_hash)

                                if group_id is None:
                                    # 这是这个MD5第一次被发现重复
                                    group_id = current_group_id
                                    current_group_id += 1  # 为下一个新组准备
                                    md5_to_group_id[md5_hash] = group_id

                                    # 给第一个文件也标记为重复
                                    first_file = existing_files[0]
                                    first_file.is_duplicate = True
                                    first_file.duplicate_group = group_id
                                    first_file.keep = True  # 第一个文件保留

                                # 标记当前文件为重复
                                file_info.is_duplicate = True
                                file_info.duplicate_group = group_id
                                file_info.keep = False  # 非第一个文件不保留

                                # 添加到组中
                                existing_files.append(file_info)

                                # 更新字典中的文件列表
                                md5_dict[md5_hash] = existing_files

                                # 更新重复组
                                duplicate_groups[group_id] = existing_files

                                # 发送重复文件信号（实时更新UI）
                                self.duplicate_found.emit(file_info, group_id)
                                duplicate_count += 1

                            else:
                                # 新的MD5，添加到字典中
                                md5_dict[md5_hash] = [file_info]

                        except (PermissionError, OSError, FileNotFoundError) as e:
                            print(f"处理文件 {file_info.path} 失败: {e}")
                            continue
                        except Exception as e:
                            print(f"处理文件 {file_info.path} 时发生未知错误: {e}")
                            continue

                        processed_files += 1

                        # 更新进度（50-95%）
                        progress = 50 + int((processed_files / total_files_to_hash) * 45)
                        if processed_files % 100 == 0:  # 每100个文件更新一次进度
                            current_file = os.path.basename(file_info.path)
                            if len(current_file) > 30:
                                current_file = current_file[:27] + "..."
                            self.scan_progress.emit(
                                min(progress, 95),
                                100,
                                f"计算: {current_file}"
                            )

            if not self.running:
                return

            print(f"发现 {len(duplicate_groups)} 个重复组，共 {duplicate_count} 个重复文件")

            # 确保所有重复组的第一个文件都被正确标记为保留（按修改时间）
            for group_id, files in duplicate_groups.items():
                if len(files) > 1:
                    # 按修改时间排序，最新的排前面
                    sorted_files = sorted(files, key=lambda x: x.modified_time, reverse=True)

                    # 重新标记保留状态
                    for i, file_info in enumerate(sorted_files):
                        file_info.keep = (i == 0)  # 只保留最新的

                    # 更新组中的文件顺序
                    duplicate_groups[group_id] = sorted_files

            # 发送完成信号
            self.scan_progress.emit(100, 100, "扫描完成")
            self.scan_finished.emit(
                file_objects,
                len(file_objects),
                len(duplicate_groups),
                duplicate_count
            )

        except Exception as e:
            print(f"重复文件扫描出错: {e}")
            import traceback
            traceback.print_exc()
            # 发送错误信号
            self.scan_progress.emit(100, 100, f"扫描出错: {str(e)}")

    def fast_scan_directory(self, directory: str, total_size_bytes: int, start_scanned_size: int,
                            file_objects: list) -> tuple:
        """快速扫描目录（不计算MD5）- 修复版"""
        scanned_size_bytes = start_scanned_size
        file_count = 0

        try:
            # 使用 try-except 包裹整个 os.walk，防止遍历过程中出错
            try:
                # 注意：这里不使用 followlinks=True，避免跟随符号链接
                for root, dirs, files in os.walk(directory, onerror=self.walk_error_handler):
                    if not self.running:
                        break

                    # 排除系统目录
                    if self.exclude_system:
                        # 安全地过滤目录
                        filtered_dirs = []
                        for d in dirs:
                            try:
                                dir_path = os.path.join(root, d)
                                if not self.is_system_path(dir_path):
                                    filtered_dirs.append(d)
                            except:
                                # 如果检查目录失败，跳过这个目录
                                continue
                        dirs[:] = filtered_dirs

                    for filename in files:
                        if not self.running:
                            break

                        file_path = os.path.join(root, filename)

                        # 使用一个统一的错误处理函数来处理每个文件
                        self.process_single_file(file_path, scanned_size_bytes, total_size_bytes,
                                                 file_objects, file_count)

                        # 注意：process_single_file 会更新 file_count 和 scanned_size_bytes
                        # 所以我们需要获取返回值
                        result = self.process_single_file(file_path, scanned_size_bytes, total_size_bytes,
                                                          file_objects, file_count)
                        if result:
                            scanned_size_bytes, file_count = result

            except Exception as e:
                # 如果整个目录遍历出错，记录错误但继续
                print(f"遍历目录 {directory} 时出错: {e}")

        except Exception as e:
            print(f"扫描目录出错 {directory}: {e}")

        return scanned_size_bytes, file_count

    def walk_error_handler(self, error):
        """处理 os.walk 过程中的错误"""
        return None

    def process_single_file(self, file_path: str, current_scanned_size: int, total_size_bytes: int,
                            file_objects: list, current_file_count: int):
        """处理单个文件 - 优化进度更新频率"""
        scanned_size_bytes = current_scanned_size
        file_count = current_file_count

        try:
            # 1. 快速检查文件是否存在
            if not os.path.lexists(file_path):
                return None

            # 2. 快速检查是否为符号链接或目录
            if os.path.islink(file_path) or not os.path.isfile(file_path):
                return None

            # 3. 快速检查文件类型
            if not self.is_file_type_match(file_path):
                return None

            # 4. 快速检查系统文件
            if self.exclude_system and self.is_system_path_quick(file_path):
                return None

            # 5. 获取文件大小
            try:
                file_size = os.path.getsize(file_path)
            except (PermissionError, OSError, FileNotFoundError):
                return None

            # 6. 检查最小文件大小
            if file_size < self.min_size:
                return None

            # 7. 更新统计
            scanned_size_bytes += file_size
            file_count += 1

            # 8. 优化进度更新频率 - 关键改进！
            # 不要每个文件都更新进度，这样会导致UI卡顿
            if total_size_bytes > 0:
                progress = min(int((scanned_size_bytes / total_size_bytes) * 50), 50)

                # 只有满足以下条件时才更新进度：
                # 1. 每扫描50个文件更新一次
                # 2. 或者扫描到大文件（>10MB）
                # 3. 或者进度变化超过1%
                if (file_count % 50 == 0 or
                        file_size > 10 * 1024 * 1024 or
                        progress > current_progress + 1):

                    current_file = os.path.basename(file_path)
                    if len(current_file) > 30:
                        current_file = current_file[:27] + "..."

                    # 只更新当前文件标签，不频繁更新进度条
                    self.scan_progress.emit(
                        progress,
                        100,
                        f"扫描: {current_file}"
                    )

            # 9. 获取修改时间
            try:
                modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            except:
                modified_time = datetime.now()

            # 10. 创建文件信息对象
            file_info = FileInfo(
                path=file_path,
                size=file_size,
                modified_time=modified_time,
                md5_hash="",
                is_duplicate=False,
                duplicate_group=0,
                keep=True
            )

            file_objects.append(file_info)

            # 11. 每处理500个文件发送一次统计进度
            if file_count % 500 == 0:
                self.file_processed.emit(
                    progress,
                    file_count,
                    f"已扫描 {file_count} 个文件"
                )

            return scanned_size_bytes, file_count

        except Exception:
            # 静默处理所有异常
            return None

    def is_system_path_quick(self, path: str) -> bool:
        """快速检查是否为系统路径 - 不访问文件系统"""
        if not self.exclude_system:
            return False

        path_lower = path.lower()

        # 快速检查常见系统目录
        system_patterns = [
            r'\windows\\',
            r'\program files\\',
            r'\programdata\\',
            r'\system32\\',
            r'\syswow64\\',
            r'\$recycle.bin',
            r'\system volume information',
            r'\config.msi',
            r'\recovery',
            r'\perflogs',
        ]

        for pattern in system_patterns:
            if pattern in path_lower:
                return True

        # 快速检查常见系统文件
        filename = os.path.basename(path_lower)
        system_files = {
            'hiberfil.sys', 'pagefile.sys', 'swapfile.sys',
            'desktop.ini', 'thumbs.db', 'bootmgr', 'bootnxt',
            'ntldr', 'io.sys', 'msdos.sys',
        }

        if filename in system_files:
            return True

        # 检查文件扩展名
        if filename.endswith(('.sys', '.dll', '.tmp', '.log')):
            # 这些文件如果在系统目录中就是系统文件
            # 这里简化处理，只检查路径
            for pattern in system_patterns:
                if pattern in path_lower:
                    return True

        return False

    def calculate_directory_size(self, directory: str) -> int:
        """快速计算目录大小（避免递归过深）"""
        total_size = 0

        try:
            # 使用栈而不是递归来处理目录遍历
            dir_stack = [directory]

            while dir_stack:
                current_dir = dir_stack.pop()

                try:
                    entries = os.listdir(current_dir)
                except (PermissionError, OSError):
                    continue

                for entry in entries:
                    full_path = os.path.join(current_dir, entry)

                    try:
                        if os.path.isdir(full_path):
                            # 排除系统目录
                            if self.exclude_system and self.is_system_path(full_path):
                                continue
                            # 将子目录加入栈中
                            dir_stack.append(full_path)
                        else:
                            # 排除系统文件
                            if self.exclude_system and self.is_system_path(full_path):
                                continue
                            # 检查文件类型
                            if not self.is_file_type_match(full_path):
                                continue

                            # 获取文件大小
                            total_size += os.path.getsize(full_path)
                    except (PermissionError, OSError):
                        pass
        except Exception as e:
            print(f"计算目录大小出错 {directory}: {e}")

        return total_size

    def scan_and_hash_directory(self, directory: str, total_size_bytes: int, start_scanned_size: int,
                                md5_dict: dict, file_objects: list) -> tuple:
        """扫描目录，计算文件MD5并实时更新进度"""
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

                            # 实时更新进度（按已扫描的文件大小）
                            if total_size_bytes > 0:
                                progress = min(int((scanned_size_bytes / total_size_bytes) * 100), 99)

                                # 实时显示当前文件名（但限制更新频率，避免UI卡顿）
                                current_file = os.path.basename(full_path)
                                if len(current_file) > 30:  # 长文件名截断
                                    current_file = current_file[:27] + "..."

                                # 每5个文件或文件大小变化较大时更新一次文本
                                if file_count % 5 == 0 or file_size > 10 * 1024 * 1024:  # 10MB以上的大文件立即显示
                                    self.scan_progress.emit(
                                        progress,
                                        100,
                                        f"正在处理: {current_file}"
                                    )

                            # 获取文件信息（先不计算MD5，提高扫描速度）
                            modified_time = datetime.fromtimestamp(os.path.getmtime(full_path))
                            file_info = FileInfo(
                                path=full_path,
                                size=file_size,
                                modified_time=modified_time,
                                md5_hash="",  # 稍后计算
                                is_duplicate=False,
                                duplicate_group=0,
                                keep=True
                            )

                            file_objects.append(file_info)

                            # 临时存储文件信息，稍后计算MD5
                            # 注意：这里我们先收集文件，稍后再计算MD5

                            # 每处理100个文件发送一次处理进度
                            if file_count % 100 == 0:
                                self.file_processed.emit(
                                    min(progress, 99),
                                    file_count,
                                    f"已扫描 {file_count} 个文件"
                                )

                        except Exception as e:
                            print(f"处理文件失败 {full_path}: {e}")

                except (PermissionError, OSError):
                    pass

        return scanned_size_bytes, file_count

    def is_system_path(self, path: str) -> bool:
        """检查是否为系统路径 - 简化版，避免文件访问"""
        if not self.exclude_system:
            return False

        try:
            path_lower = path.replace('/', '\\').lower()

            # 只检查路径字符串，不访问文件系统
            system_dirs = [
                r"c:\windows",
                r"c:\program files",
                r"c:\program files (x86)",
                r"c:\programdata",
                r"$recycle.bin",
                r"system volume information",
                r"\windows\\",
                r"\program files\\",
                r"\programdata\\",
                r"\system32\\",
                r"\syswow64\\",
            ]

            # 检查路径是否包含系统目录
            for system_dir in system_dirs:
                if system_dir in path_lower:
                    return True

            # 检查文件名（不检查文件属性）
            filename = os.path.basename(path).lower()

            # 常见系统文件
            system_files = {
                'hiberfil.sys', 'pagefile.sys', 'swapfile.sys',
                'desktop.ini', 'thumbs.db',
                'bootmgr', 'bootnxt', 'ntldr', 'io.sys', 'msdos.sys',
                '$mft', '$logfile', '$volume', '$attrdef', '$bitmap',
                '$boot', '$badclus', '$secure', '$upcase', '$extend',
            }

            if filename in system_files:
                return True

            # 检查文件扩展名
            if filename.endswith(('.sys', '.dll', '.exe', '.drv', '.ocx', '.cpl', '.tmp')):
                # 这些文件如果在系统目录中，就是系统文件
                # 但这里我们简化处理：这些扩展名的文件都跳过
                return True

            # 隐藏文件（以点开头）
            if filename.startswith('.'):
                return True

            return False

        except:
            # 如果检查失败，不将其视为系统文件
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
        """计算文件的MD5哈希值 - 添加超时控制"""
        # 对于大文件或特殊文件，使用快速哈希
        try:
            file_size = os.path.getsize(file_path)

            # 对于超大文件（>100MB），使用快速哈希
            if file_size > 100 * 1024 * 1024:
                return self.calculate_quick_hash(file_path)

            # 对于大文件（>10MB），使用简化哈希
            elif file_size > 10 * 1024 * 1024:
                return self.calculate_simple_hash(file_path)
        except:
            return ""

        # 对于小文件，计算完整MD5
        md5_hash = hashlib.md5()

        try:
            with open(file_path, 'rb') as f:
                bytes_read = 0
                while True:
                    if not self.running:
                        return ""

                    chunk = f.read(chunk_size)
                    if not chunk:
                        break

                    md5_hash.update(chunk)
                    bytes_read += len(chunk)

                    # 每读取1MB检查一次是否需要停止
                    if bytes_read % (1024 * 1024) == 0:
                        if not self.running:
                            return ""
        except:
            return ""

        return md5_hash.hexdigest()

    def calculate_simple_hash(self, file_path: str) -> str:
        """计算文件的简化哈希（用于大文件）"""
        try:
            file_size = os.path.getsize(file_path)

            # 使用文件大小 + 文件开头和结尾计算哈希
            md5_hash = hashlib.md5()
            md5_hash.update(str(file_size).encode())

            # 读取文件开头（4KB）
            with open(file_path, 'rb') as f:
                head = f.read(4096)
                md5_hash.update(head)

                # 如果文件大于8KB，读取文件末尾（4KB）
                if file_size > 8192:
                    f.seek(file_size - 4096)
                    tail = f.read(4096)
                    md5_hash.update(tail)

            return md5_hash.hexdigest()
        except:
            return f"size_{file_size}"

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