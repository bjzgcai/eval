#!/usr/bin/env python3
"""
测试运行脚本
在虚拟环境中运行测试，不依赖全局安装
"""

import sys
import subprocess
import os
from pathlib import Path

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"🧪 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"   ✅ {description}: 成功")
        if result.stdout.strip():
            print(f"   输出: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ {description}: 失败")
        if e.stdout.strip():
            print(f"   输出: {e.stdout.strip()}")
        if e.stderr.strip():
            print(f"   错误: {e.stderr.strip()}")
        return False

def check_venv():
    """检查是否在虚拟环境中"""
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  建议在虚拟环境中运行测试")
        print("   激活虚拟环境: venv\\Scripts\\activate (Windows) 或 source venv/bin/activate (Linux/Mac)")
        return False
    return True

def install_test_deps():
    """安装测试依赖"""
    print("📦 检查测试依赖...")

    # 检查pytest是否已安装
    try:
        import pytest
        print("   ✅ pytest已安装")
    except ImportError:
        print("   ❌ pytest未安装，正在安装...")
        if not run_command("pip install pytest pytest-cov pytest-mock", "安装pytest"):
            return False

    # 检查其他测试依赖
    test_deps = ["coverage", "pytest-cov", "pytest-mock"]
    for dep in test_deps:
        try:
            __import__(dep.replace("-", "_"))
            print(f"   ✅ {dep}已安装")
        except ImportError:
            print(f"   ❌ {dep}未安装，正在安装...")
            if not run_command(f"pip install {dep}", f"安装{dep}"):
                return False

    return True

def run_basic_tests():
    """运行基础测试"""
    return run_command("python -m pytest tests/test_basic.py -v", "运行基础测试")

def run_all_tests():
    """运行所有测试"""
    return run_command("python -m pytest tests/ -v", "运行所有测试")

def run_tests_with_coverage():
    """运行测试并生成覆盖率报告"""
    return run_command(
        "python -m pytest tests/ -v --cov=src/oss_audit --cov-report=term-missing --cov-report=html",
        "运行测试并生成覆盖率报告"
    )

def main():
    """主函数"""
    print("🧪 OSS Audit 测试运行器")
    print("=" * 40)

    # 检查虚拟环境
    check_venv()

    # 安装测试依赖
    if not install_test_deps():
        print("❌ 依赖安装失败")
        sys.exit(1)

    # 运行测试
    print("\n🚀 开始运行测试...")

    # 运行基础测试
    if not run_basic_tests():
        print("❌ 基础测试失败")
        sys.exit(1)

    # 询问是否运行所有测试
    print("\n📋 测试选项:")
    print("1. 运行基础测试 (已完成)")
    print("2. 运行所有测试")
    print("3. 运行测试并生成覆盖率报告")
    print("4. 退出")

    while True:
        choice = input("\n请选择 (1-4): ").strip()

        if choice == "1":
            print("✅ 基础测试已完成")
            break
        elif choice == "2":
            if run_all_tests():
                print("✅ 所有测试完成")
            else:
                print("❌ 部分测试失败")
            break
        elif choice == "3":
            if run_tests_with_coverage():
                print("✅ 测试和覆盖率报告完成")
                print("📊 覆盖率报告已生成到 htmlcov/ 目录")
            else:
                print("❌ 测试失败")
            break
        elif choice == "4":
            print("👋 退出测试")
            break
        else:
            print("❌ 无效选择，请输入 1-4")

if __name__ == "__main__":
    main()
