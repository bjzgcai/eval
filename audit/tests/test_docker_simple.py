#!/usr/bin/env python3
"""
Docker工作流简化测试
轻量级Docker配置和工作流验证
"""

import unittest
import pathlib
import json
import subprocess
import tempfile
import shutil


class TestDockerConfiguration(unittest.TestCase):
    """Docker配置测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.project_root = pathlib.Path(__file__).parent.parent
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = pathlib.Path(self.temp_dir)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_dockerfile_exists_and_valid(self):
        """测试Dockerfile存在且有效"""
        dockerfile_path = self.project_root / "Dockerfile"
        self.assertTrue(dockerfile_path.exists(), "Dockerfile应该存在")
        
        content = dockerfile_path.read_text(encoding='utf-8')
        
        # 检查基本结构
        self.assertIn("FROM", content, "Dockerfile应该包含FROM指令")
        self.assertIn("WORKDIR", content, "Dockerfile应该包含WORKDIR指令")
        self.assertIn("python:", content, "Dockerfile应该基于Python镜像")
        
        # 检查多阶段构建
        self.assertTrue(content.count("FROM") >= 2, "应该使用多阶段构建")
        
        # 检查安全性
        self.assertIn("ossaudit", content, "应该创建非root用户")
        self.assertIn("USER ossaudit", content, "应该切换到非root用户")
    
    def test_docker_compose_exists_and_valid(self):
        """测试docker-compose.yml存在且有效"""
        compose_path = self.project_root / "docker-compose.yml"
        self.assertTrue(compose_path.exists(), "docker-compose.yml应该存在")
        
        content = compose_path.read_text(encoding='utf-8')
        
        # 检查基本结构
        self.assertIn("version:", content, "应该指定compose版本")
        self.assertIn("services:", content, "应该定义服务")
        self.assertIn("oss-audit-tools:", content, "应该包含主服务")
        self.assertIn("volumes:", content, "应该定义数据卷")
        
        # 检查高级服务
        self.assertIn("sonarqube:", content, "应该包含SonarQube服务")
        self.assertIn("dependency-track:", content, "应该包含Dependency-Track服务")
        self.assertIn("profiles:", content, "应该使用配置文件")
    
    def test_run_scripts_exist(self):
        """测试运行脚本存在"""
        bash_script = self.project_root / "scripts" / "run_audit.sh" 
        ps_script = self.project_root / "scripts" / "run_audit.ps1"
        
        self.assertTrue(bash_script.exists(), "Bash运行脚本应该存在")
        self.assertTrue(ps_script.exists(), "PowerShell运行脚本应该存在")
        
        # 检查bash脚本内容
        bash_content = bash_script.read_text(encoding='utf-8')
        self.assertIn("#!/bin/bash", bash_content, "Bash脚本应该有正确的shebang")
        self.assertIn("docker", bash_content, "应该包含Docker命令")
        self.assertIn("docker-compose", bash_content, "应该包含docker-compose命令")
    
    def test_docker_image_optimization(self):
        """测试Docker镜像优化配置"""
        dockerfile_path = self.project_root / "Dockerfile"
        content = dockerfile_path.read_text(encoding='utf-8')
        
        # 检查优化措施
        self.assertIn("--no-cache-dir", content, "应该使用--no-cache-dir优化")
        self.assertIn("rm -rf", content, "应该清理缓存")
        self.assertIn("slim", content, "应该使用slim基础镜像")
        
        # 检查多阶段构建优化
        self.assertIn("python-tools", content, "应该有专门的工具构建阶段")
        self.assertIn("node-tools", content, "应该有Node.js工具构建阶段")
        
        # 检查健康检查
        self.assertIn("HEALTHCHECK", content, "应该包含健康检查")
    
    def test_container_security_configuration(self):
        """测试容器安全配置"""
        dockerfile_path = self.project_root / "Dockerfile"
        content = dockerfile_path.read_text(encoding='utf-8')
        
        # 检查用户安全
        self.assertIn("groupadd", content, "应该创建用户组")
        self.assertIn("useradd", content, "应该创建用户")
        self.assertNotIn("USER root", content, "不应该使用root用户运行")
        
        # 检查文件权限
        self.assertIn("chown", content, "应该设置正确的文件权限")


class TestDockerToolsConfiguration(unittest.TestCase):
    """Docker工具配置测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.project_root = pathlib.Path(__file__).parent.parent
    
    def test_python_tools_in_dockerfile(self):
        """测试Dockerfile中的Python工具配置"""
        dockerfile_path = self.project_root / "Dockerfile"
        content = dockerfile_path.read_text(encoding='utf-8')
        
        essential_python_tools = [
            "pylint", "flake8", "bandit", "black", "pytest", "semgrep"
        ]
        
        for tool in essential_python_tools:
            self.assertIn(tool, content, f"应该包含{tool}工具")
    
    def test_nodejs_tools_in_dockerfile(self):
        """测试Dockerfile中的Node.js工具配置"""
        dockerfile_path = self.project_root / "Dockerfile"
        content = dockerfile_path.read_text(encoding='utf-8')
        
        essential_node_tools = ["eslint", "typescript"]
        
        for tool in essential_node_tools:
            self.assertIn(tool, content, f"应该包含{tool}工具")
    
    def test_docker_compose_service_configuration(self):
        """测试docker-compose服务配置"""
        compose_path = self.project_root / "docker-compose.yml"
        content = compose_path.read_text(encoding='utf-8')
        
        # 检查主服务配置
        self.assertIn("oss-audit-tools:", content, "应该定义主审计服务")
        self.assertIn("volumes:", content, "应该配置卷挂载")
        self.assertIn("/var/run/docker.sock", content, "应该挂载Docker socket")
        
        # 检查高级服务配置
        self.assertIn("sonarqube:", content, "应该定义SonarQube服务")
        self.assertIn("9000:9000", content, "SonarQube应该暴露9000端口")
        
        self.assertIn("dependency-track:", content, "应该定义Dependency-Track服务")
        self.assertIn("8081:8080", content, "Dependency-Track应该暴露8081端口")
    
    def test_docker_environment_variables(self):
        """测试Docker环境变量配置"""
        compose_path = self.project_root / "docker-compose.yml"
        content = compose_path.read_text(encoding='utf-8')
        
        # 检查环境变量
        self.assertIn("PYTHONIOENCODING", content, "应该设置Python编码")
        self.assertIn("environment:", content, "应该定义环境变量")


class TestDockerWorkflowIntegration(unittest.TestCase):
    """Docker工作流集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.project_root = pathlib.Path(__file__).parent.parent
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = pathlib.Path(self.temp_dir)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_docker_script_argument_parsing(self):
        """测试Docker脚本参数解析"""
        script_path = self.project_root / "scripts" / "run_audit.sh"
        content = script_path.read_text(encoding='utf-8')
        
        # 检查参数处理
        self.assertIn("--help", content, "应该支持帮助参数")
        self.assertIn("--build", content, "应该支持构建参数")
        self.assertIn("--advanced", content, "应该支持高级服务参数")
        
        # 检查参数解析逻辑
        self.assertIn("while [[ $# -gt 0 ]]", content, "应该有参数解析循环")
        self.assertIn("case $1 in", content, "应该使用case语句解析参数")
    
    def test_docker_script_error_handling(self):
        """测试Docker脚本错误处理"""
        script_path = self.project_root / "scripts" / "run_audit.sh"
        content = script_path.read_text(encoding='utf-8')
        
        # 检查错误处理
        self.assertIn("set -e", content, "应该启用严格错误处理")
        self.assertIn("check_docker", content, "应该检查Docker环境")
        self.assertIn("print_error", content, "应该有错误输出函数")
        
        # 检查退出处理
        self.assertIn("exit 1", content, "应该有错误退出")
    
    def test_docker_volume_mapping_configuration(self):
        """测试Docker卷映射配置"""
        compose_path = self.project_root / "docker-compose.yml"
        content = compose_path.read_text(encoding='utf-8')
        
        # 检查持久化存储
        volume_definitions = [
            "sonarqube_data:", "sonarqube_logs:", "sonarqube_extensions:",
            "dtrack_data:", "postgres_data:"
        ]
        
        for volume in volume_definitions:
            self.assertIn(volume, content, f"应该定义{volume}卷")
    
    def test_docker_network_configuration(self):
        """测试Docker网络配置"""
        compose_path = self.project_root / "docker-compose.yml"
        content = compose_path.read_text(encoding='utf-8')
        
        # 检查网络设置
        self.assertIn("networks:", content, "应该定义网络")
        self.assertIn("oss-audit-network", content, "应该创建专用网络")
    
    def test_docker_profiles_configuration(self):
        """测试Docker配置文件功能"""
        compose_path = self.project_root / "docker-compose.yml"
        content = compose_path.read_text(encoding='utf-8')
        
        # 检查配置文件
        self.assertIn("profiles:", content, "应该使用profiles功能")
        self.assertIn("advanced", content, "应该有advanced配置文件")
        
        # 检查服务分组
        advanced_services = ["sonarqube", "dependency-track", "dtrack-postgres"]
        for service in advanced_services:
            self.assertIn(f"{service}:", content, f"应该包含{service}服务")


class TestDockerBuildOptimization(unittest.TestCase):
    """Docker构建优化测试"""
    
    def test_dockerfile_build_optimization(self):
        """测试Dockerfile构建优化"""
        dockerfile_path = pathlib.Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile_path.read_text(encoding='utf-8')
        
        # 检查层优化
        self.assertIn("RUN", content, "应该合并RUN指令")
        self.assertIn("&&", content, "应该链接命令减少层数")
        
        # 检查缓存优化
        self.assertIn("--no-cache", content, "应该清理包管理器缓存")
        self.assertIn("clean", content, "应该清理临时文件")
        
        # 检查镜像大小优化
        self.assertIn("slim", content, "应该使用slim镜像")
        self.assertIn("alpine", content, "应该使用Alpine Linux")
    
    def test_multistage_build_structure(self):
        """测试多阶段构建结构"""
        dockerfile_path = pathlib.Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile_path.read_text(encoding='utf-8')
        
        # 检查构建阶段
        build_stages = ["python-tools", "node-tools"]
        for stage in build_stages:
            self.assertIn(f"AS {stage}", content, f"应该定义{stage}构建阶段")
        
        # 检查COPY指令优化
        self.assertIn("COPY --from=", content, "应该使用多阶段构建复制")


if __name__ == '__main__':
    unittest.main(verbosity=2)