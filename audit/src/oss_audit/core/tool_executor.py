#!/usr/bin/env python3
"""
Tool Executor - 工具执行器
负责具体的工具执行和资源管理，支持并行和串行执行
"""

import os
import time
import asyncio
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

from .tool_registry import ToolRegistry, Tool, get_tool_registry
from .project_detector import ProjectInfo
from .container_manager import get_container_manager, ContainerManager

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """执行模式"""
    PARALLEL = "parallel"      # 并行执行
    SEQUENTIAL = "sequential"  # 串行执行
    MIXED = "mixed"           # 混合执行


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass 
class ToolResult:
    """工具执行结果"""
    tool_name: str
    status: ExecutionStatus
    success: bool
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'tool_name': self.tool_name,
            'status': self.status.value if hasattr(self.status, 'value') else str(self.status),
            'success': self.success,
            'result': self.result,
            'error': self.error,
            'execution_time': self.execution_time,
            'stdout': self.stdout,
            'stderr': self.stderr,
            'return_code': self.return_code
        }


@dataclass
class ExecutionPhase:
    """执行阶段"""
    name: str
    tools: List[Tool]
    mode: ExecutionMode
    timeout: int = 300  # 5分钟默认超时
    parallel_limit: int = 4  # 并行限制
    continue_on_failure: bool = True


@dataclass
class ExecutionPlan:
    """执行计划"""
    phases: List[ExecutionPhase] = field(default_factory=list)
    global_timeout: int = 1800  # 30分钟全局超时
    early_termination_threshold: float = 1.1  # 禁用早期终止（110%永远不会达到）
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    
    def add_phase(self, phase: ExecutionPhase):
        """添加执行阶段"""
        self.phases.append(phase)
    
    def get_total_estimated_time(self) -> int:
        """获取总预估时间"""
        total = 0
        for phase in self.phases:
            if phase.mode == ExecutionMode.PARALLEL:
                max_time = max(tool.estimated_time for tool in phase.tools) if phase.tools else 0
                total += max_time
            else:
                total += sum(tool.estimated_time for tool in phase.tools)
        return total


class ResourceMonitor:
    """资源监控器"""
    
    def __init__(self, max_memory_mb: int = 1024, max_cpu_percent: float = 80.0):
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.monitoring = False
        self._lock = threading.Lock()
    
    def start_monitoring(self):
        """开始资源监控"""
        with self._lock:
            self.monitoring = True
        
        def monitor():
            try:
                import psutil
                process = psutil.Process()
                
                while self.monitoring:
                    try:
                        # 检查内存使用
                        memory_mb = process.memory_info().rss / 1024 / 1024
                        if memory_mb > self.max_memory_mb:
                            logger.warning(f"内存使用过高: {memory_mb:.1f}MB > {self.max_memory_mb}MB")
                        
                        # 检查CPU使用率
                        cpu_percent = process.cpu_percent()
                        if cpu_percent > self.max_cpu_percent:
                            logger.warning(f"CPU使用率过高: {cpu_percent:.1f}% > {self.max_cpu_percent}%")
                        
                        time.sleep(5)  # 每5秒检查一次
                    except Exception as e:
                        logger.debug(f"资源监控异常: {e}")
                        break
                        
            except ImportError:
                logger.debug("psutil未安装，跳过资源监控")
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def stop_monitoring(self):
        """停止资源监控"""
        with self._lock:
            self.monitoring = False


class ToolExecutor:
    """工具执行器 - 负责具体的工具执行和资源管理"""
    
    def __init__(self, tools_registry_path: Optional[str] = None, docker_mode: bool = None):
        """
        初始化工具执行器
        
        Args:
            tools_registry_path: 工具注册表路径
            docker_mode: 是否使用Docker模式执行工具（None=自动检测）
        """
        self.registry = get_tool_registry(tools_registry_path)
        self.resource_monitor = ResourceMonitor()
        self.execution_pool = None
        self._execution_stats = {
            'total_tools': 0,
            'successful_tools': 0,
            'failed_tools': 0,
            'total_time': 0.0
        }
        
        # 初始化统一容器管理器
        self.container_manager = get_container_manager()
        
        # 加载配置文件以检查容器模式设置
        self.config = self._load_config()
        
        # 容器配置检查
        container_config = self.config.get('tools', {}).get('container_mode', {})
        force_container = container_config.get('force', False)
        container_priority = container_config.get('priority', False)
        
        # 自动检测或使用指定的容器模式
        if docker_mode is None:
            self.docker_mode = self.container_manager.is_available()
        else:
            self.docker_mode = docker_mode and self.container_manager.is_available()
        
        # 如果配置强制容器模式，确保容器引擎可用
        if force_container and not self.docker_mode:
            logger.error("配置要求强制容器模式，但容器引擎不可用！")
            diagnosis = self.container_manager.diagnose_issues()
            for issue in diagnosis["issues"]:
                logger.error(f"  问题: {issue}")
            for rec in diagnosis["recommendations"]:
                logger.warning(f"  建议: {rec}")
            raise RuntimeError("强制容器模式下容器引擎不可用")
        
        # 容器优先模式：即使本地工具可用也优先使用容器
        if container_priority and self.docker_mode:
            logger.info("🐳 容器优先模式已启用")
            
        if self.docker_mode:
            engine = self.container_manager.primary_engine.value if self.container_manager.primary_engine else "unknown"
            logger.info(f"🐳 启用容器执行模式 - 引擎: {engine}")
            
            # 检查容器环境状态
            status = self.container_manager.get_engine_status()
            if not status.get("running", False):
                if force_container:
                    logger.error("强制容器模式下容器引擎未运行")
                    raise RuntimeError("强制容器模式下容器引擎未运行")
                logger.warning("容器引擎未运行，回退到本地执行模式")
                self.docker_mode = False
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        import yaml
        from pathlib import Path
        
        config = {}
        current_dir = Path.cwd()
        possible_paths = [
            current_dir / "config.yaml",
            current_dir.parent / "config.yaml",
            Path("/app/config.yaml")  # Docker容器中的配置文件路径
        ]

        for path in possible_paths:
            if Path(path).exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f) or {}
                    logger.debug(f"已加载配置文件: {path}")
                    break
                except Exception as e:
                    logger.debug(f"配置文件加载失败 {path}: {e}")

        return config
    
    def discover_available_tools(self, project_info: ProjectInfo) -> List[Tool]:
        """
        发现项目可用的工具
        
        Args:
            project_info: 项目信息
            
        Returns:
            可用工具列表
        """
        logger.info(f"开始发现可用工具，项目语言: {list(project_info.languages.keys())}")
        
        available_tools = []
        
        # 获取语言特定工具
        for language, percentage in project_info.languages.items():
            if percentage < 0.05:  # 忽略占比低于5%的语言
                logger.debug(f"跳过低占比语言 {language}: {percentage:.1%}")
                continue
            
            lang_tools = self.registry.get_language_tools(language)
            logger.info(f"语言 {language} 发现 {len(lang_tools)} 个工具")
            
            # 添加所有工具，稍后在执行时再检查可用性
            for tool in lang_tools:
                available_tools.append(tool)
                if self.registry.is_tool_available(tool):
                    logger.debug(f"工具可用: {tool.name}")
                else:
                    logger.debug(f"工具不可用，但保留用于分析建议: {tool.name}")
        
        # 获取通用工具
        universal_tools = self.registry.get_universal_tools()
        logger.info(f"发现 {len(universal_tools)} 个通用工具")
        
        for tool in universal_tools:
            # 检查是否支持项目语言
            if tool.supports and 'all' not in tool.supports:
                if not any(lang in tool.supports for lang in project_info.languages.keys()):
                    logger.debug(f"通用工具 {tool.name} 不支持项目语言")
                    continue
            
            available_tools.append(tool)
            if self.registry.is_tool_available(tool):
                logger.debug(f"通用工具可用: {tool.name}")
            else:
                logger.debug(f"通用工具不可用，但保留用于分析建议: {tool.name}")
        
        # 统计可用工具
        actually_available = [t for t in available_tools if self.registry.is_tool_available(t)]
        
        logger.info(f"总共发现 {len(available_tools)} 个工具，其中 {len(actually_available)} 个可直接使用")
        
        # 如果可用工具太少，提示使用容器模式
        if len(actually_available) < len(available_tools) * 0.3:  # 少于30%的工具可用
            logger.warning("检测到大部分工具不可用，建议使用容器模式获得最佳体验：")
            logger.warning("  启动 Docker 或 Podman 服务后，程序将自动构建并使用容器")
            logger.warning("  容器预装了所有分析工具，无需手动安装")
        
        return available_tools
    
    
    # 旧的容器管理方法已移至 ContainerManager 统一管理
    
    def _create_direct_tool_command(self, tool: Tool, project_path: str) -> List[str]:
        """创建直接工具命令 - 适用于工具容器架构
        
        Args:
            tool: 要执行的工具
            project_path: 容器内的项目路径
            
        Returns:
            工具命令列表
        """
        # 根据工具名称直接构建命令
        # 工具已预装在容器中，无需工具注册表的复杂命令构建
        
        if tool.name == 'pylint':
            return ['pylint', '--output-format=json', '--reports=yes', '--score=yes', 
                    '--recursive=yes', '.']
        
        elif tool.name == 'flake8':
            return ['flake8', '--format=default', '--statistics', '--max-line-length=88', '.']
        
        elif tool.name == 'mypy':
            return ['mypy', '--ignore-missing-imports', '--show-error-codes', 
                    '--strict-optional', '.']
        
        elif tool.name == 'bandit':
            return ['bandit', '-r', '-f', 'json', '.']
        
        elif tool.name == 'safety':
            return ['echo', 'safety not available in minimal container']
        
        elif tool.name == 'black':
            return ['black', '--check', '--diff', '.']
        
        elif tool.name == 'isort':
            return ['isort', '--check-only', '--diff', '.']
        
        elif tool.name == 'eslint':
            return ['eslint', '--no-eslintrc', '--env', 'es6', '--format=json', '--ext', '.js,.jsx,.ts,.tsx', '.']
        
        elif tool.name == 'prettier':
            return ['echo', 'prettier not available in minimal container']
        
        elif tool.name == 'jest':
            return ['echo', 'jest not available in minimal container']
        
        elif tool.name == 'tsc':
            return ['tsc', '--noEmit', '--pretty', '--skipLibCheck']
        
        elif tool.name == 'checkstyle':
            return ['echo', 'checkstyle not available in minimal container']
        
        elif tool.name == 'spotbugs':
            return ['echo', 'spotbugs not available in minimal container']
        
        elif tool.name == 'staticcheck':
            return ['echo', 'staticcheck not available in minimal container']
        
        elif tool.name == 'gosec':
            return ['echo', 'gosec not available in minimal container']
        
        elif tool.name == 'goimports':
            return ['echo', 'goimports not available in minimal container']
        
        elif tool.name == 'golangci-lint':
            return ['echo', 'golangci-lint not available in minimal container']
        
        elif tool.name == 'rustfmt':
            return ['echo', 'rustfmt not available in minimal container']
        
        elif tool.name == 'clippy':
            return ['echo', 'clippy not available in minimal container']
        
        elif tool.name == 'cargo-audit':
            return ['echo', 'cargo-audit not available in minimal container']
        
        elif tool.name == 'semgrep':
            return ['semgrep', '--config=p/python', '--json', '--quiet', '.']
        
        elif tool.name == 'gitleaks':
            return ['echo', 'gitleaks not available in minimal container']
        
        elif tool.name == 'pytest':
            return ['pytest', '--tb=short', '--quiet', '.']
        
        elif tool.name == 'coverage':
            return ['bash', '-c', 'cd /workspace && coverage run -m pytest && coverage report']

        elif tool.name == 'sonarqube-scanner':
            # SonarQube Scanner 需要配置，返回友好提示
            return ['echo', 'SonarQube Scanner requires configuration (sonar-project.properties)']

        elif tool.name == 'cppcheck':
            # CPPCheck 在容器中不可用，返回友好提示
            return ['echo', 'CPPCheck not available in minimal container (requires system installation)']

        else:
            # 回退到基本命令
            logger.warning(f"工具 {tool.name} 未配置直接命令，使用基本执行")
            return [tool.name, '.']
    
    def create_execution_plan(self, tools: List[Tool], 
                            project_info: ProjectInfo) -> ExecutionPlan:
        """
        创建执行计划
        
        Args:
            tools: 工具列表
            project_info: 项目信息
            
        Returns:
            执行计划
        """
        plan = ExecutionPlan()
        
        # 按类别分组工具
        tool_categories = {}
        for tool in tools:
            for category in tool.categories:
                if category not in tool_categories:
                    tool_categories[category] = []
                tool_categories[category].append(tool)
        
        # 创建执行阶段
        # 阶段1: 快速静态分析工具（并行）
        fast_tools = []
        for tool in tools:
            if tool.estimated_time <= 30 and 'format' in tool.categories:
                fast_tools.append(tool)
        
        if fast_tools:
            phase1 = ExecutionPhase(
                name="快速格式检查",
                tools=fast_tools,
                mode=ExecutionMode.PARALLEL,
                timeout=120,
                parallel_limit=6
            )
            plan.add_phase(phase1)
        
        # 阶段2: 代码质量分析（并行）
        quality_tools = []
        for tool in tools:
            if tool not in fast_tools and 'quality' in tool.categories:
                quality_tools.append(tool)
        
        if quality_tools:
            phase2 = ExecutionPhase(
                name="代码质量分析",
                tools=quality_tools,
                mode=ExecutionMode.PARALLEL,
                timeout=300,
                parallel_limit=4
            )
            plan.add_phase(phase2)
        
        # 阶段3: 安全检查（并行）
        security_tools = []
        for tool in tools:
            if tool not in fast_tools and tool not in quality_tools and 'security' in tool.categories:
                security_tools.append(tool)
        
        if security_tools:
            phase3 = ExecutionPhase(
                name="安全检查",
                tools=security_tools,
                mode=ExecutionMode.PARALLEL,
                timeout=300,
                parallel_limit=3
            )
            plan.add_phase(phase3)
        
        # 阶段4: 测试和覆盖率（串行，因为可能有依赖）
        test_tools = []
        for tool in tools:
            if tool not in fast_tools and tool not in quality_tools and tool not in security_tools and 'testing' in tool.categories:
                test_tools.append(tool)
        
        if test_tools:
            phase4 = ExecutionPhase(
                name="测试和覆盖率",
                tools=test_tools,
                mode=ExecutionMode.SEQUENTIAL,
                timeout=600
            )
            plan.add_phase(phase4)
        
        # 阶段5: 其他工具（混合模式）
        remaining_tools = []
        processed_tool_names = set([t.name for t in fast_tools + quality_tools + security_tools + test_tools])
        for tool in tools:
            if tool.name not in processed_tool_names:
                remaining_tools.append(tool)
        
        if remaining_tools:
            phase5 = ExecutionPhase(
                name="其他分析工具",
                tools=remaining_tools,
                mode=ExecutionMode.PARALLEL,
                timeout=300,
                parallel_limit=2
            )
            plan.add_phase(phase5)
        
        logger.info(f"创建执行计划: {len(plan.phases)} 个阶段，预估耗时 {plan.get_total_estimated_time()//60} 分钟")
        return plan
    
    def execute_tools(self, execution_plan: ExecutionPlan, 
                     project_path: str) -> Dict[str, ToolResult]:
        """
        根据执行计划运行工具
        
        Args:
            execution_plan: 执行计划
            project_path: 项目路径
            
        Returns:
            工具执行结果字典
        """
        logger.info(f"开始执行工具，项目路径: {project_path}")
        
        # 启动资源监控
        self.resource_monitor.start_monitoring()
        
        all_results = {}
        start_time = time.time()
        
        try:
            # 按阶段执行
            for phase_idx, phase in enumerate(execution_plan.phases, 1):
                logger.info(f"执行阶段 {phase_idx}/{len(execution_plan.phases)}: {phase.name}")
                
                if phase.mode == ExecutionMode.PARALLEL:
                    phase_results = self._execute_parallel(phase, project_path)
                elif phase.mode == ExecutionMode.SEQUENTIAL:
                    phase_results = self._execute_sequential(phase, project_path)
                else:  # MIXED
                    phase_results = self._execute_mixed(phase, project_path)
                
                all_results.update(phase_results)
                
                # 检查是否需要提前终止
                if self._should_early_terminate(all_results, execution_plan):
                    logger.warning("达到提前终止条件，停止执行")
                    break
                
                # 检查全局超时
                if time.time() - start_time > execution_plan.global_timeout:
                    logger.warning("达到全局超时限制，停止执行")
                    break
        
        finally:
            # 停止资源监控
            self.resource_monitor.stop_monitoring()
            
            # 更新统计信息
            self._update_execution_stats(all_results)
            total_time = time.time() - start_time
            self._execution_stats['total_time'] = total_time
            
            logger.info(f"工具执行完成，耗时 {total_time:.1f}s")
        
        return all_results
    
    def _execute_parallel(self, phase: ExecutionPhase, 
                         project_path: str) -> Dict[str, ToolResult]:
        """并行执行工具"""
        logger.info(f"并行执行 {len(phase.tools)} 个工具，并发限制: {phase.parallel_limit}")
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=phase.parallel_limit) as executor:
            # 提交所有任务
            future_to_tool = {
                executor.submit(self._run_single_tool, tool, project_path, phase.timeout): tool
                for tool in phase.tools
            }
            
            # 收集结果
            for future in as_completed(future_to_tool, timeout=phase.timeout):
                tool = future_to_tool[future]
                try:
                    result = future.result(timeout=30)  # 额外的结果获取超时
                    results[tool.name] = result
                    logger.debug(f"工具 {tool.name} 执行完成: {'成功' if result.success else '失败'}")
                except Exception as e:
                    logger.error(f"工具 {tool.name} 执行异常: {e}")
                    results[tool.name] = ToolResult(
                        tool_name=tool.name,
                        status=ExecutionStatus.FAILED,
                        success=False,
                        error=str(e)
                    )
        
        return results
    
    def _execute_sequential(self, phase: ExecutionPhase, 
                          project_path: str) -> Dict[str, ToolResult]:
        """串行执行工具"""
        logger.info(f"串行执行 {len(phase.tools)} 个工具")
        
        results = {}
        
        for tool in phase.tools:
            try:
                result = self._run_single_tool(tool, project_path, phase.timeout)
                results[tool.name] = result
                
                logger.debug(f"工具 {tool.name} 执行完成: {'成功' if result.success else '失败'}")
                
                # 如果工具执行失败且不允许继续，则停止
                if not result.success and not phase.continue_on_failure:
                    logger.warning(f"工具 {tool.name} 执行失败，停止后续工具执行")
                    break
                    
            except Exception as e:
                logger.error(f"工具 {tool.name} 执行异常: {e}")
                results[tool.name] = ToolResult(
                    tool_name=tool.name,
                    status=ExecutionStatus.FAILED,
                    success=False,
                    error=str(e)
                )
                
                if not phase.continue_on_failure:
                    break
        
        return results
    
    def _execute_mixed(self, phase: ExecutionPhase, 
                      project_path: str) -> Dict[str, ToolResult]:
        """混合执行工具（快速工具并行，慢速工具串行）"""
        logger.info(f"混合执行 {len(phase.tools)} 个工具")
        
        # 分组工具
        fast_tools = [t for t in phase.tools if t.estimated_time <= 60]
        slow_tools = [t for t in phase.tools if t.estimated_time > 60]
        
        results = {}
        
        # 先并行执行快速工具
        if fast_tools:
            fast_phase = ExecutionPhase(
                name=f"{phase.name}_fast",
                tools=fast_tools,
                mode=ExecutionMode.PARALLEL,
                parallel_limit=min(len(fast_tools), phase.parallel_limit)
            )
            fast_results = self._execute_parallel(fast_phase, project_path)
            results.update(fast_results)
        
        # 再串行执行慢速工具
        if slow_tools:
            slow_phase = ExecutionPhase(
                name=f"{phase.name}_slow",
                tools=slow_tools,
                mode=ExecutionMode.SEQUENTIAL,
                continue_on_failure=phase.continue_on_failure
            )
            slow_results = self._execute_sequential(slow_phase, project_path)
            results.update(slow_results)
        
        return results
    
    def _run_tool_in_docker(self, tool: Tool, project_path: str, 
                           timeout: int, start_time: float) -> ToolResult:
        """使用ContainerManager统一接口执行容器工具"""
        try:
            # 构建工具执行命令
            tool_cmd = self._create_direct_tool_command(tool, "/workspace")
            
            # 挂载项目目录到容器
            project_dir = os.path.abspath(project_path)
            volumes = {project_dir: "/workspace"}
            
            # 使用ContainerManager执行工具
            success, stdout, stderr = self.container_manager.run_container(
                image=self.container_manager.default_images.get("tools", "oss-audit:tools-2.0"),
                command=tool_cmd,
                volumes=volumes,
                working_dir="/workspace",
                timeout=min(timeout, tool.timeout)
            )
            
            execution_time = time.time() - start_time
            
            # 解析工具输出
            output_to_parse = stdout or ""
            if not stdout and stderr and success:
                # 某些工具通过stderr输出结果
                output_to_parse = stderr
            
            parsed_result = self._parse_basic_tool_output(
                tool.name, output_to_parse, 0 if success else 1)
            
            # 工具执行成功的标准
            is_success = success or (
                parsed_result.get('issues_count', 0) >= 0  # 有有效的解析结果
            )
            
            # 创建结果对象
            tool_result = ToolResult(
                tool_name=tool.name,
                status=ExecutionStatus.COMPLETED,
                success=is_success,
                result=parsed_result,
                execution_time=execution_time,
                stdout=stdout,
                stderr=stderr,
                return_code=0 if success else 1
            )
            
            if not tool_result.success:
                tool_result.error = f"容器工具执行失败"
                if stderr:
                    tool_result.error += f": {stderr[:500]}"
            
            logger.debug(f"容器工具 {tool.name} 执行完成: {'成功' if tool_result.success else '失败'}")
            return tool_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"容器工具 {tool.name} 执行异常: {e}")
            
            # 尝试错误恢复
            try:
                from .container_manager import ContainerError
                error_report = self.container_manager.create_error_report(
                    e, tool_cmd if 'tool_cmd' in locals() else [tool.name], 
                    {"tool": tool.name, "operation": "tool_execution"}
                )
                
                if self.container_manager.attempt_recovery(error_report):
                    logger.info(f"容器错误恢复成功，建议重试工具 {tool.name}")
                
            except Exception as recovery_error:
                logger.debug(f"错误恢复尝试失败: {recovery_error}")
            
            return ToolResult(
                tool_name=tool.name,
                status=ExecutionStatus.FAILED,
                success=False,
                error=f"容器执行异常: {str(e)}",
                execution_time=execution_time
            )
    
    def _run_single_tool(self, tool: Tool, project_path: str, 
                        timeout: int) -> ToolResult:
        """执行单个工具"""
        start_time = time.time()
        
        logger.debug(f"开始执行工具: {tool.name}")
        
        # 容器模式优先执行
        if self.docker_mode:
            engine = self.container_manager.primary_engine.value if self.container_manager.primary_engine else "unknown"
            logger.info(f"🐳 容器模式执行: {tool.name} (引擎: {engine})")
            return self._run_tool_in_docker(tool, project_path, timeout, start_time)
        
        # 本地模式：首先检查工具是否真正可用
        if not self.registry.is_tool_available(tool):
            execution_time = time.time() - start_time
            logger.warning(f"💻 本地模式: 工具 {tool.name} 不可用，建议使用容器模式")
            
            # 生成工具不可用的建议性报告
            suggestion_result = {
                'tool_name': tool.name,
                'status': 'not_available',
                'suggestion': f'建议使用容器模式或安装 {tool.name} 工具以获得更准确的分析结果',
                'install_command': ' '.join(tool.install) if tool.install else f'请安装 {tool.name}',
                'categories': tool.categories,
                'description': f'{tool.name} 是 {tool.language} 语言的 {", ".join(tool.categories)} 工具',
                'container_recommendation': '容器方式: 启动 Docker/Podman 后重新运行审计'
            }
            
            return ToolResult(
                tool_name=tool.name,
                status=ExecutionStatus.SKIPPED,
                success=False,
                result=suggestion_result,
                execution_time=execution_time,
                stdout="",
                stderr=f"工具 {tool.name} 未安装，建议使用容器模式",
                return_code=-1
            )
        
        # 本地模式执行工具
        logger.info(f"💻 本地模式执行: {tool.name}")
        
        try:
            # 创建执行命令
            cmd = self.registry.create_tool_command(tool, project_path)
            
            # 执行命令
            # 设置环境变量以确保UTF-8输出
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['LC_ALL'] = 'C.UTF-8'

            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # 替换无法解码的字符
                timeout=min(timeout, tool.timeout),
                env=env
            )
            
            execution_time = time.time() - start_time
            
            # 解析工具输出 - 使用基础解析
            parsed_result = self._parse_basic_tool_output(
                tool.name, result.stdout or "", result.returncode)
            
            # 工具执行成功判定（与容器执行保持一致）
            is_success = result.returncode == 0 or (
                result.returncode not in [126, 127, 2] and  # 避免系统级错误
                parsed_result.get('issues_count', 0) >= 0  # 有有效的解析结果
            )
            
            # 创建结果对象
            tool_result = ToolResult(
                tool_name=tool.name,
                status=ExecutionStatus.COMPLETED,
                success=is_success,
                result=parsed_result,
                execution_time=execution_time,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode
            )
            
            if not tool_result.success:
                tool_result.error = f"工具执行失败，退出码: {result.returncode}"
                if result.stderr:
                    tool_result.error += f"\n错误输出: {result.stderr[:500]}"
            
            return tool_result
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            logger.warning(f"工具 {tool.name} 执行超时: {timeout}s")
            return ToolResult(
                tool_name=tool.name,
                status=ExecutionStatus.TIMEOUT,
                success=False,
                error=f"工具执行超时 ({timeout}s)",
                execution_time=execution_time
            )
            
        except subprocess.SubprocessError as e:
            execution_time = time.time() - start_time
            logger.error(f"工具 {tool.name} 执行错误: {e}")
            return ToolResult(
                tool_name=tool.name,
                status=ExecutionStatus.FAILED,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"工具 {tool.name} 执行异常: {e}")
            return ToolResult(
                tool_name=tool.name,
                status=ExecutionStatus.FAILED,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def _should_early_terminate(self, results: Dict[str, ToolResult], 
                              execution_plan: ExecutionPlan) -> bool:
        """检查是否需要提前终止"""
        if not results:
            return False
        
        # 计算失败率
        total_tools = len(results)
        failed_tools = sum(1 for r in results.values() if not r.success)
        failure_rate = failed_tools / total_tools
        
        # 如果失败率超过阈值，提前终止
        if failure_rate > execution_plan.early_termination_threshold:
            logger.warning(f"工具失败率过高: {failure_rate:.1%} > {execution_plan.early_termination_threshold:.1%}")
            return True
        
        return False
    
    def _update_execution_stats(self, results: Dict[str, ToolResult]):
        """更新执行统计信息"""
        self._execution_stats['total_tools'] = len(results)
        self._execution_stats['successful_tools'] = sum(
            1 for r in results.values() if r.success)
        self._execution_stats['failed_tools'] = sum(
            1 for r in results.values() if not r.success)
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        return self._execution_stats.copy()
    
    def install_missing_tools(self, tools: List[Tool]) -> Dict[str, bool]:
        """
        安装缺失的工具
        
        Args:
            tools: 工具列表
            
        Returns:
            安装结果字典 {工具名: 是否成功}
        """
        logger.info(f"开始安装 {len(tools)} 个工具")
        
        install_results = {}
        
        for tool in tools:
            if not self.registry.is_tool_available(tool):
                logger.info(f"安装工具: {tool.name}")
                success = self.registry.install_tool(tool)
                install_results[tool.name] = success
            else:
                logger.debug(f"工具已存在: {tool.name}")
                install_results[tool.name] = True
        
        successful_installs = sum(1 for success in install_results.values() if success)
        logger.info(f"工具安装完成: {successful_installs}/{len(tools)} 成功")
        
        return install_results
    
    def _parse_basic_tool_output(self, tool_name: str, output: str, return_code: int) -> Dict[str, Any]:
        """基础工具输出解析"""
        result = {
            'issues': [],
            'issues_count': 0,
            'score': 100 if return_code == 0 else 60
        }
        
        if return_code != 0 and output:
            # 简单计数输出行数作为问题估计
            lines = [line.strip() for line in output.split('\n') if line.strip()]
            result['issues_count'] = len([line for line in lines if any(indicator in line.lower() 
                                         for indicator in ['error', 'warning', 'issue', 'violation'])])
            result['score'] = max(20, 100 - result['issues_count'] * 10)
        
        return result