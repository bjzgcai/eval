#!/usr/bin/env python3
"""
依赖安装脚本
智能安装所需的依赖，支持生产环境和开发环境
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"   ✅ {description}: 成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ {description}: 失败")
        if e.stderr.strip():
            print(f"   错误: {e.stderr.strip()}")
        return False

def check_venv():
    """检查是否在虚拟环境中"""
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  建议在虚拟环境中安装依赖")
        print("   激活虚拟环境: venv\\Scripts\\activate (Windows) 或 source venv/bin/activate (Linux/Mac)")
        response = input("是否继续安装? (y/N): ").strip().lower()
        if response != 'y':
            return False
    return True

def upgrade_pip():
    """升级pip"""
    return run_command("python -m pip install --upgrade pip", "升级pip")

def install_production_deps():
    """安装生产依赖"""
    return run_command("pip install -r requirements.txt", "安装生产依赖")

def install_dev_deps():
    """安装开发依赖"""
    return run_command("pip install -r requirements-dev.txt", "安装开发依赖")

def install_editable():
    """以可编辑模式安装项目"""
    return run_command("pip install -e .", "安装项目（可编辑模式）")

def install_with_extras():
    """安装项目及其开发依赖"""
    return run_command("pip install -e .[dev]", "安装项目及开发依赖")

def setup_pre_commit():
    """设置pre-commit hooks"""
    return run_command("pre-commit install", "设置pre-commit hooks")

def verify_installation():
    """验证安装"""
    print("🔍 验证安装...")

    # 检查核心依赖
    core_deps = [
        "flask", "pytest", "coverage", "pylint", "jinja2",
        "mkdocs", "google.generativeai", "yaml", "openai"
    ]

    for dep in core_deps:
        try:
            if dep == "yaml":
                import yaml
            elif dep == "google.generativeai":
                import google.generativeai
            else:
                __import__(dep)
            print(f"   ✅ {dep}")
        except ImportError:
            print(f"   ❌ {dep} - 未安装")
            return False

    return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="OSS Audit 依赖安装脚本")
    parser.add_argument(
        "--env",
        choices=["prod", "dev", "full"],
        default="dev",
        help="安装环境: prod(生产), dev(开发), full(完整开发环境)"
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="跳过安装验证"
    )
    parser.add_argument(
        "--no-pre-commit",
        action="store_true",
        help="跳过pre-commit设置"
    )

    args = parser.parse_args()

    print("🚀 OSS Audit 依赖安装")
    print("=" * 40)

    # 检查虚拟环境
    if not check_venv():
        sys.exit(1)

    # 升级pip
    if not upgrade_pip():
        print("❌ pip升级失败")
        sys.exit(1)

    # 根据环境安装依赖
    if args.env == "prod":
        print("\n📦 安装生产依赖...")
        if not install_production_deps():
            print("❌ 生产依赖安装失败")
            sys.exit(1)
        if not install_editable():
            print("❌ 项目安装失败")
            sys.exit(1)

    elif args.env == "dev":
        print("\n📦 安装开发依赖...")
        if not install_dev_deps():
            print("❌ 开发依赖安装失败")
            sys.exit(1)
        if not install_editable():
            print("❌ 项目安装失败")
            sys.exit(1)

    elif args.env == "full":
        print("\n📦 安装完整开发环境...")
        if not install_with_extras():
            print("❌ 完整依赖安装失败")
            sys.exit(1)

    # 设置pre-commit
    if not args.no_pre_commit and args.env in ["dev", "full"]:
        print("\n🔧 设置pre-commit hooks...")
        setup_pre_commit()

    # 验证安装
    if not args.no_verify:
        print("\n🔍 验证安装...")
        if not verify_installation():
            print("❌ 安装验证失败")
            sys.exit(1)
        print("✅ 安装验证通过")

    print("\n🎉 依赖安装完成!")
    print("\n📋 下一步:")
    print("1. 运行测试: python scripts/run_tests.py")
    print("2. 运行审计: python oss_audit.py .")
    print("3. 查看帮助: python oss_audit.py --help")

if __name__ == "__main__":
    main()
