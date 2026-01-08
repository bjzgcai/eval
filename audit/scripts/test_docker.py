#!/usr/bin/env python3
"""
Docker 环境测试脚本
验证Docker镜像中的工具是否正常工作
"""

import subprocess
import sys
import tempfile
import os
from pathlib import Path

def run_command(cmd, timeout=30):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            shell=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def test_docker_available():
    """测试Docker是否可用"""
    print("🔍 检查Docker环境...")
    
    success, stdout, stderr = run_command("docker --version")
    if not success:
        print("❌ Docker未安装或不可用")
        return False
        
    print(f"✅ Docker可用: {stdout.strip()}")
    
    success, stdout, stderr = run_command("docker info")
    if not success:
        print("❌ Docker服务未运行")
        return False
        
    print("✅ Docker服务正常")
    return True

def test_image_build():
    """测试镜像构建"""
    print("🏗️ 构建Docker镜像...")
    
    success, stdout, stderr = run_command(
        "docker build -t oss-audit:test .", 
        timeout=600  # 10分钟超时
    )
    
    if not success:
        print("❌ 镜像构建失败")
        print(f"错误: {stderr}")
        return False
        
    print("✅ 镜像构建成功")
    return True

def test_tools_in_container():
    """测试容器中的工具"""
    print("🔧 测试容器中的工具...")
    
    tools_to_test = [
        # Python工具
        ("python", "python --version"),
        ("pip", "pip --version"),
        ("pylint", "python -m pylint --version"),
        ("flake8", "python -m flake8 --version"),
        ("mypy", "python -m mypy --version"),
        ("bandit", "python -m bandit --version"),
        ("black", "python -m black --version"),
        ("pytest", "python -m pytest --version"),
        
        # Node.js工具
        ("node", "node --version"),
        ("npm", "npm --version"),
        ("eslint", "npx eslint --version"),
        ("prettier", "npx prettier --version"),
        ("typescript", "npx tsc --version"),
        
        # Java工具
        ("java", "java -version"),
        ("maven", "mvn --version"),
        
        # Go工具
        ("go", "go version"),
        
        # Rust工具
        ("rustc", "rustc --version"),
        ("cargo", "cargo --version"),
        
        # C++工具
        ("gcc", "gcc --version"),
        ("clang", "clang --version"),
        ("cppcheck", "cppcheck --version"),
    ]
    
    passed = 0
    failed = 0
    
    for tool_name, cmd in tools_to_test:
        success, stdout, stderr = run_command(
            f"docker run --rm oss-audit:test {cmd}",
            timeout=60
        )
        
        if success:
            print(f"  ✅ {tool_name}: 可用")
            passed += 1
        else:
            print(f"  ❌ {tool_name}: 不可用 - {stderr.strip()[:100]}")
            failed += 1
    
    print(f"\n📊 工具测试结果: {passed} 成功, {failed} 失败")
    return failed == 0

def create_test_project():
    """创建测试项目"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建一个简单的Python项目
        project_dir = Path(temp_dir) / "test_project"
        project_dir.mkdir()
        
        # 创建一个简单的Python文件
        (project_dir / "main.py").write_text('''#!/usr/bin/env python3
"""简单的测试程序"""

def hello_world():
    """打印Hello World"""
    print("Hello, World!")

def add_numbers(a, b):
    """加法函数"""
    return a + b

if __name__ == "__main__":
    hello_world()
    result = add_numbers(2, 3)
    print(f"2 + 3 = {result}")
''')
        
        # 创建requirements.txt
        (project_dir / "requirements.txt").write_text('requests==2.31.0\n')
        
        # 创建README.md
        (project_dir / "README.md").write_text('''# Test Project

This is a test project for OSS Audit.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```
''')
        
        return str(project_dir)

def test_audit_functionality():
    """测试审计功能"""
    print("🔍 测试审计功能...")
    
    # 创建测试项目
    test_project = create_test_project()
    reports_dir = os.path.join(os.path.dirname(test_project), "reports")
    
    print(f"测试项目路径: {test_project}")
    print(f"报告输出路径: {reports_dir}")
    
    # 运行审计
    cmd = f'docker run --rm -v "{test_project}:/workspace:ro" -v "{reports_dir}:/app/reports" oss-audit:test /workspace'
    
    success, stdout, stderr = run_command(cmd, timeout=300)  # 5分钟超时
    
    if not success:
        print("❌ 审计功能测试失败")
        print(f"错误输出: {stderr}")
        return False
    
    print("✅ 审计功能测试成功")
    print(f"输出: {stdout[:500]}...")  # 显示前500个字符
    
    # 检查是否生成了报告
    if os.path.exists(reports_dir):
        report_files = os.listdir(reports_dir)
        print(f"生成的报告: {report_files}")
        
    return True

def cleanup():
    """清理测试镜像"""
    print("🧹 清理测试镜像...")
    run_command("docker rmi oss-audit:test 2>/dev/null || true")

def main():
    """主测试函数"""
    print("🐳 OSS Audit 2.0 Docker 测试")
    print("=" * 50)
    
    tests = [
        ("Docker环境检查", test_docker_available),
        ("镜像构建测试", test_image_build),
        ("容器工具测试", test_tools_in_container),
        ("审计功能测试", test_audit_functionality),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 通过")
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    # 清理
    cleanup()
    
    if passed == total:
        print("🎉 所有测试通过！Docker环境已就绪")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查Docker环境配置")
        return 1

if __name__ == "__main__":
    sys.exit(main())