# Windows工具箱

一款功能强大的 Windows 系统工具箱，帮助你清理系统垃圾、管理文件和优化系统性能。

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)

## 功能特性

### 文件清理工具

- **无效快捷方式清理** - 扫描并删除系统中无效的快捷方式，释放桌面和开始菜单空间
- **重复文件清理** - 快速查找重复文件，支持按文件名和内容比对，节省存储空间
- **大文件清理** - 扫描系统中的大文件，帮助你找出占用空间的文件
- **空文件夹清理** - 查找并删除空的文件夹，保持文件系统整洁

### 系统工具

- 开机启动项管理
- 系统信息查看
- 进程管理
- 服务管理

### 网络工具

- Ping 测试工具
- 网络连接查看
- 端口扫描
- 网络速度测试

### 自动更新

- 内置版本检测功能
- 支持自动下载和安装更新
- 基于 GitHub Releases 的版本管理

## 系统要求

- Windows 10/11
- 1GB RAM 或更高
- 50MB 可用磁盘空间

## 安装方法

### 方式 1：下载预编译版本（推荐）

1. 访问 [Releases 页面](https://github.com/ZenoLeee/z-tools/releases)
2. 下载最新的 `z-tools_v1.0.0.exe`（版本号会变化）
3. 直接运行，无需安装

### 方式 2：从源码运行

```bash
# 克隆仓库
git clone https://github.com/ZenoLeee/z-tools.git
cd z-tools

# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

### 方式 3：自行打包

```bash
# 安装依赖
pip install -r requirements.txt

# 运行打包脚本
build.bat

# 打包后的文件在 dist/z-tools_v1.0.0.exe（版本号会变化）
```

## 使用说明

### 无效快捷方式清理

1. 选择"无效快捷方式清理"标签页
2. 选择要扫描的路径（桌面、开始菜单等）
3. 点击"开始扫描"
4. 查看扫描结果，选择要删除的快捷方式
5. 点击"删除选中"清理无效快捷方式

### 重复文件清理

1. 选择"重复文件清理"标签页
2. 选择要扫描的目录
3. 点击"开始扫描"
4. 查看重复文件列表
5. 选择要删除的重复文件（每组保留一个）
6. 点击"删除选中"清理重复文件

### 大文件清理

1. 选择"大文件清理"标签页
2. 设置最小文件大小（如 100MB）
3. 选择要扫描的目录
4. 点击"开始扫描"
5. 查看大文件列表
6. 选择要删除的文件并清理

### 空文件夹清理

1. 选择"空文件夹清理"标签页
2. 选择要扫描的目录
3. 点击"开始扫描"
4. 查看空文件夹列表
5. 选择要删除的文件夹
6. 点击"删除选中"清理空文件夹

## 开发

### 项目结构

```
z-tools/
├── core/                   # 核心功能模块
│   ├── file_scanner.py    # 文件扫描功能
│   ├── network_tools.py   # 网络工具
│   ├── shortcut_scanner.py # 快捷方式扫描
│   └── version_manager.py # 版本管理
├── ui/                     # 用户界面
│   ├── main_window.py     # 主窗口
│   ├── scanner_tab.py     # 扫描标签页
│   ├── system_tab.py      # 系统工具
│   ├── network_tab.py     # 网络工具
│   └── ...
├── utils/                  # 工具函数
│   └── file_utils.py      # 文件操作工具
├── main.py                # 程序入口
├── build.bat              # 打包脚本
└── requirements.txt       # 依赖列表
```

### 依赖库

- Python 3.8+
- tkinter（GUI框架）
- psutil（系统信息）
- pywin32（Windows API）

## 更新日志

### v1.0.0 (2025-01-04)

#### 新增功能
- 无效快捷方式扫描与清理
- 重复文件查找与清理
- 大文件扫描与管理
- 空文件夹清理
- 系统工具（启动项、进程、服务管理）
- 网络工具（Ping、连接查看、端口扫描）
- 自动更新功能

#### 特性
- 现代化的用户界面
- 多线程扫描，不阻塞界面
- 支持批量操作
- 详细的扫描日志
- 安全删除（支持恢复）

## 常见问题

### Q: 删除的文件可以恢复吗？
**A**: 快捷方式清理支持从回收站恢复。其他文件删除操作会直接删除，建议在删除前仔细确认。

### Q: 扫描大目录会卡顿吗？
**A**: 不会。程序使用多线程扫描，界面会保持响应，实时显示扫描进度和结果。

### Q: 可以自定义扫描范围吗？
**A**: 可以。所有扫描工具都支持自定义选择扫描路径。

### Q: 如何获取最新版本？
**A**: 程序内置自动更新功能，启动时会自动检测。也可以通过菜单"帮助" → "检查更新"手动检查。

## 贡献

欢迎贡献代码、报告 Bug 或提出新功能建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request


## 作者

**Zeno** - [GitHub](https://github.com/ZenoLeee)

## 致谢

- 感谢所有贡献者
- 感谢使用本软件的用户

## 反馈与支持

- 提交 [Issue](https://github.com/ZenoLeee/z-tools/issues)
- 发送 [Pull Request](https://github.com/ZenoLeee/z-tools/pulls)
- 访问 [项目主页](https://github.com/ZenoLeee/z-tools)

---

⭐ 如果这个项目对你有帮助，请给个 Star！
