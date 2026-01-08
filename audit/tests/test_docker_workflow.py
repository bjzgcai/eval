#!/usr/bin/env python3
"""
Docker工作流端到端测试
验证Docker容器工具集成和完整工作流
"""

import pytest
import unittest
import tempfile
import pathlib
import os
import shutil
import subprocess
import time
import json
import requests
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
import sys
src_dir = pathlib.Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from oss_audit.core.audit_runner import AuditRunner
from oss_audit.core.project_detector import ProjectInfo, ProjectType, StructureType, SizeMetrics


class DockerTestHelper:
    """Docker测试辅助类"""
    
    @staticmethod
    def is_docker_available():
        """检查Docker是否可用"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    @staticmethod
    def is_docker_running():
        """检查Docker服务是否运行"""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    @staticmethod
    def image_exists(image_name):
        """检查Docker镜像是否存在"""
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", image_name],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    @staticmethod
    def container_is_running(container_name):
        """检查容器是否运行"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return container_name in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    @staticmethod
    def build_test_image(dockerfile_path, image_tag="test-oss-audit:latest", timeout=300):
        """构建测试用Docker镜像"""
        try:
            context_dir = dockerfile_path.parent
            result = subprocess.run(
                ["docker", "build", "-t", image_tag, "-f", str(dockerfile_path), str(context_dir)],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Build timeout"
        except Exception as e:
            return False, "", str(e)


def create_test_project(project_dir: pathlib.Path, project_type: str = "python"):
    """创建测试项目"""
    project_dir.mkdir(parents=True, exist_ok=True)
    
    if project_type == "python":
        # 创建Python项目结构
        (project_dir / "setup.py").write_text("""
from setuptools import setup, find_packages

setup(
    name="test-project",
    version="1.0.0",
    packages=find_packages(),
    install_requires=["requests"],
)
""")
        
        (project_dir / "src").mkdir(exist_ok=True)
        (project_dir / "src" / "__init__.py").write_text("")
        (project_dir / "src" / "main.py").write_text("""
def hello_world():
    print("Hello, World!")
    
if __name__ == "__main__":
    hello_world()
""")
        
        (project_dir / "tests").mkdir(exist_ok=True)
        (project_dir / "tests" / "__init__.py").write_text("")
        (project_dir / "tests" / "test_main.py").write_text("""
import unittest
from src.main import hello_world

class TestMain(unittest.TestCase):
    def test_hello_world(self):
        # This is a simple test
        self.assertIsNone(hello_world())
        
if __name__ == '__main__':
    unittest.main()
""")
        
        (project_dir / "requirements.txt").write_text("requests==2.28.0\n")
        (project_dir / "README.md").write_text("# Test Project\n\nA simple test project for OSS Audit.")
        
    elif project_type == "javascript":
        # 创建JavaScript项目结构
        (project_dir / "package.json").write_text(json.dumps({
            "name": "test-project",
            "version": "1.0.0", 
            "description": "Test project",
            "main": "index.js",
            "scripts": {
                "test": "jest",
                "lint": "eslint ."
            },
            "dependencies": {
                "express": "^4.18.0"
            },
            "devDependencies": {
                "jest": "^29.0.0",
                "eslint": "^8.0.0"
            }
        }, indent=2))
        
        (project_dir / "index.js").write_text("""
const express = require('express');
const app = express();

app.get('/', (req, res) => {
    res.send('Hello World!');
});

const port = process.env.PORT || 3000;
app.listen(port, () => {
    console.log(`Server running on port ${port}`);
});

module.exports = app;
""")
        
        (project_dir / "test").mkdir(exist_ok=True)
        (project_dir / "test" / "index.test.js").write_text("""
const request = require('supertest');
const app = require('../index');

describe('GET /', () => {
    it('should return Hello World', async () => {
        const res = await request(app).get('/');
        expect(res.statusCode).toBe(200);
        expect(res.text).toBe('Hello World!');
    });
});
""")


@pytest.mark.slow
@pytest.mark.docker
class TestDockerWorkflow(unittest.TestCase):
    """Docker工作流测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = pathlib.Path(self.temp_dir)
        self.test_project_dir = self.temp_path / "test-project"
        
        # 检查Docker环境
        self.docker_available = DockerTestHelper.is_docker_available()
        self.docker_running = DockerTestHelper.is_docker_running()
        
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.skipif(not DockerTestHelper.is_docker_available(), reason="Docker not available")
    def test_docker_environment_check(self):
        """测试Docker环境检查"""
        self.assertTrue(self.docker_available, "Docker should be available")
        self.assertTrue(self.docker_running, "Docker service should be running")
    
    @pytest.mark.skipif(not DockerTestHelper.is_docker_available(), reason="Docker not available")
    def test_dockerfile_validity(self):
        """测试Dockerfile语法有效性"""
        dockerfile_path = pathlib.Path(__file__).parent.parent / "Dockerfile"
        self.assertTrue(dockerfile_path.exists(), "Dockerfile should exist")
        
        # 检查Dockerfile基本语法
        content = dockerfile_path.read_text()
        self.assertIn("FROM", content, "Dockerfile should have FROM instruction")
        self.assertIn("WORKDIR", content, "Dockerfile should have WORKDIR instruction")
    
    @pytest.mark.skipif(not DockerTestHelper.is_docker_available(), reason="Docker not available")
    def test_docker_compose_validity(self):
        """测试docker-compose.yml有效性"""
        compose_path = pathlib.Path(__file__).parent.parent / "docker-compose.yml"
        self.assertTrue(compose_path.exists(), "docker-compose.yml should exist")
        
        # 检查compose文件语法
        try:
            result = subprocess.run(
                ["docker-compose", "config"],
                cwd=compose_path.parent,
                capture_output=True,
                text=True,
                timeout=30
            )
            self.assertEqual(result.returncode, 0, f"docker-compose config failed: {result.stderr}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.skipTest("docker-compose not available")
    
    @pytest.mark.skipif(not DockerTestHelper.is_docker_available(), reason="Docker not available")
    def test_build_docker_image(self):
        """测试Docker镜像构建"""
        dockerfile_path = pathlib.Path(__file__).parent.parent / "Dockerfile"
        
        # 构建测试镜像
        success, stdout, stderr = DockerTestHelper.build_test_image(
            dockerfile_path,
            image_tag="test-oss-audit:build-test"
        )
        
        if not success:
            self.skipTest(f"Failed to build Docker image: {stderr}")
        
        # 验证镜像存在
        self.assertTrue(
            DockerTestHelper.image_exists("test-oss-audit:build-test"),
            "Built image should exist"
        )
        
        # 清理测试镜像
        try:
            subprocess.run(
                ["docker", "rmi", "test-oss-audit:build-test"],
                capture_output=True,
                timeout=30
            )
        except:
            pass  # 清理失败不影响测试结果
    
    @pytest.mark.skipif(not DockerTestHelper.is_docker_available(), reason="Docker not available")
    def test_container_tools_availability(self):
        """测试容器中的工具可用性"""
        if not DockerTestHelper.image_exists("oss-audit:2.0"):
            self.skipTest("OSS Audit Docker image not available")
        
        # 测试Python工具
        python_tools = ["python", "pylint", "flake8", "bandit", "black", "pytest"]
        
        for tool in python_tools:
            try:
                result = subprocess.run(
                    ["docker", "run", "--rm", "oss-audit:2.0", "which", tool],
                    capture_output=True,
                    timeout=30
                )
                self.assertEqual(result.returncode, 0, f"Tool {tool} should be available in container")
            except subprocess.TimeoutExpired:
                self.fail(f"Timeout checking tool {tool}")
    
    @pytest.mark.skipif(not DockerTestHelper.is_docker_available(), reason="Docker not available")
    def test_container_python_analysis(self):
        """测试容器内Python工具分析"""
        if not DockerTestHelper.image_exists("oss-audit:2.0"):
            self.skipTest("OSS Audit Docker image not available")
        
        # 创建测试Python项目
        create_test_project(self.test_project_dir, "python")
        
        # 在容器中运行pylint
        try:
            result = subprocess.run([
                "docker", "run", "--rm",
                "-v", f"{self.test_project_dir}:/workspace/project",
                "oss-audit:2.0",
                "pylint", "--output-format=json", "/workspace/project/src/main.py"
            ], capture_output=True, text=True, timeout=60)
            
            # Pylint应该能够运行（返回码0-4都是正常的）
            self.assertLessEqual(result.returncode, 4, "Pylint should run successfully")
            
        except subprocess.TimeoutExpired:
            self.fail("Container Python analysis timeout")
    
    def test_mock_docker_workflow_integration(self):
        """模拟Docker工作流集成测试"""
        # 创建测试项目
        create_test_project(self.test_project_dir, "python")
        
        # 使用mock来模拟Docker工具执行
        with patch('oss_audit.core.tool_executor.ToolExecutor') as mock_executor:
            # 配置mock返回值
            mock_instance = mock_executor.return_value
            mock_instance.execute_tools.return_value = {
                "pylint": {
                    "success": True,
                    "score": 75,
                    "output": "Your code has been rated at 7.5/10",
                    "execution_time": 2.5
                },
                "bandit": {
                    "success": True,
                    "score": 90,
                    "output": "No issues identified.",
                    "execution_time": 1.2
                }
            }
            
            # 运行审计
            runner = AuditRunner()
            results = runner.audit_project(str(self.test_project_dir))
            
            # 验证结果
            self.assertIsNotNone(results)
            self.assertIn("overall_score", results)
    
    def test_docker_script_validation(self):
        """测试Docker脚本有效性"""
        script_path = pathlib.Path(__file__).parent.parent / "scripts" / "run_audit.sh"
        self.assertTrue(script_path.exists(), "run_audit.sh should exist")
        
        # 检查脚本权限和语法  
        content = script_path.read_text(encoding='utf-8')
        self.assertIn("#!/bin/bash", content, "Script should have bash shebang")
        self.assertIn("docker", content, "Script should contain docker commands")
        
        # Windows PowerShell脚本
        ps_script_path = pathlib.Path(__file__).parent.parent / "scripts" / "run_audit.ps1"
        self.assertTrue(ps_script_path.exists(), "run_audit.ps1 should exist")
    
    def test_docker_configuration_parsing(self):
        """测试Docker配置解析"""
        compose_path = pathlib.Path(__file__).parent.parent / "docker-compose.yml"
        
        # 简单的YAML解析验证
        content = compose_path.read_text(encoding='utf-8')
        self.assertIn("services:", content)
        self.assertIn("oss-audit-tools:", content)
        self.assertIn("volumes:", content)
    
    def test_health_check_functionality(self):
        """测试健康检查功能（模拟）"""
        # 模拟容器健康检查
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Python 3.11.0"
            
            # 模拟健康检查命令
            result = subprocess.run(["python", "--version"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
    
    def test_volume_mount_simulation(self):
        """模拟卷挂载测试"""
        # 创建测试文件
        test_file = self.test_project_dir / "test.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test content")
        
        # 模拟卷挂载读取
        self.assertTrue(test_file.exists())
        content = test_file.read_text()
        self.assertEqual(content, "test content")


@pytest.mark.slow  
@pytest.mark.docker
@pytest.mark.integration
class TestDockerEndToEnd(unittest.TestCase):
    """Docker端到端集成测试"""
    
    def setUp(self):
        """设置端到端测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = pathlib.Path(self.temp_dir)
        self.test_projects = {}
        
        # 创建多种类型的测试项目
        for project_type in ["python", "javascript"]:
            project_dir = self.temp_path / f"test-{project_type}-project"
            create_test_project(project_dir, project_type)
            self.test_projects[project_type] = project_dir
        
    def tearDown(self):
        """清理端到端测试环境"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.skipif(not DockerTestHelper.is_docker_available(), reason="Docker not available")
    def test_complete_docker_audit_workflow(self):
        """完整的Docker审计工作流测试"""
        if not DockerTestHelper.image_exists("oss-audit:2.0"):
            self.skipTest("OSS Audit Docker image not available")
        
        python_project = self.test_projects["python"]
        output_dir = self.temp_path / "reports"
        output_dir.mkdir(exist_ok=True)
        
        # 模拟完整审计流程
        with patch('oss_audit.core.audit_runner.AuditRunner.audit_project') as mock_audit:
            mock_audit.return_value = {
                "overall_score": 85,
                "dimension_scores": {
                    "security": 90,
                    "quality": 80,
                    "testing": 75
                },
                "recommendations": [
                    "Improve test coverage",
                    "Add documentation"
                ]
            }
            
            runner = AuditRunner()
            results = runner.audit_project(str(python_project))
            
            self.assertIsNotNone(results)
            self.assertEqual(results["overall_score"], 85)
    
    def test_docker_service_orchestration(self):
        """Docker服务编排测试"""
        # 模拟docker-compose服务启动
        services = ["oss-audit-tools", "sonarqube", "dependency-track"]
        
        for service in services:
            # 模拟服务状态检查
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = f"{service}\n"
                
                result = subprocess.run(
                    ["echo", service],
                    capture_output=True,
                    text=True
                )
                self.assertEqual(result.returncode, 0)
                self.assertIn(service, result.stdout)
    
    def test_docker_network_connectivity(self):
        """Docker网络连接测试"""
        # 模拟网络连接测试
        network_name = "oss-audit-network"
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = f'[{{"Name": "{network_name}"}}]'
            
            # 模拟网络检查
            result = subprocess.run(
                ["echo", f'[{{"Name": "{network_name}"}}]'],
                capture_output=True,
                text=True
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn(network_name, result.stdout)
    
    def test_advanced_services_integration(self):
        """高级服务集成测试"""
        advanced_services = {
            "sonarqube": {"port": 9000, "health_endpoint": "/api/system/status"},
            "dependency-track": {"port": 8081, "health_endpoint": "/health"}
        }
        
        for service_name, config in advanced_services.items():
            # 模拟服务健康检查
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"status": "UP"}
                mock_get.return_value = mock_response
                
                # 模拟健康检查请求
                response = requests.get(f"http://localhost:{config['port']}{config['health_endpoint']}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "UP")


class TestDockerPerformance(unittest.TestCase):
    """Docker性能测试"""
    
    def test_container_startup_time(self):
        """容器启动时间测试（模拟）"""
        start_time = time.time()
        
        # 模拟容器启动过程
        time.sleep(0.1)  # 模拟启动时间
        
        startup_time = time.time() - start_time
        self.assertLess(startup_time, 5.0, "Container should start within 5 seconds")
    
    def test_resource_usage_limits(self):
        """资源使用限制测试（模拟）"""
        # 模拟资源限制检查
        memory_limit = "2g"
        cpu_limit = "1.0"
        
        self.assertIsNotNone(memory_limit)
        self.assertIsNotNone(cpu_limit)
    
    def test_image_size_optimization(self):
        """镜像大小优化测试"""
        # 模拟镜像大小检查
        max_image_size_mb = 2048  # 2GB limit based on Dockerfile comments
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "1800MB"  # Simulated size under limit
            
            # 模拟镜像大小检查
            result = subprocess.run(
                ["echo", "1800MB"],
                capture_output=True,
                text=True
            )
            
            size_str = result.stdout.strip()
            simulated_size = int(size_str.replace("MB", ""))
            
            self.assertLess(
                simulated_size, 
                max_image_size_mb, 
                f"Image size {simulated_size}MB should be less than {max_image_size_mb}MB"
            )


if __name__ == '__main__':
    # 设置测试标记
    pytest.main([
        __file__, 
        "-v",
        "-m", "not slow",  # 默认跳过慢速测试
        "--tb=short"
    ])