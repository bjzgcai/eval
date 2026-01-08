#!/usr/bin/env python3
"""
Recommendation Agent - 智能推荐代理
智能问题优先级排序和针对性建议生成
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from collections import defaultdict

from .project_detector import ProjectInfo, ProjectType
from .adaptive_agent import ScoringModel

logger = logging.getLogger(__name__)


class IssueSeverity(Enum):
    """问题严重程度"""
    CRITICAL = "critical"
    HIGH = "high" 
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ImpactLevel(Enum):
    """影响程度"""
    BREAKING = "breaking"      # 破坏性影响
    MAJOR = "major"           # 主要影响
    MINOR = "minor"           # 轻微影响
    NEGLIGIBLE = "negligible" # 可忽略影响


@dataclass
class Issue:
    """问题定义"""
    id: str
    title: str
    description: str
    severity: IssueSeverity
    category: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    tool_source: str = ""
    fix_effort: str = "medium"  # low, medium, high
    impact_level: ImpactLevel = ImpactLevel.MINOR


@dataclass  
class Recommendation:
    """推荐建议"""
    id: str
    title: str
    description: str
    rationale: str  # 建议理由
    priority_score: float  # 优先级分数 0-100
    estimated_effort: int  # 估算工作量(小时)
    impact_level: float   # 影响程度 0-1
    category: str
    action_items: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)  # 相关资源链接
    success_metrics: List[str] = field(default_factory=list)


@dataclass
class RoadmapPhase:
    """路线图阶段"""
    name: str
    duration_weeks: int
    recommendations: List[Recommendation] 
    rationale: str
    prerequisites: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)


@dataclass
class ImprovementRoadmap:
    """改进路线图"""
    phases: List[RoadmapPhase]
    total_duration_weeks: int
    estimated_roi: float  # 投资回报率
    risk_factors: List[str] = field(default_factory=list)


@dataclass
class IntelligentRecommendations:
    """智能推荐结果"""
    recommendations: List[Recommendation]
    roadmap: ImprovementRoadmap  
    impact_predictions: Dict[str, float]
    success_metrics: List[str]
    confidence_level: float = 0.8


@dataclass
class AnalysisResults:
    """分析结果"""
    all_issues: List[Issue]
    tool_results: Dict[str, Any]
    overall_score: float
    dimension_scores: Dict[str, float] = field(default_factory=dict)


class RecommendationEngine:
    """推荐引擎"""
    
    def __init__(self):
        self.recommendation_templates = self._load_templates()
        self.issue_patterns = self._load_issue_patterns()
        
    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        """加载推荐模板"""
        return {
            "security_vulnerability": {
                "priority_multiplier": 1.8,
                "effort_base": 4,
                "impact_base": 0.8,
                "urgency": "high"
            },
            "code_quality": {
                "priority_multiplier": 1.2,
                "effort_base": 2,
                "impact_base": 0.6,
                "urgency": "medium"
            },
            "testing_gap": {
                "priority_multiplier": 1.4,
                "effort_base": 6,
                "impact_base": 0.7,
                "urgency": "high"
            },
            "documentation": {
                "priority_multiplier": 0.8,
                "effort_base": 3,
                "impact_base": 0.4,
                "urgency": "low"
            }
        }
    
    def _load_issue_patterns(self) -> Dict[str, List[str]]:
        """加载问题模式"""
        return {
            "security": [
                "sql injection", "xss", "csrf", "authentication", 
                "authorization", "encryption", "sensitive data"
            ],
            "performance": [
                "memory leak", "slow query", "inefficient algorithm",
                "resource usage", "latency"
            ],
            "maintainability": [
                "code complexity", "duplicate code", "large function",
                "coupling", "cohesion"
            ]
        }


class BestPracticesDatabase:
    """最佳实践数据库"""
    
    def __init__(self):
        self.practices = self._load_best_practices()
    
    def _load_best_practices(self) -> Dict[str, List[Dict[str, Any]]]:
        """加载最佳实践"""
        return {
            "python": [
                {
                    "name": "使用类型提示",
                    "description": "添加类型注解提高代码可读性",
                    "effort": 2,
                    "impact": 0.6
                },
                {
                    "name": "单元测试覆盖率",
                    "description": "确保测试覆盖率达到80%以上", 
                    "effort": 8,
                    "impact": 0.8
                }
            ],
            "javascript": [
                {
                    "name": "使用ESLint",
                    "description": "配置ESLint规则保证代码质量",
                    "effort": 1,
                    "impact": 0.7
                }
            ]
        }


class ImprovementPlanner:
    """改进规划器"""
    
    def create_roadmap(self, recommendations: List[Recommendation],
                      project_info: ProjectInfo) -> ImprovementRoadmap:
        """创建改进路线图"""
        try:
            # 按优先级和工作量分组推荐
            phases = []
            
            # 快速改进项目
            quick_wins = [r for r in recommendations 
                         if r.estimated_effort <= 4 and r.impact_level >= 0.6]
            if quick_wins:
                phases.append(RoadmapPhase(
                    name="Quick Wins",
                    duration_weeks=2,
                    recommendations=sorted(quick_wins, key=lambda x: x.priority_score, reverse=True)[:5],
                    rationale="快速提升项目质量，建立改进信心",
                    success_criteria=["问题修复率提升30%", "代码质量分数提升10分"]
                ))
            
            # 核心问题解决
            high_impact = [r for r in recommendations
                          if r.impact_level >= 0.7 and r not in quick_wins]
            if high_impact:
                phases.append(RoadmapPhase(
                    name="High Impact Improvements",
                    duration_weeks=4,
                    recommendations=sorted(high_impact, key=lambda x: x.priority_score, reverse=True)[:8],
                    rationale="解决最重要的质量问题",
                    prerequisites=["完成快速改进项目"],
                    success_criteria=["整体质量分数提升20分", "关键问题解决率90%"]
                ))
            
            # 系统性改进
            systematic = [r for r in recommendations
                         if r not in quick_wins and r not in high_impact]
            if systematic:
                phases.append(RoadmapPhase(
                    name="Systematic Improvements", 
                    duration_weeks=6,
                    recommendations=sorted(systematic, key=lambda x: x.priority_score, reverse=True),
                    rationale="建立长期质量保障机制",
                    prerequisites=["完成核心问题解决"],
                    success_criteria=["建立完整的质量保障流程", "技术债务减少50%"]
                ))
            
            total_weeks = sum(phase.duration_weeks for phase in phases)
            estimated_roi = self._calculate_estimated_roi(phases, project_info)
            
            return ImprovementRoadmap(
                phases=phases,
                total_duration_weeks=total_weeks,
                estimated_roi=estimated_roi,
                risk_factors=["资源投入不足", "团队技能差距", "业务需求变化"]
            )
            
        except Exception as e:
            logger.error(f"路线图创建失败: {e}")
            return ImprovementRoadmap(phases=[], total_duration_weeks=0, estimated_roi=0.0)
    
    def _calculate_estimated_roi(self, phases: List[RoadmapPhase], 
                               project_info: ProjectInfo) -> float:
        """计算估算ROI"""
        try:
            total_effort = sum(
                sum(r.estimated_effort for r in phase.recommendations)
                for phase in phases
            )
            
            if total_effort == 0:
                return 0.0
            
            total_impact = sum(
                sum(r.impact_level for r in phase.recommendations)
                for phase in phases
            )
            
            # 基于项目规模调整ROI
            size_factor = min(2.0, project_info.size_metrics.code_lines / 10000)
            
            roi = (total_impact * size_factor * 100) / max(total_effort, 1)
            return min(500.0, max(0.0, roi))  # 限制在0-500%范围
            
        except Exception as e:
            logger.error(f"ROI计算失败: {e}")
            return 0.0


class RecommendationAgent:
    """
    推荐Agent - 生成智能建议和改进路线图
    
    核心功能:
    - 智能问题优先级排序
    - 针对性建议生成
    - 智能路线图规划
    - 改进效果预测
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.recommendation_engine = RecommendationEngine()
        self.best_practices_db = BestPracticesDatabase()
        self.improvement_planner = ImprovementPlanner()
        self.recommendation_history: List[Dict[str, Any]] = []
    
    def generate_intelligent_recommendations(self, 
                                           analysis_results: AnalysisResults,
                                           project_info: ProjectInfo,
                                           scoring_model: Optional[ScoringModel] = None) -> IntelligentRecommendations:
        """
        生成智能化建议
        
        Args:
            analysis_results: 分析结果
            project_info: 项目信息
            scoring_model: 评分模型
            
        Returns:
            智能推荐结果
        """
        try:
            self.logger.info("开始生成智能推荐...")
            
            # 1. 智能问题优先级排序
            prioritized_issues = self._prioritize_issues_intelligently(
                analysis_results.all_issues, project_info, scoring_model)
            
            self.logger.debug(f"问题优先级排序完成: {len(prioritized_issues)}个问题")
            
            # 2. 生成针对性建议
            targeted_recommendations = []
            for issue in prioritized_issues[:15]:  # 处理前15个最重要问题
                recommendation = self._generate_targeted_recommendation(
                    issue, project_info)
                if recommendation:
                    targeted_recommendations.append(recommendation)
            
            # 3. 添加最佳实践建议
            best_practice_recommendations = self._generate_best_practice_recommendations(
                project_info, analysis_results)
            targeted_recommendations.extend(best_practice_recommendations)
            
            self.logger.debug(f"生成了{len(targeted_recommendations)}个推荐建议")
            
            # 4. 制定智能路线图
            roadmap = self.improvement_planner.create_roadmap(
                targeted_recommendations, project_info)
            
            # 5. 预测改进效果
            impact_predictions = self._predict_improvement_impact(
                targeted_recommendations, project_info, analysis_results)
            
            # 6. 定义成功指标
            success_metrics = self._define_success_metrics(
                targeted_recommendations, analysis_results)
            
            # 7. 计算信心度
            confidence = self._calculate_recommendation_confidence(
                targeted_recommendations, analysis_results)
            
            recommendations = IntelligentRecommendations(
                recommendations=targeted_recommendations,
                roadmap=roadmap,
                impact_predictions=impact_predictions,
                success_metrics=success_metrics,
                confidence_level=confidence
            )
            
            # 8. 记录推荐历史
            self._record_recommendation(project_info, recommendations)
            
            self.logger.info(f"智能推荐生成完成: {len(targeted_recommendations)}个建议, "
                           f"路线图{len(roadmap.phases)}个阶段, 信心度{confidence:.2f}")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"智能推荐生成失败: {e}")
            return self._create_fallback_recommendations()
    
    def _prioritize_issues_intelligently(self, issues: List[Issue], 
                                       project_info: ProjectInfo,
                                       scoring_model: Optional[ScoringModel] = None) -> List[Issue]:
        """智能优先级排序"""
        try:
            def calculate_priority_score(issue: Issue) -> float:
                score = 0.0
                
                # 基础严重程度 (40%)
                severity_weights = {
                    IssueSeverity.CRITICAL: 100,
                    IssueSeverity.HIGH: 70,
                    IssueSeverity.MEDIUM: 40,
                    IssueSeverity.LOW: 20,
                    IssueSeverity.INFO: 5
                }
                score += severity_weights.get(issue.severity, 20) * 0.4
                
                # 项目类型相关性调整 (25%)
                project_type = getattr(project_info.project_type, 'value', 'library')
                type_multiplier = 1.0
                
                if project_type == 'web_application':
                    if issue.category == "security":
                        type_multiplier = 1.8
                    elif issue.category == "performance":
                        type_multiplier = 1.3
                elif project_type == 'library':
                    if issue.category in ["api_design", "documentation"]:
                        type_multiplier = 1.5
                elif project_type == 'data_science':
                    if issue.category == "reproducibility":
                        type_multiplier = 1.6
                
                score += score * 0.25 * (type_multiplier - 1.0)
                
                # 修复成本考虑 (20%)
                effort_weights = {"low": 1.3, "medium": 1.0, "high": 0.7}
                effort_multiplier = effort_weights.get(issue.fix_effort, 1.0)
                score += score * 0.2 * (effort_multiplier - 1.0)
                
                # 影响程度 (15%)
                impact_weights = {
                    ImpactLevel.BREAKING: 30,
                    ImpactLevel.MAJOR: 20,
                    ImpactLevel.MINOR: 10,
                    ImpactLevel.NEGLIGIBLE: 2
                }
                score += impact_weights.get(issue.impact_level, 10) * 0.15
                
                return max(0.0, score)
            
            # 排序并返回
            prioritized = sorted(issues, key=calculate_priority_score, reverse=True)
            
            self.logger.debug(f"优先级排序: 最高分{calculate_priority_score(prioritized[0]):.1f}, "
                            f"最低分{calculate_priority_score(prioritized[-1]):.1f}")
            
            return prioritized
            
        except Exception as e:
            self.logger.error(f"优先级排序失败: {e}")
            return issues
    
    def _generate_targeted_recommendation(self, issue: Issue, 
                                        project_info: ProjectInfo) -> Optional[Recommendation]:
        """生成针对性建议"""
        try:
            template = self.recommendation_engine.recommendation_templates.get(
                issue.category, self.recommendation_engine.recommendation_templates["code_quality"])
            
            # 基础优先级分数
            base_score = {
                IssueSeverity.CRITICAL: 90,
                IssueSeverity.HIGH: 70,
                IssueSeverity.MEDIUM: 50,
                IssueSeverity.LOW: 30,
                IssueSeverity.INFO: 10
            }.get(issue.severity, 50)
            
            priority_score = base_score * template["priority_multiplier"]
            
            # 估算工作量
            estimated_effort = template["effort_base"]
            if issue.fix_effort == "high":
                estimated_effort *= 2
            elif issue.fix_effort == "low":
                estimated_effort *= 0.5
            
            # 生成行动项目
            action_items = self._generate_action_items(issue, project_info)
            
            # 生成资源链接
            resources = self._generate_resources(issue, project_info)
            
            recommendation = Recommendation(
                id=f"rec_{issue.id}_{int(time.time())}",
                title=f"解决{issue.title}",
                description=self._generate_recommendation_description(issue),
                rationale=self._generate_rationale(issue, project_info),
                priority_score=min(100, priority_score),
                estimated_effort=int(estimated_effort),
                impact_level=template["impact_base"],
                category=issue.category,
                action_items=action_items,
                resources=resources,
                success_metrics=self._generate_success_metrics(issue)
            )
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"针对性建议生成失败 {issue.id}: {e}")
            return None
    
    def _generate_best_practice_recommendations(self, project_info: ProjectInfo,
                                              analysis_results: AnalysisResults) -> List[Recommendation]:
        """生成最佳实践建议"""
        try:
            recommendations = []
            primary_language = project_info.get_primary_language()
            
            if primary_language in self.best_practices_db.practices:
                practices = self.best_practices_db.practices[primary_language]
                
                for i, practice in enumerate(practices[:3]):  # 最多3个最佳实践
                    rec = Recommendation(
                        id=f"bp_{primary_language}_{i}_{int(time.time())}",
                        title=practice["name"],
                        description=practice["description"],
                        rationale=f"基于{primary_language}项目最佳实践",
                        priority_score=40.0,  # 最佳实践优先级中等
                        estimated_effort=practice["effort"],
                        impact_level=practice["impact"],
                        category="best_practice",
                        action_items=[f"实施{practice['name']}"],
                        resources=[],
                        success_metrics=[f"{practice['name']}实施完成"]
                    )
                    recommendations.append(rec)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"最佳实践建议生成失败: {e}")
            return []
    
    def _predict_improvement_impact(self, recommendations: List[Recommendation],
                                  project_info: ProjectInfo,
                                  analysis_results: AnalysisResults) -> Dict[str, float]:
        """预测改进效果"""
        try:
            predictions = {}
            
            # 整体质量分数提升预测
            total_impact = sum(r.impact_level for r in recommendations)
            current_score = analysis_results.overall_score
            
            predicted_improvement = min(30, total_impact * 5)  # 最多提升30分
            predictions["overall_score_improvement"] = predicted_improvement
            predictions["predicted_new_score"] = min(100, current_score + predicted_improvement)
            
            # 按类别预测改进
            category_impacts = defaultdict(float)
            for rec in recommendations:
                category_impacts[rec.category] += rec.impact_level
            
            for category, impact in category_impacts.items():
                predictions[f"{category}_improvement"] = min(40, impact * 8)
            
            # 预测问题解决率
            high_priority_count = len([r for r in recommendations if r.priority_score > 70])
            total_recommendations = len(recommendations)
            
            if total_recommendations > 0:
                predictions["issue_resolution_rate"] = min(0.9, 0.6 + (high_priority_count / total_recommendations) * 0.3)
            
            return dict(predictions)
            
        except Exception as e:
            self.logger.error(f"改进效果预测失败: {e}")
            return {}
    
    def _define_success_metrics(self, recommendations: List[Recommendation],
                              analysis_results: AnalysisResults) -> List[str]:
        """定义成功指标"""
        try:
            metrics = []
            
            # 基于推荐数量的指标
            if len(recommendations) > 10:
                metrics.append("完成80%的推荐建议")
            else:
                metrics.append("完成90%的推荐建议")
            
            # 基于当前分数的指标
            current_score = analysis_results.overall_score
            if current_score < 60:
                metrics.append("整体质量分数提升到70分以上")
            elif current_score < 80:
                metrics.append("整体质量分数提升到85分以上") 
            else:
                metrics.append("整体质量分数提升5分以上")
            
            # 基于问题类型的指标
            security_recs = [r for r in recommendations if r.category == "security"]
            if security_recs:
                metrics.append("解决所有高优先级安全问题")
            
            testing_recs = [r for r in recommendations if "test" in r.category.lower()]
            if testing_recs:
                metrics.append("测试覆盖率达到80%以上")
            
            # 通用指标
            metrics.extend([
                "代码质量工具检查通过率达到95%",
                "团队开发效率提升15%",
                "技术债务减少30%"
            ])
            
            return metrics[:6]  # 最多6个指标
            
        except Exception as e:
            self.logger.error(f"成功指标定义失败: {e}")
            return ["完成推荐建议", "提升代码质量"]
    
    def _generate_action_items(self, issue: Issue, project_info: ProjectInfo) -> List[str]:
        """生成行动项目"""
        try:
            actions = []
            
            if issue.category == "security":
                actions = [
                    "进行安全代码审查",
                    f"修复{issue.file_path or '相关文件'}中的安全漏洞", 
                    "添加安全测试用例",
                    "更新安全编码规范"
                ]
            elif issue.category == "testing":
                actions = [
                    "编写单元测试",
                    "提高测试覆盖率",
                    "添加集成测试",
                    "设置持续集成检查"
                ]
            elif issue.category == "performance":
                actions = [
                    "性能分析和profiling",
                    "优化关键性能路径",
                    "添加性能监控",
                    "建立性能基准测试"
                ]
            else:
                actions = [
                    f"修复{issue.title}问题",
                    "代码审查",
                    "添加相关测试",
                    "更新文档"
                ]
            
            return actions[:3]  # 最多3个行动项
            
        except Exception as e:
            self.logger.error(f"行动项目生成失败: {e}")
            return ["修复问题", "添加测试"]
    
    def _generate_resources(self, issue: Issue, project_info: ProjectInfo) -> List[str]:
        """生成资源链接"""
        resources = []
        
        if issue.category == "security":
            resources = [
                "OWASP安全编码指南",
                "项目安全检查清单",
                "安全漏洞修复指南"
            ]
        elif issue.category == "testing":
            resources = [
                f"{project_info.get_primary_language()}测试最佳实践",
                "测试覆盖率提升指南",
                "单元测试编写规范"
            ]
        
        return resources[:2]  # 最多2个资源
    
    def _generate_recommendation_description(self, issue: Issue) -> str:
        """生成建议描述"""
        return f"针对{issue.category}类型的{issue.severity.value}级别问题，建议采取相应的修复措施以提升代码质量。"
    
    def _generate_rationale(self, issue: Issue, project_info: ProjectInfo) -> str:
        """生成建议理由"""
        project_type = getattr(project_info.project_type, 'value', 'unknown')
        
        if issue.category == "security":
            if project_type == "web_application":
                return "Web应用中的安全问题可能导致用户数据泄露或系统被攻击，需要优先处理。"
            else:
                return "安全问题可能影响系统稳定性和用户信任，建议及时修复。"
        elif issue.category == "performance":
            return "性能问题可能影响用户体验和系统可扩展性，建议优化改进。"
        else:
            return f"该{issue.category}问题影响代码质量和可维护性，建议及时解决。"
    
    def _generate_success_metrics(self, issue: Issue) -> List[str]:
        """生成成功指标"""
        if issue.category == "security":
            return ["安全扫描通过", "漏洞修复确认"]
        elif issue.category == "testing":
            return ["测试覆盖率提升", "所有测试通过"]
        else:
            return ["问题修复确认", "代码审查通过"]
    
    def _calculate_recommendation_confidence(self, recommendations: List[Recommendation],
                                           analysis_results: AnalysisResults) -> float:
        """计算推荐信心度"""
        try:
            base_confidence = 0.7
            
            # 基于问题数量调整
            issue_count = len(analysis_results.all_issues)
            if issue_count > 50:
                base_confidence -= 0.1  # 问题太多，信心度降低
            elif issue_count < 10:
                base_confidence += 0.1  # 问题较少，信心度提升
            
            # 基于推荐数量调整
            rec_count = len(recommendations)
            if 5 <= rec_count <= 15:
                base_confidence += 0.1  # 推荐数量合适
            elif rec_count > 20:
                base_confidence -= 0.1  # 推荐过多
            
            # 基于分析工具成功率调整
            tool_success_rate = sum(
                1 for result in analysis_results.tool_results.values()
                if result.get('success', False)
            ) / max(len(analysis_results.tool_results), 1)
            
            confidence_adjustment = (tool_success_rate - 0.5) * 0.2
            base_confidence += confidence_adjustment
            
            return max(0.3, min(1.0, base_confidence))
            
        except Exception as e:
            self.logger.error(f"信心度计算失败: {e}")
            return 0.6
    
    def _record_recommendation(self, project_info: ProjectInfo, 
                             recommendations: IntelligentRecommendations):
        """记录推荐历史"""
        try:
            record = {
                'timestamp': time.time(),
                'project_type': getattr(project_info.project_type, 'value', 'unknown'),
                'project_size': project_info.size_metrics.code_lines,
                'recommendation_count': len(recommendations.recommendations),
                'roadmap_phases': len(recommendations.roadmap.phases),
                'confidence': recommendations.confidence_level
            }
            
            self.recommendation_history.append(record)
            
            # 限制历史记录
            if len(self.recommendation_history) > 50:
                self.recommendation_history = self.recommendation_history[-50:]
                
        except Exception as e:
            self.logger.error(f"推荐历史记录失败: {e}")
    
    def _create_fallback_recommendations(self) -> IntelligentRecommendations:
        """创建降级推荐"""
        fallback_rec = Recommendation(
            id="fallback_001",
            title="提升代码质量",
            description="建议进行基础的代码质量改进",
            rationale="提升整体代码质量",
            priority_score=50.0,
            estimated_effort=4,
            impact_level=0.5,
            category="quality",
            action_items=["代码审查", "添加测试"],
            resources=["代码质量指南"],
            success_metrics=["代码质量提升"]
        )
        
        fallback_roadmap = ImprovementRoadmap(
            phases=[RoadmapPhase(
                name="基础改进",
                duration_weeks=2,
                recommendations=[fallback_rec],
                rationale="基础质量改进"
            )],
            total_duration_weeks=2,
            estimated_roi=50.0
        )
        
        return IntelligentRecommendations(
            recommendations=[fallback_rec],
            roadmap=fallback_roadmap,
            impact_predictions={"overall_improvement": 10.0},
            success_metrics=["基础质量改进完成"],
            confidence_level=0.4
        )
    
    def get_recommendation_stats(self) -> Dict[str, Any]:
        """获取推荐统计"""
        try:
            if not self.recommendation_history:
                return {"total_recommendations": 0}
            
            return {
                "total_sessions": len(self.recommendation_history),
                "avg_recommendations_per_session": sum(
                    record.get('recommendation_count', 0) 
                    for record in self.recommendation_history
                ) / len(self.recommendation_history),
                "avg_confidence": sum(
                    record.get('confidence', 0.5) 
                    for record in self.recommendation_history
                ) / len(self.recommendation_history)
            }
        except Exception as e:
            self.logger.error(f"推荐统计获取失败: {e}")
            return {}


def create_recommendation_agent() -> RecommendationAgent:
    """创建推荐代理实例"""
    return RecommendationAgent()