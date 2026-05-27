# -*- coding: utf-8 -*-
"""
RightMenuManager — Windows 右键菜单管理工具
Author: 衾衾 (Hermes Agent)

一个轻量的 Windows 右键菜单管理工具，
帮助用户清理和管理传统右键菜单中的菜单项。
"""

import sys
import os

# 确保能找到同目录下的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import App, is_admin


def main():
    """程序入口"""
    if not is_admin():
        print("提示：此程序需要管理员权限才能操作注册表。")
        print("请右键点击程序，选择'以管理员身份运行'。")
        input("按回车键退出...")
        return

    app = App()
    app.run()


if __name__ == '__main__':
    main()