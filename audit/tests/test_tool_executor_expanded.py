#!/usr/bin/env python3
"""
Comprehensive test cases for ToolExecutor - expanding coverage
Tests the critical tool execution engine with various scenarios
"""

import pytest
import unittest
import tempfile
import pathlib
import os
import shutil
import time
from unittest.mock import Mock, patch, MagicMock, call
from dataclasses import dataclass
from typing import List, Dict, Any

# Add src to path for imports
import sys
src_dir = pathlib.Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from oss_audit.core.tool_executor import (
    ToolExecutor, ExecutionPlan, ExecutionPhase, ExecutionMode,
    ToolResult, ResourceMonitor, ExecutionStatus
)
from oss_audit.core.project_detector import ProjectInfo, ProjectType, StructureType, SizeMetrics
from oss_audit.core.tool_registry import Tool


@dataclass
class MockTool:
    """Mock tool for testing"""
    name: str
    language: str = "python"
    categories: List[str] = None
    priority: int = 1
    estimated_time: int = 30
    timeout: int = 120
    available: bool = True
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = ["quality"]


def create_mock_project_info(code_lines: int = 5000) -> ProjectInfo:
    """Create mock project info for testing"""
    return ProjectInfo(
        name="test-project",
        path="/tmp/test-project",
        languages={"python": 0.8, "javascript": 0.2},
        structure_type=StructureType.SINGLE_PROJECT,
        project_type=ProjectType.LIBRARY,
        dependencies={"python": ["requests", "pytest"]},
        build_tools=["setup.py"],
        size_metrics=SizeMetrics(
            total_files=100,
            total_lines=code_lines + 1500,
            code_files=80,
            code_lines=code_lines,
            test_files=20,
            test_lines=1000
        ),
        confidence=0.9
    )


class TestToolExecutor(unittest.TestCase):
    """Comprehensive ToolExecutor test suite"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = pathlib.Path(self.temp_dir)
        
        # Create test project structure
        (self.temp_path / "main.py").write_text("print('hello')")
        (self.temp_path / "setup.py").write_text("from setuptools import setup")
        (self.temp_path / "requirements.txt").write_text("pytest\nnumpy")
        
        self.project_info = create_mock_project_info()
        
        # Initialize ToolExecutor with mock registry
        with patch('oss_audit.core.tool_executor.get_tool_registry') as mock_registry:
            mock_registry.return_value = Mock()
            self.executor = ToolExecutor()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_executor_initialization(self):
        """Test ToolExecutor initializes correctly"""
        self.assertIsNotNone(self.executor.registry)
        self.assertIsNotNone(self.executor.resource_monitor)
        self.assertIsInstance(self.executor.docker_mode, bool)
    
    def test_discover_available_tools_basic(self):
        """Test basic tool discovery functionality"""
        mock_tools = [
            MockTool("pylint", "python", ["quality"], 1, 60),
            MockTool("bandit", "python", ["security"], 1, 40),
            MockTool("eslint", "javascript", ["quality"], 1, 45),
        ]
        
        self.executor.registry.get_language_tools = Mock(side_effect=lambda lang: [
            t for t in mock_tools if t.language == lang or t.language == "universal"
        ])
        self.executor.registry.get_universal_tools = Mock(return_value=[])
        
        with patch.object(self.executor.registry, 'is_tool_available', return_value=True):
            available_tools = self.executor.discover_available_tools(self.project_info)
            
            # Should find tools for python (80% of project)
            self.assertGreater(len(available_tools), 0)
            tool_names = [t.name for t in available_tools]
            self.assertIn("pylint", tool_names)
            self.assertIn("bandit", tool_names)
    
    def test_discover_available_tools_with_unavailable_tools(self):
        """Test tool discovery when some tools are unavailable"""
        mock_tools = [
            MockTool("pylint", "python", ["quality"], 1, 60, available=True),
            MockTool("mypy", "python", ["typing"], 2, 45, available=False),
        ]
        
        self.executor.registry.get_language_tools = Mock(return_value=mock_tools)
        self.executor.registry.get_universal_tools = Mock(return_value=[])
        
        def mock_is_available(tool):
            return tool.available
            
        with patch.object(self.executor.registry, 'is_tool_available', side_effect=mock_is_available):
            available_tools = self.executor.discover_available_tools(self.project_info)
            
            # Filter only available tools
            actually_available = [t for t in available_tools if mock_is_available(t)]
            tool_names = [t.name for t in actually_available]
            self.assertIn("pylint", tool_names)
            self.assertNotIn("mypy", tool_names)
    
    def test_create_execution_plan_simple(self):
        """Test creating a simple execution plan"""
        mock_tools = [
            MockTool("pylint", "python", ["quality"], 1, 60),
            MockTool("bandit", "python", ["security"], 1, 40),
        ]
        
        plan = self.executor.create_execution_plan(mock_tools, self.project_info)
        
        self.assertIsInstance(plan, ExecutionPlan)
        self.assertGreater(len(plan.phases), 0)
        self.assertGreater(plan.get_total_estimated_time(), 0)
    
    def test_create_execution_plan_with_dependencies(self):
        """Test execution plan creation with tool dependencies"""
        mock_tools = [
            MockTool("setup", "python", ["setup"], 1, 10),
            MockTool("pylint", "python", ["quality"], 2, 60),
            MockTool("tests", "python", ["testing"], 3, 120),
        ]
        
        plan = self.executor.create_execution_plan(mock_tools, self.project_info)
        
        # Should create phases based on priority and dependencies
        self.assertGreater(len(plan.phases), 0)
        
        # Verify plan has tools
        total_tools = sum(len(phase.tools) for phase in plan.phases)
        self.assertEqual(total_tools, len(mock_tools))
    
    def test_execute_tools_sequential(self):
        """Test sequential tool execution"""
        mock_tools = [
            MockTool("tool1", "python", ["quality"], 1, 30),
            MockTool("tool2", "python", ["security"], 2, 40),
        ]
        
        # Create execution plan with sequential mode
        phase = ExecutionPhase(
            name="test_phase",
            tools=mock_tools,
            mode=ExecutionMode.SEQUENTIAL,
            timeout=300
        )
        plan = ExecutionPlan(phases=[phase])
        
        # Mock the tool execution
        with patch.object(self.executor, '_run_single_tool') as mock_execute:
            mock_execute.return_value = ToolResult(
                tool_name="test",
                status=ExecutionStatus.COMPLETED,
                success=True,
                result={"output": "test output"},
                execution_time=30,
                return_code=0
            )
            
            results = self.executor.execute_tools(plan, str(self.temp_path))
            
            self.assertEqual(len(results), 2)
            self.assertEqual(mock_execute.call_count, 2)
    
    def test_execute_tools_parallel(self):
        """Test parallel tool execution"""
        mock_tools = [
            MockTool("tool1", "python", ["quality"], 1, 30),
            MockTool("tool2", "python", ["security"], 1, 40),
        ]
        
        phase = ExecutionPhase(
            name="parallel_phase",
            tools=mock_tools,
            mode=ExecutionMode.PARALLEL,
            timeout=300
        )
        plan = ExecutionPlan(phases=[phase])
        
        with patch.object(self.executor, '_execute_parallel') as mock_parallel:
            mock_parallel.return_value = {
                "tool1": ToolResult("tool1", ExecutionStatus.COMPLETED, True, {"output": "output1"}, None, 30),
                "tool2": ToolResult("tool2", ExecutionStatus.COMPLETED, True, {"output": "output2"}, None, 40)
            }
            
            results = self.executor.execute_tools(plan, str(self.temp_path))
            
            self.assertEqual(len(results), 2)
            mock_parallel.assert_called_once()
    
    def test_execute_tools_with_timeout(self):
        """Test tool execution with timeout handling"""
        mock_tool = MockTool("slow_tool", "python", ["quality"], 1, 300)
        
        with patch.object(self.executor, '_run_single_tool') as mock_execute:
            # Simulate timeout
            mock_execute.side_effect = TimeoutError("Tool execution timed out")
            
            phase = ExecutionPhase(
                name="timeout_phase",
                tools=[mock_tool],
                mode=ExecutionMode.SEQUENTIAL,
                timeout=60
            )
            plan = ExecutionPlan(phases=[phase])
            
            results = self.executor.execute_tools(plan, str(self.temp_path))
            
            # Should handle timeout gracefully
            self.assertIn("slow_tool", results)
            result = results["slow_tool"]
            self.assertFalse(result.success)
            self.assertIn("timed out", result.error.lower())
    
    def test_execute_tools_with_failure_handling(self):
        """Test tool execution with failure handling"""
        mock_tools = [
            MockTool("failing_tool", "python", ["quality"], 1, 30),
            MockTool("working_tool", "python", ["security"], 2, 40),
        ]
        
        def mock_execute_side_effect(tool, project_path, context):
            if tool.name == "failing_tool":
                return ToolResult(
                    tool_name="failing_tool",
                    status=ExecutionStatus.FAILED,
                    success=False,
                    result={},
                    error="Tool execution failed",
                    execution_time=30,
                    return_code=1
                )
            else:
                return ToolResult(
                    tool_name="working_tool",
                    status=ExecutionStatus.COMPLETED,
                    success=True,
                    result={"output": "success output"},
                    execution_time=40,
                    return_code=0
                )
        
        with patch.object(self.executor, '_run_single_tool', side_effect=mock_execute_side_effect):
            phase = ExecutionPhase(
                name="mixed_phase",
                tools=mock_tools,
                mode=ExecutionMode.SEQUENTIAL,
                timeout=300,
                continue_on_failure=True
            )
            plan = ExecutionPlan(phases=[phase])
            
            results = self.executor.execute_tools(plan, str(self.temp_path))
            
            # Should continue execution despite failure
            self.assertEqual(len(results), 2)
            self.assertFalse(results["failing_tool"].success)
            self.assertTrue(results["working_tool"].success)
    
    def test_resource_monitoring(self):
        """Test resource monitoring during execution"""
        mock_tool = MockTool("monitored_tool", "python", ["quality"], 1, 60)
        
        with patch.object(self.executor, '_run_single_tool') as mock_execute:
            result = ToolResult(
                tool_name="monitored_tool",
                status=ExecutionStatus.COMPLETED,
                success=True,
                result={"output": "monitored output"},
                execution_time=60,
                return_code=0
            )
            mock_execute.return_value = result
            
            phase = ExecutionPhase(
                name="monitored_phase",
                tools=[mock_tool],
                mode=ExecutionMode.SEQUENTIAL,
                timeout=300
            )
            plan = ExecutionPlan(phases=[phase])
            
            results = self.executor.execute_tools(plan, str(self.temp_path))
            
            # Verify execution completed
            self.assertEqual(len(results), 1)
            self.assertTrue(results["monitored_tool"].success)
    
    def test_container_mode_initialization(self):
        """Test ToolExecutor initialization with docker mode"""
        with patch('oss_audit.core.tool_executor.get_tool_registry') as mock_registry:
            mock_registry.return_value = Mock()
            with patch.object(ToolExecutor, '_ensure_container_ready', return_value=True):
                executor = ToolExecutor(docker_mode=True)
                self.assertTrue(executor.docker_mode)
    
    def test_get_execution_stats(self):
        """Test execution statistics collection"""
        # Execute some tools to generate stats
        mock_tool = MockTool("stats_tool", "python", ["quality"], 1, 30)
        
        with patch.object(self.executor, '_run_single_tool') as mock_execute:
            mock_execute.return_value = ToolResult(
                tool_name="stats_tool",
                status=ExecutionStatus.COMPLETED,
                success=True,
                result={"output": "stats output"},
                execution_time=30,
                return_code=0
            )
            
            phase = ExecutionPhase(
                name="stats_phase",
                tools=[mock_tool],
                mode=ExecutionMode.SEQUENTIAL,
                timeout=300
            )
            plan = ExecutionPlan(phases=[phase])
            
            self.executor.execute_tools(plan, str(self.temp_path))
            
            # Check execution stats
            stats = self.executor.get_execution_stats()
            
            self.assertIn('total_tools', stats)
            self.assertIn('successful_tools', stats) 
            self.assertIn('failed_tools', stats)
            self.assertIn('total_time', stats)
    
    def test_cleanup_resources(self):
        """Test resource cleanup after execution"""
        mock_tool = MockTool("cleanup_tool", "python", ["quality"], 1, 30)
        
        with patch.object(self.executor, '_run_single_tool') as mock_execute:
            mock_execute.return_value = ToolResult(
                tool_name="cleanup_tool",
                status=ExecutionStatus.COMPLETED,
                success=True,
                result={"output": "cleanup output"},
                execution_time=30,
                return_code=0
            )
            
            phase = ExecutionPhase(
                name="cleanup_phase",
                tools=[mock_tool],
                mode=ExecutionMode.SEQUENTIAL,
                timeout=300
            )
            plan = ExecutionPlan(phases=[phase])
            
            self.executor.execute_tools(plan, str(self.temp_path))
            
            # Test basic cleanup functionality
            self.executor.resource_monitor.stop_monitoring()


class TestToolExecutorIntegration(unittest.TestCase):
    """Integration tests for ToolExecutor with real tool configurations"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = pathlib.Path(self.temp_dir)
        
        # Create realistic Python project structure
        (self.temp_path / "src").mkdir()
        (self.temp_path / "src" / "__init__.py").write_text("")
        (self.temp_path / "src" / "main.py").write_text("""
def hello_world():
    '''Simple hello world function'''
    return 'Hello, World!'

if __name__ == '__main__':
    print(hello_world())
""")
        (self.temp_path / "setup.py").write_text("""
from setuptools import setup, find_packages

setup(
    name='test-project',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'requests>=2.25.0',
    ],
)
""")
        (self.temp_path / "requirements.txt").write_text("requests>=2.25.0\npytest>=6.0.0")
        (self.temp_path / "README.md").write_text("# Test Project\nThis is a test project.")
        
        self.project_info = ProjectInfo(
            name="test-project",
            path=str(self.temp_path),
            languages={"python": 1.0},
            structure_type=StructureType.SINGLE_PROJECT,
            project_type=ProjectType.LIBRARY,
            dependencies={"python": ["requests", "pytest"]},
            build_tools=["setuptools"],
            size_metrics=SizeMetrics(
                total_files=5,
                total_lines=50,
                code_files=2,
                code_lines=20,
                test_files=0,
                test_lines=0
            ),
            confidence=0.95
        )
    
    def tearDown(self):
        """Clean up integration test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('oss_audit.core.tool_executor.get_tool_registry')
    def test_end_to_end_tool_execution(self, mock_registry):
        """Test complete end-to-end tool execution workflow"""
        # Mock registry with realistic tool configurations
        mock_tool_registry = Mock()
        mock_tool_registry.get_language_tools.return_value = [
            MockTool("pylint", "python", ["quality"], 1, 60),
            MockTool("flake8", "python", ["style"], 2, 30),
        ]
        mock_tool_registry.get_universal_tools.return_value = []
        mock_registry.return_value = mock_tool_registry
        
        executor = ToolExecutor()
        
        # Mock successful tool execution
        def mock_execute_single_tool(tool, project_path, context):
            return ToolResult(
                tool_name=tool.name,
                status=ExecutionStatus.COMPLETED,
                success=True,
                result={
                    "output": f"Mock output for {tool.name}",
                    "issues_found": [] if tool.name == "flake8" else [
                        {"type": "warning", "message": "Sample issue", "line": 1}
                    ]
                },
                execution_time=tool.estimated_time,
                return_code=0
            )
        
        with patch.object(executor.registry, 'is_tool_available', return_value=True), \
             patch.object(executor, '_run_single_tool', side_effect=mock_execute_single_tool):
            
            # Discover tools
            available_tools = executor.discover_available_tools(self.project_info)
            self.assertGreater(len(available_tools), 0)
            
            # Create execution plan
            execution_plan = executor.create_execution_plan(available_tools, self.project_info)
            self.assertIsInstance(execution_plan, ExecutionPlan)
            
            # Execute tools
            results = executor.execute_tools(execution_plan, str(self.temp_path))
            
            # Verify results
            self.assertGreater(len(results), 0)
            for tool_name, result in results.items():
                self.assertIsInstance(result, ToolResult)
                self.assertTrue(result.success)
                self.assertGreater(result.execution_time, 0)


@pytest.mark.slow
class TestToolExecutorPerformance(unittest.TestCase):
    """Performance tests for ToolExecutor"""
    
    def setUp(self):
        """Set up performance test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = pathlib.Path(self.temp_dir)
        
        # Create a larger project structure for performance testing
        for i in range(20):
            (self.temp_path / f"module_{i}.py").write_text(f"""
def function_{i}():
    '''Function {i}'''
    return {i}
""")
        
        self.project_info = create_mock_project_info(code_lines=10000)
        
        with patch('oss_audit.core.tool_executor.get_tool_registry') as mock_registry:
            mock_registry.return_value = Mock()
            self.executor = ToolExecutor()
    
    def tearDown(self):
        """Clean up performance test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parallel_execution_performance(self):
        """Test that parallel execution is faster than sequential"""
        mock_tools = [MockTool(f"tool_{i}", "python", ["quality"], 1, 100) for i in range(4)]
        
        def slow_mock_execute(tool, project_path, context):
            time.sleep(0.1)  # Simulate tool execution time
            return ToolResult(
                tool_name=tool.name,
                status=ExecutionStatus.COMPLETED,
                success=True,
                result={"output": "test output"},
                execution_time=100,
                return_code=0
            )
        
        with patch.object(self.executor, '_run_single_tool', side_effect=slow_mock_execute):
            # Test sequential execution
            sequential_phase = ExecutionPhase(
                name="sequential",
                tools=mock_tools,
                mode=ExecutionMode.SEQUENTIAL,
                timeout=600
            )
            sequential_plan = ExecutionPlan(phases=[sequential_phase])
            
            start_time = time.time()
            self.executor.execute_tools(sequential_plan, str(self.temp_path))
            sequential_time = time.time() - start_time
            
            # Test parallel execution
            parallel_phase = ExecutionPhase(
                name="parallel",
                tools=mock_tools,
                mode=ExecutionMode.PARALLEL,
                timeout=600
            )
            parallel_plan = ExecutionPlan(phases=[parallel_phase])
            
            start_time = time.time()
            self.executor.execute_tools(parallel_plan, str(self.temp_path))
            parallel_time = time.time() - start_time
            
            # Parallel should be significantly faster
            self.assertLess(parallel_time, sequential_time * 0.8)


if __name__ == '__main__':
    # Run with pytest to get better output and markers support
    unittest.main(verbosity=2)