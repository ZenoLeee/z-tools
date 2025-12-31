import subprocess
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from core.network_tools import PingThread

class NetworkToolsTab(QWidget):
    """网络工具标签页"""

    def __init__(self):
        super().__init__()
        self.ping_thread = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Ping控制面板
        ping_group = QGroupBox("网络连接测试")
        ping_layout = QVBoxLayout()

        # IP地址输入
        ip_layout = QHBoxLayout()
        ip_layout.addWidget(QLabel("目标地址:"))
        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("例如: 192.168.1.1 或 www.google.com")
        self.ip_edit.setText("8.8.8.8")
        ip_layout.addWidget(self.ip_edit)

        # Ping次数
        ip_layout.addWidget(QLabel("次数:"))
        self.ping_count_combo = QComboBox()
        self.ping_count_combo.addItems(["1", "4", "8", "16"])
        self.ping_count_combo.setCurrentIndex(1)  # 默认4次
        ip_layout.addWidget(self.ping_count_combo)

        ping_layout.addLayout(ip_layout)

        # Ping按钮
        button_layout = QHBoxLayout()
        self.ping_btn = QPushButton("开始Ping测试")
        self.ping_btn.clicked.connect(self.start_ping)
        button_layout.addWidget(self.ping_btn)

        self.stop_ping_btn = QPushButton("停止")
        self.stop_ping_btn.clicked.connect(self.stop_ping)
        self.stop_ping_btn.setEnabled(False)
        button_layout.addWidget(self.stop_ping_btn)

        button_layout.addStretch()

        # 常用地址按钮
        common_ips_layout = QHBoxLayout()
        common_ips_layout.addWidget(QLabel("快速测试:"))

        common_ips = [
            ("本地", "127.0.0.1"),
            ("网关", "192.168.1.1"),
            ("谷歌DNS", "8.8.8.8"),
            ("百度", "www.baidu.com"),
            ("腾讯", "www.qq.com")
        ]

        for name, ip in common_ips:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, ip=ip: self.set_ip_address(ip))
            common_ips_layout.addWidget(btn)

        common_ips_layout.addStretch()
        ping_layout.addLayout(common_ips_layout)
        ping_layout.addLayout(button_layout)

        ping_group.setLayout(ping_layout)
        layout.addWidget(ping_group)

        # 网络诊断工具
        diag_group = QGroupBox("网络诊断工具")
        diag_layout = QVBoxLayout()

        # 网络信息按钮
        network_buttons = QHBoxLayout()
        self.network_info_btn = QPushButton("网络连接信息")
        self.network_info_btn.clicked.connect(self.show_network_info)
        network_buttons.addWidget(self.network_info_btn)

        self.flush_dns_btn = QPushButton("刷新DNS缓存")
        self.flush_dns_btn.clicked.connect(self.flush_dns)
        network_buttons.addWidget(self.flush_dns_btn)
        diag_layout.addLayout(network_buttons)

        # IP管理按钮
        ip_buttons = QHBoxLayout()
        self.release_ip_btn = QPushButton("释放IP地址")
        self.release_ip_btn.clicked.connect(self.release_ip)
        ip_buttons.addWidget(self.release_ip_btn)

        self.renew_ip_btn = QPushButton("续约IP地址")
        self.renew_ip_btn.clicked.connect(self.renew_ip)
        ip_buttons.addWidget(self.renew_ip_btn)
        diag_layout.addLayout(ip_buttons)

        # 其他工具按钮
        other_buttons = QHBoxLayout()
        self.arp_cache_btn = QPushButton("查看ARP缓存")
        self.arp_cache_btn.clicked.connect(self.show_arp_cache)
        other_buttons.addWidget(self.arp_cache_btn)

        self.route_table_btn = QPushButton("查看路由表")
        self.route_table_btn.clicked.connect(self.show_route_table)
        other_buttons.addWidget(self.route_table_btn)
        diag_layout.addLayout(other_buttons)

        diag_group.setLayout(diag_layout)
        layout.addWidget(diag_group)

        # 输出区域
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 9))
        self.output_text.setMaximumHeight(250)
        layout.addWidget(self.output_text)

        # 输出控制按钮
        output_controls = QHBoxLayout()
        self.clear_output_btn = QPushButton("清空输出")
        self.clear_output_btn.clicked.connect(self.clear_output)
        output_controls.addWidget(self.clear_output_btn)

        self.copy_output_btn = QPushButton("复制内容")
        self.copy_output_btn.clicked.connect(self.copy_output)
        output_controls.addWidget(self.copy_output_btn)

        output_controls.addStretch()
        layout.addLayout(output_controls)

        layout.addStretch()
        self.setLayout(layout)

    def set_ip_address(self, ip: str):
        """设置IP地址到输入框"""
        self.ip_edit.setText(ip)

    def start_ping(self):
        """开始Ping测试"""
        ip = self.ip_edit.text().strip()
        if not ip:
            QMessageBox.warning(self, "警告", "请输入IP地址或域名")
            return

        # 禁用按钮，启用停止按钮
        self.ping_btn.setEnabled(False)
        self.stop_ping_btn.setEnabled(True)

        # 清空输出
        self.output_text.clear()

        # 获取Ping次数
        count = int(self.ping_count_combo.currentText())

        # 创建并启动Ping线程
        self.ping_thread = PingThread(ip, count)
        self.ping_thread.ping_output.connect(self.append_ping_output)
        self.ping_thread.ping_finished.connect(self.on_ping_finished)
        self.ping_thread.start()

    def stop_ping(self):
        """停止Ping测试"""
        if self.ping_thread and self.ping_thread.isRunning():
            self.ping_thread.stop()
            self.ping_thread.wait()
            self.append_ping_output("Ping测试已停止")

        self.ping_btn.setEnabled(True)
        self.stop_ping_btn.setEnabled(False)

    def append_ping_output(self, text: str):
        """添加Ping输出到文本区域"""
        self.output_text.append(text)
        # 滚动到底部
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_ping_finished(self, success: bool, summary: str):
        """Ping测试完成"""
        self.append_ping_output("=" * 50)
        self.append_ping_output(summary)

        # 恢复按钮状态
        self.ping_btn.setEnabled(True)
        self.stop_ping_btn.setEnabled(False)

    def show_network_info(self):
        """显示网络连接信息"""
        try:
            result = subprocess.run(
                ["ipconfig", "/all"],
                capture_output=True,
                text=True,
                encoding='gbk'
            )
            self.output_text.setText("网络连接信息:\n" + "=" * 50 + "\n")
            self.output_text.append(result.stdout)
        except Exception as e:
            self.output_text.setText(f"错误: {e}")

    def release_ip(self):
        """释放IP地址"""
        try:
            result = subprocess.run(
                ["ipconfig", "/release"],
                capture_output=True,
                text=True,
                encoding='gbk'
            )
            self.output_text.setText("IP地址释放结果:\n" + "=" * 50 + "\n")
            self.output_text.append(result.stdout)
        except Exception as e:
            self.output_text.setText(f"错误: {e}")

    def renew_ip(self):
        """续约IP地址"""
        try:
            result = subprocess.run(
                ["ipconfig", "/renew"],
                capture_output=True,
                text=True,
                encoding='gbk'
            )
            self.output_text.setText("IP地址续约结果:\n" + "=" * 50 + "\n")
            self.output_text.append(result.stdout)
        except Exception as e:
            self.output_text.setText(f"错误: {e}")

    def flush_dns(self):
        """刷新DNS缓存"""
        try:
            result = subprocess.run(
                ["ipconfig", "/flushdns"],
                capture_output=True,
                text=True,
                encoding='gbk'
            )
            self.output_text.setText("DNS缓存刷新结果:\n" + "=" * 50 + "\n")
            self.output_text.append(result.stdout)
        except Exception as e:
            self.output_text.setText(f"错误: {e}")

    def show_arp_cache(self):
        """查看ARP缓存"""
        try:
            result = subprocess.run(
                ["arp", "-a"],
                capture_output=True,
                text=True,
                encoding='gbk'
            )
            self.output_text.setText("ARP缓存:\n" + "=" * 50 + "\n")
            self.output_text.append(result.stdout)
        except Exception as e:
            self.output_text.setText(f"错误: {e}")

    def show_route_table(self):
        """查看路由表"""
        try:
            result = subprocess.run(
                ["route", "print"],
                capture_output=True,
                text=True,
                encoding='gbk'
            )
            self.output_text.setText("路由表:\n" + "=" * 50 + "\n")
            self.output_text.append(result.stdout)
        except Exception as e:
            self.output_text.setText(f"错误: {e}")

    def clear_output(self):
        """清空输出区域"""
        self.output_text.clear()

    def copy_output(self):
        """复制输出内容到剪贴板"""
        text = self.output_text.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "成功", "内容已复制到剪贴板")