"""
平台检测和工具模块
提供跨平台支持的工具函数
"""
import sys
import os


class Platform:
    """平台枚举"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


def get_platform() -> str:
    """
    获取当前平台

    Returns:
        平台标识符
    """
    # 使用 sys.platform 避免导入标准库的 platform 模块
    # sys.platform: 'win32' (Windows), 'darwin' (macOS), 'linux' (Linux)
    platform_str = sys.platform.lower()

    if platform_str == "win32":
        return Platform.WINDOWS
    elif platform_str == "darwin":
        return Platform.MACOS
    elif platform_str.startswith("linux"):
        return Platform.LINUX
    else:
        return Platform.UNKNOWN


def is_windows() -> bool:
    """是否为 Windows 平台"""
    return get_platform() == Platform.WINDOWS


def is_macos() -> bool:
    """是否为 macOS 平台"""
    return get_platform() == Platform.MACOS


def is_linux() -> bool:
    """是否为 Linux 平台"""
    return get_platform() == Platform.LINUX


def get_platform_name() -> str:
    """
    获取平台显示名称

    Returns:
        平台显示名称
    """
    platform_type = get_platform()

    names = {
        Platform.WINDOWS: "Windows",
        Platform.MACOS: "macOS",
        Platform.LINUX: "Linux",
        Platform.UNKNOWN: "Unknown"
    }

    return names.get(platform_type, "Unknown")


def get_home_directory() -> str:
    """
    获取用户主目录（跨平台）

    Returns:
        用户主目录路径
    """
    return os.path.expanduser("~")


def get_desktop_directory() -> str:
    """
    获取桌面目录（跨平台）

    Returns:
        桌面目录路径
    """
    home = get_home_directory()

    if is_windows():
        # Windows: 桌面通常在用户目录下
        desktop = os.path.join(home, "Desktop")
    elif is_macos():
        # macOS: 桌面在用户目录下
        desktop = os.path.join(home, "Desktop")
    else:  # Linux
        # Linux: 桌面通常在用户目录下
        desktop = os.path.join(home, "Desktop")

    return desktop


def get_documents_directory() -> str:
    """
    获取文档目录（跨平台）

    Returns:
        文档目录路径
    """
    home = get_home_directory()

    if is_windows():
        # Windows: 可以使用环境变量
        documents = os.path.join(home, "Documents")
    elif is_macos():
        # macOS: 文档在用户目录下
        documents = os.path.join(home, "Documents")
    else:  # Linux
        # Linux: 文档通常在用户目录下
        documents = os.path.join(home, "Documents")

    return documents


def get_downloads_directory() -> str:
    """
    获取下载目录（跨平台）

    Returns:
        下载目录路径
    """
    home = get_home_directory()

    if is_windows():
        downloads = os.path.join(home, "Downloads")
    elif is_macos():
        downloads = os.path.join(home, "Downloads")
    else:  # Linux
        downloads = os.path.join(home, "Downloads")

    return downloads


def get_appdata_directory() -> str:
    """
    获取应用数据目录（跨平台）

    Returns:
        应用数据目录路径
    """
    home = get_home_directory()

    if is_windows():
        # Windows: %APPDATA%
        appdata = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
    elif is_macos():
        # macOS: ~/Library/Application Support
        appdata = os.path.join(home, "Library", "Application Support")
    else:  # Linux
        # Linux: ~/.config 或 ~/.local/share
        xdg_config = os.environ.get("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        xdg_data = os.environ.get("XDG_DATA_HOME", os.path.join(home, ".local", "share"))
        appdata = xdg_config

    return appdata


def get_temp_directory() -> str:
    """
    获取临时文件目录（跨平台）

    Returns:
        临时目录路径
    """
    import tempfile
    return tempfile.gettempdir()


def can_run_command(command: str) -> bool:
    """
    检查是否可以运行指定命令（跨平台）

    Args:
        command: 命令名称

    Returns:
        是否可以运行
    """
    from shutil import which

    return which(command) is not None


def get_supported_features() -> dict:
    """
    获取当前平台支持的功能列表

    Returns:
        功能支持字典
    """
    features = {
        "file_cleanup": True,  # 所有平台都支持文件清理
        "duplicate_files": True,
        "large_files": True,
        "empty_folders": True,
        "network_tools": True,  # 网络工具大部分功能通用
        "ping": True,
        "network_info": True,
        "system_info": True,  # 系统信息查看
    }

    if is_windows():
        features.update({
            "registry_cleanup": True,
            "shortcut_cleanup": True,
            "startup_items": True,
            "services": True,
        })
    elif is_macos():
        features.update({
            "registry_cleanup": False,  # Mac 没有注册表
            "shortcut_cleanup": True,  # Mac 有快捷方式（.alias 等）
            "startup_items": True,  # Mac 有启动项
            "services": False,  # Mac 使用 launchd，不是传统的服务
        })
    else:  # Linux
        features.update({
            "registry_cleanup": False,
            "shortcut_cleanup": True,  # .desktop 文件
            "startup_items": True,  # systemd 等
            "services": True,
        })

    return features


# 如果直接运行此文件，显示平台信息
if __name__ == "__main__":
    print(f"当前平台: {get_platform_name()} ({get_platform()})")
    print(f"Python 版本: {sys.version}")
    print(f"主目录: {get_home_directory()}")
    print(f"桌面目录: {get_desktop_directory()}")
    print(f"文档目录: {get_documents_directory()}")
    print(f"下载目录: {get_downloads_directory()}")
    print(f"应用数据目录: {get_appdata_directory()}")
    print(f"临时目录: {get_temp_directory()}")

    features = get_supported_features()
    print(f"\n支持的功能:")
    for feature, supported in features.items():
        status = "✓" if supported else "✗"
        print(f"  {status} {feature}")
