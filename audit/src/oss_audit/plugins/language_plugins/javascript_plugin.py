#!/usr/bin/env python3
"""
JavaScript/TypeScript Language Plugin for OSS Audit 2.0
Provides comprehensive JavaScript and TypeScript code analysis
"""

import os
import subprocess
import time
import json
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


class JavaScriptPlugin(LanguagePlugin):
    """
    JavaScript/TypeScript language analysis plugin
    
    Provides comprehensive analysis for JavaScript/TypeScript projects including:
    - Code quality (eslint, jshint)
    - Type checking (tsc for TypeScript)
    - Security analysis (njsscan, retire.js)
    - Formatting (prettier)
    - Testing (jest, mocha)
    - Package security (npm audit, yarn audit)
    """
    
    @property
    def capability(self) -> PluginCapability:
        return PluginCapability(
            languages={'javascript', 'typescript'},
            file_extensions={'.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'},
            categories={
                PluginCategory.SYNTAX,
                PluginCategory.QUALITY,
                PluginCategory.SECURITY,
                PluginCategory.TESTING,
                PluginCategory.FORMATTING,
                PluginCategory.DEPENDENCIES
            },
            required_tools=[],  # No tools are absolutely required
            optional_tools=[
                'eslint', 'prettier', 'tsc', 'jest', 'mocha', 'npm', 'yarn',
                'jshint', 'retire', 'njsscan'
            ],
            min_confidence_threshold=0.1
        )
    
    @property
    def priority(self) -> PluginPriority:
        return PluginPriority.HIGH
    
    def _do_initialization(self):
        """Initialize JavaScript plugin"""
        self.logger.info("Initializing JavaScript/TypeScript plugin")
        
        # Check Node.js environment
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.debug(f"Node.js version: {result.stdout.strip()}")
            else:
                self.logger.warning("Node.js not found in PATH")
        except Exception as e:
            self.logger.warning(f"Could not check Node.js version: {e}")
        
        # Check npm
        try:
            result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.debug(f"npm version: {result.stdout.strip()}")
        except Exception as e:
            self.logger.debug(f"npm not available: {e}")
    
    def select_tools(self, project_info: ProjectInfo, available_tools: List[Tool]) -> List[Tool]:
        """Select JavaScript/TypeScript-specific tools using smart selector"""
        # Use the base class smart selector
        selected_tools = super().select_tools(project_info, available_tools)
        
        self.logger.debug(f"Smart selection result: {len(selected_tools)} JavaScript/TypeScript tools: {[t.name for t in selected_tools]}")
        return selected_tools
    
    def _execute_analysis(self, project_path: str, project_info: ProjectInfo, 
                         tools: List[Tool], result: PluginResult):
        """Execute JavaScript/TypeScript-specific analysis"""
        
        # Group tools by category for optimal execution order
        syntax_tools = []
        quality_tools = []
        security_tools = []
        format_tools = []
        test_tools = []
        dependency_tools = []
        other_tools = []
        
        for tool in tools:
            if tool.name in {'node', 'tsc'}:
                syntax_tools.append(tool)
            elif tool.name in {'eslint', 'jshint'}:
                quality_tools.append(tool)
            elif tool.name in {'retire', 'njsscan'}:
                security_tools.append(tool)
            elif tool.name in {'prettier'}:
                format_tools.append(tool)
            elif tool.name in {'jest', 'mocha', 'karma', 'cypress'}:
                test_tools.append(tool)
            elif tool.name in {'npm-audit', 'yarn-audit', 'npm', 'yarn'}:
                dependency_tools.append(tool)
            else:
                other_tools.append(tool)
        
        # Execute in order of importance
        execution_order = [
            ("Syntax Check", syntax_tools),
            ("Dependency Check", dependency_tools),
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
        """Execute a single JavaScript/TypeScript tool with Docker support"""
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
            cmd = self._build_js_command(tool, project_path, project_info)
            
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
            parsed_result = self._parse_js_tool_output(tool.name, result.stdout, result.returncode)
            
            # 工具执行成功的标准：
            # - 对于代码质量工具（如eslint、tslint），返回码可能表示发现的问题级别
            # - 系统级错误码（126、127等）才表示真正的执行失败
            # - 如果能解析出有效结果，说明工具执行成功
            is_execution_failure = result.returncode in [126, 127]  # 命令不存在或无法执行
            has_valid_result = parsed_result and (
                'issues_count' in parsed_result or 
                'score' in parsed_result or 
                'issues' in parsed_result
            )
            
            # 工具成功执行的条件：无系统错误且有有效结果，或返回码为0，或是审计工具
            tool_success = (not is_execution_failure and has_valid_result) or \
                         result.returncode == 0 or \
                         tool.name in ['npm-audit', 'yarn-audit']
            
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
    
    def _build_js_command(self, tool: Tool, project_path: str, 
                         project_info: ProjectInfo) -> List[str]:
        """Build JavaScript/TypeScript tool command"""
        cmd = tool.command.copy()
        cmd.extend(tool.args)
        
        # Special handling for different JavaScript tools
        if tool.name == 'eslint':
            # Find JavaScript/TypeScript files
            js_files = self._find_js_files(project_path)
            if js_files:
                cmd.extend(js_files[:20])  # Limit to avoid too long command line
            else:
                cmd.append('.')
        
        elif tool.name == 'prettier':
            cmd.extend(['--check', '--list-different', '.'])
        
        elif tool.name == 'tsc':
            # TypeScript compilation check
            cmd.extend(['--noEmit', '--skipLibCheck'])
        
        elif tool.name == 'jshint':
            cmd.append('.')
        
        elif tool.name == 'npm-audit':
            cmd.extend(['audit', '--json'])
        
        elif tool.name == 'yarn-audit':
            cmd.extend(['audit', '--json'])
        
        elif tool.name == 'jest':
            cmd.extend(['--passWithNoTests', '--verbose'])
        
        elif tool.name == 'mocha':
            cmd.extend(['test/', '--reporter', 'json'])
        
        elif tool.name == 'retire':
            cmd.extend(['--js', '--node', '--json'])
        
        return cmd
    
    def _find_js_files(self, project_path: str) -> List[str]:
        """Find JavaScript and TypeScript files in project"""
        js_files = []
        extensions = ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs']
        
        for root, dirs, files in os.walk(project_path):
            # Skip common directories
            dirs[:] = [d for d in dirs if d not in {
                'node_modules', '.git', 'dist', 'build', '.next', 'coverage'
            }]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    rel_path = os.path.relpath(os.path.join(root, file), project_path)
                    js_files.append(rel_path)
        
        return js_files[:30]  # Limit to avoid command line length issues
    
    def _parse_js_tool_output(self, tool_name: str, output: str, return_code: int) -> dict:
        """Parse output from JavaScript/TypeScript tools"""
        result = {
            'issues': [],
            'issues_count': 0,
            'score': 100 if return_code == 0 else 60
        }
        
        if not output:
            return result
        
        try:
            if tool_name == 'eslint':
                result.update(self._parse_eslint_output(output))
            elif tool_name == 'prettier':
                result.update(self._parse_prettier_output(output, return_code))
            elif tool_name == 'tsc':
                result.update(self._parse_tsc_output(output))
            elif tool_name == 'jshint':
                result.update(self._parse_jshint_output(output))
            elif tool_name in ['npm-audit', 'yarn-audit']:
                result.update(self._parse_audit_output(output))
            elif tool_name == 'jest':
                result.update(self._parse_jest_output(output))
            elif tool_name == 'retire':
                result.update(self._parse_retire_output(output))
            else:
                # Generic parsing
                result.update(self._parse_generic_js_output(output, return_code))
                
        except Exception as e:
            self.logger.warning(f"Failed to parse {tool_name} output: {e}")
            # Fallback to basic parsing
            result.update(self._parse_generic_js_output(output, return_code))
        
        return result
    
    def _parse_eslint_output(self, output: str) -> dict:
        """Parse ESLint output"""
        issues = []
        
        try:
            # Try to parse as JSON
            eslint_data = json.loads(output)
            for file_data in eslint_data:
                file_path = file_data.get('filePath', '')
                for message in file_data.get('messages', []):
                    issues.append({
                        'file': file_path,
                        'line': message.get('line', 0),
                        'column': message.get('column', 0),
                        'message': message.get('message', ''),
                        'rule': message.get('ruleId', ''),
                        'severity': 'error' if message.get('severity', 1) == 2 else 'warning'
                    })
        except json.JSONDecodeError:
            # Fallback to text parsing
            lines = output.strip().split('\n')
            for line in lines:
                if ':' in line and ('error' in line or 'warning' in line):
                    issues.append({
                        'message': line.strip(),
                        'severity': 'error' if 'error' in line else 'warning'
                    })
        
        score = max(20, 100 - len(issues) * 3)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score
        }
    
    def _parse_prettier_output(self, output: str, return_code: int) -> dict:
        """Parse Prettier output"""
        if return_code == 0:
            return {
                'issues': [],
                'issues_count': 0,
                'score': 100,
                'formatted': True
            }
        else:
            files_to_format = output.strip().split('\n') if output.strip() else []
            files_to_format = [f for f in files_to_format if f.strip()]
            
            return {
                'issues': [{'message': f'File needs formatting: {f}'} for f in files_to_format],
                'issues_count': len(files_to_format),
                'score': max(70, 100 - len(files_to_format) * 5),
                'formatted': False
            }
    
    def _parse_tsc_output(self, output: str) -> dict:
        """Parse TypeScript compiler output"""
        issues = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if 'error TS' in line:
                issues.append({
                    'message': line.strip(),
                    'severity': 'error'
                })
        
        score = max(30, 100 - len(issues) * 5)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score
        }
    
    def _parse_jshint_output(self, output: str) -> dict:
        """Parse JSHint output"""
        issues = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if line.strip() and 'line' in line and 'character' in line:
                issues.append({
                    'message': line.strip(),
                    'severity': 'warning'
                })
        
        score = max(40, 100 - len(issues) * 4)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score
        }
    
    def _parse_audit_output(self, output: str) -> dict:
        """Parse npm/yarn audit output"""
        issues = []
        vulnerabilities = 0
        
        try:
            audit_data = json.loads(output)
            
            if 'vulnerabilities' in audit_data:
                vulnerabilities = audit_data['vulnerabilities']
            elif 'advisories' in audit_data:
                vulnerabilities = len(audit_data['advisories'])
            
            if vulnerabilities > 0:
                issues.append({
                    'message': f'Found {vulnerabilities} security vulnerabilities',
                    'severity': 'high'
                })
                
        except json.JSONDecodeError:
            # Count lines mentioning vulnerabilities
            lines = output.strip().split('\n')
            for line in lines:
                if 'vulnerabilit' in line.lower():
                    issues.append({
                        'message': line.strip(),
                        'severity': 'high'
                    })
                    vulnerabilities += 1
        
        # High penalty for security vulnerabilities
        score = max(10, 100 - vulnerabilities * 10)
        
        return {
            'issues': issues,
            'issues_count': vulnerabilities,
            'score': score,
            'vulnerabilities': vulnerabilities
        }
    
    def _parse_jest_output(self, output: str) -> dict:
        """Parse Jest test output"""
        issues = []
        
        try:
            # Try to find test results
            if 'Tests:' in output:
                # Extract test summary
                lines = output.split('\n')
                for line in lines:
                    if 'failed' in line.lower() or 'error' in line.lower():
                        issues.append({
                            'message': line.strip(),
                            'severity': 'error'
                        })
        except:
            pass
        
        # Check for test failures
        failed_tests = len([i for i in issues if 'failed' in i.get('message', '').lower()])
        score = max(50, 100 - failed_tests * 20)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score
        }
    
    def _parse_retire_output(self, output: str) -> dict:
        """Parse retire.js output"""
        issues = []
        
        try:
            retire_data = json.loads(output)
            for result in retire_data:
                if 'results' in result:
                    for vuln in result['results']:
                        issues.append({
                            'file': result.get('file', ''),
                            'component': vuln.get('component', ''),
                            'version': vuln.get('version', ''),
                            'vulnerabilities': len(vuln.get('vulnerabilities', [])),
                            'severity': 'high'
                        })
        except:
            # Fallback text parsing
            lines = output.strip().split('\n')
            for line in lines:
                if 'vulnerability' in line.lower() or 'cve' in line.lower():
                    issues.append({
                        'message': line.strip(),
                        'severity': 'high'
                    })
        
        score = max(20, 100 - len(issues) * 15)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score
        }
    
    def _parse_generic_js_output(self, output: str, return_code: int) -> dict:
        """Generic JavaScript tool output parsing"""
        lines = output.strip().split('\n')
        issue_indicators = ['error', 'warning', 'fail', 'issue', 'violation', 'problem']
        
        issues_count = sum(1 for line in lines 
                          if any(indicator in line.lower() for indicator in issue_indicators))
        
        score = max(30, 100 - issues_count * 8) if return_code != 0 else 100
        
        return {
            'issues': [{'message': line} for line in lines if line.strip()][:10],
            'issues_count': issues_count,
            'score': score
        }
    
    def _post_process_results(self, result: PluginResult, project_info: ProjectInfo):
        """JavaScript/TypeScript-specific post-processing"""
        # Call parent post-processing first
        super()._post_process_results(result, project_info)
        
        # Add JavaScript/TypeScript-specific metrics
        result.plugin_data['has_package_json'] = os.path.exists(os.path.join(project_info.path, 'package.json'))
        result.plugin_data['has_tsconfig'] = os.path.exists(os.path.join(project_info.path, 'tsconfig.json'))
        result.plugin_data['has_eslintrc'] = any(
            os.path.exists(os.path.join(project_info.path, f))
            for f in ['.eslintrc', '.eslintrc.js', '.eslintrc.json', '.eslintrc.yml']
        )
        result.plugin_data['has_prettierrc'] = any(
            os.path.exists(os.path.join(project_info.path, f))
            for f in ['.prettierrc', '.prettierrc.js', '.prettierrc.json', 'prettier.config.js']
        )
        
        # Check for common frameworks
        if result.plugin_data['has_package_json']:
            try:
                with open(os.path.join(project_info.path, 'package.json'), 'r', encoding='utf-8') as f:
                    package_data = json.loads(f.read())
                    dependencies = package_data.get('dependencies', {})
                    dev_dependencies = package_data.get('devDependencies', {})
                    all_deps = {**dependencies, **dev_dependencies}
                    
                    # Detect frameworks
                    frameworks = []
                    if 'react' in all_deps:
                        frameworks.append('React')
                    if 'vue' in all_deps:
                        frameworks.append('Vue')
                    if 'angular' in all_deps or '@angular/core' in all_deps:
                        frameworks.append('Angular')
                    if 'express' in all_deps:
                        frameworks.append('Express')
                    if 'next' in all_deps:
                        frameworks.append('Next.js')
                    
                    result.plugin_data['frameworks'] = frameworks
                    
            except Exception as e:
                self.logger.debug(f"Could not read package.json: {e}")
                result.plugin_data['frameworks'] = []
        
        # Adjust score based on best practices
        if result.plugin_data['has_package_json']:
            result.quality_score += 5  # Bonus for proper package management
        
        if result.plugin_data['has_eslintrc']:
            result.quality_score += 5  # Bonus for linting configuration
        
        if result.plugin_data['has_prettierrc']:
            result.quality_score += 3  # Bonus for formatting configuration
        
        if result.plugin_data['has_tsconfig']:
            result.quality_score += 7  # Bonus for TypeScript configuration
        
        # Cap score at 100
        result.quality_score = min(100, result.quality_score)