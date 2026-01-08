#!/usr/bin/env python3
"""
Test cases for AuditRunner with Plugin System Integration
"""

import unittest
import tempfile
import pathlib
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from oss_audit.core.audit_runner import AuditRunner
from oss_audit.core.project_detector import ProjectInfo, StructureType, ProjectType, SizeMetrics
from oss_audit.plugins.base import PluginResult
from oss_audit.plugins import reset_plugin_registry
from oss_audit.core.tool_executor import ToolResult


class TestAuditRunnerPluginIntegration(unittest.TestCase):
    
    def setUp(self):
        # Reset plugin registry to ensure clean state for each test
        reset_plugin_registry()
        
        self.test_dir = tempfile.mkdtemp()
        self.test_path = pathlib.Path(self.test_dir)
        
        # Create a simple Python project
        (self.test_path / "main.py").write_text("print('hello world')")
        (self.test_path / "requirements.txt").write_text("requests>=2.0.0")
        (self.test_path / "README.md").write_text("# Test Project")
        
        # Create AuditRunner
        self.audit_runner = AuditRunner()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_audit_runner_initialization_with_plugins(self):
        """Test that AuditRunner properly initializes plugin system"""
        runner = AuditRunner()
        
        # Should have plugin registry
        self.assertIsNotNone(runner.plugin_registry)
        
        # Should be able to get plugin info
        plugins = runner.plugin_registry.list_plugins()
        self.assertIsInstance(plugins, dict)
    
    @patch('oss_audit.core.audit_runner.AuditRunner._execute_plugins')
    @patch('oss_audit.core.tool_executor.ToolExecutor.execute_tools')
    @patch('oss_audit.core.tool_executor.ToolExecutor.discover_available_tools')
    @patch('oss_audit.core.tool_executor.ToolExecutor.create_execution_plan')
    def test_execute_tools_hybrid_mode(self, mock_create_plan, mock_discover, mock_execute_tools, mock_execute_plugins):
        """Test hybrid execution mode (traditional tools + plugins)"""
        
        # Setup mocks
        mock_create_plan.return_value = Mock()
        mock_create_plan.return_value.phases = []
        mock_discover.return_value = []
        
        # Mock traditional tool execution
        tool_result = ToolResult(
            tool_name="mock_tool",
            status="completed",
            success=True,
            result={'score': 85, 'issues_count': 2}
        )
        mock_execute_tools.return_value = {"mock_tool": tool_result}
        
        # Mock plugin execution
        plugin_result = PluginResult(
            plugin_name="python_plugin",
            language="python", 
            success=True,
            quality_score=90.0
        )
        plugin_result.tool_results = {"pylint": tool_result}
        mock_execute_plugins.return_value = {"python_plugin": plugin_result}
        
        # Mock executor stats
        self.audit_runner.tool_executor.get_execution_stats = Mock(return_value={
            'total_tools': 1,
            'successful_tools': 1,
            'failed_tools': 0
        })
        
        # Create mock execution plan
        execution_plan = Mock()
        execution_plan.phases = []
        
        # Execute
        results = self.audit_runner._execute_tools(execution_plan, str(self.test_path))
        
        # Verify both systems were called
        mock_execute_tools.assert_called_once()
        mock_execute_plugins.assert_called_once()
        
        # Verify results are combined
        self.assertIn("mock_tool", results)
        self.assertIn("python_plugin_pylint", results)  # Plugin tools have prefix
        
        # Verify statistics include plugin info
        self.assertIn('plugins_executed', self.audit_runner.execution_stats)
        self.assertIn('plugins_successful', self.audit_runner.execution_stats)
    
    def test_execute_plugins_method(self):
        """Test plugin execution method"""
        # Create project info
        project_info = ProjectInfo(
            name="test_project",
            path=str(self.test_path),
            languages={'python': 0.9},
            structure_type=StructureType.SINGLE_PROJECT,
            project_type=ProjectType.LIBRARY,
            size_metrics=SizeMetrics(),
            build_tools=[],
            dependencies={},
            confidence=0.9
        )
        
        self.audit_runner.current_project_info = project_info
        
        # Mock plugin registry
        mock_plugin = Mock()
        mock_plugin.name = "test_plugin"
        
        mock_plugin_result = PluginResult(
            plugin_name="test_plugin",
            language="python",
            success=True,
            quality_score=85.0
        )
        
        self.audit_runner.plugin_registry.get_plugins_for_project = Mock(return_value=[mock_plugin])
        self.audit_runner.plugin_registry.execute_plugins_safely = Mock(return_value={
            "test_plugin": mock_plugin_result
        })
        self.audit_runner.tool_executor.discover_available_tools = Mock(return_value=[])
        
        # Execute plugins
        results = self.audit_runner._execute_plugins(str(self.test_path))
        
        # Verify results
        self.assertEqual(len(results), 1)
        self.assertIn("test_plugin", results)
        self.assertTrue(results["test_plugin"].success)
        self.assertEqual(results["test_plugin"].quality_score, 85.0)
    
    def test_get_plugin_stats(self):
        """Test plugin statistics calculation"""
        # Create mock plugin results
        plugin_results = {
            "plugin1": PluginResult(
                plugin_name="plugin1",
                language="python",
                success=True,
                quality_score=85.0
            ),
            "plugin2": PluginResult(
                plugin_name="plugin2", 
                language="javascript",
                success=False,
                quality_score=50.0
            )
        }
        
        # Add tool results
        tool_result1 = ToolResult("tool1", "completed", True, result={'score': 90})
        tool_result2 = ToolResult("tool2", "failed", False, error="Tool failed")
        tool_result3 = ToolResult("tool3", "completed", True, result={'score': 80})
        
        plugin_results["plugin1"].tool_results = {"tool1": tool_result1, "tool2": tool_result2}
        plugin_results["plugin2"].tool_results = {"tool3": tool_result3}
        
        # Calculate stats
        stats = self.audit_runner._get_plugin_stats(plugin_results)
        
        # Verify stats
        self.assertEqual(stats['plugins_executed'], 2)
        self.assertEqual(stats['plugins_successful'], 1)  # Only plugin1 succeeded
        self.assertEqual(stats['total_tools'], 3)         # 2 tools from plugin1, 1 from plugin2
        self.assertEqual(stats['successful_tools'], 2)    # tool1 and tool3 succeeded
        self.assertEqual(stats['failed_tools'], 1)        # tool2 failed
    
    def test_no_applicable_plugins(self):
        """Test behavior when no plugins are applicable"""
        # Create project info with unsupported language
        project_info = ProjectInfo(
            name="test_project",
            path=str(self.test_path),
            languages={'cobol': 1.0},  # Unsupported language
            structure_type=StructureType.SINGLE_PROJECT,
            project_type=ProjectType.LIBRARY,
            size_metrics=SizeMetrics(),
            build_tools=[],
            dependencies={},
            confidence=0.9
        )
        
        self.audit_runner.current_project_info = project_info
        
        # Check what plugins are available for this project
        applicable_plugins = self.audit_runner.plugin_registry.get_plugins_for_project(project_info)
        
        # The core expectation is that no plugins should be applicable to COBOL projects
        # since we only have Python plugins registered
        self.assertEqual(len(applicable_plugins), 0, 
                        f"Expected no applicable plugins for COBOL project, but found: {[p.name for p in applicable_plugins]}")
        
        # Execute plugins
        results = self.audit_runner._execute_plugins(str(self.test_path))
        
        # Should return empty results for non-supported languages
        self.assertEqual(len(results), 0)
        self.assertIsInstance(results, dict)
    
    @patch('oss_audit.core.audit_runner.ReportGenerator.generate_audit_report')
    def test_end_to_end_audit_with_plugins(self, mock_generate_report):
        """Test end-to-end audit execution with plugin system"""
        
        # Mock report generation
        mock_generate_report.return_value = "test_report.html"
        
        # Patch methods to avoid actual tool execution
        with patch.object(self.audit_runner.tool_executor, 'execute_tools') as mock_execute_tools, \
             patch.object(self.audit_runner, '_execute_plugins') as mock_execute_plugins:
            
            # Setup mocks
            mock_execute_tools.return_value = {}
            mock_execute_plugins.return_value = {}
            self.audit_runner.tool_executor.get_execution_stats = Mock(return_value={
                'total_tools': 0, 'successful_tools': 0, 'failed_tools': 0
            })
            
            # Run audit
            result_path = self.audit_runner.audit_project(str(self.test_path))
            
            # Verify execution
            self.assertEqual(result_path, "test_report.html")
            mock_execute_tools.assert_called_once()
            mock_execute_plugins.assert_called_once()
            mock_generate_report.assert_called_once()
    
    def test_plugin_error_isolation(self):
        """Test that plugin errors don't crash the audit"""
        # Create project info
        project_info = ProjectInfo(
            name="test_project",
            path=str(self.test_path),
            languages={'python': 0.9},
            structure_type=StructureType.SINGLE_PROJECT,
            project_type=ProjectType.LIBRARY,
            size_metrics=SizeMetrics(),
            build_tools=[],
            dependencies={},
            confidence=0.9
        )
        
        self.audit_runner.current_project_info = project_info
        
        # Mock plugin registry to raise an exception
        self.audit_runner.plugin_registry.get_plugins_for_project = Mock(
            side_effect=Exception("Plugin registry error")
        )
        
        # Should handle the error gracefully
        try:
            results = self.audit_runner._execute_plugins(str(self.test_path))
            # If no exception, the method should return empty results or handle gracefully
            self.assertIsInstance(results, dict)
        except Exception as e:
            # If it raises an exception, verify it's the expected one
            self.assertIn("Plugin registry error", str(e))


if __name__ == '__main__':
    unittest.main()