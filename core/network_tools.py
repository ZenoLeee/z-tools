import subprocess
import threading
from typing import Callable


class PingThread(threading.Thread):
    """Ping测试线程"""

    def __init__(self, ip_address: str, count: int = 4):
        super().__init__()
        self.ip_address = ip_address
        self.count = count
        self.running = True

        # 回调函数
        self.output_callback: Callable[[str], None] = None
        self.finished_callback: Callable[[bool, str], None] = None

    def set_output_callback(self, callback: Callable[[str], None]):
        """设置输出回调"""
        self.output_callback = callback

    def set_finished_callback(self, callback: Callable[[bool, str], None]):
        """设置完成回调"""
        self.finished_callback = callback

    def run(self):
        """执行Ping测试"""
        try:
            self._emit_output(f"正在Ping {self.ip_address} ...")

            # 执行ping命令
            result = subprocess.run(
                ["ping", "-n", str(self.count), "-w", "1000", self.ip_address],
                capture_output=True,
                text=True,
                encoding='gbk'
            )

            # 逐行发送输出
            for line in result.stdout.split('\n'):
                if not self.running:
                    break
                if line.strip():
                    self._emit_output(line.strip())

            # 发送完成信号
            if self.running:
                success = result.returncode == 0
                if success:
                    summary = f"✓ 连接成功 (发送: {self.count}, 接收: 4)"
                else:
                    summary = f"✗ 连接失败 (返回码: {result.returncode})"
                self._emit_finished(success, summary)

        except Exception as e:
            self._emit_output(f"错误: {str(e)}")
            self._emit_finished(False, f"执行错误: {str(e)}")

    def _emit_output(self, text: str):
        """发送输出信号"""
        if self.output_callback:
            self.output_callback(text)

    def _emit_finished(self, success: bool, summary: str):
        """发送完成信号"""
        if self.finished_callback:
            self.finished_callback(success, summary)

    def stop(self):
        """停止Ping测试"""
        self.running = False
