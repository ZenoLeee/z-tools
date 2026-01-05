"""
Windows 平台注册表清理模块
仅 Windows 平台可用
"""

# 这个文件包含原有的注册表清理功能
# 由于代码较长，这里通过导入原模块的方式复用
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# 导入原有的注册表清理类
from core.registry_cleaner import (
    RegistryIssue,
    RegistryScanner,
    RegistryBackup,
    RegistryCleaner,
    RegistryScannerThread
)

# 导出所有类和函数
__all__ = [
    'RegistryIssue',
    'RegistryScanner',
    'RegistryBackup',
    'RegistryCleaner',
    'RegistryScannerThread',
]
