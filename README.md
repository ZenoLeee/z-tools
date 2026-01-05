# 跨平台系统工具箱 (z-tools)

一款功能强大的跨平台系统工具箱，支持 Windows 和 macOS，帮助你清理系统垃圾、优化系统性能和管理文件。

![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)

## ✨ 功能特性

### 🧹 系统清理

整合了四大清理功能，帮助你释放磁盘空间，保持系统整洁：

- **无效快捷方式清理**
  - 扫描桌面、开始菜单等位置的无效快捷方式
  - 支持批量删除和恢复功能
  - 显示目标路径和错误信息

- **重复文件清理**
  - 基于MD5哈希值精确识别重复文件
  - 智能选择功能（自动保留最新文件）
  - 支持自定义文件类型和最小文件大小
  - 全选/反选功能

- **大文件清理**
  - 自定义最小文件大小（如100MB）
  - 快速定位占用空间的文件
  - 按大小排序，一目了然

- **空文件夹清理**
  - 扫描并显示所有空文件夹
  - 支持包含/不包含空子目录选项
  - 全选/反选批量操作

### 📋 注册表清理（仅 Windows）

安全高效地清理注册表，提升系统性能：

- **无效软件清理** - 扫描已卸载软件的注册表残留
- **启动项清理** - 清理无效的启动项引用
- **文件引用清理** - 清理最近的文档记录和运行历史
- **自动备份** - 清理前自动创建 .reg 备份文件
- **一键恢复** - 支持从备份恢复注册表
- **全选/反选** - 方便批量操作

> **注意**：macOS 没有注册表，此功能仅在 Windows 平台可用。macOS 用户可以使用启动项管理功能。

### 🌐 网络工具

全面的网络诊断和测试工具：

- **Ping 测试**
  - 支持自定义Ping次数
  - 快速测试按钮（本地DNS、谷歌DNS、百度等）
  - 实时显示Ping结果和统计信息

- **网络诊断工具**
  - 查看网络连接信息
  - 刷新DNS缓存
  - 查看ARP缓存
  - 释放/续约IP地址
  - 查看路由表
  - 输出内容支持复制

### 💻 系统工具

- 开机启动项管理
- 系统信息查看
- 进程管理
- 服务管理

### 🔄 自动更新

- 内置版本检测功能
- 基于 GitHub Releases 的版本管理
- 支持自动下载和安装更新
- 文件名格式：`z-tools_v{version}.exe`

## 系统要求

### Windows
- Windows 10/11
- 1GB RAM 或更高
- 50MB 可用磁盘空间

### macOS
- macOS 10.14 (Mojave) 或更高
- 1GB RAM 或更高
- 50MB 可用磁盘空间

### 通用要求
- Python 3.8 或更高（仅从源码运行时需要）
- 预编译版本无需安装 Python

## 安装方法

### 方式 1：下载预编译版本（推荐）

#### Windows
1. 访问 [Releases 页面](https://github.com/ZenoLeee/z-tools/releases)
2. 下载最新的 `z-tools_v{version}.exe`
3. 直接运行，无需安装

#### macOS
1. 访问 [Releases 页面](https://github.com/ZenoLeee/z-tools/releases)
2. 下载最新的 `z-tools_v{version}`
3. 添加执行权限：`chmod +x z-tools_v{version}`
4. 运行：`./z-tools_v{version}`

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

#### Windows
```bash
# 安装依赖
pip install -r requirements.txt

# 运行打包脚本
build.bat

# 打包后的文件在 dist/
```

#### macOS
```bash
# 安装依赖
pip3 install -r requirements.txt

# 添加执行权限
chmod +x build.sh

# 运行打包脚本
./build.sh

# 打包后的文件在 dist/
```

## 📖 使用说明

### 系统清理

1. 在主界面选择"系统清理"标签页
2. 选择子功能（快捷方式/重复文件/大文件/空文件夹）
3. 选择要扫描的目录或点击"全电脑扫描"
4. 点击"开始扫描"，等待扫描完成
5. 使用全选/反选功能选择要清理的项目
6. 点击"删除选中"执行清理

### 注册表清理

1. 在"系统清理"标签页选择"注册表清理"子标签
2. 勾选要扫描的类型（无效软件、启动项、文件引用）
3. 点击"开始扫描"，等待扫描完成
4. 使用全选/反选选择要清理的项目
5. 点击"清理选中"（程序会自动创建备份）
6. 如需恢复，点击"查看备份"选择备份文件恢复

**⚠️ 注意**：注册表清理前会自动创建备份到临时目录，建议定期检查备份文件。

### 网络工具

1. 选择"网络工具"标签页
2. **Ping测试**：输入IP地址或域名，点击"开始Ping测试"
3. **快速测试**：点击预设按钮快速测试常用地址
4. **诊断工具**：点击对应按钮执行网络诊断操作
5. 查看输出结果，可复制内容用于分析

## 开发

### 项目结构

```
z-tools/
├── core/                      # 核心功能模块
│   ├── file_scanner.py       # 文件扫描（重复文件、大文件、空文件夹）
│   ├── shortcut_scanner.py   # 快捷方式扫描
│   ├── registry_cleaner.py   # 注册表清理
│   ├── network_tools.py      # 网络工具
│   └── version_manager.py    # 版本管理和自动更新
├── ui/                        # 用户界面
│   ├── main_window.py        # 主窗口
│   ├── cleanup_tab.py        # 系统清理标签页
│   ├── scanner_tab.py        # 无效快捷方式
│   ├── duplicate_file_tab.py # 重复文件清理
│   ├── large_file_tab.py     # 大文件清理
│   ├── empty_folder_tab.py   # 空文件夹清理
│   ├── registry_tab.py       # 注册表清理
│   ├── system_tab.py         # 系统工具
│   └── network_tab.py        # 网络工具
├── utils/                     # 工具函数
│   └── file_utils.py         # 文件操作工具
├── main.py                   # 程序入口
├── build.bat                 # 打包脚本
└── requirements.txt          # 依赖列表
```

### 依赖库

- Python 3.8+
- tkinter（GUI框架）
- psutil（系统信息）
- pywin32（Windows API）

## 🎯 界面特性

- 🎨 **现代化UI设计** - 统一的按钮样式，清晰的颜色区分
- 📊 **实时进度显示** - 可视化进度条，实时显示扫描状态
- 🔢 **批量操作** - 全选/反选功能，高效管理大量项目
- 🎯 **智能选择** - 重复文件清理支持智能保留最新文件
- 🛡️ **安全保护** - 注册表清理自动备份，快捷方式支持恢复
- ⚡ **多线程扫描** - 后台扫描不阻塞界面，流畅体验
- 📋 **详细信息** - 完整显示文件信息、路径、大小等
- 🔍 **快速测试** - 网络工具内置常用测试地址

## 📝 更新日志

### v1.1.0 (2025-01-05)

#### 🚀 跨平台支持

**新增 macOS 平台支持**
- ✅ 完整的 macOS 平台适配
- ✅ 支持 macOS 10.14 (Mojave) 及更高版本
- ✅ 跨平台架构设计，自动识别运行平台

**平台特定功能优化**
- ✅ Windows：快捷方式（.lnk）扫描
- ✅ macOS：快捷别名（.alias）和 Web 定位（.webloc）扫描
- ✅ macOS：Dock 项目管理
- ✅ Windows：注册表清理（独占功能）
- ✅ macOS：LaunchAgents/LaunchDaemons 启动项管理

**跨平台通用功能**
- ✅ 重复文件清理（所有平台）
- ✅ 大文件管理（所有平台）
- ✅ 空文件夹清理（所有平台）
- ✅ 网络工具（所有平台）
- ✅ 系统信息查看（所有平台）

**开发工具优化**
- ✅ GitHub Actions 自动构建 Windows 和 macOS 版本
- ✅ 平台适配器模式，便于扩展 Linux 支持

**技术改进**
- ✅ 修复循环导入问题
- ✅ 优化平台检测机制（使用 sys.platform）
- ✅ 代码结构优化，分离平台特定代码

### v1.0.0 (2025-01-04)

#### 🎉 首次发布

**系统清理功能**
- ✅ 无效快捷方式扫描与清理（支持恢复）
- ✅ 重复文件查找（基于MD5）与清理
- ✅ 大文件扫描与管理
- ✅ 空文件夹清理
- ✅ 全选/反选批量操作
- ✅ 智能选择功能

**注册表清理功能**
- ✅ 无效软件注册表清理
- ✅ 启动项无效引用清理
- ✅ 最近文档和运行历史清理
- ✅ 自动备份功能
- ✅ 备份管理和一键恢复

**网络工具**
- ✅ Ping测试工具（支持快速测试）
- ✅ 网络连接信息查看
- ✅ DNS缓存刷新
- ✅ ARP缓存查看
- ✅ IP地址释放/续约
- ✅ 路由表查看
- ✅ 输出复制功能

**系统功能**
- ✅ 版本管理和自动更新
- ✅ 基于 GitHub Releases
- ✅ 开机启动项管理
- ✅ 系统信息查看
- ✅ 进程管理
- ✅ 服务管理

**界面优化**
- ✅ 现代化扁平按钮设计
- ✅ 统一的配色方案
- ✅ 实时进度显示
- ✅ 友好的错误提示
- ✅ 多线程扫描不卡顿

## ❓ 常见问题

### Q: 删除的文件可以恢复吗？
**A**:
- **快捷方式清理**：支持从回收站恢复，或使用"恢复"功能
- **注册表清理**：自动创建备份，可通过"查看备份"功能恢复
- **其他文件删除**：直接删除，建议在删除前仔细确认

### Q: 扫描大目录会卡顿吗？
**A**: 不会。程序使用多线程后台扫描，界面会保持响应，实时显示扫描进度和结果。

### Q: 可以自定义扫描范围吗？
**A**: 可以。所有扫描工具都支持自定义选择扫描路径，也可以使用"全电脑扫描"快速扫描所有磁盘。

### Q: 如何获取最新版本？
**A**: 程序内置自动更新功能，启动时会自动检测新版本。也可以手动检查更新。

### Q: 注册表清理安全吗？
**A**: 非常安全。程序在清理前会自动创建 .reg 格式的备份文件，如需恢复可直接双击备份文件或使用程序的恢复功能。

### Q: 智能选择是如何工作的？
**A**: 重复文件清理的智能选择功能会自动保留每个重复组中修改时间最新的文件，选择其他较旧的文件进行删除。

### Q: 支持哪些Windows版本？
**A**: 支持 Windows 10/11，建议使用 64 位系统以获得最佳性能。

### Q: 支持哪些macOS版本？
**A**: 支持 macOS 10.14 (Mojave) 及更高版本。

### Q: Windows和macOS功能一样吗？
**A**: 大部分功能相同，但有少量差异：
- **注册表清理**：仅 Windows 可用（macOS 没有注册表）
- **快捷方式清理**：两个平台都支持，但处理方式不同
- **启动项管理**：两个平台都支持，macOS 使用 LaunchAgents/LaunchDaemons
- **文件清理、网络工具**：完全相同

### Q: 如何在没有Mac的情况下测试Mac版本？
**A**: 有以下几种方式：
1. 使用 GitHub Actions 自动构建（已配置，推送到 GitHub 会自动构建）
2. 使用虚拟机安装 macOS
3. 借用朋友的 Mac 电脑测试
4. 使用 MacStadium 等 Mac 在线服务

## 贡献

欢迎贡献代码、报告 Bug 或提出新功能建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request


## 👨‍💻 作者

**Zeno** - [GitHub](https://github.com/ZenoLeee)

## 🙏 致谢

- 感谢所有贡献者和使用者
- 感谢开源社区的宝贵资源

## 📮 反馈与支持

- 🐛 提交 [Issue](https://github.com/ZenoLeee/z-tools/issues)
- 💡 功能建议：[Issues](https://github.com/ZenoLeee/z-tools/issues)
- 📥 访问 [项目主页](https://github.com/ZenoLeee/z-tools)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！**

Made with ❤️ by Zeno

</div>
