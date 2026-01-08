#!/usr/bin/env python3
"""
Dimension Analyzer - 维度分析器
完整的14维度分析系统，整合工具结果、AI分析和智能打分
"""

import logging
import json
import statistics
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .tool_executor import ToolResult
from .project_detector import ProjectInfo
from .smart_tool_selector import SmartToolSelector, create_smart_tool_selector

logger = logging.getLogger(__name__)


class DimensionStatus(Enum):
    """维度状态"""
    EXCELLENT = "EXCELLENT"  # 90-100分
    GOOD = "GOOD"           # 75-89分  
    WARN = "WARN"           # 50-74分
    POOR = "POOR"           # 25-49分
    CRITICAL = "CRITICAL"   # 0-24分


class AnalysisLevel(Enum):
    """分析级别"""
    BASIC = "basic"         # 仅工具结果
    ENHANCED = "enhanced"   # 工具结果 + 规则分析
    AI_POWERED = "ai"       # 工具结果 + AI分析


@dataclass
class DimensionIssue:
    """维度问题"""
    issue_id: str
    title: str
    description: str
    severity: str  # critical, high, medium, low
    category: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    tool_source: Optional[str] = None
    recommendation: Optional[str] = None


@dataclass
class DimensionInsight:
    """维度洞察"""
    insight_type: str  # trend, pattern, recommendation, warning
    title: str
    description: str
    impact: str  # high, medium, low
    suggestions: List[str] = field(default_factory=list)


@dataclass
class DimensionMetrics:
    """维度指标"""
    total_issues: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    tools_executed: int
    tools_successful: int
    coverage_percentage: float
    quality_trend: str  # improving, stable, declining


@dataclass
class DimensionAnalysisResult:
    """维度分析结果"""
    dimension_id: int
    dimension_name: str
    score: float
    status: DimensionStatus
    analysis_level: AnalysisLevel
    
    # 核心分析内容
    summary: str
    key_findings: List[str]
    issues: List[DimensionIssue]
    insights: List[DimensionInsight]
    metrics: DimensionMetrics
    
    # 工具层面数据
    tool_results: Dict[str, Dict[str, Any]]
    tools_used: List[str]
    
    # AI分析
    ai_analysis: Optional[str] = None
    ai_recommendations: List[str] = field(default_factory=list)
    
    # 元数据
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    analysis_duration: float = 0.0


class DimensionAnalyzer:
    """维度分析器"""
    
    # 14个维度定义
    DIMENSIONS = {
        1: {
            'name': '代码结构与可维护性',
            'description': '代码组织、模块化、可读性和可维护性评估',
            'tools': ['pylint', 'eslint', 'checkstyle', 'gofmt', 'sonarqube'],
            'weight': 0.15
        },
        2: {
            'name': '测试覆盖与质量保障', 
            'description': '测试完整性、覆盖率和质量保障机制',
            'tools': ['pytest', 'jest', 'junit', 'coverage', 'jacoco'],
            'weight': 0.12
        },
        3: {
            'name': '构建与工程可重复性',
            'description': '构建系统、依赖管理和环境一致性',
            'tools': ['maven', 'gradle', 'npm', 'pip', 'docker'],
            'weight': 0.10
        },
        4: {
            'name': '依赖与许可证合规',
            'description': '第三方依赖管理和许可证合规性检查',
            'tools': ['dependency-check', 'npm-audit', 'safety', 'licensee'],
            'weight': 0.08
        },
        5: {
            'name': '安全性与敏感信息防护',
            'description': '代码安全漏洞和敏感信息泄露检测',
            'tools': ['bandit', 'semgrep', 'gosec', 'gitleaks', 'trivy'],
            'weight': 0.13
        },
        6: {
            'name': 'CI/CD 自动化保障',
            'description': 'CI/CD流水线和自动化质量保障',
            'tools': ['github-actions', 'gitlab-ci', 'jenkins'],
            'weight': 0.08
        },
        7: {
            'name': '使用文档与复现性',
            'description': '文档完整性和项目复现能力评估',
            'tools': ['readme-analyzer', 'doc-coverage'],
            'weight': 0.07
        },
        8: {
            'name': '接口与平台兼容性',
            'description': 'API兼容性和跨平台支持评估',
            'tools': ['api-compatibility', 'cross-platform-test'],
            'weight': 0.06
        },
        9: {
            'name': '协作流程与代码规范',
            'description': '团队协作和代码规范一致性',
            'tools': ['git-flow-analyzer', 'commit-lint'],
            'weight': 0.05
        },
        10: {
            'name': '开源协议与法律合规',
            'description': '开源许可证和法律合规性审查',
            'tools': ['license-check', 'copyright-check'],
            'weight': 0.04
        },
        11: {
            'name': '社区治理与贡献机制',
            'description': '社区活跃度和贡献者治理机制',
            'tools': ['community-analyzer'],
            'weight': 0.04
        },
        12: {
            'name': '舆情与风险监控',
            'description': '项目声誉和潜在风险监控',
            'tools': ['reputation-analyzer'],
            'weight': 0.03
        },
        13: {
            'name': '数据与算法合规审核',
            'description': '数据处理和算法的合规性审核',
            'tools': ['data-compliance', 'algorithm-audit'],
            'weight': 0.03
        },
        14: {
            'name': 'IP（知识产权）',
            'description': '知识产权保护和侵权风险评估',
            'tools': ['ip-scanner', 'patent-check'],
            'weight': 0.02
        }
    }
    
    def __init__(self, analysis_level: AnalysisLevel = AnalysisLevel.ENHANCED):
        self.analysis_level = analysis_level
        self.ai_analyzer = None
        self.smart_tool_selector = create_smart_tool_selector()
        
        # 尝试加载AI分析器
        if analysis_level == AnalysisLevel.AI_POWERED:
            try:
                from ..utils.ai_analyzer import AIAnalyzer
                self.ai_analyzer = AIAnalyzer()
                logger.info("AI分析器已加载")
            except Exception as e:
                logger.warning(f"AI分析器不可用，降级为增强分析: {e}")
                self.analysis_level = AnalysisLevel.ENHANCED
    
    def analyze_dimension(self, dimension_id: int, 
                         tool_results: Dict[str, ToolResult],
                         project_info: ProjectInfo) -> DimensionAnalysisResult:
        """
        分析单个维度
        
        Args:
            dimension_id: 维度ID (1-14)
            tool_results: 工具执行结果
            project_info: 项目信息
            
        Returns:
            维度分析结果
        """
        start_time = datetime.now()
        
        if dimension_id not in self.DIMENSIONS:
            raise ValueError(f"无效的维度ID: {dimension_id}")
        
        dimension_config = self.DIMENSIONS[dimension_id]
        logger.info(f"开始分析维度 {dimension_id}: {dimension_config['name']}")
        
        # 1. 筛选相关工具结果
        relevant_tools = self._filter_relevant_tools(dimension_id, tool_results, project_info)
        
        # 2. 提取和标准化问题
        issues = self._extract_dimension_issues(dimension_id, relevant_tools)
        
        # 3. 计算维度指标
        metrics = self._calculate_dimension_metrics(relevant_tools, issues)
        
        # 4. 执行维度评分
        score = self._calculate_dimension_score(dimension_id, metrics, issues, project_info)
        
        # 5. 生成洞察和建议
        insights = self._generate_dimension_insights(dimension_id, metrics, issues, project_info)
        
        # 6. AI分析（如果可用）
        ai_analysis, ai_recommendations = self._perform_ai_analysis(
            dimension_id, relevant_tools, issues, project_info
        )
        
        # 7. 生成摘要和关键发现
        summary, key_findings = self._generate_dimension_summary(
            dimension_id, metrics, issues, insights
        )
        
        analysis_duration = (datetime.now() - start_time).total_seconds()
        
        result = DimensionAnalysisResult(
            dimension_id=dimension_id,
            dimension_name=dimension_config['name'],
            score=score,
            status=self._get_dimension_status(score),
            analysis_level=self.analysis_level,
            summary=summary,
            key_findings=key_findings,
            issues=issues,
            insights=insights,
            metrics=metrics,
            tool_results={name: self._serialize_tool_result(result) 
                         for name, result in relevant_tools.items()},
            tools_used=list(relevant_tools.keys()),
            ai_analysis=ai_analysis,
            ai_recommendations=ai_recommendations,
            analysis_timestamp=start_time,
            analysis_duration=analysis_duration
        )
        
        logger.info(f"维度 {dimension_id} 分析完成，得分: {score:.1f}, 状态: {result.status.value}")
        return result
    
    def _filter_relevant_tools(self, dimension_id: int, 
                              tool_results: Dict[str, ToolResult],
                              project_info: ProjectInfo) -> Dict[str, ToolResult]:
        """使用智能工具选择器筛选与维度相关的最优工具结果"""
        # 首先需要将ToolResult转换为Tool对象以供智能选择器使用
        from .tool_registry import Tool
        
        # 构造可用工具列表（基于实际执行的工具结果）
        available_tools = []
        for tool_name, result in tool_results.items():
            # 根据工具名称推测语言和优先级
            language = self._infer_tool_language(tool_name, project_info)
            priority = self._infer_tool_priority(tool_name)
            
            # 创建一个Tool对象用于选择
            tool = Tool(
                name=tool_name,
                command=[tool_name],  # 正确的命令格式
                args=[],
                language=language,
                install=[],
                priority=priority,
                estimated_time=int(result.execution_time) if result.execution_time else 60,
                categories=[self._infer_tool_category(tool_name)]
            )
            available_tools.append(tool)
        
        # 使用智能工具选择器为这个维度选择最优工具（最多2个）
        selected_tools = self.smart_tool_selector.get_tools_for_dimension(
            dimension_id, available_tools, project_info, max_tools=2
        )
        
        # 将选择的工具名称映射回原始的工具结果
        selected_tool_names = [tool.name for tool in selected_tools]
        filtered = {name: result for name, result in tool_results.items() 
                   if name in selected_tool_names}
        
        logger.info(f"维度{dimension_id}: 从{len(tool_results)}个工具中智能选择了{len(filtered)}个: {list(filtered.keys())}")
        return filtered
    
    def _is_tool_relevant_to_dimension(self, tool_name: str, dimension_id: int) -> bool:
        """判断工具是否与维度相关"""
        # 维度1: 代码结构与可维护性
        if dimension_id == 1:
            return tool_name in ['sonarqube-scanner', 'semgrep'] or 'lint' in tool_name
        # 维度2: 测试覆盖与质量保障
        elif dimension_id == 2:
            return 'test' in tool_name or 'coverage' in tool_name
        # 维度5: 安全性与敏感信息防护
        elif dimension_id == 5:
            return tool_name in ['semgrep', 'gitleaks', 'trivy', 'bandit', 'gosec']
        
        return False
    
    def _extract_dimension_issues(self, dimension_id: int, 
                                 tool_results: Dict[str, ToolResult]) -> List[DimensionIssue]:
        """从工具结果中提取维度相关问题"""
        issues = []
        issue_counter = 0
        
        for tool_name, result in tool_results.items():
            if not result.success or not result.result:
                continue
            
            tool_issues = result.result.get('issues', [])
            for issue in tool_issues:
                issue_counter += 1
                
                # 标准化问题信息
                standardized_issue = DimensionIssue(
                    issue_id=f"DIM{dimension_id}_{issue_counter:04d}",
                    title=self._extract_issue_title(issue),
                    description=self._extract_issue_description(issue),
                    severity=self._normalize_severity(issue.get('severity', 'medium')),
                    category=self._categorize_issue(dimension_id, issue),
                    file_path=issue.get('file'),
                    line_number=issue.get('line'),
                    tool_source=tool_name,
                    recommendation=self._generate_issue_recommendation(dimension_id, issue)
                )
                
                issues.append(standardized_issue)
        
        return issues
    
    def _calculate_dimension_metrics(self, tool_results: Dict[str, ToolResult], 
                                   issues: List[DimensionIssue]) -> DimensionMetrics:
        """计算维度指标"""
        total_issues = len(issues)
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        
        for issue in issues:
            severity_counts[issue.severity] += 1
        
        tools_executed = len(tool_results)
        tools_successful = sum(1 for result in tool_results.values() if result.success)
        
        coverage_percentage = (tools_successful / tools_executed * 100) if tools_executed > 0 else 0
        
        return DimensionMetrics(
            total_issues=total_issues,
            critical_issues=severity_counts['critical'],
            high_issues=severity_counts['high'],
            medium_issues=severity_counts['medium'],
            low_issues=severity_counts['low'],
            tools_executed=tools_executed,
            tools_successful=tools_successful,
            coverage_percentage=coverage_percentage,
            quality_trend="stable"  # TODO: 实现趋势分析
        )
    
    def _calculate_dimension_score(self, dimension_id: int, 
                                  metrics: DimensionMetrics,
                                  issues: List[DimensionIssue],
                                  project_info: ProjectInfo) -> float:
        """计算维度评分"""
        base_score = 100.0
        
        # 1. 基于问题数量和严重程度的扣分
        severity_penalties = {
            'critical': 20,
            'high': 10, 
            'medium': 5,
            'low': 2
        }
        
        for issue in issues:
            penalty = severity_penalties.get(issue.severity, 2)
            base_score -= penalty
        
        # 2. 工具覆盖率加分
        if metrics.coverage_percentage > 80:
            base_score += 5
        elif metrics.coverage_percentage < 50:
            base_score -= 10
        
        # 3. 维度特定调整
        base_score = self._apply_dimension_specific_adjustments(
            dimension_id, base_score, metrics, project_info
        )
        
        # 4. 确保分数在合理范围内
        return max(0, min(100, base_score))
    
    def _generate_dimension_insights(self, dimension_id: int,
                                   metrics: DimensionMetrics,
                                   issues: List[DimensionIssue],
                                   project_info: ProjectInfo) -> List[DimensionInsight]:
        """生成维度洞察"""
        insights = []
        
        # 问题模式分析
        if metrics.critical_issues > 0:
            insights.append(DimensionInsight(
                insight_type="warning",
                title="发现关键问题",
                description=f"检测到 {metrics.critical_issues} 个关键问题，需要立即关注",
                impact="high",
                suggestions=[
                    "优先解决标记为 'critical' 的问题",
                    "建立问题跟踪和解决流程",
                    "增强相关工具的检测覆盖"
                ]
            ))
        
        # 工具覆盖分析
        if metrics.coverage_percentage < 60:
            insights.append(DimensionInsight(
                insight_type="recommendation",
                title="工具覆盖率不足",
                description=f"当前工具覆盖率仅 {metrics.coverage_percentage:.1f}%",
                impact="medium",
                suggestions=[
                    "增加相关分析工具",
                    "检查工具配置是否正确",
                    "考虑集成更多自动化检测工具"
                ]
            ))
        
        # 维度特定洞察
        dimension_insights = self._generate_dimension_specific_insights(
            dimension_id, metrics, issues, project_info
        )
        insights.extend(dimension_insights)
        
        return insights
    
    def _perform_ai_analysis(self, dimension_id: int,
                           tool_results: Dict[str, ToolResult],
                           issues: List[DimensionIssue],
                           project_info: ProjectInfo) -> Tuple[Optional[str], List[str]]:
        """执行AI分析"""
        if not self.ai_analyzer:
            return None, []
        
        try:
            # 准备AI分析的上下文
            context = {
                'dimension_id': dimension_id,
                'dimension_name': self.DIMENSIONS[dimension_id]['name'],
                'project_info': {
                    'name': project_info.name,
                    'languages': project_info.languages,
                    'project_type': str(project_info.project_type),
                    'size': project_info.size_metrics.get_size_category()
                },
                'tool_results_summary': {
                    name: {
                        'success': result.success,
                        'issues_count': result.result.get('issues_count', 0) if result.result else 0,
                        'score': result.result.get('score', 0) if result.result else 0
                    }
                    for name, result in tool_results.items()
                },
                'issues_summary': {
                    'total': len(issues),
                    'by_severity': {
                        severity: len([i for i in issues if i.severity == severity])
                        for severity in ['critical', 'high', 'medium', 'low']
                    }
                }
            }
            
            analysis = self.ai_analyzer.analyze_dimension(context)
            recommendations = self.ai_analyzer.generate_recommendations(context)
            
            return analysis, recommendations
            
        except Exception as e:
            logger.warning(f"AI分析失败: {e}")
            return None, []
    
    def _generate_dimension_summary(self, dimension_id: int,
                                   metrics: DimensionMetrics,
                                   issues: List[DimensionIssue],
                                   insights: List[DimensionInsight]) -> Tuple[str, List[str]]:
        """生成维度摘要和关键发现"""
        dimension_name = self.DIMENSIONS[dimension_id]['name']
        
        # 生成摘要
        summary_parts = [
            f"{dimension_name}维度综合评估结果：",
            f"共检测到 {metrics.total_issues} 个问题",
        ]
        
        if metrics.critical_issues > 0:
            summary_parts.append(f"其中包含 {metrics.critical_issues} 个关键问题")
        
        if metrics.tools_successful < metrics.tools_executed:
            summary_parts.append(f"工具覆盖率 {metrics.coverage_percentage:.1f}%")
        
        summary = "，".join(summary_parts) + "。"
        
        # 生成关键发现
        key_findings = []
        
        if metrics.critical_issues > 0:
            key_findings.append(f"存在 {metrics.critical_issues} 个需要立即解决的关键问题")
        
        if metrics.high_issues > 5:
            key_findings.append(f"检测到 {metrics.high_issues} 个高优先级问题")
        
        # 添加洞察中的关键发现
        for insight in insights:
            if insight.impact == "high":
                key_findings.append(insight.title)
        
        if not key_findings:
            key_findings.append("未发现关键问题，维度表现良好")
        
        return summary, key_findings
    
    # 辅助方法
    def _get_dimension_status(self, score: float) -> DimensionStatus:
        """根据分数确定维度状态"""
        if score >= 90:
            return DimensionStatus.EXCELLENT
        elif score >= 75:
            return DimensionStatus.GOOD
        elif score >= 50:
            return DimensionStatus.WARN
        elif score >= 25:
            return DimensionStatus.POOR
        else:
            return DimensionStatus.CRITICAL
    
    def _serialize_tool_result(self, result: ToolResult) -> Dict[str, Any]:
        """序列化工具结果"""
        return {
            'tool_name': result.tool_name,
            'status': str(result.status),
            'success': result.success,
            'execution_time': result.execution_time,
            'issues_count': result.result.get('issues_count', 0) if result.result else 0,
            'score': result.result.get('score', 0) if result.result else 0,
            'summary': f"执行{'成功' if result.success else '失败'}，"
                      f"耗时 {result.execution_time:.1f}s，"
                      f"发现 {result.result.get('issues_count', 0) if result.result else 0} 个问题"
        }
    
    def _extract_issue_title(self, issue: Dict[str, Any]) -> str:
        """提取问题标题"""
        return issue.get('title', issue.get('message', '未知问题'))[:100]
    
    def _extract_issue_description(self, issue: Dict[str, Any]) -> str:
        """提取问题描述"""
        return issue.get('description', issue.get('message', ''))[:500]
    
    def _normalize_severity(self, severity: str) -> str:
        """标准化严重程度"""
        severity = severity.lower()
        mapping = {
            'critical': 'critical',
            'high': 'high', 
            'error': 'high',
            'warning': 'medium',
            'medium': 'medium',
            'warn': 'medium',
            'low': 'low',
            'info': 'low',
            'minor': 'low'
        }
        return mapping.get(severity, 'medium')
    
    def _categorize_issue(self, dimension_id: int, issue: Dict[str, Any]) -> str:
        """问题分类"""
        # 根据维度和工具类型确定问题分类
        categories_by_dimension = {
            1: ['结构设计', '代码复杂度', '命名规范', '可读性'],
            2: ['测试覆盖', '测试质量', '断言有效性'],
            5: ['安全漏洞', '敏感信息', '权限控制', '输入验证']
        }
        
        default_categories = categories_by_dimension.get(dimension_id, ['通用问题'])
        return issue.get('category', default_categories[0])
    
    def _generate_issue_recommendation(self, dimension_id: int, issue: Dict[str, Any]) -> str:
        """生成问题建议"""
        # 基于维度和问题类型生成建议
        return f"建议参考相关最佳实践解决此问题"
    
    def _apply_dimension_specific_adjustments(self, dimension_id: int, 
                                            base_score: float,
                                            metrics: DimensionMetrics,
                                            project_info: ProjectInfo) -> float:
        """应用维度特定的评分调整"""
        # 不同维度的特殊评分逻辑
        if dimension_id == 1:  # 代码结构与可维护性
            # 大项目对代码质量要求更高
            if project_info.size_metrics.code_lines > 10000 and metrics.total_issues > 50:
                base_score -= 10
        elif dimension_id == 5:  # 安全性
            # 安全问题零容忍
            if metrics.critical_issues > 0:
                base_score -= 30
        
        return base_score
    
    def _generate_dimension_specific_insights(self, dimension_id: int,
                                            metrics: DimensionMetrics,
                                            issues: List[DimensionIssue],
                                            project_info: ProjectInfo) -> List[DimensionInsight]:
        """生成维度特定洞察"""
        insights = []
        
        if dimension_id == 1:  # 代码结构与可维护性
            complexity_issues = [i for i in issues if '复杂度' in i.description]
            if len(complexity_issues) > 10:
                insights.append(DimensionInsight(
                    insight_type="pattern",
                    title="代码复杂度过高",
                    description=f"发现 {len(complexity_issues)} 个复杂度相关问题",
                    impact="medium",
                    suggestions=["考虑重构复杂方法", "应用设计模式简化结构"]
                ))
        
        elif dimension_id == 5:  # 安全性
            if metrics.critical_issues == 0 and metrics.high_issues == 0:
                insights.append(DimensionInsight(
                    insight_type="trend",
                    title="安全状况良好",
                    description="未发现高风险安全问题",
                    impact="low",
                    suggestions=["保持现有安全实践", "定期更新安全扫描工具"]
                ))
        
        return insights
    
    def _infer_tool_language(self, tool_name: str, project_info: ProjectInfo) -> str:
        """根据工具名称推测工具语言"""
        language_mapping = {
            'pylint': 'python',
            'flake8': 'python', 
            'mypy': 'python',
            'bandit': 'python',
            'safety': 'python',
            'black': 'python',
            'isort': 'python',
            'pytest': 'python',
            'coverage': 'python',
            
            'eslint': 'javascript',
            'prettier': 'javascript',
            'jest': 'javascript',
            'npm-audit': 'javascript',
            'tsc': 'javascript',
            'tslint': 'javascript',
            
            'checkstyle': 'java',
            'pmd': 'java',
            'spotbugs': 'java',
            'maven': 'java',
            'gradle': 'java',
            'junit': 'java',
            
            'gofmt': 'go',
            'go-vet': 'go',
            'golint': 'go',
            'gosec': 'go',
            'staticcheck': 'go',
            
            'rustfmt': 'rust',
            'clippy': 'rust',
            'cargo-audit': 'rust',
            
            # 通用工具
            'semgrep': 'universal',
            'gitleaks': 'universal',
            'trivy': 'universal',
            'sonarqube-scanner': 'universal',
            'syft': 'universal'
        }
        
        return language_mapping.get(tool_name, 'universal')
    
    def _infer_tool_priority(self, tool_name: str) -> int:
        """根据工具名称推测工具优先级（1=最高，10=最低）"""
        priority_mapping = {
            # 高优先级工具
            'pylint': 2,
            'eslint': 2,
            'semgrep': 1,
            'sonarqube-scanner': 1,
            'gitleaks': 1,
            'bandit': 2,
            
            # 中优先级工具
            'flake8': 3,
            'mypy': 3,
            'prettier': 4,
            'black': 4,
            'safety': 3,
            'npm-audit': 3,
            
            # 低优先级工具
            'isort': 5,
            'coverage': 4,
            'pytest': 3,
            'jest': 3
        }
        
        return priority_mapping.get(tool_name, 5)
    
    def _infer_tool_category(self, tool_name: str) -> str:
        """根据工具名称推测工具分类"""
        category_mapping = {
            'pylint': 'quality',
            'eslint': 'quality',
            'flake8': 'quality',
            'mypy': 'typing',
            'checkstyle': 'quality',
            'pmd': 'quality',
            
            'bandit': 'security',
            'safety': 'security',
            'semgrep': 'security',
            'gitleaks': 'security',
            'gosec': 'security',
            'npm-audit': 'security',
            'trivy': 'security',
            
            'pytest': 'testing',
            'jest': 'testing',
            'junit': 'testing',
            'coverage': 'coverage',
            
            'black': 'format',
            'prettier': 'format',
            'rustfmt': 'format',
            'gofmt': 'format',
            'isort': 'format'
        }
        
        return category_mapping.get(tool_name, 'quality')


def create_dimension_analyzer(analysis_level: AnalysisLevel = AnalysisLevel.ENHANCED) -> DimensionAnalyzer:
    """创建维度分析器实例"""
    return DimensionAnalyzer(analysis_level)