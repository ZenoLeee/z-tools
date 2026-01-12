"""
平台适配器模块
根据当前平台自动加载对应的功能模块
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.platform import get_platform, Platform


class PlatformAdapter:
    """平台适配器基类"""

    @staticmethod
    def get_shortcut_scanner():
        """获取快捷方式扫描器"""
        platform_type = get_platform()

        if platform_type == Platform.WINDOWS:
            from core.platform.windows.shortcut_scanner import WindowsShortcutScanner
            return WindowsShortcutScanner
        elif platform_type == Platform.MACOS:
            from core.platform.macos.shortcut_scanner import MacShortcutScanner
            return MacShortcutScanner
        else:
            # Linux 或其他平台，返回 None 或实现基础版本
            return None

    @staticmethod
    def get_registry_cleaner():
        """获取注册表清理器（仅 Windows）"""
        platform_type = get_platform()

        if platform_type == Platform.WINDOWS:
            from core.platform.windows.registry_cleaner import RegistryCleaner, RegistryScanner, RegistryBackup
            return {
                'cleaner': RegistryCleaner,
                'scanner': RegistryScanner,
                'backup': RegistryBackup,
            }
        else:
            # Mac/Linux 没有注册表
            return None

    @staticmethod
    def get_startup_manager():
        """获取启动项管理器"""
        platform_type = get_platform()

        if platform_type == Platform.WINDOWS:
            from core.platform.windows.startup_manager import WindowsStartupManager
            return WindowsStartupManager
        elif platform_type == Platform.MACOS:
            from core.platform.macos.startup_manager import MacStartupManager
            return MacStartupManager
        else:
            # Linux 启动项管理
            return None

    @staticmethod
    def has_registry_support() -> bool:
        """是否支持注册表清理"""
        return get_platform() == Platform.WINDOWS

    @staticmethod
    def has_shortcut_support() -> bool:
        """是否支持快捷方式清理"""
        platform_type = get_platform()
        return platform_type in [Platform.WINDOWS, Platform.MACOS]

    @staticmethod
    def has_startup_support() -> bool:
        """是否支持启动项管理"""
        platform_type = get_platform()
        return platform_type in [Platform.WINDOWS, Platform.MACOS]

    @staticmethod
    def get_platform_name() -> str:
        """获取平台显示名称"""
        from utils.platform import get_platform_name
        return get_platform_name()

    @staticmethod
    def get_supported_features() -> dict:
        """获取支持的功能列表"""
        from utils.platform import get_supported_features
        return get_supported_features()


# 导出便捷函数
def get_shortcut_scanner():
    """获取当前平台的快捷方式扫描器"""
    return PlatformAdapter.get_shortcut_scanner()


def get_registry_cleaner():
    """获取当前平台的注册表清理器（如果支持）"""
    return PlatformAdapter.get_registry_cleaner()


def get_startup_manager():
    """获取当前平台的启动项管理器"""
    return PlatformAdapter.get_startup_manager()


# 导出所有公共接口
__all__ = [
    'PlatformAdapter',
    'get_shortcut_scanner',
    'get_registry_cleaner',
    'get_startup_manager',
]
