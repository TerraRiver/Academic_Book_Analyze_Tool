import sys
import traceback
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        
        # Windows 特定设置
        if sys.platform == "win32":
            try:
                import ctypes
                # 设置应用程序 ID，让 Windows 识别为独立应用
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("mycompany.myproduct.subproduct.version")
                print("Windows 应用程序 ID 设置成功")
            except Exception as e:
                print(f"Windows 应用程序 ID 设置失败: {e}")
        
        # 设置图标
        icon_path = "assets/icons/app_icon.ico"
        print(f"尝试加载图标: {icon_path}")
        
        import os
        if os.path.exists(icon_path):
            print("图标文件存在")
            icon = QIcon(icon_path)
            if not icon.isNull():
                app.setWindowIcon(icon)
                print("应用程序图标设置成功")
            else:
                print("图标文件无法加载")
        else:
            print("图标文件不存在")
            icon = QIcon()  # 创建空图标
        
        print("创建主窗口...")
        window = MainWindow()
        
        if not icon.isNull():
            window.setWindowIcon(icon)
            print("窗口图标设置成功")
        
        print("显示窗口...")
        window.show()
        
        print("启动应用程序...")
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"发生错误: {e}")
        print("详细错误信息:")
        traceback.print_exc()
        input("按回车键退出...")  # 防止窗口立即关闭
