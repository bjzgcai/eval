#!/usr/bin/env python3
"""
Test cases for Plugin System
"""

import unittest
import tempfile
import pathlib
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from oss_audit.plugins.base import (
    LanguagePlugin, PluginResult, PluginError, PluginCapability,
    PluginPriority, PluginCategory
)
from oss_audit.plugins.registry import PluginRegistry
from oss_audit.plugins.language_plugins.python_plugin import PythonPlugin
from oss_audit.core.project_detector import ProjectInfo, StructureType, ProjectType, SizeMetrics
from oss_audit.core.tool_registry import Tool
from oss_audit.core.tool_executor import ToolResult


class TestPluginBase(unittest.TestCase):
    
    def test_plugin_capability_can_analyze(self):
        """Test PluginCapability can_analyze method"""
        capability = PluginCapability(
            languages={'python'},
            file_extensions={'.py'},
            categories={PluginCategory.QUALITY},
            required_tools=[],
            optional_tools=[],
            min_confidence_threshold=0.2
        )
        
        # Create project info with Python
        project_info = ProjectInfo(
            name="test_project",
            path="/test/path",
            languages={'python': 0.8, 'javascript': 0.2},
            structure_type=StructureType.SINGLE_PROJECT,
            project_type=ProjectType.LIBRARY,
            size_metrics=SizeMetrics(),
            build_tools=[],
            dependencies={},
            confidence=0.9
        )
        
        self.assertTrue(capability.can_analyze(project_info))
        
        # Test with low confidence
        project_info.languages = {'python': 0.1}
        self.assertFalse(capability.can_analyze(project_info))
        
        # Test with no matching language
        project_info.languages = {'java': 0.9}
        self.assertFalse(capability.can_analyze(project_info))
    
    def test_plugin_error(self):
        """Test PluginError class"""
        error = PluginError(
            plugin_name="test_plugin",
            error_type="TestError",
            message="Test error message",
            recoverable=True,
            details={'key': 'value'}
        )
        
        self.assertEqual(error.plugin_name, "test_plugin")
        self.assertEqual(error.error_type, "TestError")
        self.assertTrue(error.recoverable)
        self.assertEqual(str(error), "[test_plugin] TestError: Test error message")
    
    def test_plugin_result(self):
        """Test PluginResult class"""
        result = PluginResult(
            plugin_name="test_plugin",
            language="python",
            success=True
        )
        
        self.assertEqual(result.plugin_name, "test_plugin")
        self.assertEqual(result.language, "python")
        self.assertTrue(result.success)
        
        # Test adding error
        error = PluginError("test_plugin", "TestError", "Test message", recoverable=False)
        result.add_error(error)
        
        self.assertFalse(result.success)  # Should become False for non-recoverable error
        self.assertEqual(len(result.errors), 1)
        
        # Test to_dict conversion
        result_dict = result.to_dict()
        self.assertIsInstance(result_dict, dict)
        self.assertEqual(result_dict['plugin_name'], "test_plugin")


class TestPluginRegistry(unittest.TestCase):
    
    def setUp(self):
        self.registry = PluginRegistry()
    
    def tearDown(self):
        self.registry.cleanup()
    
    def test_plugin_registration(self):
        """Test plugin registration"""
        # Create mock plugin class
        class MockPlugin(LanguagePlugin):
            @property
            def capability(self):
                return PluginCapability(
                    languages={'python'},
                    file_extensions={'.py'},
                    categories={PluginCategory.QUALITY},
                    required_tools=[],
                    optional_tools=[]
                )
            
            @property
            def priority(self):
                return PluginPriority.HIGH
            
            def _execute_analysis(self, project_path, project_info, tools, result):
                pass
        
        # Register plugin
        success = self.registry.register_plugin("mock_plugin", MockPlugin)
        self.assertTrue(success)
        
        # Verify plugin is registered
        plugin = self.registry.get_plugin("mock_plugin")
        self.assertIsNotNone(plugin)
        self.assertEqual(plugin.name, "mock_plugin")
        
        # Verify language mapping
        python_plugins = self.registry.get_plugins_for_language("python")
        self.assertEqual(len(python_plugins), 1)
        self.assertEqual(python_plugins[0].name, "mock_plugin")
    
    def test_plugin_registry_list_plugins(self):
        """Test listing plugins"""
        # Initially empty
        plugins = self.registry.list_plugins()
        self.assertEqual(len(plugins), 0)
        
        # Register a plugin
        class TestPlugin(LanguagePlugin):
            @property
            def capability(self):
                return PluginCapability(
                    languages={'python'},
                    file_extensions={'.py'},
                    categories={PluginCategory.QUALITY},
                    required_tools=[],
                    optional_tools=[]
                )
            
            @property
            def priority(self):
                return PluginPriority.MEDIUM
            
            def _execute_analysis(self, project_path, project_info, tools, result):
                pass
        
        self.registry.register_plugin("test_plugin", TestPlugin)
        
        # Verify plugin is listed
        plugins = self.registry.list_plugins()
        self.assertEqual(len(plugins), 1)
        self.assertIn("test_plugin", plugins)
        
        plugin_info = plugins["test_plugin"]
        self.assertEqual(plugin_info['name'], "test_plugin")
        self.assertTrue(plugin_info['initialized'])
        self.assertIn('python', plugin_info['languages'])
    
    def test_get_plugins_for_project(self):
        """Test getting plugins for a specific project"""
        # Register test plugin
        class TestPlugin(LanguagePlugin):
            @property
            def capability(self):
                return PluginCapability(
                    languages={'python'},
                    file_extensions={'.py'},
                    categories={PluginCategory.QUALITY},
                    required_tools=[],
                    optional_tools=[],
                    min_confidence_threshold=0.3
                )
            
            @property
            def priority(self):
                return PluginPriority.HIGH
            
            def _execute_analysis(self, project_path, project_info, tools, result):
                pass
        
        self.registry.register_plugin("test_plugin", TestPlugin)
        
        # Create project info
        project_info = ProjectInfo(
            name="test_project",
            path="/test/path",
            languages={'python': 0.8},
            structure_type=StructureType.SINGLE_PROJECT,
            project_type=ProjectType.LIBRARY,
            size_metrics=SizeMetrics(),
            build_tools=[],
            dependencies={},
            confidence=0.9
        )
        
        # Get plugins for project
        plugins = self.registry.get_plugins_for_project(project_info)
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0].name, "test_plugin")
        
        # Test with project that doesn't meet confidence threshold
        project_info.languages = {'python': 0.1}
        plugins = self.registry.get_plugins_for_project(project_info)
        self.assertEqual(len(plugins), 0)


class TestPythonPlugin(unittest.TestCase):
    
    def setUp(self):
        self.plugin = PythonPlugin("python_plugin")
        self.plugin.initialize()
        
        self.test_dir = tempfile.mkdtemp()
        self.test_path = pathlib.Path(self.test_dir)
        
        # Create test project info
        self.project_info = ProjectInfo(
            name="test_project",
            path=str(self.test_path),
            languages={'python': 0.9},
            structure_type=StructureType.SINGLE_PROJECT,
            project_type=ProjectType.LIBRARY,
            size_metrics=SizeMetrics(code_files=5, code_lines=100, test_files=2, test_lines=50),
            build_tools=['setuptools'],
            dependencies={'python': ['pytest', 'requests']},
            confidence=0.9
        )
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_python_plugin_initialization(self):
        """Test Python plugin initialization"""
        self.assertEqual(self.plugin.name, "python_plugin")
        self.assertTrue(self.plugin._initialized)
        self.assertEqual(self.plugin.priority, PluginPriority.HIGH)
    
    def test_python_plugin_capability(self):
        """Test Python plugin capabilities"""
        capability = self.plugin.capability
        
        self.assertIn('python', capability.languages)
        self.assertIn('.py', capability.file_extensions)
        self.assertIn(PluginCategory.QUALITY, capability.categories)
        self.assertIn(PluginCategory.SECURITY, capability.categories)
        self.assertIn('pylint', capability.optional_tools)
    
    def test_can_analyze_python_project(self):
        """Test if plugin can analyze Python project"""
        self.assertTrue(self.plugin.can_analyze(self.project_info))
        
        # Test with non-Python project
        non_python_info = ProjectInfo(
            name="java_project",
            path="/test",
            languages={'java': 0.9},
            structure_type=StructureType.SINGLE_PROJECT,
            project_type=ProjectType.LIBRARY,
            size_metrics=SizeMetrics(),
            build_tools=[],
            dependencies={},
            confidence=0.9
        )
        
        self.assertFalse(self.plugin.can_analyze(non_python_info))
    
    def test_tool_selection(self):
        """Test Python tool selection logic"""
        # Create mock tools
        tools = [
            Tool(
                name="pylint",
                command=["pylint"],
                args=[],
                language="python",
                install=[],
                priority=1,
                categories=["quality"]
            ),
            Tool(
                name="flake8", 
                command=["flake8"],
                args=[],
                language="python",
                install=[],
                priority=1,
                categories=["quality"]
            ),
            Tool(
                name="bandit",
                command=["bandit"],
                args=[],
                language="python", 
                install=[],
                priority=2,
                categories=["security"]
            ),
            Tool(
                name="javac",
                command=["javac"],
                args=[],
                language="java",
                install=[],
                priority=1,
                categories=["syntax"]
            )
        ]
        
        selected = self.plugin.select_tools(self.project_info, tools)
        
        # Should select Python tools but not Java tools
        selected_names = [tool.name for tool in selected]
        self.assertIn("pylint", selected_names)
        self.assertIn("flake8", selected_names) 
        self.assertIn("bandit", selected_names)
        self.assertNotIn("javac", selected_names)
    
    def test_python_command_building(self):
        """Test Python command building for different tools"""
        # Test pylint command
        pylint_tool = Tool(
            name="pylint",
            command=["python", "-m", "pylint"],
            args=["--output-format=json"],
            language="python",
            install=[],
            priority=1
        )
        
        # Create a simple Python file
        (self.test_path / "test.py").write_text("print('hello')")
        
        cmd = self.plugin._build_python_command(pylint_tool, str(self.test_path), self.project_info)
        
        self.assertEqual(cmd[0:3], ["python", "-m", "pylint"])
        self.assertIn("--output-format=json", cmd)
    
    def test_output_parsing(self):
        """Test parsing of different tool outputs"""
        # Test pylint output parsing
        pylint_output = """test.py:1:0: C0111: Missing module docstring (missing-docstring)
test.py:2:0: W0622: Redefining built-in 'print' (redefined-builtin)"""
        
        result = self.plugin._parse_pylint_output(pylint_output)
        
        self.assertEqual(result['issues_count'], 2)
        self.assertLess(result['score'], 100)
        self.assertEqual(len(result['issues']), 2)
        
        # Test flake8 output parsing
        flake8_output = """test.py:1:1: E302 expected 2 blank lines, found 1
test.py:2:80: E501 line too long (82 > 79 characters)"""
        
        result = self.plugin._parse_flake8_output(flake8_output)
        
        self.assertEqual(result['issues_count'], 2)
        self.assertLess(result['score'], 100)
    
    @patch('subprocess.run')
    def test_tool_execution_with_mock(self, mock_run):
        """Test tool execution with mocked subprocess"""
        # Setup mock
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "All good"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        tool = Tool(
            name="pylint",
            command=["pylint"], 
            args=[],
            language="python",
            install=[],
            priority=1,
            timeout=60
        )
        
        result = self.plugin._execute_single_tool(tool, str(self.test_path), self.project_info)
        
        self.assertTrue(result.success)
        self.assertEqual(result.tool_name, "pylint")
        self.assertEqual(result.return_code, 0)
    
    def test_post_processing(self):
        """Test Python-specific post-processing"""
        # Create requirements.txt
        (self.test_path / "requirements.txt").write_text("requests>=2.0.0\npytest>=6.0.0")
        
        result = PluginResult(
            plugin_name="python_plugin",
            language="python",
            success=True,
            quality_score=75
        )
        
        self.plugin._post_process_results(result, self.project_info)
        
        # Should have bonus for having requirements.txt
        self.assertGreater(result.quality_score, 75)
        self.assertTrue(result.plugin_data['has_requirements'])
        self.assertFalse(result.plugin_data['has_setup_py'])


class TestPluginErrorIsolation(unittest.TestCase):
    """Test plugin error isolation and recovery"""
    
    def setUp(self):
        self.registry = PluginRegistry()
    
    def tearDown(self):
        self.registry.cleanup()
    
    def test_plugin_execution_error_isolation(self):
        """Test that plugin errors don't affect other plugins"""
        # Create a plugin that always fails
        class FailingPlugin(LanguagePlugin):
            @property
            def capability(self):
                return PluginCapability(
                    languages={'python'},
                    file_extensions={'.py'},
                    categories={PluginCategory.QUALITY},
                    required_tools=[],
                    optional_tools=[]
                )
            
            @property
            def priority(self):
                return PluginPriority.LOW
            
            def _execute_analysis(self, project_path, project_info, tools, result):
                raise Exception("Plugin failed!")
        
        # Create a plugin that works
        class WorkingPlugin(LanguagePlugin):
            @property
            def capability(self):
                return PluginCapability(
                    languages={'python'},
                    file_extensions={'.py'},
                    categories={PluginCategory.QUALITY},
                    required_tools=[],
                    optional_tools=[]
                )
            
            @property
            def priority(self):
                return PluginPriority.HIGH
            
            def _execute_analysis(self, project_path, project_info, tools, result):
                result.quality_score = 85.0
        
        # Register both plugins
        self.registry.register_plugin("failing_plugin", FailingPlugin)
        self.registry.register_plugin("working_plugin", WorkingPlugin)
        
        # Create project info
        project_info = ProjectInfo(
            name="test_project",
            path="/test",
            languages={'python': 0.9},
            structure_type=StructureType.SINGLE_PROJECT,
            project_type=ProjectType.LIBRARY,
            size_metrics=SizeMetrics(),
            build_tools=[],
            dependencies={},
            confidence=0.9
        )
        
        # Get plugins and execute them
        plugins = self.registry.get_plugins_for_project(project_info)
        self.assertEqual(len(plugins), 2)
        
        # Execute plugins safely
        results = self.registry.execute_plugins_safely(
            plugins, "/test", project_info, []
        )
        
        # Should have results for both plugins
        self.assertEqual(len(results), 2)
        
        # Failing plugin should have error result
        self.assertFalse(results['failing_plugin'].success)
        self.assertGreater(len(results['failing_plugin'].errors), 0)
        
        # Working plugin should succeed
        self.assertTrue(results['working_plugin'].success)
        self.assertEqual(results['working_plugin'].quality_score, 85.0)


if __name__ == '__main__':
    unittest.main()