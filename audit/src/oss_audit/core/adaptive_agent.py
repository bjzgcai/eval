#!/usr/bin/env python3
"""
Adaptive Agent - 自适应评分优化代理
动态评分模型适配和分析过程优化
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from collections import defaultdict

from .project_detector import ProjectInfo, ProjectType, StructureType
from .tool_registry import Tool

logger = logging.getLogger(__name__)


class AdaptationLevel(Enum):
    """自适应程度"""
    MINIMAL = "minimal"      # 最小自适应
    MODERATE = "moderate"    # 中等自适应  
    AGGRESSIVE = "aggressive" # 积极自适应


@dataclass
class ScoringModel:
    """评分模型"""
    weights: Dict[str, float]  # 维度权重
    quality_adjustments: Dict[str, float]  # 质量调整
    historical_adjustments: Dict[str, float]  # 历史调整
    confidence_level: float  # 信心度
    model_version: str = "1.0"
    created_time: float = field(default_factory=time.time)


@dataclass
class OptimizationActions:
    """优化建议"""
    additional_tools: List[Tool] = field(default_factory=list)
    arbitration_tools: List[Tool] = field(default_factory=list)
    supplementary_analysis: List[str] = field(default_factory=list)
    weight_adjustments: Dict[str, float] = field(default_factory=dict)
    time_budget_adjustment: Optional[int] = None
    priority_changes: Dict[str, int] = field(default_factory=dict)


class AdaptiveAgent:
    """
    自适应Agent - 动态评分优化和持续改进
    
    核心功能:
    - 动态评分模型适配
    - 项目类型权重调整
    - 分析过程优化 
    - 历史数据学习
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scoring_models: Dict[str, ScoringModel] = {}
        self.benchmark_db = BenchmarkDatabase()
        self.adaptation_history: List[Dict[str, Any]] = []
        self._initialize_base_models()
    
    def _initialize_base_models(self):
        """初始化基础评分模型"""
        # Web应用基础模型
        self.scoring_models["web_application"] = ScoringModel(
            weights={
                "security": 0.30,
                "quality": 0.25, 
                "performance": 0.20,
                "testing": 0.15,
                "documentation": 0.10
            },
            quality_adjustments={},
            historical_adjustments={},
            confidence_level=0.8
        )
        
        # 库项目基础模型
        self.scoring_models["library"] = ScoringModel(
            weights={
                "quality": 0.30,
                "testing": 0.25,
                "documentation": 0.20,
                "security": 0.15,
                "api_design": 0.10
            },
            quality_adjustments={},
            historical_adjustments={},
            confidence_level=0.8
        )
        
        # CLI工具基础模型
        self.scoring_models["cli_tool"] = ScoringModel(
            weights={
                "quality": 0.25,
                "usability": 0.25,
                "testing": 0.20,
                "documentation": 0.15,
                "performance": 0.15
            },
            quality_adjustments={},
            historical_adjustments={},
            confidence_level=0.8
        )
        
        # 数据科学项目基础模型
        self.scoring_models["data_science"] = ScoringModel(
            weights={
                "reproducibility": 0.30,
                "data_quality": 0.25,
                "documentation": 0.20,
                "testing": 0.15,
                "security": 0.10
            },
            quality_adjustments={},
            historical_adjustments={},
            confidence_level=0.8
        )
    
    def adapt_scoring_model(self, project_info: ProjectInfo, 
                          tool_results: Dict[str, Any]) -> ScoringModel:
        """
        根据项目特征自适应评分模型
        
        Args:
            project_info: 项目信息
            tool_results: 工具执行结果
            
        Returns:
            适配后的评分模型
        """
        try:
            self.logger.info("开始自适应评分模型适配...")
            
            # 1. 选择基础评分模型
            base_model = self._select_base_model(project_info.project_type)
            
            # 2. 根据项目特征调整权重
            adapted_weights = self._adapt_dimension_weights(
                base_model.weights.copy(), project_info)
            
            # 3. 根据工具结果质量调整
            quality_adjustments = self._analyze_tool_result_quality(tool_results)
            
            # 4. 历史数据学习调整
            historical_adjustments = self._learn_from_similar_projects(project_info)
            
            # 5. 计算适配信心度
            confidence = self._calculate_adaptation_confidence(
                project_info, tool_results, historical_adjustments)
            
            adapted_model = ScoringModel(
                weights=adapted_weights,
                quality_adjustments=quality_adjustments,
                historical_adjustments=historical_adjustments,
                confidence_level=confidence,
                model_version=f"adapted_{int(time.time())}"
            )
            
            # 6. 记录适配历史
            self._record_adaptation(project_info, base_model, adapted_model)
            
            self.logger.info(f"评分模型适配完成，信心度: {confidence:.2f}")
            return adapted_model
            
        except Exception as e:
            self.logger.error(f"评分模型适配失败: {e}")
            return self._get_fallback_model(project_info.project_type)
    
    def _select_base_model(self, project_type) -> ScoringModel:
        """选择基础评分模型"""
        try:
            if hasattr(project_type, 'value'):
                type_key = project_type.value
            else:
                type_key = str(project_type).lower()
            
            return self.scoring_models.get(type_key, self.scoring_models["library"])
            
        except Exception as e:
            self.logger.error(f"基础模型选择失败: {e}")
            return self.scoring_models["library"]
    
    def _adapt_dimension_weights(self, base_weights: Dict[str, float], 
                               project_info: ProjectInfo) -> Dict[str, float]:
        """自适应调整维度权重"""
        try:
            adapted = base_weights.copy()
            
            # 基于项目类型调整
            project_type = getattr(project_info.project_type, 'value', 'library')
            
            if project_type == 'web_application':
                # Web应用提高安全权重
                adapted["security"] = min(0.4, adapted.get("security", 0.2) * 1.5)
                adapted["performance"] = min(0.3, adapted.get("performance", 0.15) * 1.2)
                
            elif project_type == 'library':
                # 库项目提高文档和API质量权重
                adapted["documentation"] = min(0.3, adapted.get("documentation", 0.15) * 1.4)
                adapted["api_design"] = min(0.2, adapted.get("api_design", 0.1) * 1.3)
                
            elif project_type == 'data_science':
                # 数据科学项目提高可复现性权重
                adapted["reproducibility"] = min(0.4, adapted.get("reproducibility", 0.2) * 1.6)
                adapted["data_quality"] = min(0.3, adapted.get("data_quality", 0.15) * 1.4)
            
            # 基于项目规模调整
            code_lines = project_info.size_metrics.code_lines
            if code_lines > 50000:  # 大型项目
                # 大型项目更注重架构和测试
                adapted["architecture"] = adapted.get("architecture", 0.1) * 1.3
                adapted["testing"] = min(0.3, adapted.get("testing", 0.2) * 1.2)
            elif code_lines < 1000:  # 小型项目
                # 小型项目更注重简洁性
                adapted["simplicity"] = adapted.get("simplicity", 0.1) * 1.5
            
            # 基于语言多样性调整
            if len(project_info.languages) > 2:
                # 多语言项目更注重一致性
                adapted["consistency"] = adapted.get("consistency", 0.1) * 1.4
                adapted["integration"] = adapted.get("integration", 0.1) * 1.3
            
            # 重新归一化权重
            total = sum(adapted.values())
            if total > 0:
                adapted = {k: v/total for k, v in adapted.items()}
            
            return adapted
            
        except Exception as e:
            self.logger.error(f"权重调整失败: {e}")
            return base_weights
    
    def _analyze_tool_result_quality(self, tool_results: Dict[str, Any]) -> Dict[str, float]:
        """分析工具结果质量"""
        try:
            quality_adjustments = {}
            
            total_tools = len(tool_results)
            successful_tools = sum(1 for result in tool_results.values() 
                                 if result.get('success', False))
            
            success_rate = successful_tools / max(total_tools, 1)
            
            # 基于成功率调整信心度
            if success_rate < 0.5:
                quality_adjustments["confidence_penalty"] = -0.2
            elif success_rate > 0.9:
                quality_adjustments["confidence_bonus"] = 0.1
            
            # 检查工具结果一致性
            scores = [result.get('score', 50) for result in tool_results.values() 
                     if result.get('success', False)]
            
            if len(scores) > 1:
                import statistics
                score_std = statistics.stdev(scores)
                if score_std > 25:  # 分数差异大
                    quality_adjustments["consistency_penalty"] = -0.1
                elif score_std < 10:  # 分数一致性好
                    quality_adjustments["consistency_bonus"] = 0.05
            
            return quality_adjustments
            
        except Exception as e:
            self.logger.error(f"工具结果质量分析失败: {e}")
            return {}
    
    def _learn_from_similar_projects(self, project_info: ProjectInfo) -> Dict[str, float]:
        """从相似项目学习"""
        try:
            historical_adjustments = {}
            
            # 查找相似项目
            similar_projects = self.benchmark_db.find_similar_projects(
                project_info, limit=10)
            
            if not similar_projects:
                return {}
            
            # 分析相似项目的权重分布
            weight_patterns = defaultdict(list)
            for project in similar_projects:
                if 'scoring_weights' in project:
                    for dim, weight in project['scoring_weights'].items():
                        weight_patterns[dim].append(weight)
            
            # 计算推荐权重
            for dim, weights in weight_patterns.items():
                if len(weights) >= 3:  # 至少3个样本
                    avg_weight = sum(weights) / len(weights)
                    historical_adjustments[f"{dim}_historical"] = avg_weight
            
            return historical_adjustments
            
        except Exception as e:
            self.logger.error(f"历史学习失败: {e}")
            return {}
    
    def _calculate_adaptation_confidence(self, project_info: ProjectInfo,
                                       tool_results: Dict[str, Any],
                                       historical_adjustments: Dict[str, float]) -> float:
        """计算适配信心度"""
        try:
            confidence = 0.5  # 基础信心度
            
            # 基于工具执行成功率调整
            success_rate = sum(1 for r in tool_results.values() if r.get('success', False)) / max(len(tool_results), 1)
            confidence += (success_rate - 0.5) * 0.3
            
            # 基于历史数据可用性调整
            if historical_adjustments:
                confidence += min(0.2, len(historical_adjustments) * 0.02)
            
            # 基于项目信息完整性调整
            if project_info.size_metrics.code_lines > 0:
                confidence += 0.1
            if len(project_info.languages) > 0:
                confidence += 0.1
            if project_info.dependencies:
                confidence += 0.05
            
            return max(0.1, min(1.0, confidence))
            
        except Exception as e:
            self.logger.error(f"信心度计算失败: {e}")
            return 0.5
    
    def optimize_analysis_process(self, current_results: Dict[str, Any],
                                project_info: ProjectInfo) -> OptimizationActions:
        """基于当前结果优化分析过程"""
        try:
            self.logger.info("开始分析过程优化...")
            
            actions = OptimizationActions()
            
            # 1. 检测高风险问题
            if self._detect_high_risk_issues(current_results):
                actions.additional_tools.extend(
                    self._recommend_additional_security_tools())
                self.logger.info("检测到高风险问题，建议启用额外安全工具")
            
            # 2. 检测工具结果冲突
            conflicts = self._detect_tool_conflicts(current_results)
            if conflicts:
                actions.arbitration_tools.extend(
                    self._suggest_arbitration_tools(conflicts))
                self.logger.info(f"检测到{len(conflicts)}个工具冲突，建议仲裁工具")
            
            # 3. 检测结果不确定性
            uncertainty = self._measure_result_uncertainty(current_results)
            if uncertainty > 0.3:
                actions.supplementary_analysis.extend(
                    self._design_supplementary_analysis())
                self.logger.info(f"结果不确定性高({uncertainty:.2f})，建议补充分析")
            
            # 4. 权重动态调整
            weight_adjustments = self._suggest_weight_adjustments(
                current_results, project_info)
            actions.weight_adjustments.update(weight_adjustments)
            
            # 5. 时间预算调整
            if self._should_extend_analysis_time(current_results):
                actions.time_budget_adjustment = 300  # 延长5分钟
                self.logger.info("建议延长分析时间")
            
            return actions
            
        except Exception as e:
            self.logger.error(f"分析过程优化失败: {e}")
            return OptimizationActions()
    
    def _detect_high_risk_issues(self, results: Dict[str, Any]) -> bool:
        """检测高风险问题"""
        try:
            for tool_name, result in results.items():
                if result.get('success', False):
                    issues = result.get('issues', [])
                    for issue in issues:
                        if issue.get('severity') == 'critical':
                            return True
                        if 'security' in issue.get('category', '').lower():
                            return True
            return False
            
        except Exception as e:
            self.logger.error(f"高风险问题检测失败: {e}")
            return False
    
    def _detect_tool_conflicts(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测工具结果冲突"""
        try:
            conflicts = []
            tool_scores = {}
            
            # 收集各工具分数
            for tool_name, result in results.items():
                if result.get('success', False):
                    score = result.get('score', 50)
                    tool_scores[tool_name] = score
            
            # 检测分数差异大的工具
            scores = list(tool_scores.values())
            if len(scores) > 1:
                import statistics
                if statistics.stdev(scores) > 30:  # 标准差大于30
                    conflicts.append({
                        'type': 'score_conflict',
                        'tools': list(tool_scores.keys()),
                        'scores': tool_scores
                    })
            
            return conflicts
            
        except Exception as e:
            self.logger.error(f"工具冲突检测失败: {e}")
            return []
    
    def _measure_result_uncertainty(self, results: Dict[str, Any]) -> float:
        """测量结果不确定性"""
        try:
            if not results:
                return 1.0
            
            # 基于成功率的不确定性
            success_count = sum(1 for r in results.values() if r.get('success', False))
            success_rate = success_count / len(results)
            success_uncertainty = 1.0 - success_rate
            
            # 基于分数分散度的不确定性
            scores = [r.get('score', 50) for r in results.values() if r.get('success', False)]
            if len(scores) > 1:
                import statistics
                score_std = statistics.stdev(scores)
                score_uncertainty = min(1.0, score_std / 50.0)
            else:
                score_uncertainty = 0.5
            
            # 综合不确定性
            overall_uncertainty = (success_uncertainty * 0.6 + score_uncertainty * 0.4)
            
            return max(0.0, min(1.0, overall_uncertainty))
            
        except Exception as e:
            self.logger.error(f"不确定性测量失败: {e}")
            return 0.5
    
    def _recommend_additional_security_tools(self) -> List[Tool]:
        """推荐额外安全工具"""
        # 这里应该返回Tool对象，简化为工具名称
        return [
            {'name': 'semgrep', 'category': 'security'},
            {'name': 'gitleaks', 'category': 'security'}
        ]
    
    def _suggest_arbitration_tools(self, conflicts: List[Dict[str, Any]]) -> List[Tool]:
        """建议仲裁工具"""
        return [
            {'name': 'sonarqube', 'category': 'arbitration'}
        ]
    
    def _design_supplementary_analysis(self) -> List[str]:
        """设计补充分析"""
        return [
            "manual_code_review",
            "peer_review",
            "additional_testing"
        ]
    
    def _suggest_weight_adjustments(self, results: Dict[str, Any], 
                                  project_info: ProjectInfo) -> Dict[str, float]:
        """建议权重调整"""
        adjustments = {}
        
        # 如果安全工具发现问题，提高安全权重
        security_issues = sum(1 for r in results.values() 
                            if 'security' in str(r.get('issues', [])).lower())
        if security_issues > 0:
            adjustments['security'] = 0.1  # 增加10%权重
        
        return adjustments
    
    def _should_extend_analysis_time(self, results: Dict[str, Any]) -> bool:
        """是否应该延长分析时间"""
        # 如果有工具超时或失败，建议延长时间
        failed_count = sum(1 for r in results.values() if not r.get('success', True))
        return failed_count > len(results) * 0.3  # 超过30%失败
    
    def _record_adaptation(self, project_info: ProjectInfo, 
                         base_model: ScoringModel, adapted_model: ScoringModel):
        """记录适配历史"""
        try:
            adaptation_record = {
                'timestamp': time.time(),
                'project_type': getattr(project_info.project_type, 'value', 'unknown'),
                'project_size': project_info.size_metrics.code_lines,
                'base_weights': base_model.weights,
                'adapted_weights': adapted_model.weights,
                'confidence_change': adapted_model.confidence_level - base_model.confidence_level
            }
            
            self.adaptation_history.append(adaptation_record)
            
            # 限制历史记录数量
            if len(self.adaptation_history) > 100:
                self.adaptation_history = self.adaptation_history[-100:]
                
        except Exception as e:
            self.logger.error(f"适配历史记录失败: {e}")
    
    def _get_fallback_model(self, project_type) -> ScoringModel:
        """获取降级模型"""
        return ScoringModel(
            weights={
                "quality": 0.3,
                "testing": 0.25,
                "security": 0.2,
                "documentation": 0.15,
                "performance": 0.1
            },
            quality_adjustments={},
            historical_adjustments={},
            confidence_level=0.4
        )
    
    def get_adaptation_stats(self) -> Dict[str, Any]:
        """获取适配统计信息"""
        try:
            if not self.adaptation_history:
                return {"total_adaptations": 0}
            
            return {
                "total_adaptations": len(self.adaptation_history),
                "avg_confidence_improvement": sum(
                    record.get('confidence_change', 0) 
                    for record in self.adaptation_history
                ) / len(self.adaptation_history),
                "most_adapted_project_types": self._get_top_adapted_types()
            }
            
        except Exception as e:
            self.logger.error(f"适配统计获取失败: {e}")
            return {}
    
    def _get_top_adapted_types(self) -> List[str]:
        """获取最常适配的项目类型"""
        try:
            type_counts = defaultdict(int)
            for record in self.adaptation_history:
                type_counts[record.get('project_type', 'unknown')] += 1
            
            return sorted(type_counts.keys(), 
                        key=lambda x: type_counts[x], reverse=True)[:5]
        except:
            return []


class BenchmarkDatabase:
    """基准数据库 - 存储项目基准数据"""
    
    def __init__(self):
        self.projects: List[Dict[str, Any]] = []
        self._load_benchmark_data()
    
    def _load_benchmark_data(self):
        """加载基准数据"""
        # 简化实现，实际应从文件或数据库加载
        self.projects = [
            {
                'project_type': 'web_application',
                'size': 15000,
                'languages': ['python', 'javascript'],
                'scoring_weights': {
                    'security': 0.35,
                    'quality': 0.25,
                    'performance': 0.25,
                    'testing': 0.15
                }
            },
            {
                'project_type': 'library', 
                'size': 5000,
                'languages': ['python'],
                'scoring_weights': {
                    'quality': 0.35,
                    'testing': 0.3,
                    'documentation': 0.25,
                    'security': 0.1
                }
            }
        ]
    
    def find_similar_projects(self, project_info: ProjectInfo, 
                            limit: int = 10) -> List[Dict[str, Any]]:
        """查找相似项目"""
        try:
            project_type = getattr(project_info.project_type, 'value', 'unknown')
            project_size = project_info.size_metrics.code_lines
            
            similar = []
            for project in self.projects:
                if project.get('project_type') == project_type:
                    # 简单的相似度计算
                    size_diff = abs(project.get('size', 0) - project_size) / max(project_size, 1)
                    if size_diff < 2.0:  # 规模差异不超过2倍
                        similar.append(project)
            
            return similar[:limit]
            
        except Exception as e:
            logger.error(f"查找相似项目失败: {e}")
            return []


def create_adaptive_agent() -> AdaptiveAgent:
    """创建自适应代理实例"""
    return AdaptiveAgent()