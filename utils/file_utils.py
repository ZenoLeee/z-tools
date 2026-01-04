import os
from typing import Tuple

def try_delete_file(file_path: str) -> Tuple[bool, str]:
    """尝试删除文件，返回成功状态和消息"""
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return False, f"文件不存在: {os.path.basename(file_path)}"

        # 检查是否为只读文件
        if not os.access(file_path, os.W_OK):
            try:
                # 尝试修改文件属性
                os.chmod(file_path, 0o666)
            except:
                return False, f"文件只读，无法修改权限: {os.path.basename(file_path)}"

        # 检查路径长度
        if len(file_path) > 260:
            # Windows路径长度限制，尝试使用长路径前缀
            long_path = '\\\\?\\' + file_path
            if os.path.exists(long_path):
                os.remove(long_path)
            else:
                return False, f"路径太长且无法访问: {os.path.basename(file_path)}"
        else:
            os.remove(file_path)

        return True, f"成功删除: {os.path.basename(file_path)}"

    except PermissionError:
        return False, f"权限不足，无法删除: {os.path.basename(file_path)}"
    except OSError as e:
        return False, f"系统错误({e.errno}): {os.path.basename(file_path)}"
    except Exception as e:
        return False, f"未知错误: {os.path.basename(file_path)} - {str(e)}"


def try_delete_folder(folder_path: str) -> Tuple[bool, str]:
    """尝试删除空文件夹，返回成功状态和消息"""
    try:
        # 检查文件夹是否存在
        if not os.path.exists(folder_path):
            return False, f"文件夹不存在: {os.path.basename(folder_path)}"

        # 检查是否为文件夹
        if not os.path.isdir(folder_path):
            return False, f"不是文件夹: {os.path.basename(folder_path)}"

        # 检查文件夹是否为空
        try:
            entries = os.listdir(folder_path)
            if entries:
                return False, f"文件夹不为空: {os.path.basename(folder_path)}"
        except PermissionError:
            return False, f"无法访问文件夹: {os.path.basename(folder_path)}"

        # 检查路径长度
        if len(folder_path) > 260:
            # Windows路径长度限制，尝试使用长路径前缀
            long_path = '\\\\?\\' + folder_path
            if os.path.exists(long_path):
                os.rmdir(long_path)
            else:
                return False, f"路径太长且无法访问: {os.path.basename(folder_path)}"
        else:
            os.rmdir(folder_path)

        return True, f"成功删除: {os.path.basename(folder_path)}"

    except PermissionError:
        return False, f"权限不足，无法删除: {os.path.basename(folder_path)}"
    except OSError as e:
        return False, f"系统错误({e.errno}): {os.path.basename(folder_path)}"
    except Exception as e:
        return False, f"未知错误: {os.path.basename(folder_path)} - {str(e)}"