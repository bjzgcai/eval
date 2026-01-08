#!/usr/bin/env python3
"""
Java Language Plugin for OSS Audit 2.0
Provides comprehensive Java code analysis
"""

import os
import subprocess
import time
import xml.etree.ElementTree as ET
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


class JavaPlugin(LanguagePlugin):
    """
    Java language analysis plugin
    
    Provides comprehensive analysis for Java projects including:
    - Code quality (checkstyle, PMD, SpotBugs)
    - Security analysis (SpotBugs security rules, find-sec-bugs)
    - Build analysis (Maven, Gradle)
    - Testing (JUnit, TestNG)
    - Dependency analysis (OWASP Dependency Check)
    """
    
    @property
    def capability(self) -> PluginCapability:
        return PluginCapability(
            languages={'java'},
            file_extensions={'.java', '.jar', '.class'},
            categories={
                PluginCategory.SYNTAX,
                PluginCategory.QUALITY,
                PluginCategory.SECURITY,
                PluginCategory.TESTING,
                PluginCategory.DEPENDENCIES
            },
            required_tools=[],  # No tools are absolutely required
            optional_tools=[
                'javac', 'checkstyle', 'pmd', 'spotbugs', 'maven', 'gradle',
                'junit', 'dependency-check', 'find-sec-bugs'
            ],
            min_confidence_threshold=0.1
        )
    
    @property
    def priority(self) -> PluginPriority:
        return PluginPriority.HIGH
    
    def _do_initialization(self):
        """Initialize Java plugin"""
        self.logger.info("Initializing Java plugin")
        
        # Check Java environment
        try:
            result = subprocess.run(['java', '-version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                java_version = result.stderr.split('\n')[0] if result.stderr else result.stdout.split('\n')[0]
                self.logger.debug(f"Java version: {java_version}")
            else:
                self.logger.info("Java not found in PATH - Java analysis will be limited")
        except FileNotFoundError:
            self.logger.info("Java not installed - Java analysis will be limited to basic file checks")
        except Exception as e:
            self.logger.debug(f"Java environment check failed: {e}")
        
        # Check Maven
        try:
            result = subprocess.run(['mvn', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                mvn_version = result.stdout.split('\n')[0] if result.stdout else ""
                self.logger.debug(f"Maven: {mvn_version}")
        except Exception as e:
            self.logger.debug(f"Maven not available: {e}")
        
        # Check Gradle
        try:
            result = subprocess.run(['gradle', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.debug("Gradle available")
        except Exception as e:
            self.logger.debug(f"Gradle not available: {e}")
    
    def select_tools(self, project_info: ProjectInfo, available_tools: List[Tool]) -> List[Tool]:
        """Select Java-specific tools using smart selector"""
        # Use the base class smart selector
        selected_tools = super().select_tools(project_info, available_tools)
        
        self.logger.debug(f"Smart selection result: {len(selected_tools)} Java tools: {[t.name for t in selected_tools]}")
        return selected_tools
    
    def _execute_analysis(self, project_path: str, project_info: ProjectInfo, 
                         tools: List[Tool], result: PluginResult):
        """Execute Java-specific analysis"""
        
        # Group tools by category for optimal execution order
        build_tools = []
        quality_tools = []
        security_tools = []
        test_tools = []
        dependency_tools = []
        other_tools = []
        
        for tool in tools:
            if tool.name in {'maven', 'gradle'}:
                build_tools.append(tool)
            elif tool.name in {'checkstyle', 'pmd', 'spotbugs'}:
                quality_tools.append(tool)
            elif tool.name in {'find-sec-bugs'}:
                security_tools.append(tool)
            elif tool.name in {'junit', 'testng'}:
                test_tools.append(tool)
            elif tool.name in {'dependency-check'}:
                dependency_tools.append(tool)
            else:
                other_tools.append(tool)
        
        # Execute in order of importance
        execution_order = [
            ("Build Check", build_tools),
            ("Code Quality", quality_tools),
            ("Security Analysis", security_tools),
            ("Dependency Check", dependency_tools),
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
        """Execute a single Java tool"""
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
            cmd = self._build_java_command(tool, project_path, project_info)
            
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
            parsed_result = self._parse_java_tool_output(tool.name, result.stdout, result.returncode, result.stderr)
            
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
    
    def _build_java_command(self, tool: Tool, project_path: str, 
                          project_info: ProjectInfo) -> List[str]:
        """Build Java tool command"""
        cmd = tool.command.copy()
        cmd.extend(tool.args)
        
        # Special handling for different Java tools
        if tool.name == 'checkstyle':
            # Find Java files
            java_files = self._find_java_files(project_path)
            if java_files:
                cmd.extend(java_files[:50])  # Limit to avoid command line length issues
            else:
                cmd.append('src/')
        
        elif tool.name == 'pmd':
            cmd.extend(['-d', 'src/', '-R', 'rulesets/java/quickstart.xml', '-f', 'xml'])
        
        elif tool.name == 'spotbugs':
            # SpotBugs typically works with compiled classes
            if os.path.exists(os.path.join(project_path, 'target/classes')):
                cmd.extend(['-xml', 'target/classes/'])
            elif os.path.exists(os.path.join(project_path, 'build/classes')):
                cmd.extend(['-xml', 'build/classes/'])
            else:
                cmd.extend(['-xml', 'src/'])
        
        elif tool.name == 'maven':
            cmd.extend(['compile', '-q'])
        
        elif tool.name == 'gradle':
            cmd.extend(['compileJava', '-q'])
        
        elif tool.name == 'dependency-check':
            cmd.extend(['--project', project_info.name, '--scan', '.', '--format', 'XML'])
        
        elif tool.name == 'junit':
            # Maven/Gradle test execution
            if os.path.exists(os.path.join(project_path, 'pom.xml')):
                cmd = ['mvn', 'test']
            elif os.path.exists(os.path.join(project_path, 'build.gradle')):
                cmd = ['gradle', 'test']
        
        return cmd
    
    def _find_java_files(self, project_path: str) -> List[str]:
        """Find Java files in project"""
        java_files = []
        
        for root, dirs, files in os.walk(project_path):
            # Skip common directories
            dirs[:] = [d for d in dirs if d not in {
                'target', 'build', '.git', '.gradle', '.mvn'
            }]
            
            for file in files:
                if file.endswith('.java'):
                    rel_path = os.path.relpath(os.path.join(root, file), project_path)
                    java_files.append(rel_path)
        
        return java_files[:100]  # Limit to avoid command line length issues
    
    def _parse_java_tool_output(self, tool_name: str, output: str, return_code: int, stderr: str = "") -> dict:
        """Parse output from Java tools"""
        result = {
            'issues': [],
            'issues_count': 0,
            'score': 100 if return_code == 0 else 60
        }
        
        if not output and not stderr:
            return result
        
        full_output = output + "\n" + stderr if stderr else output
        
        try:
            if tool_name == 'checkstyle':
                result.update(self._parse_checkstyle_output(full_output))
            elif tool_name == 'pmd':
                result.update(self._parse_pmd_output(full_output))
            elif tool_name == 'spotbugs':
                result.update(self._parse_spotbugs_output(full_output))
            elif tool_name in ['maven', 'gradle']:
                result.update(self._parse_build_output(full_output, return_code))
            elif tool_name == 'dependency-check':
                result.update(self._parse_dependency_check_output(full_output))
            elif tool_name == 'junit':
                result.update(self._parse_junit_output(full_output))
            else:
                # Generic parsing
                result.update(self._parse_generic_java_output(full_output, return_code))
                
        except Exception as e:
            self.logger.warning(f"Failed to parse {tool_name} output: {e}")
            # Fallback to basic parsing
            result.update(self._parse_generic_java_output(full_output, return_code))
        
        return result
    
    def _parse_checkstyle_output(self, output: str) -> dict:
        """Parse Checkstyle output"""
        issues = []
        
        try:
            # Try XML parsing first
            if output.strip().startswith('<?xml') or '<checkstyle' in output:
                root = ET.fromstring(output)
                for file_elem in root.findall('file'):
                    file_name = file_elem.get('name', '')
                    for error in file_elem.findall('error'):
                        issues.append({
                            'file': file_name,
                            'line': error.get('line', '0'),
                            'column': error.get('column', '0'),
                            'message': error.get('message', ''),
                            'source': error.get('source', ''),
                            'severity': error.get('severity', 'warning')
                        })
            else:
                # Fallback to text parsing
                lines = output.strip().split('\n')
                for line in lines:
                    if ':' in line and ('error' in line.lower() or 'warning' in line.lower()):
                        issues.append({
                            'message': line.strip(),
                            'severity': 'error' if 'error' in line.lower() else 'warning'
                        })
        except Exception as e:
            self.logger.debug(f"Checkstyle parsing error: {e}")
            # Simple line-based parsing
            lines = output.strip().split('\n')
            issues = [{'message': line, 'severity': 'warning'} for line in lines if line.strip() and ':' in line]
        
        score = max(30, 100 - len(issues) * 2)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score
        }
    
    def _parse_pmd_output(self, output: str) -> dict:
        """Parse PMD output"""
        issues = []
        
        try:
            if output.strip().startswith('<?xml') or '<pmd' in output:
                root = ET.fromstring(output)
                for file_elem in root.findall('file'):
                    file_name = file_elem.get('name', '')
                    for violation in file_elem.findall('violation'):
                        issues.append({
                            'file': file_name,
                            'line': violation.get('beginline', '0'),
                            'rule': violation.get('rule', ''),
                            'priority': violation.get('priority', '3'),
                            'message': violation.text.strip() if violation.text else '',
                            'severity': 'high' if int(violation.get('priority', '3')) <= 2 else 'medium'
                        })
        except Exception as e:
            self.logger.debug(f"PMD parsing error: {e}")
            # Simple text parsing
            lines = output.strip().split('\n')
            issues = [{'message': line, 'severity': 'medium'} for line in lines 
                     if line.strip() and any(word in line.lower() for word in ['violation', 'error', 'warning'])]
        
        score = max(25, 100 - len(issues) * 3)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score
        }
    
    def _parse_spotbugs_output(self, output: str) -> dict:
        """Parse SpotBugs output"""
        issues = []
        
        try:
            if output.strip().startswith('<?xml') or '<BugCollection' in output:
                root = ET.fromstring(output)
                for bug in root.findall('BugInstance'):
                    issues.append({
                        'type': bug.get('type', ''),
                        'priority': bug.get('priority', '3'),
                        'rank': bug.get('rank', '20'),
                        'category': bug.get('category', ''),
                        'message': bug.find('LongMessage').text if bug.find('LongMessage') is not None else '',
                        'severity': 'high' if int(bug.get('priority', '3')) <= 2 else 'medium'
                    })
        except Exception as e:
            self.logger.debug(f"SpotBugs parsing error: {e}")
            lines = output.strip().split('\n')
            issues = [{'message': line, 'severity': 'medium'} for line in lines 
                     if line.strip() and 'bug' in line.lower()]
        
        # SpotBugs issues are typically more serious
        score = max(20, 100 - len(issues) * 5)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score,
            'by_severity': self._group_by_severity(issues)
        }
    
    def _parse_build_output(self, output: str, return_code: int) -> dict:
        """Parse Maven/Gradle build output"""
        issues = []
        
        if return_code != 0:
            lines = output.strip().split('\n')
            for line in lines:
                if any(indicator in line.lower() for indicator in ['error', 'failed', 'compilation failure']):
                    issues.append({
                        'message': line.strip(),
                        'severity': 'error'
                    })
        
        score = 100 if return_code == 0 else max(40, 100 - len(issues) * 10)
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score,
            'build_success': return_code == 0
        }
    
    def _parse_dependency_check_output(self, output: str) -> dict:
        """Parse OWASP Dependency Check output"""
        issues = []
        vulnerabilities = 0
        
        try:
            if output.strip().startswith('<?xml') or '<analysis' in output:
                root = ET.fromstring(output)
                for dependency in root.findall('.//dependency'):
                    vulns = dependency.findall('.//vulnerability')
                    if vulns:
                        for vuln in vulns:
                            severity = vuln.find('severity')
                            issues.append({
                                'cve': vuln.find('name').text if vuln.find('name') is not None else '',
                                'severity': severity.text if severity is not None else 'medium',
                                'description': vuln.find('description').text[:200] if vuln.find('description') is not None else ''
                            })
                            vulnerabilities += 1
        except Exception as e:
            self.logger.debug(f"Dependency check parsing error: {e}")
            lines = output.strip().split('\n')
            vulnerabilities = len([line for line in lines if 'cve-' in line.lower() or 'vulnerability' in line.lower()])
            issues = [{'message': 'Security vulnerabilities found', 'severity': 'high'}] if vulnerabilities > 0 else []
        
        # High penalty for security vulnerabilities
        score = max(10, 100 - vulnerabilities * 8)
        
        return {
            'issues': issues,
            'issues_count': vulnerabilities,
            'score': score,
            'vulnerabilities': vulnerabilities
        }
    
    def _parse_junit_output(self, output: str) -> dict:
        """Parse JUnit test output"""
        issues = []
        
        # Look for test failures
        lines = output.strip().split('\n')
        test_failures = 0
        
        for line in lines:
            if 'FAIL' in line or 'ERROR' in line or 'test failure' in line.lower():
                issues.append({
                    'message': line.strip(),
                    'severity': 'error'
                })
                test_failures += 1
        
        # Extract test summary if available
        tests_run = 0
        for line in lines:
            if 'Tests run:' in line:
                # Parse Maven/Gradle test summary
                try:
                    parts = line.split(',')
                    for part in parts:
                        if 'Tests run:' in part:
                            tests_run = int(part.split(':')[1].strip())
                except:
                    pass
        
        score = max(50, 100 - test_failures * 15) if test_failures > 0 else 95
        
        return {
            'issues': issues,
            'issues_count': len(issues),
            'score': score,
            'tests_run': tests_run,
            'test_failures': test_failures
        }
    
    def _parse_generic_java_output(self, output: str, return_code: int) -> dict:
        """Generic Java tool output parsing"""
        lines = output.strip().split('\n')
        issue_indicators = ['error', 'warning', 'fail', 'exception', 'violation']
        
        issues_count = sum(1 for line in lines 
                          if any(indicator in line.lower() for indicator in issue_indicators))
        
        score = max(40, 100 - issues_count * 6) if return_code != 0 else 100
        
        return {
            'issues': [{'message': line} for line in lines if line.strip()][:15],
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
        """Java-specific post-processing"""
        # Call parent post-processing first
        super()._post_process_results(result, project_info)
        
        # Add Java-specific metrics
        result.plugin_data['has_pom_xml'] = os.path.exists(os.path.join(project_info.path, 'pom.xml'))
        result.plugin_data['has_build_gradle'] = os.path.exists(os.path.join(project_info.path, 'build.gradle'))
        result.plugin_data['has_gradle_kts'] = os.path.exists(os.path.join(project_info.path, 'build.gradle.kts'))
        result.plugin_data['build_system'] = self._detect_build_system(project_info.path)
        
        # Check for common frameworks
        frameworks = self._detect_java_frameworks(project_info.path)
        result.plugin_data['frameworks'] = frameworks
        
        # Detect Java version from project configuration
        java_version = self._detect_java_version(project_info.path)
        result.plugin_data['java_version'] = java_version
        
        # Adjust score based on Java best practices
        if result.plugin_data['has_pom_xml'] or result.plugin_data['has_build_gradle']:
            result.quality_score += 10  # Bonus for build system
        
        if frameworks:
            result.quality_score += 5   # Bonus for using established frameworks
        
        if java_version and java_version >= 11:
            result.quality_score += 5   # Bonus for modern Java version
        
        # Cap score at 100
        result.quality_score = min(100, result.quality_score)
    
    def _detect_build_system(self, project_path: str) -> str:
        """Detect Java build system"""
        if os.path.exists(os.path.join(project_path, 'pom.xml')):
            return 'Maven'
        elif (os.path.exists(os.path.join(project_path, 'build.gradle')) or 
              os.path.exists(os.path.join(project_path, 'build.gradle.kts'))):
            return 'Gradle'
        else:
            return 'Unknown'
    
    def _detect_java_frameworks(self, project_path: str) -> List[str]:
        """Detect Java frameworks used in the project"""
        frameworks = []
        
        # Check Maven dependencies
        pom_path = os.path.join(project_path, 'pom.xml')
        if os.path.exists(pom_path):
            try:
                with open(pom_path, 'r', encoding='utf-8') as f:
                    pom_content = f.read().lower()
                    
                    if 'spring-boot' in pom_content:
                        frameworks.append('Spring Boot')
                    elif 'spring-' in pom_content:
                        frameworks.append('Spring')
                    
                    if 'hibernate' in pom_content:
                        frameworks.append('Hibernate')
                    
                    if 'junit' in pom_content:
                        frameworks.append('JUnit')
                    
                    if 'jackson' in pom_content:
                        frameworks.append('Jackson')
                        
            except Exception as e:
                self.logger.debug(f"Could not read pom.xml: {e}")
        
        # Check Gradle dependencies
        gradle_path = os.path.join(project_path, 'build.gradle')
        if os.path.exists(gradle_path):
            try:
                with open(gradle_path, 'r', encoding='utf-8') as f:
                    gradle_content = f.read().lower()
                    
                    if 'spring-boot' in gradle_content:
                        frameworks.append('Spring Boot')
                    elif 'spring' in gradle_content:
                        frameworks.append('Spring')
                    
                    if 'hibernate' in gradle_content:
                        frameworks.append('Hibernate')
                        
            except Exception as e:
                self.logger.debug(f"Could not read build.gradle: {e}")
        
        return frameworks
    
    def _detect_java_version(self, project_path: str) -> int:
        """Detect Java version from project configuration"""
        # Check Maven pom.xml
        pom_path = os.path.join(project_path, 'pom.xml')
        if os.path.exists(pom_path):
            try:
                tree = ET.parse(pom_path)
                root = tree.getroot()
                
                # Look for maven.compiler.source or maven.compiler.target (with and without namespace)
                for properties in root.findall('.//properties'):
                    for child in properties:
                        tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                        if 'compiler.source' in tag_name or 'compiler.target' in tag_name:
                            try:
                                return int(float(child.text))
                            except:
                                pass
                
                # Also check with namespace
                for prop in root.findall('.//{http://maven.apache.org/POM/4.0.0}properties'):
                    for child in prop:
                        if 'compiler.source' in child.tag or 'compiler.target' in child.tag:
                            try:
                                return int(float(child.text))
                            except:
                                pass
                
                # Look for java.version property (both ways)
                for java_ver in root.findall('.//java.version'):
                    try:
                        return int(float(java_ver.text))
                    except:
                        pass
                        
                for prop in root.findall('.//{http://maven.apache.org/POM/4.0.0}java.version'):
                    try:
                        return int(float(prop.text))
                    except:
                        pass
                        
            except Exception as e:
                self.logger.debug(f"Could not parse pom.xml for Java version: {e}")
        
        # Check Gradle build.gradle
        gradle_path = os.path.join(project_path, 'build.gradle')
        if os.path.exists(gradle_path):
            try:
                with open(gradle_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Look for sourceCompatibility or targetCompatibility
                    import re
                    source_match = re.search(r'sourceCompatibility\s*=\s*["\']?(\d+)', content)
                    if source_match:
                        return int(source_match.group(1))
                    
                    target_match = re.search(r'targetCompatibility\s*=\s*["\']?(\d+)', content)
                    if target_match:
                        return int(target_match.group(1))
                        
            except Exception as e:
                self.logger.debug(f"Could not read build.gradle for Java version: {e}")
        
        return 8  # Default to Java 8