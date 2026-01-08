"""
测试容器管理器功能
"""

import pytest
import subprocess
from unittest.mock import Mock, patch, MagicMock
import json

from oss_audit.core.container_manager import (
    ContainerManager,
    ContainerEngine, 
    ContainerStatus,
    ContainerInfo,
    ContainerError,
    get_container_manager
)


class TestContainerManager:
    """测试容器管理器"""
    
    @pytest.fixture
    def manager(self):
        """创建容器管理器实例"""
        with patch.object(ContainerManager, '_initialize'):
            manager = ContainerManager()
            return manager
    
    def test_container_manager_initialization(self, manager):
        """测试容器管理器初始化"""
        assert manager.available_engines == []
        assert manager.primary_engine is None
        assert manager.fallback_engines == []
        assert "tools" in manager.default_images
        assert "memory" in manager.resource_limits
    
    @patch('shutil.which')
    @patch('subprocess.run')
    def test_check_engine_availability_docker_available(self, mock_run, mock_which, manager):
        """测试Docker引擎可用性检查"""
        # Mock Docker可用
        mock_which.return_value = "/usr/bin/docker"
        mock_run.return_value.returncode = 0
        
        result = manager._check_engine_availability(ContainerEngine.DOCKER)
        
        assert result is True
        mock_which.assert_called_with("docker")
        mock_run.assert_called_once()
    
    @patch('shutil.which')
    def test_check_engine_availability_not_found(self, mock_which, manager):
        """测试引擎未找到的情况"""
        mock_which.return_value = None
        
        result = manager._check_engine_availability(ContainerEngine.DOCKER)
        
        assert result is False
        mock_which.assert_called_with("docker")
    
    @patch('shutil.which')
    @patch('subprocess.run')
    def test_check_engine_availability_timeout(self, mock_run, mock_which, manager):
        """测试引擎检查超时"""
        mock_which.return_value = "/usr/bin/docker"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["docker", "version"], timeout=10)
        
        result = manager._check_engine_availability(ContainerEngine.DOCKER)
        
        assert result is False
    
    @patch.object(ContainerManager, '_check_engine_availability')
    def test_discover_engines(self, mock_check, manager):
        """测试引擎发现"""
        # Mock Docker和Podman可用
        mock_check.side_effect = lambda engine: engine in [ContainerEngine.DOCKER, ContainerEngine.PODMAN]
        
        manager._discover_engines()
        
        assert len(manager.available_engines) == 2
        assert ContainerEngine.DOCKER in manager.available_engines
        assert ContainerEngine.PODMAN in manager.available_engines
        assert ContainerEngine.NERDCTL not in manager.available_engines
    
    def test_is_available_true(self, manager):
        """测试容器引擎可用"""
        manager.available_engines = [ContainerEngine.DOCKER]
        
        assert manager.is_available() is True
    
    def test_is_available_false(self, manager):
        """测试容器引擎不可用"""
        manager.available_engines = []
        
        assert manager.is_available() is False
    
    @patch('subprocess.run')
    def test_get_engine_status_running(self, mock_run, manager):
        """测试获取运行中的引擎状态"""
        manager.primary_engine = ContainerEngine.DOCKER
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Docker version info..."
        
        status = manager.get_engine_status()
        
        assert status["available"] is True
        assert status["engine"] == "docker"
        assert status["running"] is True
        assert "Docker version info..." in status["info"]
    
    @patch('subprocess.run')
    def test_get_engine_status_not_running(self, mock_run, manager):
        """测试获取未运行的引擎状态"""
        manager.primary_engine = ContainerEngine.DOCKER
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Cannot connect to Docker daemon"
        
        status = manager.get_engine_status()
        
        assert status["available"] is True
        assert status["engine"] == "docker"
        assert status["running"] is False
        assert "Cannot connect to Docker daemon" in status["error"]
    
    def test_get_engine_status_no_engine(self, manager):
        """测试没有可用引擎时的状态"""
        manager.primary_engine = None
        
        status = manager.get_engine_status()
        
        assert status["available"] is False
        assert "No container engine available" in status["error"]
    
    @patch('subprocess.run')
    def test_ensure_image_exists(self, mock_run, manager):
        """测试镜像已存在的情况"""
        manager.primary_engine = ContainerEngine.DOCKER
        mock_run.return_value.returncode = 0
        
        result = manager.ensure_image("python:3.11")
        
        assert result is True
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_ensure_image_pull_success(self, mock_run, manager):
        """测试镜像拉取成功"""
        manager.primary_engine = ContainerEngine.DOCKER
        
        # 第一次调用（inspect）返回错误，第二次调用（pull）成功
        mock_run.side_effect = [
            Mock(returncode=1),  # image inspect 失败
            Mock(returncode=0)   # pull 成功
        ]
        
        result = manager.ensure_image("python:3.11")
        
        assert result is True
        assert mock_run.call_count == 2
    
    @patch('subprocess.run')
    def test_ensure_image_pull_failed(self, mock_run, manager):
        """测试镜像拉取失败"""
        manager.primary_engine = ContainerEngine.DOCKER
        
        # inspect失败，pull也失败
        mock_run.side_effect = [
            Mock(returncode=1),  # image inspect 失败
            Mock(returncode=1, stderr="Network error")   # pull 失败
        ]
        
        result = manager.ensure_image("python:3.11")
        
        assert result is False
        assert mock_run.call_count == 2
    
    @patch('subprocess.run')
    def test_run_container_success(self, mock_run, manager):
        """测试容器运行成功"""
        manager.primary_engine = ContainerEngine.DOCKER
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Container output",
            stderr=""
        )
        
        success, stdout, stderr = manager.run_container(
            image="python:3.11",
            command=["python", "-c", "print('hello')"],
            volumes={"/host/path": "/container/path"},
            environment={"TEST": "value"},
            working_dir="/workspace"
        )
        
        assert success is True
        assert stdout == "Container output"
        assert stderr == ""
        
        # 验证命令构建
        call_args = mock_run.call_args[0][0]
        assert "docker" in call_args
        assert "run" in call_args
        assert "--rm" in call_args
        assert "-v" in call_args
        assert "-e" in call_args
        assert "-w" in call_args
    
    @patch('subprocess.run')
    def test_run_container_timeout(self, mock_run, manager):
        """测试容器运行超时"""
        manager.primary_engine = ContainerEngine.DOCKER
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["docker", "run"], timeout=60
        )
        
        success, stdout, stderr = manager.run_container(
            image="python:3.11",
            command=["sleep", "120"],
            timeout=60
        )
        
        assert success is False
        assert stdout == ""
        assert "timeout" in stderr.lower()
    
    @patch('subprocess.run')
    def test_get_container_info_running(self, mock_run, manager):
        """测试获取运行中的容器信息"""
        manager.primary_engine = ContainerEngine.DOCKER
        
        mock_container_data = [{
            "Id": "abc123def456",
            "State": {"Running": True, "Status": "running"},
            "Config": {"Image": "python:3.11"},
            "Created": "2023-01-01T12:00:00Z"
        }]
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mock_container_data)
        )
        
        info = manager.get_container_info("test_container")
        
        assert info is not None
        assert info.name == "test_container"
        assert info.status == ContainerStatus.RUNNING
        assert info.image == "python:3.11"
        assert info.id == "abc123def456"
    
    @patch('subprocess.run')
    def test_get_container_info_not_found(self, mock_run, manager):
        """测试获取不存在的容器信息"""
        manager.primary_engine = ContainerEngine.DOCKER
        mock_run.return_value = Mock(returncode=1)
        
        info = manager.get_container_info("nonexistent_container")
        
        assert info is not None
        assert info.name == "nonexistent_container"
        assert info.status == ContainerStatus.NOT_FOUND
    
    @patch('subprocess.run')
    def test_cleanup_containers(self, mock_run, manager):
        """测试容器清理"""
        manager.primary_engine = ContainerEngine.DOCKER
        
        # Mock ps 命令返回容器列表
        mock_run.side_effect = [
            Mock(returncode=0, stdout="container1\ncontainer2\n"),
            Mock(returncode=0),  # rm container1
            Mock(returncode=0)   # rm container2
        ]
        
        cleaned = manager.cleanup_containers("test*")
        
        assert cleaned == 2
        assert mock_run.call_count == 3
    
    def test_diagnose_issues_no_engines(self, manager):
        """测试诊断无可用引擎的问题"""
        manager.available_engines = []
        manager.primary_engine = None
        
        diagnosis = manager.diagnose_issues()
        
        assert diagnosis["engines_available"] == 0
        assert diagnosis["primary_engine"] is None
        assert len(diagnosis["issues"]) > 0
        assert "没有可用的容器引擎" in diagnosis["issues"]
        assert len(diagnosis["recommendations"]) > 0
    
    @patch.object(ContainerManager, 'get_engine_status')
    def test_diagnose_issues_engine_not_running(self, mock_status, manager):
        """测试诊断引擎未运行的问题"""
        manager.available_engines = [ContainerEngine.DOCKER]
        manager.primary_engine = ContainerEngine.DOCKER
        
        mock_status.return_value = {"running": False}
        
        diagnosis = manager.diagnose_issues()
        
        assert diagnosis["engines_available"] == 1
        assert len(diagnosis["issues"]) > 0
        assert any("未运行" in issue for issue in diagnosis["issues"])
    
    def test_create_error_report_timeout(self, manager):
        """测试创建超时错误报告"""
        error = subprocess.TimeoutExpired(cmd=["docker", "run"], timeout=60)
        command = ["docker", "run", "python:3.11"]
        context = {"operation": "test"}
        
        error_report = manager.create_error_report(error, command, context)
        
        assert error_report.error_type == "TimeoutExpired"
        assert error_report.command == command
        assert len(error_report.suggestions) > 0
        assert "增加超时时间" in error_report.suggestions
    
    def test_create_error_report_called_process_error(self, manager):
        """测试创建进程调用错误报告"""
        error = subprocess.CalledProcessError(1, ["docker", "run"])
        command = ["docker", "run", "python:3.11"]
        context = {"operation": "test"}
        
        error_report = manager.create_error_report(error, command, context)
        
        assert error_report.error_type == "CalledProcessError"
        assert error_report.command == command
        assert len(error_report.suggestions) > 0
        assert any("检查容器镜像" in suggestion for suggestion in error_report.suggestions)
    
    def test_attempt_recovery_timeout(self, manager):
        """测试从超时错误恢复"""
        error = ContainerError(
            error_type="TimeoutExpired",
            message="Command timeout",
            command=["docker", "run"]
        )
        
        original_timeout = manager.resource_limits['timeout']
        result = manager.attempt_recovery(error)
        
        assert result is True
        assert manager.resource_limits['timeout'] > original_timeout
    
    def test_attempt_recovery_with_fallback_engine(self, manager):
        """测试使用备用引擎恢复"""
        manager.primary_engine = ContainerEngine.DOCKER
        manager.fallback_engines = [ContainerEngine.PODMAN]
        
        error = ContainerError(
            error_type="CalledProcessError",
            message="Command failed",
            command=["docker", "run"]
        )
        
        result = manager.attempt_recovery(error)
        
        assert result is True
        assert manager.primary_engine == ContainerEngine.PODMAN
        assert ContainerEngine.DOCKER in manager.fallback_engines
    
    def test_global_container_manager(self):
        """测试全局容器管理器"""
        manager1 = get_container_manager()
        manager2 = get_container_manager()
        
        # 应该返回同一个实例
        assert manager1 is manager2


class TestContainerDataClasses:
    """测试容器数据类"""
    
    def test_container_info_creation(self):
        """测试容器信息创建"""
        info = ContainerInfo(
            name="test_container",
            image="python:3.11",
            status=ContainerStatus.RUNNING,
            engine=ContainerEngine.DOCKER,
            id="abc123"
        )
        
        assert info.name == "test_container"
        assert info.image == "python:3.11"
        assert info.status == ContainerStatus.RUNNING
        assert info.engine == ContainerEngine.DOCKER
        assert info.id == "abc123"
    
    def test_container_error_creation(self):
        """测试容器错误创建"""
        error = ContainerError(
            error_type="TestError",
            message="Test error message",
            command=["docker", "run"],
            suggestions=["suggestion1", "suggestion2"]
        )
        
        assert error.error_type == "TestError"
        assert error.message == "Test error message"
        assert error.command == ["docker", "run"]
        assert len(error.suggestions) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])