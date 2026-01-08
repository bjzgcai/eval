#!/usr/bin/env python3
"""
Audit Runner - 主审计运行器
整合所有核心组件，提供统一的审计入口
整合所有核心组件，提供统一的审计入口
"""

import os
import sys
import time
import pathlib
import logging
import yaml
from typing import Dict, List, Any, Optional

from .project_detector import ProjectDetector, ProjectInfo
from .tool_registry import get_tool_registry, ToolRegistry
from .tool_executor import ToolExecutor, ExecutionPlan
from .report_generator import ReportGenerator
from .decision_agent import DecisionAgent, create_decision_agent
from .adaptive_agent import AdaptiveAgent, create_adaptive_agent
from .recommendation_agent import RecommendationAgent, create_recommendation_agent
from ..plugins import get_plugin_registry
from ..utils.performance_monitor import (
    PerformanceProfiler, BaselineManager, PerformanceOptimizer,
    get_global_profiler, profile_operation
)
from ..utils.git_utils import resolve_project_path, GitUtils
from ..utils.multi_platform_org_analyzer import MultiPlatformOrgAnalyzer

logger = logging.getLogger(__name__)


class AuditRunner:
    """主审计运行器 - 整合项目检测、工具执行和报告生成"""
    
    def __init__(self, 
                 tools_registry_path: Optional[str] = None,
                 language_config_path: Optional[str] = None):
        """
        初始化审计运行器
        
        Args:
            tools_registry_path: 工具注册表路径
            language_config_path: 语言检测配置路径
        """
        logger.info("初始化OSS Audit 2.0 审计运行器")
        
        # 加载配置
        self.default_config = self._load_default_config()
        
        # 初始化核心组件
        self.project_detector = ProjectDetector(language_config_path)
        self.tool_executor = ToolExecutor(tools_registry_path)
        self.report_generator = ReportGenerator()
        # 智能代理系统
        self.decision_agent = create_decision_agent()
        self.adaptive_agent = create_adaptive_agent()
        self.recommendation_agent = create_recommendation_agent()
        
        # 初始化插件系统
        self.plugin_registry = get_plugin_registry()
        
        # 初始化性能监控系统
        self.profiler = get_global_profiler()
        self.baseline_manager = BaselineManager()
        self.performance_optimizer = PerformanceOptimizer()
        
        # 初始化多平台组织分析器
        self.multi_platform_analyzer = MultiPlatformOrgAnalyzer()
        
        # 运行时状态
        self.current_project_info: Optional[ProjectInfo] = None
        self.project_config: Optional[Dict[str, Any]] = None
        self.execution_stats = {
            'start_time': 0,
            'end_time': 0,
            'total_duration': 0,
            'phases_completed': 0,
            'tools_executed': 0,
            'tools_successful': 0,
            'tools_failed': 0
        }
    
    def audit_project(self, project_path: str, 
                     output_dir: Optional[str] = None,
                     config_overrides: Optional[Dict[str, Any]] = None) -> str:
        """
        对项目进行完整的审计评估
        
        Args:
            project_path: 项目路径
            output_dir: 输出目录（可选）
            config_overrides: 配置覆盖（可选）
            
        Returns:
            主报告文件路径
        """
        logger.info(f"开始审计项目: {project_path}")
        
        # 记录开始时间
        self.execution_stats['start_time'] = time.time()
        
        # 开始性能监控
        with self.profiler.profile("full_audit", collect_system_metrics=True) as p:
            try:
                # 记录项目特征用于性能分析
                p.record_metric("project_path_length", len(project_path))
                
                # 0. 配置加载阶段
                logger.info("阶段0: 配置加载与合并")
                project_config = self._load_project_config(project_path)
            
                # 1. 项目检测阶段（提前执行以获取项目信息用于智能配置）
                logger.info("阶段1: 项目信息检测")
                self.current_project_info = self._detect_project_info(project_path)
                
                # 记录项目检测指标
                p.record_metric("project_files_count", len(list(pathlib.Path(project_path).rglob("*"))) if pathlib.Path(project_path).exists() else 0)
                p.record_metric("project_languages_count", len(self.current_project_info.languages) if self.current_project_info.languages else 0)
            
                # 根据项目信息生成智能配置
                smart_config = self._generate_smart_config(self.current_project_info)
                merged_config = self._merge_configs(self.default_config, smart_config, project_config, config_overrides)
                self.project_config = merged_config
            
                project_name = merged_config.get('project', {}).get('name', self.current_project_info.name)
                project_type = merged_config.get('project', {}).get('type', self.current_project_info.project_type.value if hasattr(self.current_project_info.project_type, 'value') else str(self.current_project_info.project_type))
                logger.info(f"✅ 配置完成 - 项目: {project_name} ({project_type})")
                if project_config:
                    logger.info(f"🔧 应用了项目配置文件自定义设置")
                else:
                    logger.info(f"🤖 智能配置 - 根据项目特征自动优化")
                
                # 2. 工具发现阶段  
                logger.info("阶段2: 工具发现与可用性检查")
                available_tools = self._discover_tools()
                p.record_metric("available_tools_count", len(available_tools))
                
                # 3. 智能工具选择阶段（DecisionAgent）
                logger.info("阶段3: 智能工具选择")
                selected_tools = self._intelligent_tool_selection(available_tools)
                p.record_metric("selected_tools_count", len(selected_tools))
                
                # 4. 执行计划制定
                logger.info("阶段4: 制定执行计划")
                execution_plan = self._create_execution_plan(selected_tools)
                p.record_metric("execution_phases_count", len(execution_plan.phases))
                
                # 5. 工具执行阶段
                logger.info("阶段5: 执行工具分析")
                tool_results = self._execute_tools(execution_plan, project_path)
                p.record_metric("tool_results_count", len(tool_results))
                
                # 6. 报告生成阶段
                logger.info("阶段6: 生成审计报告")
                report_path = self._generate_reports(tool_results, output_dir or project_path)
                
                # 记录结束时间和性能分析
                self.execution_stats['end_time'] = time.time()
                self.execution_stats['total_duration'] = (
                    self.execution_stats['end_time'] - self.execution_stats['start_time']
                )
                
                # 性能分析和基线比较
                self._analyze_performance_and_create_baseline(p, project_name, project_type)
                
                logger.info(f"审计完成！总耗时: {self.execution_stats['total_duration']:.1f}s")
                logger.info(f"主报告路径: {report_path}")
                
                return report_path
            
            except Exception as e:
                logger.error(f"审计过程中发生错误: {e}")
                raise
            
            finally:
                self._cleanup()
    
    def analyze_git_organization(self, org_url: str, 
                                   output_dir: Optional[str] = None) -> str:
        """
        分析Git平台组织
        
        Args:
            org_url: Git平台组织URL (GitHub/GitLab/Gitee/Gitea)
            output_dir: 输出目录
            
        Returns:
            组织报告文件路径
        """
        platform_name = self.multi_platform_analyzer.extract_platform_name(org_url)
        org_name = self.multi_platform_analyzer.extract_org_name(org_url)
        
        logger.info(f"开始分析{platform_name}组织: {org_name}")
        
        if not org_name:
            raise ValueError(f"无效的{platform_name}组织URL: {org_url}")
        
        try:
            # 分析组织
            context = self.multi_platform_analyzer.analyze_organization(
                org_url, AuditRunner, output_dir
            )
            
            # 生成组织级别报告
            report_path = self._generate_organization_report(context, output_dir)
            
            logger.info(f"{platform_name}组织分析完成！")
            logger.info(f"组织报告路径: {report_path}")
            
            return report_path
            
        except Exception as e:
            logger.error(f"{platform_name}组织分析过程中发生错误: {e}")
            raise
    
    def _detect_project_info(self, project_path: str) -> ProjectInfo:
        """检测项目信息"""
        logger.info("检测项目基本信息...")
        
        project_info = self.project_detector.detect_project_info(project_path)
        
        # 记录检测结果
        logger.info(f"项目名称: {project_info.name}")
        logger.info(f"主要语言: {project_info.get_primary_language()}")
        logger.info(f"项目结构: {project_info.structure_type.value if hasattr(project_info.structure_type, 'value') else str(project_info.structure_type)}")
        logger.info(f"项目类型: {project_info.project_type.value if hasattr(project_info.project_type, 'value') else str(project_info.project_type)}")
        logger.info(f"代码规模: {project_info.size_metrics.get_size_category()}")
        logger.info(f"检测置信度: {project_info.confidence:.2f}")
        
        if project_info.confidence < 0.5:
            logger.warning(f"项目检测置信度较低: {project_info.confidence:.2f}")
        
        return project_info
    
    def _discover_tools(self) -> List:
        """发现可用工具"""
        if not self.current_project_info:
            raise ValueError("项目信息未初始化")
        
        logger.info("发现项目适用的工具...")
        
        # 发现可用工具
        available_tools = self.tool_executor.discover_available_tools(self.current_project_info)
        
        logger.info(f"发现 {len(available_tools)} 个可用工具")
        
        # 按类别统计工具
        tool_categories = {}
        for tool in available_tools:
            for category in tool.categories:
                if category not in tool_categories:
                    tool_categories[category] = []
                tool_categories[category].append(tool.name)
        
        for category, tools in tool_categories.items():
            logger.info(f"  {category}: {', '.join(tools)}")
        
        return available_tools
    
    def _intelligent_tool_selection(self, available_tools: List) -> List:
        """智能工具选择（使用DecisionAgent）"""
        if not self.current_project_info:
            raise ValueError("项目信息未初始化")
        
        logger.info("使用DecisionAgent进行智能工具选择...")
        
        try:
            # 使用DecisionAgent进行智能工具选择
            selected_tools = self.decision_agent.make_tool_selection_decision(
                self.current_project_info, available_tools)
            
            logger.info(f"智能选择结果: 从{len(available_tools)}个可用工具中选择了{len(selected_tools)}个")
            
            # 按类别统计选中的工具
            tool_categories = {}
            for tool in selected_tools:
                for category in tool.categories:
                    if category not in tool_categories:
                        tool_categories[category] = []
                    tool_categories[category].append(tool.name)
            
            for category, tools in tool_categories.items():
                logger.info(f"  {category}: {', '.join(tools)}")
            
            # 计算预估执行时间
            estimated_time = sum(t.estimated_time for t in selected_tools)
            logger.info(f"预估执行时间: {estimated_time//60}分{estimated_time%60}秒")
            
            return selected_tools
            
        except Exception as e:
            logger.error(f"DecisionAgent工具选择失败: {e}")
            # 降级策略：返回前10个可用工具
            logger.warning("使用降级策略：选择前10个可用工具")
            return available_tools[:10]
    
    def _create_execution_plan(self, selected_tools: List) -> ExecutionPlan:
        """创建执行计划（使用DecisionAgent）"""
        if not self.current_project_info:
            raise ValueError("项目信息未初始化")
        
        logger.info("使用DecisionAgent制定智能执行计划...")
        
        try:
            # 使用DecisionAgent创建执行计划
            decision_execution_plan = self.decision_agent.create_execution_plan(
                selected_tools, self.current_project_info)
            
            # 转换为传统执行计划格式以保持兼容性
            execution_plan = self._convert_to_legacy_execution_plan(decision_execution_plan)
            
        except Exception as e:
            logger.error(f"DecisionAgent执行计划制定失败: {e}")
            # 降级策略：使用传统执行计划
            logger.warning("使用降级策略：传统执行计划")
            execution_plan = self.tool_executor.create_execution_plan(
                selected_tools, self.current_project_info)
        
        logger.info(f"执行计划包含 {len(execution_plan.phases)} 个阶段")
        logger.info(f"预估总耗时: {execution_plan.get_total_estimated_time()//60} 分钟")
        logger.info(f"最大并行工具数: {getattr(execution_plan, 'max_parallel_tools', 4)}")
        
        # 打印各阶段信息
        for i, phase in enumerate(execution_plan.phases, 1):
            phase_mode = getattr(phase, 'mode', None)
            if hasattr(phase_mode, 'value'):
                mode_str = phase_mode.value
            else:
                mode_str = str(phase_mode) if phase_mode else 'unknown'
            logger.info(f"  阶段{i}: {phase.name} ({len(phase.tools)} 个工具, {mode_str})")
        
        return execution_plan
    
    def _convert_to_legacy_execution_plan(self, decision_plan) -> ExecutionPlan:
        """转换DecisionAgent的执行计划为传统格式"""
        from .tool_executor import ExecutionPhase as LegacyPhase, ExecutionMode as LegacyMode
        
        legacy_phases = []
        
        for phase in decision_plan.phases:
            # 转换执行模式
            if hasattr(phase, 'mode'):
                if phase.mode.value == 'parallel':
                    legacy_mode = LegacyMode.PARALLEL
                elif phase.mode.value == 'sequential':
                    legacy_mode = LegacyMode.SEQUENTIAL
                else:
                    legacy_mode = LegacyMode.HYBRID
            else:
                legacy_mode = LegacyMode.PARALLEL
            
            legacy_phase = LegacyPhase(
                name=phase.name,
                tools=phase.tools,
                mode=legacy_mode,
                timeout=getattr(phase, 'timeout', 300),
                continue_on_failure=getattr(phase, 'allow_failure', True)
            )
            legacy_phases.append(legacy_phase)
        
        return ExecutionPlan(
            phases=legacy_phases,
            total_estimated_time=decision_plan.total_estimated_time,
            max_parallel_tools=getattr(decision_plan, 'max_parallel_tools', 4),
            early_termination_conditions=getattr(decision_plan, 'early_termination_conditions', []),
            fallback_strategy=getattr(decision_plan, 'fallback_strategy', 'continue')
        )
    
    def _execute_tools(self, execution_plan: ExecutionPlan, project_path: str) -> Dict:
        """执行工具分析（混合模式：传统工具执行器 + 插件系统）"""
        logger.info("开始执行工具分析...")
        
        # 传统工具执行（保持向后兼容）
        logger.info("执行传统工具分析")
        tool_results = self.tool_executor.execute_tools(execution_plan, project_path)
        
        # 插件系统执行（智能分析）
        logger.info("执行插件系统智能分析")
        plugin_results = self._execute_plugins(project_path)
        
        # 合并结果
        combined_results = tool_results.copy()
        
        # 将插件结果转换为工具结果格式以保持兼容性
        for plugin_name, plugin_result in plugin_results.items():
            # 为每个插件的工具结果添加到总结果中
            for tool_name, tool_result in plugin_result.tool_results.items():
                # 使用插件前缀避免命名冲突
                combined_tool_name = f"{plugin_name}_{tool_name}"
                combined_results[combined_tool_name] = tool_result
        
        # 更新统计信息
        executor_stats = self.tool_executor.get_execution_stats()
        plugin_stats = self._get_plugin_stats(plugin_results)
        
        self.execution_stats.update({
            'phases_completed': len(execution_plan.phases),
            'tools_executed': executor_stats.get('total_tools', 0) + plugin_stats['total_tools'],
            'tools_successful': executor_stats.get('successful_tools', 0) + plugin_stats['successful_tools'],
            'tools_failed': executor_stats.get('failed_tools', 0) + plugin_stats['failed_tools'],
            'plugins_executed': plugin_stats['plugins_executed'],
            'plugins_successful': plugin_stats['plugins_successful']
        })
        
        # 工具执行完成，准备生成报告
        logger.info("所有工具执行完成，开始生成报告")
        
        return combined_results
    
    def _execute_plugins(self, project_path: str) -> Dict:
        """执行插件分析"""
        if not self.current_project_info:
            raise ValueError("项目信息未初始化")
        
        # 获取适用的插件
        plugins = self.plugin_registry.get_plugins_for_project(self.current_project_info)
        
        if not plugins:
            logger.info("未找到适用的语言插件")
            return {}
        
        logger.info(f"发现 {len(plugins)} 个适用的语言插件: {[p.name for p in plugins]}")
        
        # 获取可用工具
        available_tools = self.tool_executor.discover_available_tools(self.current_project_info)
        
        # 安全执行插件
        plugin_results = self.plugin_registry.execute_plugins_safely(
            plugins, project_path, self.current_project_info, available_tools
        )
        
        # 记录插件执行结果
        for plugin_name, result in plugin_results.items():
            if result.success:
                logger.info(f"✅ 插件 {plugin_name} 执行成功 (质量分数: {result.quality_score:.1f})")
            else:
                logger.warning(f"❌ 插件 {plugin_name} 执行失败: {len(result.errors)} 个错误")
        
        return plugin_results
    
    def _get_plugin_stats(self, plugin_results: Dict) -> Dict[str, int]:
        """获取插件执行统计信息"""
        stats = {
            'plugins_executed': len(plugin_results),
            'plugins_successful': 0,
            'total_tools': 0,
            'successful_tools': 0,
            'failed_tools': 0
        }
        
        for result in plugin_results.values():
            if result.success:
                stats['plugins_successful'] += 1
            
            stats['total_tools'] += len(result.tool_results)
            stats['successful_tools'] += len([tr for tr in result.tool_results.values() if tr.success])
            stats['failed_tools'] += len([tr for tr in result.tool_results.values() if not tr.success])
        
        return stats
    
    def _generate_reports(self, tool_results: Dict, output_dir: str) -> str:
        """生成智能增强审计报告"""
        if not self.current_project_info:
            raise ValueError("项目信息未初始化")
        
        logger.info("阶段7: 智能分析与报告生成...")
        
        try:
            # 自适应评分优化
            logger.info("7.1: AdaptiveAgent 自适应评分优化")
            adaptive_scoring_model = self.adaptive_agent.adapt_scoring_model(
                self.current_project_info, tool_results)
            
            optimization_actions = self.adaptive_agent.optimize_analysis_process(
                tool_results, self.current_project_info)
            
            logger.info(f"自适应评分完成, 信心度: {adaptive_scoring_model.confidence_level:.2f}")
            
            # 智能推荐生成
            logger.info("7.2: RecommendationAgent 生成智能推荐")
            
            # 准备分析结果
            from .recommendation_agent import AnalysisResults, Issue, IssueSeverity, ImpactLevel
            
            all_issues = self._extract_issues_from_results(tool_results)
            analysis_results = AnalysisResults(
                all_issues=all_issues,
                tool_results=tool_results,
                overall_score=self._calculate_overall_score(tool_results),
                dimension_scores=self._calculate_dimension_scores(tool_results)
            )
            
            intelligent_recommendations = self.recommendation_agent.generate_intelligent_recommendations(
                analysis_results, self.current_project_info, adaptive_scoring_model)
            
            logger.info(f"智能推荐生成完成: {len(intelligent_recommendations.recommendations)}个建议, "
                       f"路线图{len(intelligent_recommendations.roadmap.phases)}个阶段")
            
            # 准备输出目录
            output_path = pathlib.Path(output_dir) if output_dir else None
            project_path = pathlib.Path(self.current_project_info.path)
            
            if output_path and output_path.exists() and output_path.samefile(project_path):
                # 输出目录就是项目目录，使用当前工作目录的reports
                reports_dir = pathlib.Path.cwd() / "reports" / self.current_project_info.name
            else:
                # 使用指定的输出目录
                reports_dir = output_path / self.current_project_info.name if output_path else pathlib.Path.cwd() / "reports" / self.current_project_info.name
            
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            # 智能增强版报告生成 - 集成智能推荐和自适应评分
            logger.info("7.3: 生成智能增强版审计报告")
            report_path = self.report_generator.generate_adaptive_audit_report(
                project_info=self.current_project_info,
                tool_results=tool_results,
                execution_stats=self.execution_stats,
                adaptive_scoring_model=adaptive_scoring_model,
                intelligent_recommendations=intelligent_recommendations,
                optimization_actions=optimization_actions,
                output_dir=str(reports_dir)
            )
            
            return report_path
            
        except Exception as e:
            logger.error(f"报告生成时发生错误: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _generate_organization_report(self, context, output_dir: Optional[str] = None) -> str:
        """生成GitHub组织分析报告"""
        from ..utils.git_platform_analyzer import OrgAnalysisContext
        
        # 确定输出目录
        if not output_dir:
            output_dir = "reports"
        
        org_report_dir = os.path.join(output_dir, f"github-org-{context.org_name}")
        os.makedirs(org_report_dir, exist_ok=True)
        
        # 生成HTML报告
        html_content = self._generate_org_html_report(context)
        html_path = os.path.join(org_report_dir, f"{context.org_name}_organization_report.html")
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 生成JSON数据
        json_data = {
            'organization_info': {
                'name': context.org_name,
                'total_repositories': context.total_repos,
                'analyzed_repositories': context.analyzed_repos,
                'failed_repositories': context.failed_repos
            },
            'aggregate_metrics': context.aggregate_metrics,
            'repository_results': context.analysis_results,
            'repositories': [
                {
                    'name': repo.name,
                    'full_name': repo.full_name,
                    'description': repo.description,
                    'language': repo.language,
                    'stars': repo.stars,
                    'forks': repo.forks,
                    'size': repo.size
                } 
                for repo in context.repos
            ]
        }
        
        import json
        json_path = os.path.join(org_report_dir, f"{context.org_name}_organization_data.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"组织报告已生成: {html_path}")
        logger.info(f"组织数据已保存: {json_path}")
        
        return html_path
    
    def _generate_org_html_report(self, context) -> str:
        """生成GitHub组织HTML报告"""
        metrics = context.aggregate_metrics
        
        # 构建仓库表格行
        repo_rows = []
        for repo in context.repos:
            result = context.analysis_results.get(repo.name, {})
            score = result.get('overall_score', 'N/A')
            status = result.get('overall_status', 'UNKNOWN')
            
            status_color = {
                'EXCELLENT': '#28a745',
                'GOOD': '#ffc107', 
                'FAIR': '#fd7e14',
                'POOR': '#dc3545',
                'UNKNOWN': '#6c757d'
            }.get(status, '#6c757d')
            
            repo_rows.append(f"""
                <tr>
                    <td><a href="{repo.html_url}" target="_blank">{repo.name}</a></td>
                    <td>{repo.description or 'N/A'}</td>
                    <td>{repo.language or 'N/A'}</td>
                    <td>{repo.stars}</td>
                    <td>{repo.forks}</td>
                    <td><span class="badge" style="background-color: {status_color}">{status}</span></td>
                    <td><strong>{score if isinstance(score, (int, float)) else 'N/A'}</strong></td>
                </tr>
            """)
        
        # 构建语言分布图表数据
        lang_data = []
        if 'languages' in metrics:
            for lang, percentage in list(metrics['languages'].items())[:10]:  # 前10种语言
                lang_data.append(f"['{lang}', {percentage:.2f}]")
        
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{context.org_name} - GitHub组织分析报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            min-height: 100vh; 
            color: #212529;
            line-height: 1.6;
        }}
        .container {{ 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 16px; 
            box-shadow: 0 20px 40px rgba(0,0,0,0.1), 0 4px 8px rgba(0,0,0,0.05); 
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.8);
        }}
        .header {{ 
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); 
            color: white; 
            padding: 40px 30px; 
            position: relative;
        }}
        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, rgba(39,174,96,0.1) 0%, rgba(46,204,113,0.1) 100%);
        }}
        .header h1 {{ position: relative; z-index: 1; margin: 0 0 10px 0; }}
        .header p {{ position: relative; z-index: 1; opacity: 0.9; margin: 5px 0; }}
        .content {{ padding: 40px; }}
        .summary-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); 
            gap: 24px; 
            margin: 30px 0; 
        }}
        .summary-card {{ 
            background: linear-gradient(135deg, #fff 0%, #fcfcfc 100%); 
            padding: 28px; 
            border-radius: 16px; 
            text-align: center; 
            border: 1px solid rgba(233,236,239,0.8);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }}
        .summary-card:hover {{
            transform: translateY(-4px) scale(1.02);
            box-shadow: 0 12px 24px rgba(0,0,0,0.12), 0 4px 8px rgba(0,0,0,0.06);
        }}
        .summary-card h3 {{ 
            margin: 0 0 15px 0; 
            color: #2c3e50; 
            font-size: 1.1em;
            font-weight: 600;
        }}
        .summary-card .value {{ 
            font-size: 2.2em; 
            font-weight: 700; 
            color: #27ae60;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .chart-container {{
            max-width: 400px;
            margin: 20px auto;
        }}
        table {{ 
            width: 100%; 
            border-collapse: collapse; 
            margin: 25px 0; 
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 8px 16px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);
            border: 1px solid rgba(233,236,239,0.6);
        }}
        th, td {{ 
            padding: 18px 16px; 
            text-align: left; 
            border-bottom: 1px solid rgba(233,236,239,0.6); 
        }}
        th {{ 
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); 
            color: white;
            font-weight: 600; 
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.8px;
        }}
        tr:hover {{ 
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            transition: background 0.2s ease;
        }}
        .badge {{ 
            padding: 6px 12px; 
            border-radius: 20px; 
            color: white; 
            font-size: 0.875em; 
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .section {{ margin: 40px 0; }}
        .section h2 {{ 
            color: #2c3e50; 
            border-bottom: 3px solid #27ae60; 
            padding-bottom: 12px; 
            font-size: 1.8em;
            font-weight: 700;
            margin-bottom: 25px;
        }}
        a {{ color: #27ae60; text-decoration: none; }}
        a:hover {{ color: #1e8449; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{context.org_name} - GitHub组织分析报告</h1>
            <p>组织级别开源项目成熟度评估</p>
            <p>分析时间: {__import__('time').strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>组织概览</h2>
                <div class="summary-grid">
                    <div class="summary-card">
                        <h3>总仓库数</h3>
                        <div class="value">{context.total_repos}</div>
                    </div>
                    <div class="summary-card">
                        <h3>分析成功</h3>
                        <div class="value">{context.analyzed_repos}</div>
                    </div>
                    <div class="summary-card">
                        <h3>分析失败</h3>
                        <div class="value" style="color: #e74c3c">{context.failed_repos}</div>
                    </div>
                    <div class="summary-card">
                        <h3>成功率</h3>
                        <div class="value">{metrics.get('success_rate', 0):.1%}</div>
                    </div>
                </div>
            </div>
            
            {'<div class="section"><h2>技术栈分布</h2><div class="chart-container"><canvas id="languageChart"></canvas></div></div>' if lang_data else ''}
            
            {'<div class="section"><h2>质量指标</h2><div class="summary-grid"><div class="summary-card"><h3>平均分</h3><div class="value">' + f"{metrics['average_scores']['overall']:.1f}" + '</div></div><div class="summary-card"><h3>最高分</h3><div class="value">' + f"{metrics['average_scores']['max']:.1f}" + '</div></div><div class="summary-card"><h3>最低分</h3><div class="value">' + f"{metrics['average_scores']['min']:.1f}" + '</div></div></div></div>' if 'average_scores' in metrics else ''}
            
            <div class="section">
                <h2>仓库详情</h2>
                <table>
                    <thead>
                        <tr>
                            <th>仓库名</th>
                            <th>描述</th>
                            <th>语言</th>
                            <th>星标</th>
                            <th>分支</th>
                            <th>状态</th>
                            <th>得分</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(repo_rows)}
                    </tbody>
                </table>
            </div>
            
            {'<div class="section"><h2>TOP 10 仓库</h2><ol>' + ''.join([f'<li><strong>{name}</strong> - {score:.1f}分 ({status})</li>' for name, score, status in metrics.get('top_repositories', [])[:10]]) + '</ol></div>' if 'top_repositories' in metrics else ''}
        </div>
    </div>

    {'<script>const ctx = document.getElementById("languageChart").getContext("2d");new Chart(ctx, {type: "doughnut", data: {labels: [' + ', '.join([f'"{lang}"' for lang, _ in list(metrics['languages'].items())[:10]]) + '], datasets: [{data: [' + ', '.join([f'{percentage:.2f}' for _, percentage in list(metrics['languages'].items())[:10]]) + '], backgroundColor: ["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c", "#34495e", "#e67e22", "#95a5a6", "#f1c40f"]}]}, options: {responsive: true, plugins: {legend: {position: "bottom"}}}});</script>' if lang_data else ''}
</body>
</html>
        """
    
    def _analyze_performance_and_create_baseline(self, profiler, project_name: str, project_type: str):
        """分析性能并创建/更新基线"""
        try:
            # 获取性能统计
            stats = self.profiler.get_operation_stats("full_audit")
            if not stats:
                logger.warning("无法获取性能统计信息")
                return
            
            # 性能优化分析
            optimization_analysis = self.performance_optimizer.analyze_performance(stats)
            performance_score = optimization_analysis['performance_score']
            performance_level = optimization_analysis['performance_level']
            
            logger.info(f"📊 性能分析完成 - 性能评分: {performance_score}/100 ({performance_level})")
            
            if optimization_analysis['issues']:
                logger.warning(f"⚠️  发现 {len(optimization_analysis['issues'])} 个性能问题")
                for issue in optimization_analysis['issues'][:3]:  # 只显示前3个
                    logger.warning(f"   - {issue}")
            
            if optimization_analysis['recommendations']:
                logger.info("💡 性能优化建议:")
                for rec in optimization_analysis['recommendations'][:3]:  # 只显示前3个
                    logger.info(f"   - {rec}")
            
            # 创建或更新性能基线
            baseline_key = f"{project_name}_{project_type}"
            project_characteristics = {
                "project_name": project_name,
                "project_type": project_type,
                "files_count": stats.get('custom_metrics', {}).get('project_files_count', [{}])[-1].get('value', 0) if stats.get('custom_metrics', {}).get('project_files_count') else 0,
                "languages_count": stats.get('custom_metrics', {}).get('project_languages_count', [{}])[-1].get('value', 0) if stats.get('custom_metrics', {}).get('project_languages_count') else 0,
                "tools_executed": self.execution_stats.get('tools_executed', 0)
            }
            
            # 检查是否存在基线
            existing_baseline = self.baseline_manager.get_baseline(baseline_key)
            if existing_baseline:
                # 与基线比较
                comparison = self.baseline_manager.compare_with_baseline(baseline_key, stats)
                if comparison.get('overall_within_tolerance'):
                    logger.info("✅ 性能表现符合历史基线预期")
                else:
                    logger.warning("⚠️  性能表现偏离历史基线")
                    for metric, result in comparison.get('results', {}).items():
                        if not result['within_tolerance']:
                            diff = result['diff_percent']
                            logger.warning(f"   {metric}: 偏差 {diff:.1f}%")
            else:
                # 创建新基线
                baseline = self.baseline_manager.create_baseline(
                    baseline_key, stats, project_characteristics
                )
                logger.info(f"📋 创建性能基线: {baseline_key}")
            
        except Exception as e:
            logger.warning(f"性能分析失败: {e}")
    
    def _cleanup(self):
        """清理资源"""
        logger.debug("清理审计运行器资源...")
        # 这里可以添加资源清理逻辑
        pass
    
    def get_supported_languages(self) -> List[str]:
        """获取支持的编程语言列表"""
        registry = get_tool_registry()
        return registry.get_supported_languages()
    
    def get_tool_categories(self) -> List[str]:
        """获取工具分类列表"""
        registry = get_tool_registry()
        return registry.get_tool_categories()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        default_config = {
            'project': {
                'type': 'unknown',
                'description': ''
            },
            'tools': {
                'disabled': [],
                'enabled': [],
                'configs': {}
            },
            'dimensions': {
                'security': {'weight': 0.25, 'enabled': True},
                'quality': {'weight': 0.25, 'enabled': True},
                'testing': {'weight': 0.20, 'enabled': True},
                'documentation': {'weight': 0.15, 'enabled': True},
                'performance': {'weight': 0.15, 'enabled': True}
            },
            'exclude': {
                'paths': ['node_modules/', 'venv/', '.git/', '__pycache__/'],
                'files': ['*.min.js', '*.pyc', '*.log']
            },
            'reports': {
                'formats': ['html', 'json'],
                'output_dir': 'reports/',
                'detail_level': 'full'
            },
            'advanced': {
                'parallelism': {'max_workers': 4},
                'timeout_multiplier': 1.0
            }
        }
        return default_config
    
    def _load_project_config(self, project_path: str) -> Dict[str, Any]:
        """加载项目特定配置（可选）"""
        config_files = ['.oss-audit.yaml', '.oss-audit.yml', 'oss-audit.yaml']
        project_path_obj = pathlib.Path(project_path)
        
        for config_file in config_files:
            config_path = project_path_obj / config_file
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        project_config = yaml.safe_load(f)
                    logger.info(f"✅ 发现项目配置文件: {config_path.name}")
                    return project_config or {}
                except Exception as e:
                    logger.warning(f"⚠️ 项目配置文件解析失败 {config_path}: {e}")
        
        logger.info("ℹ️ 零配置模式 - 使用智能默认设置")
        return {}
    
    def _generate_smart_config(self, project_info: ProjectInfo) -> Dict[str, Any]:
        """根据项目信息生成智能配置"""
        smart_config = {
            'project': {
                'name': project_info.name,
                'type': project_info.project_type.value if hasattr(project_info.project_type, 'value') else str(project_info.project_type),
                'description': f"自动检测的{project_info.project_type.value if hasattr(project_info.project_type, 'value') else str(project_info.project_type)}项目"
            }
        }
        
        # 根据项目类型调整维度权重
        project_type_str = project_info.project_type.value if hasattr(project_info.project_type, 'value') else str(project_info.project_type)
        if project_type_str == 'web_application':
            smart_config['dimensions'] = {
                'security': {'weight': 0.30, 'enabled': True},
                'quality': {'weight': 0.25, 'enabled': True},
                'performance': {'weight': 0.20, 'enabled': True},
                'testing': {'weight': 0.15, 'enabled': True},
                'documentation': {'weight': 0.10, 'enabled': True}
            }
        elif project_type_str == 'library':
            smart_config['dimensions'] = {
                'quality': {'weight': 0.30, 'enabled': True},
                'documentation': {'weight': 0.25, 'enabled': True},
                'testing': {'weight': 0.20, 'enabled': True},
                'security': {'weight': 0.15, 'enabled': True},
                'performance': {'weight': 0.10, 'enabled': True}
            }
        elif project_type_str == 'cli_tool':
            smart_config['dimensions'] = {
                'quality': {'weight': 0.25, 'enabled': True},
                'documentation': {'weight': 0.20, 'enabled': True},
                'testing': {'weight': 0.20, 'enabled': True},
                'performance': {'weight': 0.15, 'enabled': True},
                'security': {'weight': 0.20, 'enabled': True}
            }
        
        # 根据项目规模调整并行度
        code_lines = project_info.size_metrics.code_lines
        if code_lines > 10000:
            smart_config['advanced'] = {'parallelism': {'max_workers': 6}}
        elif code_lines > 5000:
            smart_config['advanced'] = {'parallelism': {'max_workers': 4}}
        else:
            smart_config['advanced'] = {'parallelism': {'max_workers': 2}}
        
        # 根据主要语言调整工具选择
        primary_language = project_info.get_primary_language()
        if primary_language:
            smart_config['tools'] = {'enabled': []}
            if primary_language == 'python':
                smart_config['tools']['enabled'] = ['pylint', 'mypy', 'bandit', 'pytest', 'coverage']
            elif primary_language in ['javascript', 'typescript']:
                smart_config['tools']['enabled'] = ['eslint', 'prettier', 'jest']
            elif primary_language == 'java':
                smart_config['tools']['enabled'] = ['checkstyle', 'spotbugs', 'junit']
        
        return smart_config
    
    def _merge_configs(self, default_config: Dict[str, Any], 
                      smart_config: Dict[str, Any],
                      project_config: Dict[str, Any], 
                      overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """合并配置（项目配置覆盖默认配置，覆盖参数优先级最高）"""
        merged_config = default_config.copy()
        
        # 递归合并字典
        def deep_merge(target: dict, source: dict):
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    deep_merge(target[key], value)
                else:
                    target[key] = value
        
        # 合并智能配置
        if smart_config:
            deep_merge(merged_config, smart_config)
        
        # 合并项目配置
        if project_config:
            deep_merge(merged_config, project_config)
        
        # 合并覆盖配置
        if overrides:
            deep_merge(merged_config, overrides)
        
        return merged_config
    
    # ========== 智能分析辅助方法 ==========
    
    def _extract_issues_from_results(self, tool_results: Dict) -> List:
        """从工具结果中提取问题列表"""
        try:
            from .recommendation_agent import Issue, IssueSeverity, ImpactLevel
            
            all_issues = []
            issue_id = 1
            
            for tool_name, result in tool_results.items():
                if result.get('success', False) and 'issues' in result:
                    for issue_data in result['issues']:
                        try:
                            # 解析严重程度
                            severity_str = issue_data.get('severity', 'medium').lower()
                            severity_map = {
                                'critical': IssueSeverity.CRITICAL,
                                'high': IssueSeverity.HIGH,
                                'medium': IssueSeverity.MEDIUM,
                                'low': IssueSeverity.LOW,
                                'info': IssueSeverity.INFO
                            }
                            severity = severity_map.get(severity_str, IssueSeverity.MEDIUM)
                            
                            # 解析影响程度
                            if severity == IssueSeverity.CRITICAL:
                                impact_level = ImpactLevel.BREAKING
                            elif severity == IssueSeverity.HIGH:
                                impact_level = ImpactLevel.MAJOR
                            elif severity == IssueSeverity.MEDIUM:
                                impact_level = ImpactLevel.MINOR
                            else:
                                impact_level = ImpactLevel.NEGLIGIBLE
                            
                            issue = Issue(
                                id=f"issue_{issue_id}",
                                title=issue_data.get('message', f'Issue from {tool_name}'),
                                description=issue_data.get('description', issue_data.get('message', '')),
                                severity=severity,
                                category=issue_data.get('category', tool_name),
                                file_path=issue_data.get('filename', issue_data.get('file')),
                                line_number=issue_data.get('line', issue_data.get('line_number')),
                                tool_source=tool_name,
                                fix_effort=self._estimate_fix_effort(issue_data, severity),
                                impact_level=impact_level
                            )
                            
                            all_issues.append(issue)
                            issue_id += 1
                            
                        except Exception as e:
                            logger.warning(f"解析问题失败 ({tool_name}): {e}")
                            continue
            
            logger.debug(f"从工具结果中提取了{len(all_issues)}个问题")
            return all_issues
            
        except Exception as e:
            logger.error(f"问题提取失败: {e}")
            return []
    
    def _estimate_fix_effort(self, issue_data: Dict, severity) -> str:
        """估算修复工作量"""
        from .recommendation_agent import IssueSeverity
        if severity == IssueSeverity.CRITICAL:
            return "high"
        elif severity == IssueSeverity.HIGH:
            return "medium"  
        elif severity == IssueSeverity.MEDIUM:
            return "medium"
        else:
            return "low"
    
    def _calculate_overall_score(self, tool_results: Dict) -> float:
        """计算整体分数"""
        try:
            scores = []
            for result in tool_results.values():
                if result.get('success', False) and 'score' in result:
                    scores.append(float(result['score']))
            
            if scores:
                return sum(scores) / len(scores)
            else:
                return 50.0  # 默认分数
                
        except Exception as e:
            logger.error(f"整体分数计算失败: {e}")
            return 50.0
    
    def _calculate_dimension_scores(self, tool_results: Dict) -> Dict[str, float]:
        """计算维度分数"""
        try:
            dimension_scores = {
                'security': 50.0,
                'quality': 50.0,
                'testing': 50.0,
                'performance': 50.0,
                'documentation': 50.0
            }
            
            # 基于工具类型计算维度分数
            for tool_name, result in tool_results.items():
                if not result.get('success', False) or 'score' not in result:
                    continue
                
                score = float(result['score'])
                
                # 根据工具名称推断维度
                if 'bandit' in tool_name or 'security' in tool_name.lower():
                    dimension_scores['security'] = score
                elif 'pylint' in tool_name or 'eslint' in tool_name:
                    dimension_scores['quality'] = score
                elif 'test' in tool_name.lower() or 'coverage' in tool_name:
                    dimension_scores['testing'] = score
            
            return dimension_scores
            
        except Exception as e:
            logger.error(f"维度分数计算失败: {e}")
            return {'quality': 50.0}
    
    def validate_project_path(self, project_path: str) -> bool:
        """验证项目路径（支持Git URL和GitHub组织URL）"""
        # 如果是Git URL，暂时返回True，实际验证在resolve_project_path中
        if GitUtils.is_git_url(project_path):
            return True
        
        # 如果是支持的Git平台组织URL，验证组织是否存在
        if self.multi_platform_analyzer.is_supported_org_url(project_path):
            org_name = self.multi_platform_analyzer.extract_org_name(project_path)
            if not org_name:
                platform = self.multi_platform_analyzer.extract_platform_name(project_path)
                logger.error(f"无效的{platform}组织URL: {project_path}")
                return False
            return True
            
        # 本地路径验证
        path = pathlib.Path(project_path)
        
        if not path.exists():
            logger.error(f"项目路径不存在: {project_path}")
            return False
        
        if not path.is_dir():
            logger.error(f"项目路径不是目录: {project_path}")
            return False
        
        # 检查是否为空目录
        if not any(path.iterdir()):
            logger.warning(f"项目目录为空: {project_path}")
            return False
        
        return True


def print_help():
    """打印帮助信息"""
    print("OSS Audit 2.0 - 开源软件成熟度评估工具")
    print()
    print("用法:")
    print("    python main.py <项目路径/Git URL/Git平台组织URL> [输出目录]")
    print("    python -m oss_audit.core.audit_runner <项目路径/Git URL/Git平台组织URL> [输出目录]")
    print("    oss-audit <项目路径/Git URL/Git平台组织URL> [输出目录]        # 安装后可用")
    print()
    print("参数:")
    print("    项目路径/URL  要分析的项目目录路径、Git仓库URL或Git平台组织URL（必需）")
    print("    输出目录     报告输出目录（可选，默认为 reports/）")
    print()
    print("选项:")
    print("    -h, --help   显示此帮助信息")
    print()
    print("特性:")
    print("    - 零配置运行 - 无需配置文件，智能分析")
    print("    - 多语言支持 - Python、JavaScript、TypeScript、Java、Go、Rust、C++")
    print("    - 智能检测   - 自动识别项目类型和特征")
    print("    - Git仓库支持 - 直接分析GitHub/GitLab/Gitee/Gitea仓库")
    print("    - 多平台组织分析 - 批量分析GitHub/GitLab/Gitee/Gitea组织下所有仓库 (NEW!)")
    print("    - Monorepo支持 - 多项目仓库结构智能分析")
    print("    - AI增强     - 可选的AI分析增强功能")
    print()
    print("示例:")
    print("    # 本地项目")
    print("    python main.py ./my-python-project")
    print("    python main.py ./my-js-app ./custom-reports")
    print("    python main.py ../enterprise-project")
    print("    ")
    print("    # Git仓库")
    print("    python main.py https://github.com/user/repo.git")
    print("    python main.py git@github.com:user/repo.git")
    print("    ")
    print("    # 多平台组织分析 (NEW!)")
    print("    python main.py https://github.com/Netflix")
    print("    python main.py https://gitlab.com/gitlab-org")
    print("    python main.py https://gitee.com/openharmony")
    print("    python main.py https://gitea.io/gitea-org ./reports")
    print()
    print("更多信息: https://gitee.com/oss-audit/oss-audit")


def setup_logging(level: str = "INFO"):
    """设置日志配置"""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    # 配置日志格式
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 设置第三方库日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)




def main():
    """主函数 - 命令行入口"""
    
    # 设置日志
    setup_logging(os.environ.get('LOG_LEVEL', 'INFO'))
    
    logger.info("OSS Audit 2.0 - 开源软件成熟度评估工具")
    logger.info("智能增强版: DecisionAgent, AdaptiveAgent, RecommendationAgent 集成")
    
    # 解析命令行参数
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help', 'help']:
        print_help()
        sys.exit(0)
    
    project_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        # 创建审计运行器
        runner = AuditRunner()
        
        # 验证项目路径
        if not runner.validate_project_path(project_path):
            logger.error("项目路径验证失败")
            sys.exit(1)
        
        # 检查是否为支持的Git平台组织URL
        if runner.multi_platform_analyzer.is_supported_org_url(project_path):
            platform_name = runner.multi_platform_analyzer.extract_platform_name(project_path)
            org_name = runner.multi_platform_analyzer.extract_org_name(project_path)
            
            # 执行Git组织分析
            report_path = runner.analyze_git_organization(project_path, output_dir)
            
            print(f"\n✅ {platform_name}组织分析完成！")
            print(f"📊 报告路径: {report_path}")
            print(f"🏢 组织: {org_name}")
            
            return True
        else:
            # 解析项目路径（支持Git URL）
            actual_project_path, is_temp = resolve_project_path(project_path)
            
            try:
                # 执行审计
                report_path = runner.audit_project(actual_project_path, output_dir)
                
                print(f"\n✅ 审计完成！")
                print(f"📊 报告路径: {report_path}")
                print(f"⏱️  总耗时: {runner.execution_stats['total_duration']:.1f}s")
                
                if GitUtils.is_git_url(project_path):
                    print(f"🌐 源仓库: {project_path}")
                
                return True
                
            finally:
                # 清理临时目录
                if is_temp:
                    GitUtils.cleanup_temp_repo(actual_project_path)
        
    except KeyboardInterrupt:
        logger.info("审计被用户中断")
        return False
        
    except Exception as e:
        logger.error(f"审计失败: {e}")
        return False