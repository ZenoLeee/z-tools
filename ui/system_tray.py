"""
系统托盘管理模块
提供跨平台的系统托盘功能
"""
import os
import sys


class SystemTrayManager:
    """系统托盘管理器"""

    def __init__(self, window, show_window_callback, quit_callback):
        """
        初始化系统托盘管理器

        Args:
            window: 主窗口对象
            show_window_callback: 显示窗口的回调函数
            quit_callback: 退出程序的回调函数
        """
        self.window = window
        self.show_window_callback = show_window_callback
        self.quit_callback = quit_callback
        self.icon = None

    def _get_icon_path(self):
        """获取图标文件路径"""
        # 获取资源目录路径
        if getattr(sys, 'frozen', False):
            # 打包后的exe，资源在exe所在目录
            base_path = os.path.dirname(sys.executable)
        else:
            # 开发环境
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        icon_path = os.path.join(base_path, 'resources', 'icon.ico')

        if not os.path.exists(icon_path):
            print(f"警告: 图标文件不存在: {icon_path}")
            return None

        return icon_path

    def _create_icon_image_fallback(self):
        """
        后备方案：动态创建托盘图标（需要Pillow）
        仅在图标文件不存在时使用
        """
        try:
            from PIL import Image, ImageDraw

            # 创建一个 64x64 的图像
            width = 64
            height = 64
            image = Image.new('RGB', (width, height), color=(74, 144, 226))
            draw = ImageDraw.Draw(image)

            # 绘制工具箱图标
            center_x, center_y = width // 2, height // 2
            box_size = 24

            draw.rectangle(
                [(center_x - box_size, center_y - box_size),
                 (center_x + box_size, center_y + box_size)],
                fill='white',
                outline='white'
            )

            inner_size = 16
            draw.rectangle(
                [(center_x - inner_size, center_y - inner_size),
                 (center_x + inner_size, center_y + inner_size)],
                fill=(74, 144, 226),
                outline=(74, 144, 226)
            )

            handle_height = 8
            handle_width = 16
            draw.rectangle(
                [(center_x - handle_width // 2, center_y - box_size - handle_height),
                 (center_x + handle_width // 2, center_y - box_size)],
                fill='white',
                outline='white'
            )

            return image
        except ImportError:
            print("错误: Pillow 未安装，无法创建图标")
            return None

    def _create_menu(self):
        """创建托盘右键菜单"""
        import pystray
        menu = pystray.Menu(
            pystray.MenuItem('显示窗口', self._on_show_window, default=True),
            pystray.MenuItem('退出程序', self._on_quit)
        )
        return menu

    def _on_show_window(self):
        """显示窗口"""
        if self.show_window_callback:
            # 使用 tkinter 的 after 方法确保在主线程中执行
            self.window.after(0, self.show_window_callback)

    def _on_quit(self):
        """退出程序"""
        if self.quit_callback:
            # 使用 tkinter 的 after 方法确保在主线程中执行
            self.window.after(0, self.quit_callback)

    def _on_click(self):
        """托盘图标单击事件"""
        self._on_show_window()

    def create_tray_icon(self):
        """创建系统托盘图标"""
        import pystray

        # 尝试加载图标文件
        icon_path = self._get_icon_path()

        if icon_path and os.path.exists(icon_path):
            from PIL import Image
            icon_image = Image.open(icon_path)
        else:
            icon_image = self._create_icon_image_fallback()
            if not icon_image:
                raise RuntimeError("无法创建托盘图标")

        # 创建托盘图标
        self.icon = pystray.Icon(
            'WindowsToolbox',
            icon_image,
            menu=self._create_menu(),
            default_action=self._on_click
        )

        return self.icon

    def stop(self):
        """停止托盘图标"""
        if self.icon:
            self.icon.stop()