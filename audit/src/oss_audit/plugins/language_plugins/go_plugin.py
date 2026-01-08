#!/usr/bin/env python3
"""
Go Language Plugin for OSS Audit 2.0 (Basic Version)
Provides basic Go code analysis
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


class GoPlugin(LanguagePlugin):
    """
    Go language analysis plugin (Basic Version)
    
    Provides basic analysis for Go projects including:
    - Code quality (go vet, golint, staticcheck)
    - Formatting (gofmt, goimports)  
    - Security analysis (gosec)
    - Testing (go test)
    - Module management (go mod)
    """
    
    @property
    def capability(self) -> PluginCapability:
        return PluginCapability(
            languages={'go'},
            file_extensions={'.go', '.mod', '.sum'},
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
                'go', 'gofmt', 'goimports', 'golint', 'go-vet', 
                'staticcheck', 'gosec', 'golangci-lint'
            ],
            min_confidence_threshold=0.1
        )
    
    @property
    def priority(self) -> PluginPriority:
        return PluginPriority.MEDIUM  # Basic version has medium priority
    
    def _do_initialization(self):
        """Initialize Go plugin"""
        self.logger.info("Initializing Go plugin (Basic Version)")
        
        # Check Go environment
        try:
            result = subprocess.run(['go', 'version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                go_version = result.stdout.strip()
                self.logger.debug(f"Go version: {go_version}")
            else:
                self.logger.info("Go not found in PATH - Go analysis will be limited")
        except FileNotFoundError:
            self.logger.info("Go not installed - Go analysis will be limited to basic file checks")
        except Exception as e:
            self.logger.debug(f"Go environment check failed: {e}")
    
    def select_tools(self, project_info: ProjectInfo, available_tools: List[Tool]) -> List[Tool]:
        """Select Go-specific tools using smart selector"""
        # Use the base class smart selector
        selected_tools = super().select_tools(project_info, available_tools)
        
        self.logger.debug(f"Smart selection result: {len(selected_tools)} Go tools: {[t.name for t in selected_tools]}")
        return selected_tools
    
    def _execute_analysis(self, project_path: str, project_info: ProjectInfo, 
                         tools: List[Tool], result: PluginResult):
        """Execute Go-specific analysis"""
        
        # Group tools by category
        build_tools = []
        format_tools = []
        quality_tools = []
        security_tools = []
        test_tools = []
        other_tools = []
        
        for tool in tools:
            if tool.name in {'go'}:
                build_tools.append(tool)
            elif tool.name in {'gofmt', 'goimports'}:
                format_tools.append(tool)
            elif tool.name in {'go-vet', 'golint', 'staticcheck', 'golangci-lint'}:
                quality_tools.append(tool)
            elif tool.name in {'gosec'}:
                security_tools.append(tool)
            elif 'test' in tool.name:
                test_tools.append(tool)
            else:
                other_tools.append(tool)
        
        # Execute in order of importance
        execution_order = [
            ("Build Check", build_tools),
            ("Format Check", format_tools),
            ("Code Quality", quality_tools),
            ("Security Analysis", security_tools),
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
        """Execute a single Go tool"""
        start_time = time.time()
        
        # Check if Docker mode is available and prioritized
        try:
            from ...core.tool_executor import ToolExecutor
            executor = ToolExecutor()
            
            # Use Docker mode if available and prioritized
            if hasattr(executor, 'docker_mode') and executor.docker_mode:
                self.logger.debug(f"Plugin using Docker mode for tool: {tool.name}")
                return executor._run_single_tool(tool, project_path, tool.timeout)
                
        except Exception as e:
            self.logger.debug(f"Could not use Docker mode: {e}")
        
        # Fallback to local execution
        try:
            # Build command
            cmd = self._build_go_command(tool, project_path, project_info)
            
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
            parsed_result = self._parse_go_tool_output(tool.name, result.stdout, result.returncode, result.stderr)
            
            return ToolResult(
                tool_name=tool.name,
                status="completed",
                success=result.returncode == 0,
                result=parsed_result,
                execution_time=execution_time,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                error=result.stderr if result.returncode != 0 else None
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
    
    def _build_go_command(self, tool: Tool, project_path: str, 
                         project_info: ProjectInfo) -> List[str]:
        """Build Go tool command"""
        cmd = tool.command.copy()
        cmd.extend(tool.args)
        
        # Special handling for different Go tools
        if tool.name == 'go':
            # Basic build check
            cmd.extend(['build', './...'])
        
        elif tool.name == 'gofmt':
            cmd.extend(['-l', '-d', '.'])
        
        elif tool.name == 'goimports':
            cmd.extend(['-l', '-d', '.'])
        
        elif tool.name == 'go-vet':
            cmd.extend(['vet', './...'])
        
        elif tool.name == 'golint':
            cmd.extend(['./...'])
        
        elif tool.name == 'staticcheck':
            cmd.extend(['./...'])
        
        elif tool.name == 'gosec':
            cmd.extend(['-fmt', 'json', './...'])
        
        elif tool.name == 'golangci-lint':
            cmd.extend(['run', '--out-format', 'json'])
        
        return cmd
    
    def _parse_go_tool_output(self, tool_name: str, output: str, return_code: int, stderr: str = "") -> dict:
        """Parse output from Go tools"""
        result = {
            'issues': [],
            'issues_count': 0,
            'score': 100 if return_code == 0 else 70
        }
        
        if not output and not stderr:
            return result
        
        full_output = output + "\n" + stderr if stderr else output
        
        try:
            if tool_name == 'gofmt':
                result.update(self._parse_gofmt_output(full_output, return_code))
            elif tool.name == 'goimports':
                result.update(self._parse_goimports_output(full_output, return_code))
            elif tool_name == 'go-vet':
                result.update(self._parse_go_vet_output(full_output))
            elif tool_name == 'golint':
                result.update(self._parse_golint_output(full_output))
            elif tool_name == 'staticcheck':
                result.update(self._parse_staticcheck_output(full_output))
            elif tool_name == 'gosec':
                result.update(self._parse_gosec_output(full_output))
            elif tool_name == 'go':
                result.update(self._parse_go_build_output(full_output, return_code))
            else:
                # Generic parsing
                result.update(self._parse_generic_go_output(full_output, return_code))
                
        except Exception as e:
            self.logger.warning(f"Failed to parse {tool_name} output: {e}")
            # Fallback to basic parsing
            result.update(self._parse_generic_go_output(full_output, return_code))
        
        return result
    
    def _parse_gofmt_output(self, output: str, return_code: int) -> dict:
        """Parse gofmt output"""
        if return_code == 0 and not output.strip():
            return {
                'issues': [],
                'issues_count': 0,
                'score': 100,
                'formatted': True
            }
        else:
            # Files that need formatting
            lines = [line for line in output.strip().split('\n') if line.strip()]
            
            return {
                'issues': [{'message': f'File needs formatting: {line}'} for line in lines],
                'issues_count': len(lines),
                'score': max(75, 100 - len(lines) * 3),
                'formatted': False
            }
    
    def _parse_goimports_output(self, output: str, return_code: int) -> dict:
        """Parse goimports output"""
        return self._parse_gofmt_output(output, return_code)  # Same format as gofmt
    
    def _parse_go_vet_output(self, output: str) -> dict:
        """Parse go vet output"""
        issues = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if line.strip() and ':' in line:
                issues.append({
                    'message': line.strip(),
                    'severity': 'warning'
                })
        
        score = max(40, 100 - len(issues) * 8)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score
        }
    
    def _parse_golint_output(self, output: str) -> dict:
        """Parse golint output"""
        issues = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if line.strip():
                issues.append({
                    'message': line.strip(),
                    'severity': 'suggestion'
                })
        
        score = max(60, 100 - len(issues) * 2)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score
        }
    
    def _parse_staticcheck_output(self, output: str) -> dict:
        """Parse staticcheck output"""
        issues = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if line.strip() and ':' in line:
                issues.append({
                    'message': line.strip(),
                    'severity': 'warning'
                })
        
        score = max(50, 100 - len(issues) * 5)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score
        }
    
    def _parse_gosec_output(self, output: str) -> dict:
        """Parse gosec output"""
        issues = []
        
        try:
            import json
            gosec_data = json.loads(output)
            
            for issue in gosec_data.get('Issues', []):
                issues.append({
                    'file': issue.get('file', ''),
                    'line': issue.get('line', ''),
                    'rule_id': issue.get('rule_id', ''),
                    'details': issue.get('details', ''),
                    'severity': issue.get('severity', 'medium').lower(),
                    'confidence': issue.get('confidence', 'medium').lower()
                })
                
        except (json.JSONDecodeError, Exception):
            # Fallback to simple parsing
            lines = output.strip().split('\n')
            for line in lines:
                if 'issue' in line.lower() or 'vulnerability' in line.lower():
                    issues.append({
                        'message': line.strip(),
                        'severity': 'medium'
                    })
        
        # High penalty for security issues
        score = max(20, 100 - len(issues) * 10)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score,
            'by_severity': self._group_by_severity(issues)
        }
    
    def _parse_go_build_output(self, output: str, return_code: int) -> dict:
        """Parse go build output"""
        issues = []
        
        if return_code != 0:
            lines = output.strip().split('\n')
            for line in lines:
                if line.strip() and any(indicator in line.lower() for indicator in ['error', 'fail']):
                    issues.append({
                        'message': line.strip(),
                        'severity': 'error'
                    })
        
        score = 100 if return_code == 0 else max(30, 100 - len(issues) * 15)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score,
            'build_success': return_code == 0
        }
    
    def _parse_generic_go_output(self, output: str, return_code: int) -> dict:
        """Generic Go tool output parsing"""
        lines = output.strip().split('\n')
        issue_indicators = ['error', 'warning', 'fail', 'issue']
        
        issues_count = sum(1 for line in lines 
                          if any(indicator in line.lower() for indicator in issue_indicators))
        
        score = max(50, 100 - issues_count * 5) if return_code != 0 else 100
        
        return {
            'issues': [{'message': line} for line in lines if line.strip()][:10],
            'issues_count': issues_count,
            'score': score
        }
    
    def _group_by_severity(self, issues: List[dict]) -> dict:
        """Group issues by severity"""
        severity_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        
        for issue in issues:
            severity = issue.get('severity', 'medium').upper()
            if severity in ['HIGH', 'CRITICAL', 'ERROR']:
                severity_counts['HIGH'] += 1
            elif severity in ['MEDIUM', 'WARNING', 'WARN']:
                severity_counts['MEDIUM'] += 1
            else:
                severity_counts['LOW'] += 1
        
        return severity_counts
    
    def _post_process_results(self, result: PluginResult, project_info: ProjectInfo):
        """Go-specific post-processing"""
        # Call parent post-processing first
        super()._post_process_results(result, project_info)
        
        # Add Go-specific metrics
        result.plugin_data['has_go_mod'] = os.path.exists(os.path.join(project_info.path, 'go.mod'))
        result.plugin_data['has_go_sum'] = os.path.exists(os.path.join(project_info.path, 'go.sum'))
        result.plugin_data['go_version'] = self._detect_go_version(project_info.path)
        
        # Check for common Go project structures
        result.plugin_data['has_cmd_dir'] = os.path.exists(os.path.join(project_info.path, 'cmd'))
        result.plugin_data['has_internal_dir'] = os.path.exists(os.path.join(project_info.path, 'internal'))
        result.plugin_data['has_pkg_dir'] = os.path.exists(os.path.join(project_info.path, 'pkg'))
        
        # Adjust score based on Go best practices
        if result.plugin_data['has_go_mod']:
            result.quality_score += 10  # Bonus for Go modules
        
        if result.plugin_data['has_go_sum']:
            result.quality_score += 5   # Bonus for dependency locking
        
        if result.plugin_data['has_internal_dir']:
            result.quality_score += 5   # Bonus for proper package organization
        
        # Cap score at 100
        result.quality_score = min(100, result.quality_score)
    
    def _detect_go_version(self, project_path: str) -> str:
        """Detect Go version from go.mod"""
        go_mod_path = os.path.join(project_path, 'go.mod')
        if os.path.exists(go_mod_path):
            try:
                with open(go_mod_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    import re
                    version_match = re.search(r'go\s+(\d+\.\d+)', content)
                    if version_match:
                        return version_match.group(1)
                        
            except Exception as e:
                self.logger.debug(f"Could not read go.mod: {e}")
        
        return "unknown"