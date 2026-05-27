# RightMenuManager - Windows 右键菜单管理工具

## 项目概述

一款轻量的 Windows 右键菜单管理工具，帮助用户清理和管理传统右键菜单中的菜单项。

## 背景

Windows 11 默认使用"简化版"右键菜单，很多功能被隐藏。用户可以通过注册表或工具禁用简化版菜单，恢复传统右键菜单。但传统菜单也会随着软件安装越来越乱，需要一个工具来管理。

## 功能需求

### 核心功能

1. **扫描菜单项**
   - 扫描文件右键菜单（所有文件类型）
   - 扫描文件夹右键菜单
   - 扫描桌面/背景右键菜单
   - 显示每个菜单项的来源（注册表路径）

2. **禁用/启用菜单项**
   - 一键禁用指定菜单项（不删除，只是隐藏）
   - 一键启用已禁用的菜单项
   - 批量操作支持

3. **清理无效项**
   - 自动检测无效/残留的菜单项
   - 一键清理所有无效项

4. **备份/恢复**
   - 导出当前菜单配置到文件
   - 从备份文件恢复
   - 自动备份（每次修改前）

### 界面设计

```
┌─────────────────────────────────────────────────────────────┐
│  📋 RightMenuManager - 右键菜单管理                         │
├─────────────────────────────────────────────────────────────┤
│  [扫描] [清理无效] [备份] [恢复]                            │
├─────────────────────────────────────────────────────────────┤
│  菜单类型: ○文件 ○文件夹 ○桌面 ●全部                        │
├─────────────────────────────────────────────────────────────┤
│  ☑ 新建                        HKCR\*\shell\New            │
│  ☑ 打开方式                    HKCR\*\shell\OpenWith       │
│  ☐ Adobe Acrobat               HKCR\*\shell\Acrobat        │
│  ☑ 添加到压缩文件              HKCR\*\shell\WinRAR         │
│  ☑ 复制到                      HKCR\*\shell\CopyTo         │
│  ☑ 移动到                      HKCR\*\shell\MoveTo         │
│  ...                                                        │
├─────────────────────────────────────────────────────────────┤
│  已选择: 5 项 | 已禁用: 1 项 | 无效: 0 项                   │
└─────────────────────────────────────────────────────────────┘
```

### 操作说明

- **勾选/取消勾选**：启用/禁用菜单项
- **右键菜单**：查看详情、删除、导出
- **双击**：跳转到注册表位置（打开 regedit）
- **拖拽**：排序（如果支持）

## 技术方案

### 技术栈

- **语言**: Python 3.7+
- **界面**: tkinter（轻量，无需额外依赖）
- **注册表操作**: `winreg` 模块（Python 内置）
- **打包**: PyInstaller

### 注册表路径

```
# 文件右键菜单
HKEY_CLASSES_ROOT\*\shell\                    # 所有文件
HKEY_CLASSES_ROOT\*\shellex\ContextMenuHandlers\  # Shell 扩展

# 文件夹右键菜单
HKEY_CLASSES_ROOT\Directory\shell\
HKEY_CLASSES_ROOT\Directory\shellex\ContextMenuHandlers\

# 桌面/背景右键菜单
HKEY_CLASSES_ROOT\Directory\Background\shell\
HKEY_CLASSES_ROOT\DesktopBackground\shell\

# 特定文件类型
HKEY_CLASSES_ROOT\.txt\shell\                # .txt 文件
HKEY_CLASSES_ROOT\.jpg\shell\                # .jpg 文件
```

### 禁用机制

**方法一：添加 Disabled 键值（推荐）**
```python
# 在菜单项下添加 "Disabled" 字符串值
import winreg
key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"*\shell\SomeMenu", 0, winreg.KEY_SET_VALUE)
winreg.SetValueEx(key, "Disabled", 0, winreg.REG_SZ, "")
winreg.CloseKey(key)
```

**方法二：修改 Flags（备选）**
```python
# 在菜单项的 command 下添加 flags
key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"*\shell\SomeMenu\command", 0, winreg.KEY_SET_VALUE)
winreg.SetValueEx(key, "Flags", 0, winreg.REG_DWORD, 0x00000001)  # 1 = 禁用
winreg.CloseKey(key)
```

**推荐方法一**，因为：
- 不删除原始数据，安全
- Windows 原生支持
- 恢复时删除 Disabled 键值即可

### 文件结构

```
RightMenuManager/
├── main.py              # 程序入口
├── core.py              # 注册表扫描和操作逻辑
├── gui.py               # tkinter 界面
├── backup.py            # 备份/恢复功能
├── README.md            # 项目说明
├── LICENSE              # MIT 开源协议
└── start.bat            # 一键启动脚本
```

### 核心模块设计

#### core.py - 注册表操作引擎

```python
class MenuItem:
    """菜单项数据类"""
    name: str           # 菜单项名称
    registry_path: str  # 注册表路径
    command: str        # 执行的命令
    is_disabled: bool   # 是否已禁用
    is_valid: bool      # 是否有效（命令存在）
    menu_type: str      # 类型：file/folder/desktop

class MenuScanner:
    """菜单扫描器"""
    def scan_file_menus() -> List[MenuItem]
    def scan_folder_menus() -> List[MenuItem]
    def scan_desktop_menus() -> List[MenuItem]
    def scan_all() -> List[MenuItem]

class MenuManager:
    """菜单管理器"""
    def disable_item(item: MenuItem) -> bool
    def enable_item(item: MenuItem) -> bool
    def delete_item(item: MenuItem) -> bool
    def cleanup_invalid() -> int
```

#### backup.py - 备份管理

```python
class BackupManager:
    """备份管理器"""
    def export_backup(filepath: str) -> bool
    def import_backup(filepath: str) -> bool
    def auto_backup() -> str  # 返回备份文件路径
```

## 执行步骤

### 第一阶段：核心功能（最小可用版本）

1. **创建项目结构**
   - 创建目录和基础文件
   - 初始化 git 仓库

2. **实现注册表扫描**
   - 扫描 `HKEY_CLASSES_ROOT\*\shell\`
   - 解析菜单项名称和命令
   - 检测是否已禁用

3. **实现禁用/启用功能**
   - 添加 Disabled 键值
   - 删除 Disabled 键值

4. **实现基础界面**
   - 显示菜单项列表
   - 勾选/取消勾选操作
   - 应用按钮

### 第二阶段：增强功能

5. **扩展扫描范围**
   - 文件夹菜单
   - 桌面菜单
   - 特定文件类型

6. **清理无效项**
   - 检测命令路径是否存在
   - 一键清理功能

7. **备份/恢复**
   - 导出到 JSON 文件
   - 从 JSON 恢复
   - 自动备份

### 第三阶段：优化体验

8. **界面美化**
   - 分组显示
   - 搜索功能
   - 右键菜单

9. **打包发布**
   - PyInstaller 打包
   - 创建 README
   - 发布到 GitHub

## 注意事项

### 安全性

- **不删除菜单项**：只禁用，不删除，避免系统损坏
- **自动备份**：每次修改前自动备份
- **恢复功能**：提供一键恢复到初始状态

### 兼容性

- **Windows 10/11**：支持两个版本
- **管理员权限**：修改注册表需要管理员权限
- **杀毒软件**：可能被误报，需要添加白名单

### 维护性

- **模块化设计**：扫描、管理、备份分离
- **配置文件**：用户配置保存在 JSON 文件
- **日志记录**：记录所有操作，方便排查问题

## 后续扩展（可选）

- **菜单项排序**：通过注册表调整顺序
- **自定义菜单项**：添加自定义功能
- **导入/导出规则**：分享菜单配置
- **定时清理**：自动清理新安装软件添加的菜单项

---

*方案由衾衾整理，等主人确认后开工。*