#!/usr/bin/env python3
"""
策略引擎 - 制定工具选择和执行策略
为智能决策代理提供策略制定支持
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import time

from .project_detector import ProjectInfo, ProjectType, StructureType
from .tool_registry import Tool

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """策略类型"""
    CONSERVATIVE = "conservative"    # 保守策略：少量工具，快速执行
    BALANCED = "balanced"           # 平衡策略：中等工具数量和执行时间
    COMPREHENSIVE = "comprehensive" # 全面策略：更多工具，完整分析
    SECURITY_FOCUSED = "security_focused"  # 安全专注策略
    QUALITY_FOCUSED = "quality_focused"    # 质量专注策略


class ResourceConstraint(Enum):
    """资源约束类型"""
    TIME_LIMITED = "time_limited"      # 时间受限
    CPU_LIMITED = "cpu_limited"        # CPU受限
    MEMORY_LIMITED = "memory_limited"  # 内存受限
    NETWORK_LIMITED = "network_limited" # 网络受限


@dataclass
class ToolSelectionStrategy:
    """工具选择策略"""
    strategy_type: StrategyType
    selected_tools: List[Tool]
    tool_priorities: Dict[str, int]  # 工具名称 -> 优先级
    execution_constraints: Dict[str, Any]
    quality_thresholds: Dict[str, float]  # 质量阈值
    time_budget: int  # 时间预算（秒）
    resource_limits: Dict[ResourceConstraint, float]
    reasoning: str = ""  # 策略选择理由
    confidence: float = 0.0  # 策略信心度


@dataclass  
class ExecutionContext:
    """执行上下文"""
    project_complexity: float
    risk_score: float
    available_resources: Dict[str, float]
    time_constraints: Optional[int] = None
    quality_requirements: Dict[str, float] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)


class StrategyEngine:
    """
    策略引擎 - 基于项目特征和约束条件制定最优策略
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._initialize_strategy_templates()
        self._initialize_decision_rules()
        
    def _initialize_strategy_templates(self):
        """初始化策略模板"""
        self.strategy_templates = {
            StrategyType.CONSERVATIVE: {
                'max_tools_per_category': 1,
                'max_total_tools': 5,
                'max_execution_time': 300,  # 5分钟
                'prefer_fast_tools': True,
                'parallel_execution': True,
                'quality_threshold': 0.6,
                'tool_categories_priority': ['security', 'syntax', 'basic_quality']
            },
            StrategyType.BALANCED: {
                'max_tools_per_category': 2,
                'max_total_tools': 8,
                'max_execution_time': 600,  # 10分钟
                'prefer_fast_tools': False,
                'parallel_execution': True,
                'quality_threshold': 0.7,
                'tool_categories_priority': ['security', 'quality', 'testing', 'dependencies']
            },
            StrategyType.COMPREHENSIVE: {
                'max_tools_per_category': 3,
                'max_total_tools': 12,
                'max_execution_time': 1200,  # 20分钟
                'prefer_fast_tools': False,
                'parallel_execution': True,
                'quality_threshold': 0.8,
                'tool_categories_priority': ['security', 'quality', 'testing', 'dependencies', 'performance', 'documentation']
            },
            StrategyType.SECURITY_FOCUSED: {
                'max_tools_per_category': 3,
                'max_total_tools': 10,
                'max_execution_time': 900,  # 15分钟
                'prefer_fast_tools': False,
                'parallel_execution': False,  # 串行执行确保准确性
                'quality_threshold': 0.9,
                'tool_categories_priority': ['security', 'dependencies', 'static_analysis']
            },
            StrategyType.QUALITY_FOCUSED: {
                'max_tools_per_category': 4,
                'max_total_tools': 15,
                'max_execution_time': 1800,  # 30分钟
                'prefer_fast_tools': False,
                'parallel_execution': True,
                'quality_threshold': 0.85,
                'tool_categories_priority': ['quality', 'testing', 'code_style', 'complexity', 'documentation']
            }
        }
        
    def _initialize_decision_rules(self):
        """初始化决策规则"""
        # 项目类型 -> 推荐策略类型
        self.project_strategy_mapping = {
            ProjectType.WEB_APPLICATION: StrategyType.SECURITY_FOCUSED,
            ProjectType.LIBRARY: StrategyType.QUALITY_FOCUSED,
            ProjectType.CLI_TOOL: StrategyType.BALANCED,
            ProjectType.DATA_SCIENCE: StrategyType.COMPREHENSIVE,
            ProjectType.DESKTOP_APP: StrategyType.BALANCED,
            ProjectType.MOBILE_APP: StrategyType.BALANCED
        }
        
        # 复杂度范围 -> 策略调整
        self.complexity_adjustments = {
            (0, 25): {'strategy_bias': StrategyType.CONSERVATIVE, 'time_multiplier': 0.7},
            (25, 50): {'strategy_bias': StrategyType.BALANCED, 'time_multiplier': 1.0},
            (50, 75): {'strategy_bias': StrategyType.COMPREHENSIVE, 'time_multiplier': 1.3},
            (75, 100): {'strategy_bias': StrategyType.COMPREHENSIVE, 'time_multiplier': 1.5}
        }
        
        # 风险分数 -> 安全策略权重
        self.risk_strategy_weights = {
            (0, 30): 0.1,      # 低风险
            (30, 60): 0.3,     # 中等风险  
            (60, 80): 0.6,     # 高风险
            (80, 100): 0.9     # 极高风险
        }
    
    def create_strategy(self, complexity: float, risks: List, 
                       effectiveness: Dict[str, float], time_budget: Optional[int],
                       project_info: ProjectInfo, available_tools: List[Tool]) -> ToolSelectionStrategy:
        """
        创建工具选择策略
        
        Args:
            complexity: 复杂度分数
            risks: 风险因素列表
            effectiveness: 工具效果预测
            time_budget: 时间预算
            project_info: 项目信息
            available_tools: 可用工具
            
        Returns:
            工具选择策略
        """
        try:
            # 1. 确定基础策略类型
            base_strategy_type = self._determine_base_strategy(project_info, complexity, risks)
            
            # 2. 创建执行上下文
            context = ExecutionContext(
                project_complexity=complexity,
                risk_score=self._calculate_risk_score(risks),
                available_resources={'time': time_budget or 1200},
                time_constraints=time_budget,
                quality_requirements={'min_score': 0.7},
                user_preferences={}
            )
            
            # 3. 调整策略参数
            adjusted_strategy = self._adjust_strategy_for_context(base_strategy_type, context)
            
            # 4. 选择最优工具组合
            selected_tools = self._select_optimal_tools(
                available_tools, adjusted_strategy, effectiveness, project_info)
            
            # 5. 计算工具优先级
            tool_priorities = self._calculate_tool_priorities(selected_tools, effectiveness, risks)
            
            # 6. 设定执行约束
            execution_constraints = self._create_execution_constraints(adjusted_strategy, context)
            
            # 7. 计算策略信心度
            confidence = self._calculate_strategy_confidence(
                selected_tools, effectiveness, context)
            
            strategy = ToolSelectionStrategy(
                strategy_type=base_strategy_type,
                selected_tools=selected_tools,
                tool_priorities=tool_priorities,
                execution_constraints=execution_constraints,
                quality_thresholds={'min_effectiveness': 0.5},
                time_budget=adjusted_strategy['max_execution_time'],
                resource_limits={
                    ResourceConstraint.TIME_LIMITED: adjusted_strategy['max_execution_time'],
                    ResourceConstraint.CPU_LIMITED: 80.0,  # 80% CPU使用率上限
                    ResourceConstraint.MEMORY_LIMITED: 2048.0  # 2GB内存上限
                },
                reasoning=self._generate_strategy_reasoning(
                    base_strategy_type, selected_tools, context),
                confidence=confidence
            )
            
            self.logger.info(f"策略创建完成: {base_strategy_type.value}, "
                           f"选择{len(selected_tools)}个工具, 信心度={confidence:.2f}")
            
            return strategy
            
        except Exception as e:
            self.logger.error(f"策略创建失败: {e}")
            # 返回默认保守策略
            return self._create_fallback_strategy(available_tools)
    
    def _determine_base_strategy(self, project_info: ProjectInfo, 
                               complexity: float, risks: List) -> StrategyType:
        """确定基础策略类型"""
        try:
            # 基于项目类型的推荐策略
            project_type = project_info.project_type
            if hasattr(project_type, 'value'):
                project_type_enum = ProjectType(project_type.value)
            else:
                project_type_enum = ProjectType.LIBRARY  # 默认
            
            base_strategy = self.project_strategy_mapping.get(
                project_type_enum, StrategyType.BALANCED)
            
            # 基于复杂度调整
            for (min_complexity, max_complexity), adjustment in self.complexity_adjustments.items():
                if min_complexity <= complexity < max_complexity:
                    if adjustment['strategy_bias'] != base_strategy:
                        # 如果复杂度建议不同策略，选择更保守的
                        if complexity < 30:
                            base_strategy = StrategyType.CONSERVATIVE
                        elif complexity > 70:
                            base_strategy = StrategyType.COMPREHENSIVE
                    break
            
            # 基于风险调整
            risk_score = self._calculate_risk_score(risks)
            if risk_score > 60:
                # 高风险项目倾向于安全专注策略
                if base_strategy not in [StrategyType.SECURITY_FOCUSED, StrategyType.COMPREHENSIVE]:
                    base_strategy = StrategyType.SECURITY_FOCUSED
            
            return base_strategy
            
        except Exception as e:
            self.logger.error(f"基础策略确定失败: {e}")
            return StrategyType.BALANCED
    
    def _adjust_strategy_for_context(self, strategy_type: StrategyType, 
                                   context: ExecutionContext) -> Dict[str, Any]:
        """根据上下文调整策略参数"""
        try:
            # 获取基础模板
            base_template = self.strategy_templates[strategy_type].copy()
            
            # 基于项目复杂度调整
            complexity_multiplier = 1.0
            if context.project_complexity < 25:
                complexity_multiplier = 0.8
            elif context.project_complexity > 75:
                complexity_multiplier = 1.2
            
            # 调整工具数量限制
            base_template['max_total_tools'] = int(
                base_template['max_total_tools'] * complexity_multiplier)
            
            # 基于时间约束调整
            if context.time_constraints:
                # 如果用户设定了时间约束，优先满足
                base_template['max_execution_time'] = min(
                    base_template['max_execution_time'], context.time_constraints)
                
                # 时间紧张时减少工具数量
                if context.time_constraints < 300:  # 少于5分钟
                    base_template['max_total_tools'] = min(
                        base_template['max_total_tools'], 3)
                    base_template['prefer_fast_tools'] = True
            
            # 基于风险分数调整安全工具权重
            if context.risk_score > 50:
                security_categories = ['security', 'static_analysis', 'dependencies']
                existing_priorities = base_template['tool_categories_priority']
                
                # 将安全相关类别提前
                new_priorities = []
                for category in security_categories:
                    if category in existing_priorities:
                        new_priorities.append(category)
                
                for category in existing_priorities:
                    if category not in new_priorities:
                        new_priorities.append(category)
                
                base_template['tool_categories_priority'] = new_priorities
            
            return base_template
            
        except Exception as e:
            self.logger.error(f"策略调整失败: {e}")
            return self.strategy_templates[StrategyType.BALANCED]
    
    def _select_optimal_tools(self, available_tools: List[Tool], 
                            strategy: Dict[str, Any],
                            effectiveness: Dict[str, float],
                            project_info: ProjectInfo) -> List[Tool]:
        """选择最优工具组合"""
        try:
            # 按类别分组工具
            tools_by_category = {}
            for tool in available_tools:
                for category in tool.categories:
                    if category not in tools_by_category:
                        tools_by_category[category] = []
                    tools_by_category[category].append(tool)
            
            selected_tools = []
            total_time = 0
            max_time = strategy['max_execution_time']
            max_tools = strategy['max_total_tools']
            
            # 按优先级类别选择工具
            for category in strategy['tool_categories_priority']:
                if category not in tools_by_category:
                    continue
                
                category_tools = tools_by_category[category]
                max_category_tools = strategy['max_tools_per_category']
                
                # 按效果和优先级排序
                scored_tools = []
                for tool in category_tools:
                    if len(selected_tools) >= max_tools:
                        break
                    
                    effectiveness_score = effectiveness.get(tool.name, 0.5)
                    
                    # 综合评分：效果 + 优先级 + 速度
                    priority_score = (6 - tool.priority) / 5.0  # 转换为0-1分数
                    speed_score = max(0.1, 60.0 / tool.estimated_time) if strategy['prefer_fast_tools'] else 0.5
                    
                    composite_score = (
                        effectiveness_score * 0.5 +
                        priority_score * 0.3 +
                        speed_score * 0.2
                    )
                    
                    scored_tools.append((composite_score, tool))
                
                # 排序并选择最佳工具
                scored_tools.sort(key=lambda x: x[0], reverse=True)
                
                category_selected = 0
                for score, tool in scored_tools:
                    if (category_selected >= max_category_tools or 
                        len(selected_tools) >= max_tools or
                        total_time + tool.estimated_time > max_time):
                        break
                    
                    if tool not in selected_tools:
                        selected_tools.append(tool)
                        total_time += tool.estimated_time
                        category_selected += 1
            
            # 如果选择的工具太少，补充一些通用工具
            if len(selected_tools) < 3:
                universal_tools = [t for t in available_tools 
                                 if 'universal' in t.categories and t not in selected_tools]
                universal_tools.sort(key=lambda t: effectiveness.get(t.name, 0.5), reverse=True)
                
                for tool in universal_tools[:2]:
                    if total_time + tool.estimated_time <= max_time:
                        selected_tools.append(tool)
                        total_time += tool.estimated_time
            
            self.logger.debug(f"选择了{len(selected_tools)}个工具，预估时间{total_time}秒")
            return selected_tools
            
        except Exception as e:
            self.logger.error(f"工具选择失败: {e}")
            return available_tools[:3]  # 降级策略
    
    def _calculate_tool_priorities(self, tools: List[Tool], 
                                 effectiveness: Dict[str, float],
                                 risks: List) -> Dict[str, int]:
        """计算工具优先级"""
        try:
            priorities = {}
            
            # 安全工具在高风险项目中优先级更高
            has_security_risk = any('security' in str(risk) for risk in risks)
            
            for i, tool in enumerate(tools):
                base_priority = len(tools) - i  # 基础优先级
                
                # 基于工具本身优先级调整
                tool_priority_bonus = (6 - tool.priority) * 2
                
                # 基于效果预测调整
                effectiveness_bonus = int(effectiveness.get(tool.name, 0.5) * 10)
                
                # 安全工具加分
                security_bonus = 5 if (has_security_risk and 'security' in tool.categories) else 0
                
                final_priority = base_priority + tool_priority_bonus + effectiveness_bonus + security_bonus
                priorities[tool.name] = final_priority
            
            return priorities
            
        except Exception as e:
            self.logger.error(f"优先级计算失败: {e}")
            return {tool.name: i for i, tool in enumerate(tools, 1)}
    
    def _create_execution_constraints(self, strategy: Dict[str, Any], 
                                    context: ExecutionContext) -> Dict[str, Any]:
        """创建执行约束"""
        return {
            'max_execution_time': strategy['max_execution_time'],
            'max_parallel_tools': 4 if strategy['parallel_execution'] else 1,
            'timeout_per_tool': strategy['max_execution_time'] // len(strategy.get('selected_tools', [1])),
            'memory_limit_mb': 2048,
            'cpu_limit_percent': 80,
            'allow_tool_failure': True,
            'early_termination_on_critical_error': True
        }
    
    def _calculate_strategy_confidence(self, tools: List[Tool], 
                                     effectiveness: Dict[str, float],
                                     context: ExecutionContext) -> float:
        """计算策略信心度"""
        try:
            if not tools:
                return 0.1
            
            # 基于工具效果预测的信心度
            avg_effectiveness = sum(effectiveness.get(t.name, 0.5) for t in tools) / len(tools)
            effectiveness_confidence = avg_effectiveness
            
            # 基于工具数量的信心度（太少或太多都降低信心度）
            tool_count_confidence = 1.0
            if len(tools) < 3:
                tool_count_confidence = 0.7
            elif len(tools) > 10:
                tool_count_confidence = 0.8
            
            # 基于时间预算的信心度
            total_estimated_time = sum(t.estimated_time for t in tools)
            time_confidence = 1.0
            if context.time_constraints and total_estimated_time > context.time_constraints:
                time_confidence = 0.6
            
            # 综合信心度
            overall_confidence = (
                effectiveness_confidence * 0.5 +
                tool_count_confidence * 0.3 +
                time_confidence * 0.2
            )
            
            return min(max(overall_confidence, 0.1), 1.0)
            
        except Exception as e:
            self.logger.error(f"信心度计算失败: {e}")
            return 0.5
    
    def _generate_strategy_reasoning(self, strategy_type: StrategyType,
                                   tools: List[Tool], 
                                   context: ExecutionContext) -> str:
        """生成策略选择理由"""
        reasoning_parts = []
        
        # 策略类型理由
        strategy_reasons = {
            StrategyType.CONSERVATIVE: "项目复杂度较低，选择快速执行策略",
            StrategyType.BALANCED: "综合考虑项目特征，选择平衡策略",
            StrategyType.COMPREHENSIVE: "项目复杂度高，需要全面分析",
            StrategyType.SECURITY_FOCUSED: "检测到安全风险，优先安全分析",
            StrategyType.QUALITY_FOCUSED: "库项目或质量要求高，专注代码质量"
        }
        
        reasoning_parts.append(strategy_reasons.get(strategy_type, "基于项目特征选择策略"))
        
        # 工具选择理由
        if len(tools) <= 5:
            reasoning_parts.append(f"选择{len(tools)}个核心工具确保执行效率")
        elif len(tools) <= 8:
            reasoning_parts.append(f"选择{len(tools)}个工具平衡分析深度和执行时间")
        else:
            reasoning_parts.append(f"选择{len(tools)}个工具进行全面分析")
        
        # 时间约束理由
        if context.time_constraints and context.time_constraints < 600:
            reasoning_parts.append("时间受限，优先快速工具")
        
        # 风险考虑
        if context.risk_score > 60:
            reasoning_parts.append("高风险项目，加强安全检查")
        
        return "; ".join(reasoning_parts)
    
    def _calculate_risk_score(self, risks: List) -> float:
        """计算风险分数"""
        if not risks:
            return 0.0
        
        # 不同风险因素的权重
        risk_weights = {
            'security': 20,
            'web_security': 25,
            'sql_injection': 30,
            'xss': 25,
            'dependency_risk': 15,
            'performance': 10,
            'data_privacy': 20,
            'license_risk': 5,
            'build_complexity': 5,
            'multi_language': 10
        }
        
        total_score = 0.0
        for risk in risks:
            risk_name = str(risk).lower()
            for key, weight in risk_weights.items():
                if key in risk_name:
                    total_score += weight
                    break
        
        return min(total_score, 100.0)
    
    def _create_fallback_strategy(self, available_tools: List[Tool]) -> ToolSelectionStrategy:
        """创建降级策略"""
        # 选择前3个可用工具
        selected_tools = available_tools[:3]
        
        return ToolSelectionStrategy(
            strategy_type=StrategyType.CONSERVATIVE,
            selected_tools=selected_tools,
            tool_priorities={tool.name: i for i, tool in enumerate(selected_tools, 1)},
            execution_constraints={'max_execution_time': 300},
            quality_thresholds={'min_effectiveness': 0.3},
            time_budget=300,
            resource_limits={ResourceConstraint.TIME_LIMITED: 300},
            reasoning="降级策略：系统异常时的最小工具集",
            confidence=0.3
        )

    def evaluate_strategy_performance(self, strategy: ToolSelectionStrategy,
                                    actual_results: Dict[str, Any]) -> Dict[str, float]:
        """评估策略执行效果（用于学习和优化）"""
        try:
            performance_metrics = {}
            
            # 时间效率评估
            actual_time = actual_results.get('total_execution_time', 0)
            planned_time = strategy.time_budget
            
            if planned_time > 0:
                time_efficiency = min(1.0, planned_time / max(actual_time, 1))
                performance_metrics['time_efficiency'] = time_efficiency
            
            # 工具成功率
            successful_tools = actual_results.get('successful_tools', 0)
            total_tools = len(strategy.selected_tools)
            
            if total_tools > 0:
                success_rate = successful_tools / total_tools
                performance_metrics['success_rate'] = success_rate
            
            # 质量发现效果
            issues_found = actual_results.get('total_issues', 0)
            quality_score = actual_results.get('overall_quality_score', 0)
            
            # 基于发现问题数量和质量分数评估效果
            discovery_effectiveness = min(1.0, (issues_found * 0.1 + quality_score / 100) / 2)
            performance_metrics['discovery_effectiveness'] = discovery_effectiveness
            
            # 综合效果分数
            overall_performance = (
                performance_metrics.get('time_efficiency', 0.5) * 0.3 +
                performance_metrics.get('success_rate', 0.5) * 0.4 +
                performance_metrics.get('discovery_effectiveness', 0.5) * 0.3
            )
            
            performance_metrics['overall_performance'] = overall_performance
            
            self.logger.debug(f"策略效果评估完成: 综合分数={overall_performance:.2f}")
            
            return performance_metrics
            
        except Exception as e:
            self.logger.error(f"策略效果评估失败: {e}")
            return {'overall_performance': 0.5}