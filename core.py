# -*- coding: utf-8 -*-
"""
core.py — RightMenuManager 注册表扫描和操作引擎
Author: 衾衾 (Hermes Agent)

功能：
1. MenuScanner — 扫描右键菜单项
2. MenuManager — 启用/禁用/删除菜单项
3. BackupManager — 备份/恢复功能
"""

import winreg
import json
import os
import shutil
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Tuple
from datetime import datetime


@dataclass
class MenuItem:
    """菜单项数据类"""
    name: str               # 菜单项名称
    registry_path: str      # 注册表完整路径
    command: str            # 执行的命令（可能为空）
    is_disabled: bool       # 是否已禁用
    is_valid: bool          # 是否有效（命令对应的文件存在）
    menu_type: str          # 类型：file/folder/desktop
    parent_key: str         # 父级注册表键名


# ── 注册表路径常量 ──

REG_PATHS = {
    'file': [
        (winreg.HKEY_CLASSES_ROOT, r'*\shell'),
        (winreg.HKEY_CLASSES_ROOT, r'*\shellex\ContextMenuHandlers'),
    ],
    'folder': [
        (winreg.HKEY_CLASSES_ROOT, r'Directory\shell'),
        (winreg.HKEY_CLASSES_ROOT, r'Directory\shellex\ContextMenuHandlers'),
        (winreg.HKEY_CLASSES_ROOT, r'Folder\shell'),
    ],
    'desktop': [
        (winreg.HKEY_CLASSES_ROOT, r'Directory\Background\shell'),
        (winreg.HKEY_CLASSES_ROOT, r'DesktopBackground\shell'),
    ],
}


class MenuScanner:
    """菜单扫描器"""

    @staticmethod
    def _parse_command(key_path: str, hive: int) -> str:
        """解析菜单项的命令"""
        try:
            cmd_path = key_path + r'\command'
            key = winreg.OpenKey(hive, cmd_path, 0, winreg.KEY_READ)
            command, _ = winreg.QueryValueEx(key, '')
            winreg.CloseKey(key)
            return command
        except (FileNotFoundError, OSError):
            return ''

    @staticmethod
    def _is_disabled(key_path: str, hive: int) -> bool:
        """检查菜单项是否已禁用"""
        try:
            key = winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, 'LegacyDisable')
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                pass
            try:
                winreg.QueryValueEx(key, 'Disabled')
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
        except (FileNotFoundError, OSError):
            pass
        return False

    @staticmethod
    def _is_valid_command(command: str) -> bool:
        """检查命令是否有效"""
        if not command:
            return True  # 没有命令的不算无效（可能是子菜单）

        # 提取可执行文件路径
        cmd = command.strip()

        # 处理带引号的路径
        if cmd.startswith('"'):
            end_quote = cmd.find('"', 1)
            if end_quote > 0:
                cmd = cmd[1:end_quote]
        else:
            # 取第一个空格前的部分
            cmd = cmd.split(' ')[0]

        # 跳过环境变量路径（%开头的）
        if cmd.startswith('%'):
            return True

        # 跳过特殊命令
        if cmd.lower() in ['cmd', 'cmd.exe', 'powershell', 'powershell.exe']:
            return True

        # 检查文件是否存在
        if os.path.exists(cmd):
            return True

        # 尝试在PATH中查找
        for path_dir in os.environ.get('PATH', '').split(';'):
            full_path = os.path.join(path_dir, cmd)
            if os.path.exists(full_path):
                return True
            if os.path.exists(full_path + '.exe'):
                return True

        return False

    @staticmethod
    def _get_menu_type_name(menu_type: str) -> str:
        """获取菜单类型的中文名称"""
        names = {
            'file': '文件菜单',
            'folder': '文件夹菜单',
            'desktop': '桌面菜单',
        }
        return names.get(menu_type, menu_type)

    @classmethod
    def _scan_single_path(cls, hive: int, path: str, menu_type: str) -> List[MenuItem]:
        """扫描单个注册表路径"""
        items = []
        # 根据 hive 确定前缀
        hive_name = 'HKEY_CLASSES_ROOT' if hive == winreg.HKEY_CLASSES_ROOT else 'HKEY_CURRENT_USER'

        try:
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey_path = path + '\\' + subkey_name
                    full_path = hive_name + '\\' + subkey_path

                    # 读取显示名称
                    try:
                        subkey = winreg.OpenKey(hive, subkey_path, 0, winreg.KEY_READ)
                        try:
                            display_name, _ = winreg.QueryValueEx(subkey, '')
                            if not display_name:
                                display_name = subkey_name
                        except FileNotFoundError:
                            display_name = subkey_name
                        winreg.CloseKey(subkey)
                    except (FileNotFoundError, OSError):
                        display_name = subkey_name

                    # 解析命令
                    command = cls._parse_command(subkey_path, hive)

                    # 检查状态
                    is_disabled = cls._is_disabled(subkey_path, hive)
                    is_valid = cls._is_valid_command(command)

                    # 创建菜单项
                    item = MenuItem(
                        name=display_name,
                        registry_path=full_path,
                        command=command,
                        is_disabled=is_disabled,
                        is_valid=is_valid,
                        menu_type=menu_type,
                        parent_key=subkey_name,
                    )
                    items.append(item)

                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except (FileNotFoundError, OSError):
            pass
        return items

    @classmethod
    def scan(cls, menu_types: Optional[List[str]] = None) -> List[MenuItem]:
        """扫描指定类型的菜单项"""
        if menu_types is None:
            menu_types = list(REG_PATHS.keys())

        all_items = []
        for menu_type in menu_types:
            if menu_type not in REG_PATHS:
                continue
            for hive, path in REG_PATHS[menu_type]:
                items = cls._scan_single_path(hive, path, menu_type)
                all_items.extend(items)

        # 去重（按注册表路径）
        seen = set()
        unique_items = []
        for item in all_items:
            if item.registry_path not in seen:
                seen.add(item.registry_path)
                unique_items.append(item)

        return unique_items


class MenuManager:
    """菜单管理器"""

    @staticmethod
    def disable_item(item: MenuItem) -> bool:
        """禁用菜单项（添加 LegacyDisable 键值）"""
        try:
            # 根据注册表路径确定 hive
            if item.registry_path.startswith('HKEY_CLASSES_ROOT\\'):
                hive = winreg.HKEY_CLASSES_ROOT
                path = item.registry_path[len('HKEY_CLASSES_ROOT\\'):]
            elif item.registry_path.startswith('HKEY_CURRENT_USER\\'):
                hive = winreg.HKEY_CURRENT_USER
                path = item.registry_path[len('HKEY_CURRENT_USER\\'):]
            else:
                return False

            # 尝试打开键
            try:
                key = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE)
            except PermissionError:
                # 权限不足，尝试以管理员权限打开
                return False
            except FileNotFoundError:
                return False

            # 写入 LegacyDisable
            try:
                winreg.SetValueEx(key, 'LegacyDisable', 0, winreg.REG_SZ, '')
                winreg.CloseKey(key)
                return True
            except Exception:
                winreg.CloseKey(key)
                return False
        except Exception:
            return False

    @staticmethod
    def enable_item(item: MenuItem) -> bool:
        """启用菜单项（删除 LegacyDisable 键值）"""
        try:
            # 根据注册表路径确定 hive
            if item.registry_path.startswith('HKEY_CLASSES_ROOT\\'):
                hive = winreg.HKEY_CLASSES_ROOT
                path = item.registry_path[len('HKEY_CLASSES_ROOT\\'):]
            elif item.registry_path.startswith('HKEY_CURRENT_USER\\'):
                hive = winreg.HKEY_CURRENT_USER
                path = item.registry_path[len('HKEY_CURRENT_USER\\'):]
            else:
                return False

            # 尝试打开键
            try:
                key = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE)
            except PermissionError:
                return False
            except FileNotFoundError:
                return False

            # 删除禁用标记
            try:
                winreg.DeleteValue(key, 'LegacyDisable')
            except FileNotFoundError:
                pass
            try:
                winreg.DeleteValue(key, 'Disabled')
            except FileNotFoundError:
                pass

            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    @staticmethod
    def delete_item(item: MenuItem) -> bool:
        """删除菜单项（危险操作，需要谨慎）"""
        try:
            if item.registry_path.startswith('HKEY_CLASSES_ROOT'):
                hive = winreg.HKEY_CLASSES_ROOT
                path = item.registry_path.replace('HKEY_CLASSES_ROOT\\', '')
            else:
                return False

            # 获取父路径
            parent_path = '\\'.join(path.split('\\')[:-1])
            key_name = path.split('\\')[-1]

            parent_key = winreg.OpenKey(hive, parent_path, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteKey(parent_key, key_name)
            winreg.CloseKey(parent_key)
            return True
        except (FileNotFoundError, OSError):
            return False


class BackupManager:
    """备份管理器"""

    def __init__(self, backup_dir: str = None):
        if backup_dir is None:
            backup_dir = os.path.join(os.path.expanduser('~'), '.RightMenuManager', 'backups')
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)

    def export_backup(self, items: List[MenuItem], filepath: str = None) -> str:
        """导出备份到文件"""
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = os.path.join(self.backup_dir, f'backup_{timestamp}.json')

        data = {
            'timestamp': datetime.now().isoformat(),
            'items': [asdict(item) for item in items],
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filepath

    def import_backup(self, filepath: str) -> List[MenuItem]:
        """从备份文件恢复"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        items = []
        for item_data in data.get('items', []):
            items.append(MenuItem(**item_data))

        return items

    def list_backups(self) -> List[str]:
        """列出所有备份文件"""
        backups = []
        for f in os.listdir(self.backup_dir):
            if f.endswith('.json'):
                backups.append(os.path.join(self.backup_dir, f))
        return sorted(backups, reverse=True)

    def auto_backup(self, items: List[MenuItem]) -> str:
        """自动备份（返回备份文件路径）"""
        return self.export_backup(items)