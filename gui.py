# -*- coding: utf-8 -*-
"""
gui.py — RightMenuManager 界面
Author: 衾衾 (Hermes Agent)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import ctypes
import sys

from core import MenuScanner, MenuManager, BackupManager, MenuItem


class App:
    """右键菜单管理器主界面"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RightMenuManager - 右键菜单管理")
        self.root.geometry("700x500")
        self.root.resizable(True, True)

        # 核心模块
        self.scanner = MenuScanner()
        self.manager = MenuManager()
        self.backup_mgr = BackupManager()

        # 数据
        self.all_items: list[MenuItem] = []
        self.filtered_items: list[MenuItem] = []
        self.check_vars: dict[str, tk.BooleanVar] = {}  # registry_path -> var

        # 界面
        self._build_ui()
        self._scan_menus()

    def _build_ui(self):
        root = self.root

        # 顶部工具栏
        toolbar = tk.Frame(root)
        toolbar.pack(fill='x', padx=10, pady=(10, 5))

        tk.Button(toolbar, text="扫描", command=self._scan_menus, width=8).pack(side='left', padx=2)
        tk.Button(toolbar, text="禁用选中", command=self._disable_selected, width=8, bg='#f44336', fg='white').pack(side='left', padx=2)
        tk.Button(toolbar, text="启用选中", command=self._enable_selected, width=8, bg='#4CAF50', fg='white').pack(side='left', padx=2)
        tk.Button(toolbar, text="清理无效", command=self._cleanup_invalid, width=8).pack(side='left', padx=2)

        ttk.Separator(toolbar, orient='vertical').pack(side='left', fill='y', padx=8)

        tk.Button(toolbar, text="备份", command=self._export_backup, width=6).pack(side='left', padx=2)
        tk.Button(toolbar, text="恢复", command=self._import_backup, width=6).pack(side='left', padx=2)

        ttk.Separator(toolbar, orient='vertical').pack(side='left', fill='y', padx=8)

        tk.Button(toolbar, text="全选", command=self._select_all, width=4).pack(side='left', padx=2)
        tk.Button(toolbar, text="反选", command=self._invert_selection, width=4).pack(side='left', padx=2)

        # 筛选区域
        filter_frame = tk.Frame(root)
        filter_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(filter_frame, text="菜单类型:").pack(side='left')
        self.type_var = tk.StringVar(value='all')
        for text, value in [("全部", "all"), ("文件", "file"), ("文件夹", "folder"), ("桌面", "desktop")]:
            tk.Radiobutton(filter_frame, text=text, variable=self.type_var, value=value,
                          command=self._apply_filter).pack(side='left', padx=5)

        tk.Label(filter_frame, text="  搜索:").pack(side='left', padx=(20, 0))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *_: self._apply_filter())
        tk.Entry(filter_frame, textvariable=self.search_var, width=20).pack(side='left', padx=5)

        tk.Label(filter_frame, text="显示:").pack(side='left', padx=(20, 0))
        self.show_var = tk.StringVar(value='all')
        for text, value in [("全部", "all"), ("已启用", "enabled"), ("已禁用", "disabled")]:
            tk.Radiobutton(filter_frame, text=text, variable=self.show_var, value=value,
                          command=self._apply_filter).pack(side='left', padx=5)

        # 菜单列表
        list_frame = tk.Frame(root)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Treeview
        columns = ('name', 'type', 'command', 'status')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', selectmode='extended')

        self.tree.heading('name', text='名称')
        self.tree.heading('type', text='类型')
        self.tree.heading('command', text='命令')
        self.tree.heading('status', text='状态')

        self.tree.column('name', width=150, minwidth=100)
        self.tree.column('type', width=80, minwidth=60)
        self.tree.column('command', width=300, minwidth=150)
        self.tree.column('status', width=80, minwidth=60)

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # 绑定事件
        self.tree.bind('<Double-1>', self._on_double_click)

        # 底部状态栏
        status_frame = tk.Frame(root)
        status_frame.pack(fill='x', padx=10, pady=(5, 10))

        self.status_label = tk.Label(status_frame, text="就绪", anchor='w')
        self.status_label.pack(side='left')

        self.count_label = tk.Label(status_frame, text="", anchor='e')
        self.count_label.pack(side='right')

    def _scan_menus(self):
        """扫描菜单"""
        self.status_label.config(text="正在扫描...")
        self.root.update()

        self.all_items = self.scanner.scan()
        self._apply_filter()

        self.status_label.config(text="扫描完成")
        self._update_count()

    def _apply_filter(self):
        """应用筛选条件"""
        type_filter = self.type_var.get()
        show_filter = self.show_var.get()
        search_text = self.search_var.get().lower()

        self.filtered_items = []
        for item in self.all_items:
            # 类型筛选
            if type_filter != 'all' and item.menu_type != type_filter:
                continue
            # 状态筛选
            if show_filter == 'enabled' and item.is_disabled:
                continue
            if show_filter == 'disabled' and not item.is_disabled:
                continue
            # 搜索筛选
            if search_text and search_text not in item.name.lower() and search_text not in item.command.lower():
                continue
            self.filtered_items.append(item)

        self._refresh_list()

    def _refresh_list(self):
        """刷新列表显示"""
        # 清空
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 重新填充
        for item in self.filtered_items:
            type_name = {'file': '文件', 'folder': '文件夹', 'desktop': '桌面'}.get(item.menu_type, item.menu_type)
            status = '已禁用' if item.is_disabled else '✓'
            tags = ('disabled',) if item.is_disabled else ()

            self.tree.insert('', 'end', iid=item.registry_path,
                           values=(item.name, type_name, item.command[:60], status),
                           tags=tags)

        # 样式
        self.tree.tag_configure('disabled', foreground='gray')

        self._update_count()

    def _update_count(self):
        """更新计数"""
        total = len(self.filtered_items)
        enabled = sum(1 for i in self.filtered_items if not i.is_disabled)
        disabled = total - enabled
        invalid = sum(1 for i in self.filtered_items if not i.is_valid)
        self.count_label.config(text=f"共 {total} 项 | 启用 {enabled} | 禁用 {disabled} | 无效 {invalid}")

    def _get_selected_items(self) -> list[MenuItem]:
        """获取选中的菜单项"""
        selected = self.tree.selection()
        items = []
        for path in selected:
            for item in self.filtered_items:
                if item.registry_path == path:
                    items.append(item)
                    break
        return items

    def _disable_selected(self):
        """禁用选中的菜单项"""
        selected = self._get_selected_items()
        if not selected:
            messagebox.showinfo("提示", "请先选择要禁用的菜单项")
            return

        # 过滤出已启用的项
        to_disable = [item for item in selected if not item.is_disabled]
        if not to_disable:
            messagebox.showinfo("提示", "选中的菜单项都已经是禁用状态")
            return

        # 自动备份
        self.backup_mgr.auto_backup(self.all_items)

        success_count = 0
        failed_items = []
        for item in to_disable:
            result = self.manager.disable_item(item)
            if result:
                item.is_disabled = True
                success_count += 1
            else:
                failed_items.append(item.name)

        self._refresh_list()

        if failed_items:
            detail = "\n".join([f"- {name}" for name in failed_items[:5]])
            messagebox.showwarning("部分失败",
                f"已禁用 {success_count} 个菜单项\n\n以下项目禁用失败（可能是权限不足）：\n{detail}")
        else:
            messagebox.showinfo("完成", f"已禁用 {success_count} 个菜单项")

    def _enable_selected(self):
        """启用选中的菜单项"""
        selected = self._get_selected_items()
        if not selected:
            messagebox.showinfo("提示", "请先选择要启用的菜单项")
            return

        # 过滤出已禁用的项
        to_enable = [item for item in selected if item.is_disabled]
        if not to_enable:
            messagebox.showinfo("提示", "选中的菜单项都已经是启用状态")
            return

        # 自动备份
        self.backup_mgr.auto_backup(self.all_items)

        success_count = 0
        for item in to_enable:
            if self.manager.enable_item(item):
                item.is_disabled = False
                success_count += 1

        self._refresh_list()
        messagebox.showinfo("完成", f"已启用 {success_count} 个菜单项")

    def _cleanup_invalid(self):
        """清理无效菜单项"""
        # 重新扫描，确保数据最新
        self._scan_menus()

        invalid_items = [item for item in self.all_items if not item.is_valid and not item.is_disabled]
        if not invalid_items:
            messagebox.showinfo("提示", "没有发现需要清理的无效菜单项")
            return

        # 显示详细信息
        detail = "\n".join([f"- {item.name} ({item.menu_type})" for item in invalid_items[:10]])
        if len(invalid_items) > 10:
            detail += f"\n... 还有 {len(invalid_items) - 10} 项"

        result = messagebox.askyesno("确认清理",
            f"发现 {len(invalid_items)} 个无效菜单项：\n\n{detail}\n\n是否全部禁用？")
        if not result:
            return

        # 自动备份
        self.backup_mgr.auto_backup(self.all_items)

        success_count = 0
        for item in invalid_items:
            if self.manager.disable_item(item):
                item.is_disabled = True
                success_count += 1

        self._refresh_list()
        messagebox.showinfo("完成", f"已禁用 {success_count} 个无效菜单项")

    def _export_backup(self):
        """导出备份"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json")],
            title="导出备份",
        )
        if filepath:
            self.backup_mgr.export_backup(self.all_items, filepath)
            messagebox.showinfo("完成", f"备份已保存到：\n{filepath}")

    def _import_backup(self):
        """导入备份"""
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON 文件", "*.json")],
            title="选择备份文件",
        )
        if filepath:
            try:
                items = self.backup_mgr.import_backup(filepath)
                # 恢复状态
                for item in items:
                    if item.is_disabled:
                        self.manager.disable_item(item)
                    else:
                        self.manager.enable_item(item)
                self._scan_menus()
                messagebox.showinfo("完成", "备份已恢复")
            except Exception as e:
                messagebox.showerror("错误", f"恢复失败：{e}")

    def _select_all(self):
        """全选"""
        for item in self.tree.get_children():
            self.tree.selection_add(item)

    def _invert_selection(self):
        """反选"""
        selected = set(self.tree.selection())
        for item in self.tree.get_children():
            if item in selected:
                self.tree.selection_remove(item)
            else:
                self.tree.selection_add(item)

    def _on_double_click(self, event):
        """双击跳转到注册表"""
        selected = self._get_selected_items()
        if selected:
            item = selected[0]
            # 打开注册表编辑器并定位
            import subprocess
            reg_path = item.registry_path.replace("HKEY_CLASSES_ROOT\\", "")
            subprocess.Popen(['regedit', '/e', 'nul', reg_path])

    def run(self):
        self.root.mainloop()


def is_admin():
    """检查是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


if __name__ == '__main__':
    if not is_admin():
        # 请求管理员权限
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)

    app = App()
    app.run()