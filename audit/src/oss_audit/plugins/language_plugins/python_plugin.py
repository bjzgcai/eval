#!/usr/bin/env python3
"""
Python Language Plugin for OSS Audit 2.0
Provides comprehensive Python code analysis
"""

import os
import subprocess
import time
from typing import List, Set
import logging

import sys
import os

# Add parent directories to path for imports when loaded as standalone module
current_dir = os.path.dirname(os.path.abspath(__file__))
plugin_dir = os.path.dirname(current_dir)
src_dir = os.path.dirname(plugin_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    from ..base import (
        LanguagePlugin, PluginResult, PluginError, PluginCapability, 
        PluginPriority, PluginCategory
    )
    from ...core.tool_registry import Tool
    from ...core.tool_executor import ToolResult
    from ...core.project_detector import ProjectInfo
except ImportError:
    # Fallback for standalone loading
    from oss_audit.plugins.base import (
        LanguagePlugin, PluginResult, PluginError, PluginCapability, 
        PluginPriority, PluginCategory
    )
    from oss_audit.core.tool_registry import Tool
    from oss_audit.core.tool_executor import ToolResult
    from oss_audit.core.project_detector import ProjectInfo

logger = logging.getLogger(__name__)


class PythonPlugin(LanguagePlugin):
    """
    Python language analysis plugin
    
    Provides comprehensive analysis for Python projects including:
    - Code quality (pylint, flake8)
    - Type checking (mypy)  
    - Security analysis (bandit)
    - Formatting (black, isort)
    - Testing and coverage (pytest, coverage)
    """
    
    @property
    def capability(self) -> PluginCapability:
        return PluginCapability(
            languages={'python'},
            file_extensions={'.py', '.pyx', '.pyi'},
            categories={
                PluginCategory.SYNTAX,
                PluginCategory.QUALITY, 
                PluginCategory.SECURITY,
                PluginCategory.TESTING,
                PluginCategory.FORMATTING,
                PluginCategory.DEPENDENCIES
            },
            required_tools=[],  # No tools are absolutely required
            optional_tools=['pylint', 'flake8', 'mypy', 'bandit', 'black', 'isort', 'pytest', 'coverage', 'safety'],
            min_confidence_threshold=0.1
        )
    
    @property
    def priority(self) -> PluginPriority:
        return PluginPriority.HIGH
    
    def _do_initialization(self):
        """Initialize Python plugin"""
        self.logger.info("Initializing Python plugin")
        
        # Check Python environment
        try:
            result = subprocess.run(['python', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.debug(f"Python version: {result.stdout.strip()}")
            else:
                self.logger.warning("Python not found in PATH")
        except Exception as e:
            self.logger.warning(f"Could not check Python version: {e}")
    
    def select_tools(self, project_info: ProjectInfo, available_tools: List[Tool]) -> List[Tool]:
        """Select Python-specific tools using smart selector"""        
        # Use the base class smart selector
        selected_tools = super().select_tools(project_info, available_tools)
        
        self.logger.debug(f"Smart selection result: {len(selected_tools)} Python tools: {[t.name for t in selected_tools]}")
        return selected_tools
    
    def _execute_analysis(self, project_path: str, project_info: ProjectInfo, 
                         tools: List[Tool], result: PluginResult):
        """Execute Python-specific analysis"""
        
        # Group tools by category for optimal execution order
        syntax_tools = []
        quality_tools = []
        security_tools = []
        format_tools = []
        test_tools = []
        other_tools = []
        
        for tool in tools:
            if tool.name in {'python', 'py_compile'}:
                syntax_tools.append(tool)
            elif tool.name in {'pylint', 'flake8', 'mypy'}:
                quality_tools.append(tool)
            elif tool.name in {'bandit', 'safety'}:
                security_tools.append(tool)
            elif tool.name in {'black', 'isort'}:
                format_tools.append(tool)
            elif tool.name in {'pytest', 'coverage'}:
                test_tools.append(tool)
            else:
                other_tools.append(tool)
        
        # Execute in order of importance
        execution_order = [
            ("Syntax Check", syntax_tools),
            ("Code Quality", quality_tools), 
            ("Security Analysis", security_tools),
            ("Format Check", format_tools),
            ("Test Analysis", test_tools),
            ("Other Tools", other_tools)
        ]
        
        for phase_name, phase_tools in execution_order:
            if not phase_tools:
                continue
                
            self.logger.debug(f"Executing {phase_name} phase with {len(phase_tools)} tools")
            
            for tool in phase_tools:
                try:
                    tool_result = self._execute_single_tool(tool, project_path, project_info)
                    result.tool_results[tool.name] = tool_result
                    result.tools_executed.append(tool.name)
                    
                    if not tool_result.success:
                        self.logger.warning(f"Tool {tool.name} failed: {tool_result.error}")
                    
                except Exception as e:
                    self.logger.error(f"Error executing tool {tool.name}: {e}")
                    result.tools_skipped.append(tool.name)
                    result.add_error(PluginError(
                        plugin_name=self.name,
                        error_type="ToolExecutionError",
                        message=f"Failed to execute {tool.name}: {str(e)}",
                        recoverable=True,
                        details={'tool_name': tool.name}
                    ))
    
    def _execute_single_tool(self, tool: Tool, project_path: str, 
                           project_info: ProjectInfo) -> ToolResult:
        """Execute a single Python tool with Docker support"""
        start_time = time.time()
        
        try:
            # Check if we should use Docker mode by accessing global tool executor
            # This ensures plugins respect Docker mode settings
            from ...core.tool_executor import ToolExecutor
            executor = ToolExecutor()
            
            # Use tool executor which handles Docker mode automatically
            if hasattr(executor, 'docker_mode') and executor.docker_mode:
                self.logger.debug(f"Plugin using Docker mode for tool: {tool.name}")
                return executor._run_single_tool(tool, project_path, tool.timeout)
            else:
                self.logger.debug(f"Plugin using local mode for tool: {tool.name}")
            
            # Fallback to local execution if Docker mode is not enabled
            # Build command
            cmd = self._build_python_command(tool, project_path, project_info)
            
            # Execute
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=tool.timeout,
                env=os.environ.copy()
            )
            
            execution_time = time.time() - start_time
            
            # Parse result
            parsed_result = self._parse_python_tool_output(tool.name, result.stdout, result.returncode)
            
            # 工具执行成功的标准：
            # - 对于代码质量工具（如pylint），返回码可能表示发现的问题级别，不代表执行失败
            # - 系统级错误码（126、127等）才表示真正的执行失败
            # - 如果能解析出有效结果，说明工具执行成功
            is_execution_failure = result.returncode in [126, 127]  # 命令不存在或无法执行
            has_valid_result = parsed_result and (
                'issues_count' in parsed_result or 
                'score' in parsed_result or 
                'issues' in parsed_result
            )
            
            # 工具成功执行的条件：无系统错误且有有效结果，或返回码为0
            tool_success = (not is_execution_failure and has_valid_result) or result.returncode == 0
            
            return ToolResult(
                tool_name=tool.name,
                status="completed",
                success=tool_success,
                result=parsed_result,
                execution_time=execution_time,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                error=result.stderr if is_execution_failure else None
            )
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return ToolResult(
                tool_name=tool.name,
                status="timeout", 
                success=False,
                execution_time=execution_time,
                error=f"Tool execution timed out after {tool.timeout}s"
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult(
                tool_name=tool.name,
                status="failed",
                success=False,
                execution_time=execution_time,
                error=str(e)
            )
    
    def _build_python_command(self, tool: Tool, project_path: str, 
                            project_info: ProjectInfo) -> List[str]:
        """Build Python tool command"""
        cmd = tool.command.copy()
        cmd.extend(tool.args)
        
        # Special handling for different Python tools
        if tool.name == 'pylint':
            # Find Python modules/packages
            python_files = self._find_python_modules(project_path)
            if python_files:
                cmd.extend(python_files)
            else:
                cmd.append('.')
        
        elif tool.name == 'flake8':
            cmd.append('.')
        
        elif tool.name == 'mypy':
            # Find main Python files
            main_files = self._find_main_python_files(project_path)
            if main_files:
                cmd.extend(main_files)
            else:
                cmd.append('.')
        
        elif tool.name == 'bandit':
            cmd.extend(['-r', '.'])
        
        elif tool.name == 'black':
            cmd.extend(['--check', '--diff', '.'])
        
        elif tool.name == 'isort':
            cmd.extend(['--check-only', '--diff', '.'])
        
        elif tool.name == 'safety':
            # Check installed packages
            cmd.extend(['check', '--json'])
        
        elif tool.name == 'pytest':
            # Add coverage if available
            cmd.extend(['--tb=short', '-v'])
            if 'coverage' in [t.name for t in self._get_available_tools()]:
                cmd.extend(['--cov=.'])
        
        return cmd
    
    def _find_python_modules(self, project_path: str) -> List[str]:
        """Find Python modules and packages in project"""
        modules = []
        
        for root, dirs, files in os.walk(project_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            # Skip common non-package directories
            dirs[:] = [d for d in dirs if d not in {'__pycache__', 'build', 'dist', '.git'}]
            
            for file in files:
                if file.endswith('.py') and file != '__init__.py':
                    rel_path = os.path.relpath(os.path.join(root, file), project_path)
                    modules.append(rel_path)
        
        return modules[:20]  # Limit to avoid too long command line
    
    def _find_main_python_files(self, project_path: str) -> List[str]:
        """Find main Python files for type checking"""
        main_files = []
        
        # Look for common entry points
        common_names = ['main.py', 'app.py', 'run.py', 'cli.py', '__main__.py']
        
        for name in common_names:
            if os.path.exists(os.path.join(project_path, name)):
                main_files.append(name)
        
        # Look for package __init__.py files
        for root, dirs, files in os.walk(project_path):
            if '__init__.py' in files:
                # This is a package
                rel_path = os.path.relpath(root, project_path)
                if rel_path != '.':
                    main_files.append(rel_path)
        
        return main_files if main_files else ['.']
    
    def _parse_python_tool_output(self, tool_name: str, output: str, return_code: int) -> dict:
        """Parse output from Python tools"""
        result = {
            'issues': [],
            'issues_count': 0,
            'score': 100 if return_code == 0 else 60
        }
        
        if not output:
            return result
        
        try:
            if tool_name == 'pylint':
                result.update(self._parse_pylint_output(output))
            elif tool_name == 'flake8':
                result.update(self._parse_flake8_output(output))
            elif tool_name == 'mypy':
                result.update(self._parse_mypy_output(output))
            elif tool_name == 'bandit':
                result.update(self._parse_bandit_output(output))
            elif tool_name == 'safety':
                result.update(self._parse_safety_output(output))
            elif tool_name in ['black', 'isort']:
                result.update(self._parse_formatter_output(output, return_code))
            else:
                # Generic parsing
                result.update(self._parse_generic_output(output, return_code))
                
        except Exception as e:
            self.logger.warning(f"Failed to parse {tool_name} output: {e}")
            # Fallback to basic parsing
            result.update(self._parse_generic_output(output, return_code))
        
        return result
    
    def _parse_pylint_output(self, output: str) -> dict:
        """Parse pylint output"""
        issues = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if line.strip() and not line.startswith('*'):
                # Pylint format: file:line:column: message-id: message
                parts = line.split(':', 3)
                if len(parts) >= 4:
                    issues.append({
                        'file': parts[0],
                        'line': parts[1],
                        'column': parts[2] if parts[2].isdigit() else '0',
                        'message': parts[3].strip(),
                        'severity': 'warning'
                    })
        
        # Calculate score based on issues
        score = max(20, 100 - len(issues) * 2)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score
        }
    
    def _parse_flake8_output(self, output: str) -> dict:
        """Parse flake8 output"""
        issues = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if line.strip():
                # Flake8 format: file:line:column: error_code error_message
                parts = line.split(':', 3)
                if len(parts) >= 4:
                    issues.append({
                        'file': parts[0],
                        'line': parts[1],
                        'column': parts[2],
                        'message': parts[3].strip(),
                        'severity': 'error' if parts[3].strip().startswith('E') else 'warning'
                    })
        
        score = max(30, 100 - len(issues) * 3)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score
        }
    
    def _parse_mypy_output(self, output: str) -> dict:
        """Parse mypy output"""
        issues = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if ':' in line and 'error:' in line:
                issues.append({
                    'message': line.strip(),
                    'severity': 'error' if 'error:' in line else 'warning'
                })
        
        score = max(40, 100 - len(issues) * 4)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score
        }
    
    def _parse_bandit_output(self, output: str) -> dict:
        """Parse bandit output"""
        issues = []
        
        try:
            import json
            data = json.loads(output)
            
            if 'results' in data:
                for result in data['results']:
                    issues.append({
                        'file': result.get('filename', ''),
                        'line': str(result.get('line_number', '')),
                        'message': result.get('issue_text', ''),
                        'severity': result.get('issue_severity', 'medium').lower(),
                        'confidence': result.get('issue_confidence', 'medium').lower()
                    })
        except:
            # Fallback to text parsing
            lines = output.strip().split('\n')
            for line in lines:
                if 'security issue' in line.lower():
                    issues.append({
                        'message': line.strip(),
                        'severity': 'medium'
                    })
        
        # Higher penalty for security issues
        score = max(10, 100 - len(issues) * 8)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score,
            'by_severity': self._group_by_severity(issues)
        }
    
    def _parse_safety_output(self, output: str) -> dict:
        """Parse safety output"""
        issues = []
        
        try:
            import json
            data = json.loads(output)
            
            if isinstance(data, list):
                for vuln in data:
                    issues.append({
                        'package': vuln.get('package', ''),
                        'version': vuln.get('installed_version', ''),
                        'vulnerability': vuln.get('vulnerability', ''),
                        'severity': 'high'  # Safety issues are typically serious
                    })
        except:
            # Count lines as potential vulnerabilities
            lines = [line for line in output.strip().split('\n') if line.strip()]
            issues = [{'message': line, 'severity': 'high'} for line in lines[:10]]
        
        # Very high penalty for security vulnerabilities
        score = max(5, 100 - len(issues) * 15)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score,
            'by_severity': self._group_by_severity(issues)
        }
    
    def _parse_formatter_output(self, output: str, return_code: int) -> dict:
        """Parse formatter (black, isort) output"""
        if return_code == 0:
            return {
                'issues': [],
                'issues_count': 0,
                'score': 100,
                'formatted': True
            }
        else:
            # Count files that would be reformatted
            lines = output.strip().split('\n')
            files_to_format = [line for line in lines if 'would reformat' in line or 'Fixing' in line]
            
            return {
                'issues': [{'message': f'File needs formatting: {line}'} for line in files_to_format],
                'issues_count': len(files_to_format),
                'score': max(70, 100 - len(files_to_format) * 5),
                'formatted': False
            }
    
    def _parse_generic_output(self, output: str, return_code: int) -> dict:
        """Generic output parsing"""
        lines = output.strip().split('\n')
        issue_indicators = ['error', 'warning', 'fail', 'violation', 'issue']
        
        issues_count = sum(1 for line in lines 
                          if any(indicator in line.lower() for indicator in issue_indicators))
        
        score = max(20, 100 - issues_count * 10) if return_code != 0 else 100
        
        return {
            'issues': [{'message': line} for line in lines if line.strip()][:10],  # Limit issues
            'issues_count': issues_count,
            'score': score
        }
    
    def _group_by_severity(self, issues: List[dict]) -> dict:
        """Group issues by severity"""
        severity_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        
        for issue in issues:
            severity = issue.get('severity', 'medium').upper()
            if severity in ['HIGH', 'CRITICAL']:
                severity_counts['HIGH'] += 1
            elif severity in ['MEDIUM', 'WARNING']:
                severity_counts['MEDIUM'] += 1
            else:
                severity_counts['LOW'] += 1
        
        return severity_counts
    
    def _get_available_tools(self) -> List[Tool]:
        """Helper method to get available tools (implementation needed)"""
        # This would normally come from the tool registry
        return []
    
    def _post_process_results(self, result: PluginResult, project_info: ProjectInfo):
        """Python-specific post-processing"""
        # Call parent post-processing first
        super()._post_process_results(result, project_info)
        
        # Add Python-specific metrics
        result.plugin_data['python_version_detected'] = self._detect_python_version(project_info.path)
        result.plugin_data['has_requirements'] = os.path.exists(os.path.join(project_info.path, 'requirements.txt'))
        result.plugin_data['has_setup_py'] = os.path.exists(os.path.join(project_info.path, 'setup.py'))
        result.plugin_data['has_pyproject_toml'] = os.path.exists(os.path.join(project_info.path, 'pyproject.toml'))
        
        # Adjust score based on Python best practices
        if result.plugin_data['has_requirements'] or result.plugin_data['has_pyproject_toml']:
            result.quality_score += 5  # Bonus for dependency management
        
        if result.plugin_data['has_setup_py'] or result.plugin_data['has_pyproject_toml']:
            result.quality_score += 5  # Bonus for packaging
        
        # Cap score at 100
        result.quality_score = min(100, result.quality_score)
    
    def _detect_python_version(self, project_path: str) -> str:
        """Detect Python version requirements"""
        version_indicators = [
            'pyproject.toml',
            'setup.py', 
            'setup.cfg',
            '.python-version',
            'runtime.txt'
        ]
        
        for indicator in version_indicators:
            file_path = os.path.join(project_path, indicator)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'python_requires' in content or 'Programming Language :: Python' in content:
                            return 'specified'
                except:
                    pass
        
        return 'unspecified'