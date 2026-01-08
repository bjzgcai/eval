#!/usr/bin/env python3
"""
开发环境设置脚本
自动创建虚拟环境并安装依赖
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"   ✅ {description}: 成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ {description}: 失败")
        print(f"   错误信息: {e.stderr}")
        return False

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ 需要Python 3.8或更高版本")
        print(f"   当前版本: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python版本检查通过: {version.major}.{version.minor}.{version.micro}")
    return True

def create_venv():
    """创建虚拟环境"""
    venv_path = Path("venv")
    if venv_path.exists():
        print("⚠️  虚拟环境已存在，跳过创建")
        return True

    return run_command("python -m venv venv", "创建虚拟环境")

def get_activate_command():
    """获取激活虚拟环境的命令"""
    system = platform.system().lower()
    if system == "windows":
        return "venv\\Scripts\\activate"
    else:
        return "source venv/bin/activate"

def install_dependencies():
    """安装依赖"""
    # 检查是否在虚拟环境中
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  请先激活虚拟环境")
        print(f"   运行: {get_activate_command()}")
        return False

    # 升级pip
    run_command("python -m pip install --upgrade pip", "升级pip")

    # 安装开发依赖
    if not run_command("pip install -r requirements-dev.txt", "安装开发依赖"):
        return False

    # 安装项目本身（可编辑模式）
    if not run_command("pip install -e .", "安装项目（可编辑模式）"):
        return False

    return True

def setup_pre_commit():
    """设置pre-commit hooks"""
    return run_command("pre-commit install", "设置pre-commit hooks")

def run_tests():
    """运行测试"""
    return run_command("python -m pytest tests/test_basic.py -v", "运行基础测试")

def main():
    """主函数"""
    print("🚀 OSS Audit 开发环境设置")
    print("=" * 50)

    # 检查Python版本
    if not check_python_version():
        sys.exit(1)

    # 创建虚拟环境
    if not create_venv():
        sys.exit(1)

    print("\n📋 下一步操作:")
    print("1. 激活虚拟环境:")
    print(f"   {get_activate_command()}")
    print("\n2. 重新运行此脚本:")
    print("   python scripts/setup_dev_env.py")
    print("\n或者手动执行以下命令:")
    print("   pip install -r requirements-dev.txt")
    print("   pip install -e .")
    print("   pre-commit install")
    print("   python -m pytest tests/test_basic.py -v")

if __name__ == "__main__":
    main()
