# build.py
import os
import sys
import shutil
import subprocess
from pathlib import Path

def clean_build():
    """清理之前的构建文件"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"已清理: {dir_name}")

def build_exe():
    """构建exe文件"""
    print("开始构建exe...")
    
    if shutil.which("uv") is None:
        print("未找到 uv，请先安装 uv 后再执行构建。")
        return False

    # 使用 uv 管理构建依赖，并通过 build 依赖组运行 PyInstaller
    cmd = ['uv', 'run', '--group', 'build', 'pyinstaller', '--clean', 'build_config.spec']
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("构建成功！")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("构建失败！")
        print(e.stderr)
        return False
    
    return True

def post_build_setup():
    """构建后的设置"""
    dist_dir = Path('dist')
    if not dist_dir.exists():
        print("dist目录不存在")
        return
    
    # 复制必要的文件到dist目录
    files_to_copy = [
        'config.ini',
        'README.md'
    ]
    
    for item in files_to_copy:
        src = Path(item)
        if src.exists():
            if src.is_file():
                shutil.copy2(src, dist_dir / src.name)
            else:
                shutil.copytree(src, dist_dir / src.name, dirs_exist_ok=True)
            print(f"已复制: {item}")
    
    # 创建data目录
    data_dir = dist_dir / 'data'
    data_dir.mkdir(exist_ok=True)
    print("已创建data目录")

if __name__ == "__main__":
    print("=== PyInstaller 构建脚本 ===")
    
    # 清理
    clean_build()
    
    # 构建
    if build_exe():
        # 后处理
        post_build_setup()
        print("\n构建完成！可执行文件位于 dist/ 目录中")
    else:
        print("\n构建失败！")
        sys.exit(1)
