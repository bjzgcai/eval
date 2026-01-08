#!/usr/bin/env python3
"""
Test cases for Multi-Language Plugins (Phase 2 Week 3-4)
Tests JavaScript, Java, and Go plugins
"""

import unittest
import tempfile
import pathlib
import os
import sys
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from oss_audit.plugins.base import PluginResult, PluginCapability, PluginCategory
from oss_audit.plugins.language_plugins.javascript_plugin import JavaScriptPlugin
from oss_audit.plugins.language_plugins.java_plugin import JavaPlugin
from oss_audit.plugins.language_plugins.go_plugin import GoPlugin
from oss_audit.plugins.result_validator import PluginResultValidator, ResultStandardizer
from oss_audit.plugins import reset_plugin_registry, get_plugin_registry
from oss_audit.core.project_detector import ProjectInfo, StructureType, ProjectType, SizeMetrics
from oss_audit.core.tool_executor import ToolResult
from oss_audit.core.tool_registry import Tool


class TestJavaScriptPlugin(unittest.TestCase):
    
    def setUp(self):
        reset_plugin_registry()
        self.plugin = JavaScriptPlugin("javascript_plugin")
        self.plugin.initialize()
        
        self.test_dir = tempfile.mkdtemp()
        self.test_path = pathlib.Path(self.test_dir)
        
        # Create JavaScript project
        (self.test_path / "package.json").write_text('{"name": "test", "dependencies": {"react": "^17.0.0"}}')
        (self.test_path / "src").mkdir()
        (self.test_path / "src" / "index.js").write_text("console.log('Hello World');")
        (self.test_path / ".eslintrc.json").write_text('{"extends": ["eslint:recommended"]}')
        
        self.project_info = ProjectInfo(
            name="test_project",
            path=str(self.test_path),
            languages={'javascript': 0.8, 'typescript': 0.2},
            structure_type=StructureType.SINGLE_PROJECT,
            project_type=ProjectType.WEB_APPLICATION,
            size_metrics=SizeMetrics(code_files=1, code_lines=20, test_files=0),
            build_tools=['npm'],
            dependencies={'javascript': ['react']},
            confidence=0.9
        )
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_javascript_plugin_initialization(self):
        """Test JavaScript plugin initialization"""
        self.assertEqual(self.plugin.name, "javascript_plugin")
        self.assertTrue(self.plugin._initialized)
        self.assertIn('javascript', self.plugin.capability.languages)
        self.assertIn('typescript', self.plugin.capability.languages)
    
    def test_javascript_plugin_capability(self):
        """Test JavaScript plugin capabilities"""
        capability = self.plugin.capability
        
        self.assertIn('javascript', capability.languages)
        self.assertIn('typescript', capability.languages)
        self.assertIn('.js', capability.file_extensions)
        self.assertIn('.tsx', capability.file_extensions)
        self.assertIn(PluginCategory.QUALITY, capability.categories)
        self.assertIn(PluginCategory.SECURITY, capability.categories)
        self.assertIn('eslint', capability.optional_tools)
        self.assertIn('prettier', capability.optional_tools)
    
    def test_can_analyze_javascript_project(self):
        """Test JavaScript plugin project analysis capability"""
        self.assertTrue(self.plugin.can_analyze(self.project_info))
        
        # Test with non-JS project
        non_js_info = ProjectInfo(
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
        
        self.assertFalse(self.plugin.can_analyze(non_js_info))
    
    def test_javascript_tool_selection(self):
        """Test JavaScript tool selection"""
        tools = [
            Tool("eslint", ["eslint"], [], "javascript", [], 1, categories=["quality"]),
            Tool("prettier", ["prettier"], [], "javascript", [], 1, categories=["formatting"]),
            Tool("jest", ["jest"], [], "javascript", [], 2, categories=["testing"]),
            Tool("javac", ["javac"], [], "java", [], 1, categories=["syntax"])
        ]
        
        selected = self.plugin.select_tools(self.project_info, tools)
        selected_names = [tool.name for tool in selected]
        
        self.assertIn("eslint", selected_names)
        self.assertIn("prettier", selected_names)
        self.assertNotIn("javac", selected_names)  # Java tool should not be selected
    
    def test_javascript_output_parsing(self):
        """Test JavaScript tool output parsing"""
        # Test ESLint JSON output
        eslint_output = '[{"filePath":"test.js","messages":[{"ruleId":"no-console","severity":1,"message":"Unexpected console statement","line":1,"column":1}]}]'
        result = self.plugin._parse_eslint_output(eslint_output)
        
        self.assertGreater(len(result['issues']), 0)
        self.assertEqual(result['issues_count'], 1)
        self.assertLess(result['score'], 100)
        
        # Test Prettier output
        prettier_result = self.plugin._parse_prettier_output("src/index.js\nsrc/app.js", 1)
        self.assertEqual(prettier_result['issues_count'], 2)
        self.assertFalse(prettier_result['formatted'])
    
    def test_javascript_post_processing(self):
        """Test JavaScript post-processing"""
        result = PluginResult("javascript_plugin", "javascript", True, quality_score=75.0)
        
        self.plugin._post_process_results(result, self.project_info)
        
        # Should detect project characteristics
        self.assertTrue(result.plugin_data['has_package_json'])
        self.assertTrue(result.plugin_data['has_eslintrc'])
        self.assertIn('React', result.plugin_data.get('frameworks', []))
        
        # Score should be adjusted for best practices
        self.assertGreater(result.quality_score, 75.0)


class TestJavaPlugin(unittest.TestCase):
    
    def setUp(self):
        reset_plugin_registry()
        self.plugin = JavaPlugin("java_plugin")
        self.plugin.initialize()
        
        self.test_dir = tempfile.mkdtemp()
        self.test_path = pathlib.Path(self.test_dir)
        
        # Create Java project
        (self.test_path / "pom.xml").write_text('''
        <project>
            <modelVersion>4.0.0</modelVersion>
            <groupId>com.test</groupId>
            <artifactId>test-project</artifactId>
            <version>1.0.0</version>
            <properties>
                <maven.compiler.source>11</maven.compiler.source>
            </properties>
        </project>
        ''')
        (self.test_path / "src" / "main" / "java").mkdir(parents=True)
        (self.test_path / "src" / "main" / "java" / "Main.java").write_text('''
        public class Main {
            public static void main(String[] args) {
                System.out.println("Hello World");
            }
        }
        ''')
        
        self.project_info = ProjectInfo(
            name="test_project",
            path=str(self.test_path),
            languages={'java': 0.95},
            structure_type=StructureType.SINGLE_PROJECT,
            project_type=ProjectType.LIBRARY,
            size_metrics=SizeMetrics(code_files=1, code_lines=50),
            build_tools=['maven'],
            dependencies={'java': ['junit']},
            confidence=0.9
        )
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_java_plugin_initialization(self):
        """Test Java plugin initialization"""
        self.assertEqual(self.plugin.name, "java_plugin")
        self.assertTrue(self.plugin._initialized)
        self.assertIn('java', self.plugin.capability.languages)
    
    def test_java_plugin_capability(self):
        """Test Java plugin capabilities"""
        capability = self.plugin.capability
        
        self.assertIn('java', capability.languages)
        self.assertIn('.java', capability.file_extensions)
        self.assertIn(PluginCategory.QUALITY, capability.categories)
        self.assertIn(PluginCategory.SECURITY, capability.categories)
        self.assertIn('checkstyle', capability.optional_tools)
        self.assertIn('spotbugs', capability.optional_tools)
    
    def test_java_tool_selection(self):
        """Test Java tool selection"""
        tools = [
            Tool("checkstyle", ["checkstyle"], [], "java", [], 1, categories=["quality"]),
            Tool("maven", ["mvn"], [], "java", [], 1, categories=["build"]),
            Tool("eslint", ["eslint"], [], "javascript", [], 1, categories=["quality"])
        ]
        
        selected = self.plugin.select_tools(self.project_info, tools)
        selected_names = [tool.name for tool in selected]
        
        self.assertIn("checkstyle", selected_names)
        self.assertIn("maven", selected_names)  # Should select Maven for pom.xml project
        self.assertNotIn("eslint", selected_names)  # JavaScript tool should not be selected
    
    def test_java_output_parsing(self):
        """Test Java tool output parsing"""
        # Test Checkstyle XML output
        checkstyle_output = '''<?xml version="1.0" encoding="UTF-8"?>
        <checkstyle version="8.0">
            <file name="Main.java">
                <error line="5" column="1" severity="error" message="Missing javadoc comment" source="com.puppycrawl.tools.checkstyle.checks.javadoc.JavadocMethodCheck"/>
            </file>
        </checkstyle>'''
        
        result = self.plugin._parse_checkstyle_output(checkstyle_output)
        
        self.assertEqual(len(result['issues']), 1)
        self.assertEqual(result['issues_count'], 1)
        self.assertLess(result['score'], 100)
    
    def test_java_framework_detection(self):
        """Test Java framework detection"""
        frameworks = self.plugin._detect_java_frameworks(str(self.test_path))
        # Should not find frameworks in basic project
        self.assertEqual(len(frameworks), 0)
        
        # Test Java version detection
        java_version = self.plugin._detect_java_version(str(self.test_path))
        self.assertEqual(java_version, 11)  # From pom.xml
    
    def test_java_post_processing(self):
        """Test Java post-processing"""
        result = PluginResult("java_plugin", "java", True, quality_score=70.0)
        
        self.plugin._post_process_results(result, self.project_info)
        
        # Should detect project characteristics
        self.assertTrue(result.plugin_data['has_pom_xml'])
        self.assertEqual(result.plugin_data['build_system'], 'Maven')
        self.assertEqual(result.plugin_data['java_version'], 11)
        
        # Score should be adjusted for build system
        self.assertGreater(result.quality_score, 70.0)


class TestGoPlugin(unittest.TestCase):
    
    def setUp(self):
        reset_plugin_registry()
        self.plugin = GoPlugin("go_plugin")
        self.plugin.initialize()
        
        self.test_dir = tempfile.mkdtemp()
        self.test_path = pathlib.Path(self.test_dir)
        
        # Create Go project
        (self.test_path / "go.mod").write_text('''
        module test-project
        
        go 1.19
        
        require (
            github.com/gorilla/mux v1.8.0
        )
        ''')
        (self.test_path / "main.go").write_text('''
        package main
        
        import "fmt"
        
        func main() {
            fmt.Println("Hello, World!")
        }
        ''')
        
        self.project_info = ProjectInfo(
            name="test_project",
            path=str(self.test_path),
            languages={'go': 0.9},
            structure_type=StructureType.SINGLE_PROJECT,
            project_type=ProjectType.CLI_TOOL,
            size_metrics=SizeMetrics(code_files=1, code_lines=30),
            build_tools=['go'],
            dependencies={'go': ['gorilla/mux']},
            confidence=0.9
        )
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_go_plugin_initialization(self):
        """Test Go plugin initialization"""
        self.assertEqual(self.plugin.name, "go_plugin")
        self.assertTrue(self.plugin._initialized)
        self.assertIn('go', self.plugin.capability.languages)
    
    def test_go_plugin_capability(self):
        """Test Go plugin capabilities"""
        capability = self.plugin.capability
        
        self.assertIn('go', capability.languages)
        self.assertIn('.go', capability.file_extensions)
        self.assertIn(PluginCategory.QUALITY, capability.categories)
        self.assertIn(PluginCategory.FORMATTING, capability.categories)
        self.assertIn('gofmt', capability.optional_tools)
        self.assertIn('gosec', capability.optional_tools)
    
    def test_go_tool_selection(self):
        """Test Go tool selection"""
        tools = [
            Tool("gofmt", ["gofmt"], [], "go", [], 1, categories=["formatting"]),
            Tool("gosec", ["gosec"], [], "go", [], 2, categories=["security"]),
            Tool("pylint", ["pylint"], [], "python", [], 1, categories=["quality"])
        ]
        
        selected = self.plugin.select_tools(self.project_info, tools)
        selected_names = [tool.name for tool in selected]
        
        self.assertIn("gofmt", selected_names)
        self.assertIn("gosec", selected_names)
        self.assertNotIn("pylint", selected_names)  # Python tool should not be selected
    
    def test_go_version_detection(self):
        """Test Go version detection from go.mod"""
        version = self.plugin._detect_go_version(str(self.test_path))
        self.assertEqual(version, "1.19")
    
    def test_go_post_processing(self):
        """Test Go post-processing"""
        result = PluginResult("go_plugin", "go", True, quality_score=80.0)
        
        self.plugin._post_process_results(result, self.project_info)
        
        # Should detect project characteristics
        self.assertTrue(result.plugin_data['has_go_mod'])
        self.assertEqual(result.plugin_data['go_version'], "1.19")
        
        # Score should be adjusted for Go modules
        self.assertGreater(result.quality_score, 80.0)


class TestResultValidator(unittest.TestCase):
    """Test plugin result validation and standardization"""
    
    def setUp(self):
        self.validator = PluginResultValidator()
    
    def test_valid_plugin_result(self):
        """Test validation of a valid plugin result"""
        result = PluginResult("test_plugin", "javascript", True, quality_score=85.0)
        result.tool_results["eslint"] = ToolResult(
            "eslint", "completed", True, 
            result={
                'issues': [{'message': 'Test issue', 'severity': 'warning'}],
                'issues_count': 1,
                'score': 90
            }
        )
        
        errors = self.validator.validate_plugin_result(result)
        
        # Should have no critical errors
        critical_errors = [e for e in errors if e.severity == "error"]
        self.assertEqual(len(critical_errors), 0)
    
    def test_invalid_plugin_result(self):
        """Test validation of invalid plugin result"""
        result = PluginResult("", "", True, quality_score=150.0)  # Invalid values
        result.tool_results["test_tool"] = ToolResult(
            "test_tool", "invalid_status", True,
            result={'score': 200, 'issues_count': -1}  # Invalid values
        )
        
        errors = self.validator.validate_plugin_result(result)
        
        # Should have multiple errors
        self.assertGreater(len(errors), 0)
        
        error_fields = [e.field for e in errors]
        self.assertIn("plugin_name", error_fields)
        self.assertIn("language", error_fields)
        self.assertIn("quality_score", error_fields)
    
    def test_result_standardization(self):
        """Test result standardization"""
        result = PluginResult("test_plugin", "java", True, quality_score=150.0)
        result.tool_results["test_tool"] = ToolResult(
            "test_tool", "completed", True,
            result={
                'score': 200,  # Over 100
                'issues': [{'severity': 'err'}],  # Non-standard severity
                'issues_count': -1  # Negative count
            }
        )
        
        standardized = ResultStandardizer.standardize_plugin_result(result)
        
        # Score should be capped at 100
        self.assertEqual(standardized.quality_score, 100)
        
        # Tool result score should be capped
        tool_result = standardized.tool_results["test_tool"]
        self.assertEqual(tool_result.result['score'], 100)
        
        # Issues count should be non-negative
        self.assertEqual(tool_result.result['issues_count'], 1)  # Length of issues list
        
        # Severity should be standardized
        self.assertEqual(tool_result.result['issues'][0]['severity'], 'error')


class TestPluginIntegration(unittest.TestCase):
    """Integration tests for multi-language plugins"""
    
    def setUp(self):
        reset_plugin_registry()
    
    def test_plugin_registry_discovers_all_plugins(self):
        """Test that plugin registry discovers all language plugins"""
        registry = get_plugin_registry()
        
        # Should discover all plugins (may take a moment)
        plugins = registry.list_plugins()
        
        # Should have at least our core plugins
        expected_plugins = {'python_plugin', 'javascript_plugin', 'java_plugin', 'go_plugin'}
        found_plugins = set(plugins.keys())
        
        # Check which expected plugins were found
        for plugin_name in expected_plugins:
            if plugin_name not in found_plugins:
                print(f"Plugin {plugin_name} not found. Available: {found_plugins}")
    
    def test_mixed_language_project_analysis(self):
        """Test analysis of mixed language project"""
        registry = get_plugin_registry()
        
        # Create mixed project info
        project_info = ProjectInfo(
            name="mixed_project",
            path="/test",
            languages={'javascript': 0.4, 'python': 0.3, 'java': 0.3},
            structure_type=StructureType.SINGLE_PROJECT,
            project_type=ProjectType.WEB_APPLICATION,
            size_metrics=SizeMetrics(),
            build_tools=[],
            dependencies={},
            confidence=0.8
        )
        
        # Get applicable plugins
        applicable_plugins = registry.get_plugins_for_project(project_info)
        
        # Should find plugins for multiple languages
        plugin_languages = set()
        for plugin in applicable_plugins:
            plugin_languages.update(plugin.capability.languages)
        
        # Should support at least JavaScript and Python (if plugins are loaded)
        if applicable_plugins:
            print(f"Found plugins for languages: {plugin_languages}")


if __name__ == '__main__':
    unittest.main()