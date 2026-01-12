"""
启动项智能评分系统
基于规则库和启发式算法自动识别可安全禁用的启动项
"""
import re
from typing import Tuple, Optional


class StartupScorer:
    """启动项评分器"""

    # 白名单：必须保留的系统启动项
    WHITELIST_PATTERNS = [
        r'^.*Windows.*Defender.*$',
        r'^.*System.*$',
        r'^.*Security.*Health.*$',
        r'^.*Windows.*Security.*$',
        r'^.*Microsoft\.Security.*$',
        r'^RtHDVCpl\.exe$',         # Realtek音频
        r'^RtkAudUService\.exe$',
        r'^igfxHK\.exe$',           # Intel显卡
        r'^igfxTray\.exe$',
        r'^NvBackend\.exe$',        # NVIDIA显卡
        r'^Nvidia.*$',
        r'^AMD.*$',
        r'^ATI.*$',
    ]

    # 黑名单：可以安全禁用的启动项
    BLACKLIST_PATTERNS = [
        r'^.*Adobe.*Update.*$',     # Adobe更新
        r'^.*Java.*Update.*$',      # Java更新
        r'^.*Google.*Update.*$',    # Google更新
        r'^.*Chrome.*Update.*$',
        r'^jusched\.exe$',          # Java更新调度器
        r'^Adobe.*Updater\.exe$',
        r'^Google.*Update\.exe$',
    ]

    # 延迟启动建议
    DELAY_START_PATTERNS = [
        r'.*Chrome.*',
        r'.*Firefox.*',
        r'.*Edge.*',
        r'.*Office.*',
        r'.*iTunes.*',
    ]

    @classmethod
    def score_startup_item(cls, name: str, command: str = "", is_valid: bool = True) -> Tuple[int, str]:
        """
        对启动项进行评分

        Args:
            name: 启动项名称
            command: 启动命令
            is_valid: 文件是否存在

        Returns:
            (分数, 建议描述) - 分数范围 0-100
        """
        score = 50  # 基础分

        # 检查无效启动项
        if not is_valid:
            score = 5
            return (score, "❌ 文件不存在，建议删除此启动项")

        combined = f"{name} {command}".lower()

        # 1. 检查白名单（系统关键组件）
        if cls._matches_whitelist(name, command):
            score = 85
            return (score, "🔒 系统关键组件，建议保留")

        # 2. 检查黑名单（可安全禁用）
        if cls._matches_blacklist(name, command):
            score = 15
            return (score, "✅ 可安全禁用，需要时可手动启动")

        # 3. 检查更新服务
        if cls._is_update_service(name, command):
            score = 20
            return (score, "🔄 更新服务可禁用，建议手动更新")

        # 4. 检查云同步软件
        if cls._is_cloud_sync(name, command):
            score = 30
            return (score, "☁️ 云同步可根据需要启用或禁用")

        # 5. 检查硬件驱动相关
        if cls._is_hardware_related(name, command):
            score = 70
            return (score, "⚙️ 硬件驱动，建议保留以确保功能正常")

        # 6. 检查即时通讯软件
        if cls._is_im_software(name, command):
            score = 40
            return (score, "💬 如需常驻可保留，否则建议禁用")

        # 7. 检查媒体软件
        if cls._is_media_software(name, command):
            score = 35
            return (score, "🎵 媒体软件，建议按需启用")

        # 8. 检查延迟启动潜力
        if cls._can_delay_start(name, command):
            score = 45
            return (score, "⏱️ 可设置为延迟启动，加快开机速度")

        # 默认建议
        if score >= 70:
            return (score, "建议保留")
        elif score >= 40:
            return (score, "根据需要决定是否保留")
        else:
            return (score, "建议禁用以优化开机速度")

    @classmethod
    def _matches_whitelist(cls, name: str, command: str) -> bool:
        """检查是否匹配白名单"""
        combined = f"{name} {command}".lower()
        return any(re.search(pattern.lower(), combined) for pattern in cls.WHITELIST_PATTERNS)

    @classmethod
    def _matches_blacklist(cls, name: str, command: str) -> bool:
        """检查是否匹配黑名单"""
        combined = f"{name} {command}".lower()
        return any(re.search(pattern.lower(), combined) for pattern in cls.BLACKLIST_PATTERNS)

    @classmethod
    def _is_update_service(cls, name: str, command: str) -> bool:
        """检查是否为更新服务"""
        update_keywords = ['update', 'updater', 'updateservice', 'autoupdate']
        combined = f"{name} {command}".lower()
        # 排除Windows更新
        if 'windows' in combined and 'update' in combined:
            return False
        return any(keyword in combined for keyword in update_keywords)

    @classmethod
    def _is_cloud_sync(cls, name: str, command: str) -> bool:
        """检查是否为云同步软件"""
        cloud_keywords = ['onedrive', 'dropbox', 'googledrive', 'icloud', 'baiduwangpan', 'baidunetdisk']
        combined = f"{name} {command}".lower()
        return any(keyword in combined for keyword in cloud_keywords)

    @classmethod
    def _is_hardware_related(cls, name: str, command: str) -> bool:
        """检查是否为硬件驱动相关"""
        hardware_keywords = ['nvidia', 'amd', 'ati', 'intel', 'realtek', 'radeon', 'geforce', 'cuda']
        combined = f"{name} {command}".lower()
        return any(keyword in combined for keyword in hardware_keywords)

    @classmethod
    def _is_im_software(cls, name: str, command: str) -> bool:
        """检查是否为即时通讯软件"""
        im_keywords = ['qq', 'wechat', 'telegram', 'slack', 'teams', 'discord', 'dingtalk']
        combined = f"{name} {command}".lower()
        return any(keyword in combined for keyword in im_keywords)

    @classmethod
    def _is_media_software(cls, name: str, command: str) -> bool:
        """检查是否为媒体软件"""
        media_keywords = ['spotify', 'itunes', 'winamp', 'foobar', 'music', 'player']
        combined = f"{name} {command}".lower()
        return any(keyword in combined for keyword in media_keywords)

    @classmethod
    def _can_delay_start(cls, name: str, command: str) -> bool:
        """检查是否可延迟启动"""
        delay_keywords = ['chrome', 'firefox', 'edge', 'office', 'adobe reader', 'word', 'excel']
        combined = f"{name} {command}".lower()
        return any(keyword in combined for keyword in delay_keywords)
