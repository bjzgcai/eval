"""
容器工具支持集成测试
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from oss_audit.core.tool_executor import ToolExecutor
from oss_audit.core.tool_registry import Tool
from oss_audit.core.container_manager import ContainerManager, ContainerEngine


class TestContainerIntegration:
    """容器工具支持集成测试"""
    
    @pytest.fixture
    def mock_container_manager(self):
        """模拟容器管理器"""
        with patch('oss_audit.core.tool_executor.get_container_manager') as mock_get_cm:
            mock_cm = Mock(spec=ContainerManager)
            mock_cm.is_available.return_value = True
            mock_cm.primary_engine = ContainerEngine.DOCKER
            mock_cm.default_images = {"tools": "oss-audit:tools-2.0"}
            mock_cm.get_engine_status.return_value = {"running": True, "available": True}
            mock_cm.run_container.return_value = (True, "tool output", "")
            mock_get_cm.return_value = mock_cm
            return mock_cm
    
    def test_tool_executor_container_initialization(self, mock_container_manager):
        """测试ToolExecutor容器初始化"""
        executor = ToolExecutor()
        
        # 验证容器管理器集成
        assert executor.container_manager is not None
        assert executor.docker_mode is True
        
        # 验证容器功能可用
        assert executor.container_manager.is_available()
    
    def test_tool_executor_forced_container_mode(self):
        """测试强制容器模式配置"""
        # 模拟配置文件
        config_data = {
            'tools': {
                'container_mode': {
                    'force': True,
                    'priority': True
                }
            }
        }
        
        with patch('oss_audit.core.tool_executor.get_container_manager') as mock_get_cm:
            mock_cm = Mock(spec=ContainerManager)
            mock_cm.is_available.return_value = False
            mock_cm.diagnose_issues.return_value = {
                "issues": ["没有可用的容器引擎"],
                "recommendations": ["安装 Docker Desktop"]
            }
            mock_get_cm.return_value = mock_cm
            
            with patch.object(ToolExecutor, '_load_config', return_value=config_data):
                # 强制容器模式下，容器不可用应该抛出异常
                with pytest.raises(RuntimeError, match="强制容器模式下容器引擎不可用"):
                    ToolExecutor()
    
    def test_container_tool_execution_success(self, mock_container_manager):
        """测试容器工具执行成功"""
        with patch.object(ToolExecutor, '__init__', lambda x: None):
            executor = ToolExecutor.__new__(ToolExecutor)
            executor.container_manager = mock_container_manager
            executor.docker_mode = True
            
            # 创建测试工具
            test_tool = Tool(
                name="pylint",
                command=["pylint"],
                args=[],
                language="python",
                categories=["quality"],
                install=["pip install pylint"],
                timeout=60,
                estimated_time=30
            )
            
            # 模拟容器执行成功
            mock_container_manager.run_container.return_value = (
                True, 
                "pylint output with issues found", 
                ""
            )
            
            with tempfile.TemporaryDirectory() as temp_dir:
                result = executor._run_tool_in_docker(test_tool, temp_dir, 120, 0.0)
                
                # 验证结果
                assert result.tool_name == "pylint"
                assert result.success is True
                assert result.stdout == "pylint output with issues found"
                assert result.return_code == 0
            
            # 验证容器管理器被正确调用
            mock_container_manager.run_container.assert_called_once()
            call_args = mock_container_manager.run_container.call_args
            
            assert call_args[1]['image'] == "oss-audit:tools-2.0"
            assert call_args[1]['working_dir'] == "/workspace"
            assert '/workspace' in call_args[1]['volumes'].values()
    
    def test_container_tool_execution_failure_with_recovery(self, mock_container_manager):
        """测试容器工具执行失败和错误恢复"""
        with patch.object(ToolExecutor, '__init__', lambda x: None):
            executor = ToolExecutor.__new__(ToolExecutor)
            executor.container_manager = mock_container_manager
            executor.docker_mode = True
            
            test_tool = Tool(
                name="mypy",
                command=["mypy"],
                args=[],
                language="python", 
                categories=["quality"],
                install=["pip install mypy"],
                timeout=60,
                estimated_time=45
            )
            
            # 模拟容器执行异常
            mock_container_manager.run_container.side_effect = Exception("Container execution failed")
            mock_container_manager.create_error_report.return_value = Mock()
            mock_container_manager.attempt_recovery.return_value = True
            
            with tempfile.TemporaryDirectory() as temp_dir:
                result = executor._run_tool_in_docker(test_tool, temp_dir, 120, 0.0)
                
                # 验证失败结果
                assert result.tool_name == "mypy"
                assert result.success is False
                assert "容器执行异常" in result.error
            
            # 验证错误恢复被尝试
            mock_container_manager.create_error_report.assert_called_once()
            mock_container_manager.attempt_recovery.assert_called_once()
    
    def test_container_mode_fallback_to_local(self):
        """测试容器模式回退到本地模式"""
        with patch('oss_audit.core.tool_executor.get_container_manager') as mock_get_cm:
            mock_cm = Mock(spec=ContainerManager)
            mock_cm.is_available.return_value = True
            mock_cm.primary_engine = ContainerEngine.DOCKER
            mock_cm.get_engine_status.return_value = {"running": False, "available": True}
            mock_get_cm.return_value = mock_cm
            
            # 非强制模式下，容器引擎未运行应该回退到本地模式
            with patch.object(ToolExecutor, '_load_config', return_value={}):
                executor = ToolExecutor()
                assert executor.docker_mode is False  # 应该回退到本地模式
    
    def test_container_priority_mode(self, mock_container_manager):
        """测试容器优先模式"""
        config_data = {
            'tools': {
                'container_mode': {
                    'priority': True
                }
            }
        }
        
        with patch.object(ToolExecutor, '_load_config', return_value=config_data):
            executor = ToolExecutor()
            
            # 容器优先模式应该启用
            assert executor.docker_mode is True
            assert executor.container_manager is not None
    
    def test_direct_tool_command_creation(self, mock_container_manager):
        """测试直接工具命令创建"""
        executor = ToolExecutor()
        
        # 测试不同工具的命令创建
        test_cases = [
            ("pylint", ["pylint", "--output-format=json", "--reports=yes", "--score=yes", "--recursive=yes", "."]),
            ("flake8", ["flake8", "--format=default", "--statistics", "--max-line-length=88", "."]),
            ("bandit", ["bandit", "-r", "-f", "json", "."]),
            ("eslint", ["eslint", "--no-eslintrc", "--env", "es6", "--format=json", "--ext", ".js,.jsx,.ts,.tsx", "."]),
            ("semgrep", ["semgrep", "--config=p/python", "--json", "--quiet", "."])
        ]
        
        for tool_name, expected_cmd in test_cases:
            test_tool = Tool(
                name=tool_name,
                command=[tool_name],
                args=[],
                language="python" if tool_name in ["pylint", "flake8", "bandit"] else "javascript",
                categories=["quality"],
                install=[f"pip install {tool_name}"],
                timeout=60,
                estimated_time=30
            )
            
            cmd = executor._create_direct_tool_command(test_tool, "/workspace")
            assert cmd == expected_cmd, f"工具 {tool_name} 命令不匹配: 期望 {expected_cmd}, 实际 {cmd}"
    
    def test_container_engine_detection(self):
        """测试容器引擎检测"""
        with patch('oss_audit.core.tool_executor.get_container_manager') as mock_get_cm:
            # 测试不同的容器引擎
            for engine in [ContainerEngine.DOCKER, ContainerEngine.PODMAN, ContainerEngine.NERDCTL]:
                mock_cm = Mock(spec=ContainerManager)
                mock_cm.is_available.return_value = True
                mock_cm.primary_engine = engine
                mock_cm.get_engine_status.return_value = {"running": True, "available": True}
                mock_get_cm.return_value = mock_cm
                
                executor = ToolExecutor()
                assert executor.docker_mode is True
                assert executor.container_manager.primary_engine == engine
    
    def test_container_diagnosis_integration(self):
        """测试容器诊断集成"""
        with patch('oss_audit.core.tool_executor.get_container_manager') as mock_get_cm:
            mock_cm = Mock(spec=ContainerManager)
            mock_cm.is_available.return_value = False
            mock_cm.diagnose_issues.return_value = {
                "engines_available": 0,
                "primary_engine": None,
                "issues": [
                    "没有可用的容器引擎",
                    "Docker 服务未运行"
                ],
                "recommendations": [
                    "安装 Docker Desktop 或 Podman",
                    "确保容器服务正在运行",
                    "检查用户权限"
                ]
            }
            mock_get_cm.return_value = mock_cm
            
            # 强制模式下应该调用诊断
            config_data = {'tools': {'container_mode': {'force': True}}}
            
            with patch.object(ToolExecutor, '_load_config', return_value=config_data):
                with pytest.raises(RuntimeError):
                    ToolExecutor()
                
                # 验证诊断被调用
                mock_cm.diagnose_issues.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])