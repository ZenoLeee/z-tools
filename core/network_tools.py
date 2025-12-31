import subprocess
from PyQt5.QtCore import QThread, pyqtSignal

class PingThread(QThread):
    """Ping测试线程"""
    ping_output = pyqtSignal(str)  # Ping输出信号
    ping_finished = pyqtSignal(bool, str)  # 完成信号(成功与否, 结果摘要)

    def __init__(self, ip_address: str, count: int = 4):
        super().__init__()
        self.ip_address = ip_address
        self.count = count
        self.running = True

    def run(self):
        """执行Ping测试"""
        try:
            self.ping_output.emit(f"正在Ping {self.ip_address} ...")

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
                    self.ping_output.emit(line.strip())

            # 发送完成信号
            if self.running:
                success = result.returncode == 0
                if success:
                    summary = f"✓ 连接成功 (发送: {self.count}, 接收: 4)"
                else:
                    summary = f"✗ 连接失败 (返回码: {result.returncode})"
                self.ping_finished.emit(success, summary)

        except Exception as e:
            self.ping_output.emit(f"错误: {str(e)}")
            self.ping_finished.emit(False, f"执行错误: {str(e)}")

    def stop(self):
        """停止Ping测试"""
        self.running = False