#!/usr/bin/env python3
"""
Decision Agent - 智能决策代理
基于项目特征和可用工具，智能制定工具选择和执行策略

核心特性:
- 集成 ToolKnowledgeBase 工具知识库
- 集成 StrategyEngine 策略引擎  
- 集成 SimpleMLModel 简单学习模型
- 工具效果预测和资源需求分析
- 智能降级策略和超时处理
"""

import logging
import time
from dataclasses import dataclass, field
from typing import List, Dict, Set, Any, Optional, Tuple
from enum import Enum
from collections import defaultdict

from .project_detector import ProjectInfo, ProjectType, StructureType
from .tool_registry import Tool
from .tool_knowledge_base import ToolKnowledgeBase
from .strategy_engine import StrategyEngine, StrategyType, ToolSelectionStrategy
from .simple_ml_model import SimpleMLModel

logger = logging.getLogger(__name__)


class ComplexityLevel(Enum):
    """项目复杂度等级"""
    LOW = "low"           # 简单项目 (<1K LOC)
    MEDIUM = "medium"     # 中等项目 (1K-10K LOC)
    HIGH = "high"         # 复杂项目 (10K-100K LOC)
    VERY_HIGH = "very_high"  # 极高复杂度 (>100K LOC)


class RiskFactor(Enum):
    """风险因素枚举"""
    SECURITY = "security"               # 安全风险
    WEB_SECURITY = "web_security"       # Web安全风险
    SQL_INJECTION = "sql_injection"     # SQL注入风险
    XSS = "xss"                        # XSS风险
    DEPENDENCY_RISK = "dependency_risk" # 依赖风险
    PERFORMANCE = "performance"         # 性能风险
    DATA_PRIVACY = "data_privacy"       # 数据隐私风险
    LICENSE_RISK = "license_risk"       # 许可证风险
    BUILD_COMPLEXITY = "build_complexity" # 构建复杂性
    MULTI_LANGUAGE = "multi_language"   # 多语言项目风险


class ExecutionMode(Enum):
    """执行模式"""
    PARALLEL = "parallel"     # 并行执行
    SEQUENTIAL = "sequential" # 串行执行
    HYBRID = "hybrid"         # 混合执行


class ToolPriority(Enum):
    """工具优先级"""
    CRITICAL = 1    # 关键工具，必须执行
    HIGH = 2        # 高优先级
    MEDIUM = 3      # 中等优先级
    LOW = 4         # 低优先级
    OPTIONAL = 5    # 可选工具


@dataclass
class ExecutionPhase:
    """执行阶段定义"""
    name: str
    tools: List[Tool]
    mode: ExecutionMode
    timeout: int = 300  # 阶段超时时间（秒）
    dependencies: List[str] = field(default_factory=list)  # 依赖的阶段名称
    allow_failure: bool = True  # 是否允许工具执行失败


@dataclass
class ExecutionPlan:
    """执行计划"""
    phases: List[ExecutionPhase]
    total_estimated_time: int  # 预估总执行时间
    max_parallel_tools: int = 4  # 最大并行工具数
    early_termination_conditions: List[str] = field(default_factory=list)
    fallback_strategy: str = "continue"  # 失败时的降级策略
    
    def get_total_tools(self) -> int:
        """获取总工具数量"""
        return sum(len(phase.tools) for phase in self.phases)


@dataclass
class ProjectComplexityMetrics:
    """项目复杂度指标"""
    code_lines: int
    file_count: int
    directory_depth: int
    language_count: int
    dependency_count: int
    build_files_count: int
    config_files_count: int
    complexity_score: float  # 综合复杂度分数 0-100


@dataclass
class RiskAssessment:
    """风险评估结果"""
    risk_factors: List[RiskFactor]
    risk_score: float  # 风险分数 0-100
    high_risk_areas: List[str]
    recommended_security_tools: List[str]
    risk_mitigation_priority: Dict[RiskFactor, int]  # 风险缓解优先级


class DecisionAgent:
    """
    决策Agent - 智能工具选择和执行策略制定
    
    核心特性：
    1. 集成工具知识库进行效果预测
    2. 使用策略引擎制定最优策略
    3. 基于ML模型预测工具表现
    4. 智能资源需求分析和超时策略
    5. 完整的降级和错误处理机制
    """
    
    def __init__(self, knowledge_base_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # 智能代理核心组件
        self.knowledge_base = ToolKnowledgeBase(knowledge_base_path)
        self.strategy_engine = StrategyEngine()
        self.learning_model = SimpleMLModel()
        
        self._initialize_decision_rules()
    
    def _initialize_decision_rules(self):
        """初始化决策规则"""
        # 项目类型到推荐工具类型的映射
        self.project_type_tool_preferences = {
            ProjectType.WEB_APPLICATION: {
                'security': ['bandit', 'semgrep', 'gitleaks', 'npm-audit'],
                'quality': ['pylint', 'eslint', 'sonarqube-scanner'],
                'testing': ['pytest', 'jest', 'coverage']
            },
            ProjectType.LIBRARY: {
                'quality': ['pylint', 'eslint', 'checkstyle', 'mypy'],
                'testing': ['pytest', 'jest', 'junit', 'coverage'],
                'documentation': ['sphinx', 'jsdoc']
            },
            ProjectType.CLI_TOOL: {
                'quality': ['pylint', 'go-vet', 'clippy'],
                'testing': ['pytest', 'go-test', 'cargo-test'],
                'build': ['black', 'gofmt', 'rustfmt']
            },
            ProjectType.DATA_SCIENCE: {
                'security': ['bandit', 'safety'],
                'quality': ['pylint', 'flake8'],
                'dependencies': ['safety', 'pip-audit']
            }
        }
        
        # 复杂度等级到工具选择策略的映射
        self.complexity_strategies = {
            ComplexityLevel.LOW: {
                'max_tools_per_category': 1,
                'prefer_fast_tools': True,
                'max_execution_time': 300  # 5分钟
            },
            ComplexityLevel.MEDIUM: {
                'max_tools_per_category': 2,
                'prefer_fast_tools': False,
                'max_execution_time': 600  # 10分钟
            },
            ComplexityLevel.HIGH: {
                'max_tools_per_category': 2,
                'prefer_fast_tools': False,
                'max_execution_time': 1200  # 20分钟
            },
            ComplexityLevel.VERY_HIGH: {
                'max_tools_per_category': 3,
                'prefer_fast_tools': False,
                'max_execution_time': 1800  # 30分钟
            }
        }
    
    def analyze_project_complexity(self, project_info: ProjectInfo) -> ProjectComplexityMetrics:
        """
        分析项目复杂度
        
        Args:
            project_info: 项目信息
            
        Returns:
            项目复杂度指标
        """
        try:
            metrics = ProjectComplexityMetrics(
                code_lines=project_info.size_metrics.code_lines,
                file_count=project_info.size_metrics.total_files,
                directory_depth=self._calculate_directory_depth(project_info.path),
                language_count=len(project_info.languages),
                dependency_count=sum(len(deps) for deps in project_info.dependencies.values()),
                build_files_count=len(project_info.build_tools),
                config_files_count=self._count_config_files(project_info.path),
                complexity_score=0.0
            )
            
            # 计算综合复杂度分数
            complexity_score = 0.0
            
            # 代码行数权重 (40%)
            if metrics.code_lines < 1000:
                complexity_score += 10
            elif metrics.code_lines < 10000:
                complexity_score += 30
            elif metrics.code_lines < 100000:
                complexity_score += 60
            else:
                complexity_score += 90
            
            # 语言数量权重 (20%)
            if metrics.language_count == 1:
                complexity_score += 0
            elif metrics.language_count <= 3:
                complexity_score += 5
            else:
                complexity_score += 15
            
            # 依赖数量权重 (20%)
            if metrics.dependency_count < 10:
                complexity_score += 0
            elif metrics.dependency_count < 50:
                complexity_score += 5
            elif metrics.dependency_count < 100:
                complexity_score += 10
            else:
                complexity_score += 15
            
            # 项目结构权重 (10%)
            if project_info.structure_type == StructureType.MONOREPO:
                complexity_score += 8
            elif project_info.structure_type == StructureType.MULTI_PROJECT:
                complexity_score += 5
            
            # 构建复杂度权重 (10%)
            complexity_score += min(metrics.build_files_count * 2, 10)
            
            metrics.complexity_score = min(complexity_score, 100.0)
            
            self.logger.debug(f"项目复杂度分析完成: 分数={metrics.complexity_score:.1f}, "
                            f"代码行数={metrics.code_lines}, 语言数={metrics.language_count}")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"项目复杂度分析失败: {e}")
            # 返回默认的中等复杂度指标
            return ProjectComplexityMetrics(
                code_lines=project_info.size_metrics.code_lines or 5000,
                file_count=project_info.size_metrics.total_files or 50,
                directory_depth=5,
                language_count=len(project_info.languages) or 1,
                dependency_count=20,
                build_files_count=1,
                config_files_count=3,
                complexity_score=50.0
            )
    
    def assess_project_risks(self, project_info: ProjectInfo, 
                           complexity_metrics: ProjectComplexityMetrics) -> RiskAssessment:
        """
        评估项目风险
        
        Args:
            project_info: 项目信息
            complexity_metrics: 复杂度指标
            
        Returns:
            风险评估结果
        """
        risk_factors = []
        high_risk_areas = []
        recommended_security_tools = []
        risk_score = 0.0
        
        try:
            # 基于项目类型识别风险
            project_type = project_info.project_type
            if hasattr(project_type, 'value'):
                project_type_value = project_type.value
            else:
                project_type_value = str(project_type)
            
            if project_type_value == 'web_application':
                risk_factors.extend([RiskFactor.SECURITY, RiskFactor.WEB_SECURITY, RiskFactor.XSS])
                high_risk_areas.extend(['Web安全', 'API安全', '用户输入验证'])
                recommended_security_tools.extend(['bandit', 'semgrep', 'npm-audit'])
                risk_score += 30
            
            elif project_type_value == 'data_science':
                risk_factors.extend([RiskFactor.DATA_PRIVACY, RiskFactor.DEPENDENCY_RISK])
                high_risk_areas.extend(['数据隐私', '敏感数据处理'])
                recommended_security_tools.extend(['bandit', 'safety'])
                risk_score += 20
            
            # 基于依赖数量评估风险
            if complexity_metrics.dependency_count > 100:
                risk_factors.append(RiskFactor.DEPENDENCY_RISK)
                high_risk_areas.append('大量第三方依赖')
                recommended_security_tools.extend(['safety', 'npm-audit', 'trivy'])
                risk_score += 15
            elif complexity_metrics.dependency_count > 50:
                risk_factors.append(RiskFactor.DEPENDENCY_RISK)
                risk_score += 10
            
            # 多语言项目风险
            if complexity_metrics.language_count > 3:
                risk_factors.append(RiskFactor.MULTI_LANGUAGE)
                high_risk_areas.append('多语言项目复杂性')
                risk_score += 10
            
            # 大型项目风险
            if complexity_metrics.code_lines > 50000:
                risk_factors.extend([RiskFactor.PERFORMANCE, RiskFactor.BUILD_COMPLEXITY])
                high_risk_areas.extend(['性能问题', '构建复杂性'])
                risk_score += 15
            
            # 检查是否有数据库相关依赖
            all_deps = []
            for deps in project_info.dependencies.values():
                all_deps.extend([dep.lower() for dep in deps])
            
            db_indicators = ['mysql', 'postgres', 'sqlite', 'mongodb', 'redis', 'django', 'sqlalchemy']
            if any(indicator in ' '.join(all_deps) for indicator in db_indicators):
                risk_factors.append(RiskFactor.SQL_INJECTION)
                high_risk_areas.append('数据库安全')
                recommended_security_tools.append('semgrep')
                risk_score += 10
            
            # 去重推荐工具
            recommended_security_tools = list(set(recommended_security_tools))
            
            # 风险缓解优先级
            risk_mitigation_priority = {}
            for i, risk in enumerate(risk_factors):
                risk_mitigation_priority[risk] = len(risk_factors) - i
            
            risk_assessment = RiskAssessment(
                risk_factors=risk_factors,
                risk_score=min(risk_score, 100.0),
                high_risk_areas=high_risk_areas,
                recommended_security_tools=recommended_security_tools,
                risk_mitigation_priority=risk_mitigation_priority
            )
            
            self.logger.debug(f"风险评估完成: 风险分数={risk_assessment.risk_score:.1f}, "
                            f"风险因素数={len(risk_factors)}, 推荐安全工具={recommended_security_tools}")
            
            return risk_assessment
            
        except Exception as e:
            self.logger.error(f"风险评估失败: {e}")
            # 返回默认的中等风险评估
            return RiskAssessment(
                risk_factors=[RiskFactor.SECURITY],
                risk_score=30.0,
                high_risk_areas=['一般安全风险'],
                recommended_security_tools=['semgrep', 'gitleaks'],
                risk_mitigation_priority={RiskFactor.SECURITY: 1}
            )
    
    def make_tool_selection_decision(self, project_info: ProjectInfo, 
                                   available_tools: List[Tool]) -> List[Tool]:
        """
        智能工具选择决策
        
        核心特性:
        - 集成工具知识库进行效果预测
        - 使用策略引擎制定最优策略
        - 基于ML模型的工具表现预测
        - 智能时间预算和资源约束
        
        Args:
            project_info: 项目信息
            available_tools: 可用工具列表
            
        Returns:
            选择的工具列表
        """
        try:
            self.logger.info("开始智能工具选择决策...")
            
            # 1. 分析项目特征
            complexity_metrics = self.analyze_project_complexity(project_info)
            risk_assessment = self.assess_project_risks(project_info, complexity_metrics)
            
            self.logger.debug(f"项目特征分析完成: 复杂度={complexity_metrics.complexity_score:.1f}, "
                            f"风险分数={risk_assessment.risk_score:.1f}")
            
            # 2. 工具效果预测
            tool_effectiveness = self.predict_tool_effectiveness(available_tools, project_info)
            
            self.logger.debug(f"工具效果预测完成: {len(tool_effectiveness)}个工具预测")
            
            # 3. 策略引擎决策
            strategy = self.strategy_engine.create_strategy(
                complexity=complexity_metrics.complexity_score,
                risks=risk_assessment.risk_factors,
                effectiveness=tool_effectiveness,
                time_budget=self._estimate_time_budget(project_info),
                project_info=project_info,
                available_tools=available_tools
            )
            
            self.logger.info(f"策略决策完成: {strategy.strategy_type.value}, "
                           f"选择{len(strategy.selected_tools)}个工具, "
                           f"信心度={strategy.confidence:.2f}")
            
            # 4. 记录历史数据用于学习
            self._record_selection_decision(project_info, available_tools, 
                                          strategy.selected_tools, tool_effectiveness)
            
            return strategy.selected_tools
            
        except Exception as e:
            self.logger.error(f"智能工具选择决策失败: {e}")
            # 智能降级策略
            return self._create_fallback_selection(available_tools, project_info)
    
    def create_execution_plan(self, selected_tools: List[Tool], 
                            project_info: ProjectInfo) -> ExecutionPlan:
        """
        制定执行计划
        
        Args:
            selected_tools: 选择的工具列表
            project_info: 项目信息
            
        Returns:
            执行计划
        """
        try:
            if not selected_tools:
                return ExecutionPlan(phases=[], total_estimated_time=0)
            
            # 分析项目复杂度以决定执行策略
            complexity_metrics = self.analyze_project_complexity(project_info)
            complexity_level = self._get_complexity_level(complexity_metrics.complexity_score)
            
            # 按工具类型和依赖关系分组
            phases = []
            
            # 阶段1: 快速语法检查和基础工具（并行）
            fast_tools = [t for t in selected_tools if t.estimated_time <= 30]
            if fast_tools:
                phases.append(ExecutionPhase(
                    name="快速检查阶段",
                    tools=fast_tools,
                    mode=ExecutionMode.PARALLEL,
                    timeout=120,
                    allow_failure=True
                ))
            
            # 阶段2: 质量分析工具（根据复杂度决定执行模式）
            quality_tools = [t for t in selected_tools 
                           if t not in fast_tools and 'quality' in t.categories]
            if quality_tools:
                # 复杂项目使用串行执行避免资源竞争
                mode = ExecutionMode.SEQUENTIAL if complexity_level in [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH] else ExecutionMode.PARALLEL
                phases.append(ExecutionPhase(
                    name="质量分析阶段",
                    tools=quality_tools,
                    mode=mode,
                    timeout=600,
                    dependencies=["快速检查阶段"] if fast_tools else [],
                    allow_failure=True
                ))
            
            # 阶段3: 安全分析工具（串行执行，确保准确性）
            security_tools = [t for t in selected_tools 
                            if t not in fast_tools and t not in quality_tools and 'security' in t.categories]
            if security_tools:
                phases.append(ExecutionPhase(
                    name="安全分析阶段",
                    tools=security_tools,
                    mode=ExecutionMode.SEQUENTIAL,
                    timeout=900,
                    dependencies=["质量分析阶段"] if quality_tools else (["快速检查阶段"] if fast_tools else []),
                    allow_failure=False  # 安全工具不允许失败
                ))
            
            # 阶段4: 其他工具（剩余工具）
            other_tools = [t for t in selected_tools 
                          if t not in fast_tools and t not in quality_tools and t not in security_tools]
            if other_tools:
                phases.append(ExecutionPhase(
                    name="其他分析阶段",
                    tools=other_tools,
                    mode=ExecutionMode.PARALLEL,
                    timeout=300,
                    dependencies=["安全分析阶段"] if security_tools else [],
                    allow_failure=True
                ))
            
            # 计算总预估时间
            total_time = 0
            for phase in phases:
                if phase.mode == ExecutionMode.PARALLEL:
                    # 并行执行取最长工具时间
                    phase_time = max([t.estimated_time for t in phase.tools]) if phase.tools else 0
                else:
                    # 串行执行累加所有工具时间
                    phase_time = sum(t.estimated_time for t in phase.tools)
                total_time += phase_time
            
            # 根据复杂度调整并行工具数
            max_parallel = 2 if complexity_level == ComplexityLevel.LOW else (3 if complexity_level == ComplexityLevel.MEDIUM else 4)
            
            execution_plan = ExecutionPlan(
                phases=phases,
                total_estimated_time=total_time,
                max_parallel_tools=max_parallel,
                early_termination_conditions=[
                    "critical_security_issue_found",
                    "build_failure"
                ],
                fallback_strategy="continue_with_warnings"
            )
            
            self.logger.info(f"执行计划制定完成: {len(phases)}个阶段, "
                           f"总工具数={execution_plan.get_total_tools()}, "
                           f"预估时间={total_time}秒")
            
            return execution_plan
            
        except Exception as e:
            self.logger.error(f"执行计划制定失败: {e}")
            # 降级策略：简单的单阶段并行执行
            return ExecutionPlan(
                phases=[ExecutionPhase(
                    name="默认执行阶段",
                    tools=selected_tools,
                    mode=ExecutionMode.PARALLEL,
                    timeout=600
                )],
                total_estimated_time=sum(t.estimated_time for t in selected_tools),
                max_parallel_tools=2
            )
    
    def _get_complexity_level(self, complexity_score: float) -> ComplexityLevel:
        """根据复杂度分数确定等级"""
        if complexity_score < 20:
            return ComplexityLevel.LOW
        elif complexity_score < 50:
            return ComplexityLevel.MEDIUM
        elif complexity_score < 80:
            return ComplexityLevel.HIGH
        else:
            return ComplexityLevel.VERY_HIGH
    
    def _categorize_tools(self, tools: List[Tool]) -> Dict[str, List[Tool]]:
        """按类别对工具进行分组"""
        categories = defaultdict(list)
        
        for tool in tools:
            for category in tool.categories:
                categories[category].append(tool)
        
        return dict(categories)
    
    def _calculate_directory_depth(self, project_path: str) -> int:
        """计算项目目录深度"""
        import os
        max_depth = 0
        try:
            for root, dirs, files in os.walk(project_path):
                # 跳过常见的忽略目录
                dirs[:] = [d for d in dirs if d not in {
                    '.git', 'node_modules', '__pycache__', '.pytest_cache',
                    'venv', '.venv', 'env', '.env', 'target', 'build',
                    'dist', '.idea', '.vscode'
                }]
                
                depth = len(os.path.relpath(root, project_path).split(os.sep))
                max_depth = max(max_depth, depth)
        except Exception as e:
            self.logger.debug(f"计算目录深度失败: {e}")
            return 5  # 默认深度
        
        return max_depth
    
    def _count_config_files(self, project_path: str) -> int:
        """统计配置文件数量"""
        import os
        config_files = [
            '.gitignore', '.editorconfig', '.pre-commit-config.yaml',
            'pytest.ini', 'setup.cfg', 'pyproject.toml', 'tox.ini',
            'package.json', 'tsconfig.json', '.eslintrc', '.prettierrc',
            'pom.xml', 'build.gradle', 'Cargo.toml', 'go.mod',
            'Dockerfile', 'docker-compose.yml', 'requirements.txt'
        ]
        
        count = 0
        try:
            for config_file in config_files:
                if os.path.exists(os.path.join(project_path, config_file)):
                    count += 1
        except Exception as e:
            self.logger.debug(f"统计配置文件失败: {e}")
        
        return count


    # ========== 智能分析方法 ==========
    
    def predict_tool_effectiveness(self, tools: List[Tool], project_info: ProjectInfo) -> Dict[str, float]:
        """
        预测工具效果
        
        集成工具知识库和ML模型进行效果预测
        """
        try:
            # 1. 使用工具知识库预测
            knowledge_predictions = self.knowledge_base.predict_tool_effectiveness(tools, project_info)
            
            # 2. 使用ML模型预测
            risk_score = sum(10 for _ in self.assess_project_risks(project_info, 
                           self.analyze_project_complexity(project_info)).risk_factors)
            
            features = self.learning_model.extract_features(project_info, risk_score)
            ml_predictions = self.learning_model.predict_batch(tools, features)
            
            # 3. 综合预测结果（知识库权重0.6，ML模型权重0.4）
            combined_predictions = {}
            for tool in tools:
                knowledge_score = knowledge_predictions.get(tool.name, 0.5)
                ml_score = ml_predictions.get(tool.name)
                
                if ml_score:
                    combined_score = knowledge_score * 0.6 + ml_score.predicted_effectiveness * 0.4
                    # 考虑ML模型的信心度
                    confidence_weight = ml_score.confidence
                    final_score = combined_score * confidence_weight + knowledge_score * (1 - confidence_weight)
                else:
                    final_score = knowledge_score
                
                combined_predictions[tool.name] = max(0.1, min(1.0, final_score))
            
            self.logger.debug(f"综合效果预测完成: 平均分数={sum(combined_predictions.values())/len(combined_predictions):.2f}")
            return combined_predictions
            
        except Exception as e:
            self.logger.error(f"工具效果预测失败: {e}")
            return {tool.name: 0.5 for tool in tools}
    
    def _estimate_time_budget(self, project_info: ProjectInfo) -> Optional[int]:
        """估算时间预算"""
        try:
            # 基于项目规模估算合理的分析时间
            code_lines = project_info.size_metrics.code_lines
            
            if code_lines < 1000:
                return 300   # 5分钟
            elif code_lines < 10000:
                return 600   # 10分钟
            elif code_lines < 50000:
                return 1200  # 20分钟
            else:
                return 1800  # 30分钟
                
        except Exception as e:
            self.logger.error(f"时间预算估算失败: {e}")
            return 600  # 默认10分钟
    
    def _record_selection_decision(self, project_info: ProjectInfo, 
                                 available_tools: List[Tool],
                                 selected_tools: List[Tool],
                                 effectiveness_predictions: Dict[str, float]):
        """记录选择决策用于学习"""
        try:
            # 记录选择的工具及其预测效果
            for tool in selected_tools:
                predicted_effectiveness = effectiveness_predictions.get(tool.name, 0.5)
                
                # 这里实际应用中会在工具执行后记录真实效果
                # 现在先记录预测值作为占位符
                self.knowledge_base.record_tool_execution(
                    tool_name=tool.name,
                    project_info=project_info,
                    execution_time=tool.estimated_time,
                    success=True,  # 预测成功
                    quality_score=predicted_effectiveness * 100,
                    issues_found=int(predicted_effectiveness * 10)  # 估算问题数
                )
            
            self.logger.debug(f"记录了{len(selected_tools)}个工具的选择决策")
            
        except Exception as e:
            self.logger.error(f"记录选择决策失败: {e}")
    
    def _create_fallback_selection(self, available_tools: List[Tool], 
                                 project_info: ProjectInfo) -> List[Tool]:
        """创建智能降级选择"""
        try:
            # 智能降级：选择最可靠的基础工具
            fallback_tools = []
            
            # 按语言选择核心工具
            primary_language = project_info.get_primary_language()
            
            if primary_language == 'python':
                preferred_names = ['pylint', 'bandit', 'safety']
            elif primary_language == 'javascript':
                preferred_names = ['eslint', 'npm-audit']
            elif primary_language == 'java':
                preferred_names = ['checkstyle', 'spotbugs']
            elif primary_language == 'go':
                preferred_names = ['gofmt', 'gosec']
            else:
                preferred_names = ['semgrep', 'gitleaks']  # 通用工具
            
            # 选择可用的首选工具
            for name in preferred_names:
                for tool in available_tools:
                    if tool.name == name:
                        fallback_tools.append(tool)
                        break
                if len(fallback_tools) >= 3:  # 最多3个降级工具
                    break
            
            # 如果还不够，补充优先级最高的工具
            if len(fallback_tools) < 3:
                remaining_tools = [t for t in available_tools if t not in fallback_tools]
                remaining_tools.sort(key=lambda t: t.priority)
                fallback_tools.extend(remaining_tools[:3-len(fallback_tools)])
            
            self.logger.warning(f"使用降级工具选择: {[t.name for t in fallback_tools]}")
            return fallback_tools
            
        except Exception as e:
            self.logger.error(f"降级选择失败: {e}")
            return available_tools[:3]  # 最后的降级策略
    
    def _analyze_tool_dependencies(self, tools: List[Tool]) -> Dict[str, List[str]]:
        """
        分析工具依赖关系
        
        Returns:
            Dict[tool_name, List[dependent_tool_names]]
        """
        try:
            dependencies = {}
            
            for tool in tools:
                tool_deps = []
                
                # 基于工具类型分析依赖
                if tool.name in ['coverage', 'pytest-cov']:
                    # 覆盖率工具依赖测试工具
                    test_tools = [t.name for t in tools if 'test' in t.categories and t.name != tool.name]
                    tool_deps.extend(test_tools)
                
                elif tool.name in ['sonarqube-scanner']:
                    # SonarQube依赖其他质量工具的结果
                    quality_tools = [t.name for t in tools if 'quality' in t.categories and t.name != tool.name]
                    tool_deps.extend(quality_tools[:2])  # 最多依赖2个
                
                elif 'integration' in tool.categories:
                    # 集成测试可能依赖单元测试
                    unit_test_tools = [t.name for t in tools if 'unit_test' in t.categories]
                    tool_deps.extend(unit_test_tools)
                
                dependencies[tool.name] = tool_deps
            
            return dependencies
            
        except Exception as e:
            self.logger.error(f"工具依赖分析失败: {e}")
            return {tool.name: [] for tool in tools}
    
    def _predict_resource_needs(self, tools: List[Tool], project_info: ProjectInfo) -> Dict[str, Dict[str, float]]:
        """
        预测资源需求
        
        Returns:
            Dict[tool_name, Dict[resource_type, estimated_value]]
        """
        try:
            resource_predictions = {}
            project_size_factor = min(4.0, project_info.size_metrics.code_lines / 10000)
            
            for tool in tools:
                # CPU使用率预测（基于工具类型和项目规模）
                if tool.name in ['pylint', 'eslint', 'checkstyle']:
                    cpu_usage = min(80, 30 + project_size_factor * 10)
                elif tool.name in ['semgrep', 'sonarqube-scanner']:
                    cpu_usage = min(90, 50 + project_size_factor * 15)
                else:
                    cpu_usage = min(70, 20 + project_size_factor * 8)
                
                # 内存使用预测
                if tool.name in ['sonarqube-scanner', 'semgrep']:
                    memory_mb = min(2048, 512 + project_size_factor * 200)
                elif tool.name in ['pylint', 'eslint']:
                    memory_mb = min(1024, 256 + project_size_factor * 100)
                else:
                    memory_mb = min(512, 128 + project_size_factor * 50)
                
                # 磁盘IO预测
                disk_io = project_size_factor * 0.1  # 相对值
                
                resource_predictions[tool.name] = {
                    'cpu_percent': cpu_usage,
                    'memory_mb': memory_mb,
                    'disk_io_relative': disk_io,
                    'network_required': 1 if tool.name in ['npm-audit', 'safety'] else 0
                }
            
            return resource_predictions
            
        except Exception as e:
            self.logger.error(f"资源需求预测失败: {e}")
            return {}
    
    def _create_timeout_strategy(self, resource_requirements: Dict[str, Dict[str, float]]) -> Dict[str, int]:
        """
        创建超时策略
        
        Returns:
            Dict[tool_name, timeout_seconds]
        """
        try:
            timeout_strategy = {}
            
            for tool_name, resources in resource_requirements.items():
                # 基础超时时间
                base_timeout = 60  # 1分钟基础时间
                
                # 基于内存使用调整
                memory_factor = resources.get('memory_mb', 256) / 256
                memory_timeout = int(base_timeout * memory_factor)
                
                # 基于CPU使用调整
                cpu_factor = resources.get('cpu_percent', 50) / 50
                cpu_timeout = int(base_timeout * cpu_factor)
                
                # 网络工具额外时间
                network_bonus = 30 if resources.get('network_required', 0) else 0
                
                final_timeout = max(60, min(600, memory_timeout + cpu_timeout + network_bonus))
                timeout_strategy[tool_name] = final_timeout
            
            return timeout_strategy
            
        except Exception as e:
            self.logger.error(f"超时策略创建失败: {e}")
            return {}
    
    def _create_fallback_plan(self, tools: List[Tool]) -> Dict[str, List[str]]:
        """
        创建降级计划
        
        Returns:
            Dict[tool_name, List[fallback_tool_names]]
        """
        try:
            fallback_plan = {}
            
            for tool in tools:
                fallbacks = []
                
                # 基于工具功能寻找替代品
                if tool.name == 'pylint':
                    fallbacks = ['flake8', 'pycodestyle']
                elif tool.name == 'eslint':
                    fallbacks = ['jshint', 'prettier']
                elif tool.name == 'bandit':
                    fallbacks = ['semgrep', 'gitleaks']
                elif tool.name == 'safety':
                    fallbacks = ['pip-audit', 'semgrep']
                elif tool.name == 'npm-audit':
                    fallbacks = ['yarn-audit', 'semgrep']
                elif tool.name in ['sonarqube-scanner']:
                    # 复杂工具的降级策略：分解为多个简单工具
                    fallbacks = ['pylint', 'bandit', 'safety']
                
                # 过滤出实际可用的降级工具
                available_fallbacks = []
                for fallback_name in fallbacks:
                    for available_tool in tools:
                        if available_tool.name == fallback_name and available_tool != tool:
                            available_fallbacks.append(fallback_name)
                            break
                
                fallback_plan[tool.name] = available_fallbacks
            
            return fallback_plan
            
        except Exception as e:
            self.logger.error(f"降级计划创建失败: {e}")
            return {}
    
    def update_tool_execution_results(self, tool_name: str, project_info: ProjectInfo,
                                    actual_time: float, success: bool, 
                                    quality_score: float, issues_found: int):
        """
        更新工具执行结果用于学习优化
        """
        try:
            # 更新知识库
            self.knowledge_base.record_tool_execution(
                tool_name=tool_name,
                project_info=project_info,
                execution_time=actual_time,
                success=success,
                quality_score=quality_score,
                issues_found=issues_found
            )
            
            # 为ML模型添加训练样本
            risk_score = sum(10 for _ in self.assess_project_risks(project_info, 
                           self.analyze_project_complexity(project_info)).risk_factors)
            
            features = self.learning_model.extract_features(project_info, risk_score)
            self.learning_model.add_training_example(
                features=features,
                tool_name=tool_name,
                actual_effectiveness=quality_score / 100.0,  # 转换为0-1范围
                actual_execution_time=actual_time,
                success=success
            )
            
            self.logger.debug(f"更新工具执行结果: {tool_name}, 成功={success}, 质量分数={quality_score}")
            
        except Exception as e:
            self.logger.error(f"更新执行结果失败: {e}")
    
    def get_decision_stats(self) -> Dict[str, Any]:
        """获取决策统计信息"""
        try:
            return {
                'knowledge_base_stats': self.knowledge_base.get_tool_statistics(),
                'ml_model_stats': self.learning_model.get_model_stats(),
                'strategy_engine_version': '1.0'
            }
        except Exception as e:
            self.logger.error(f"获取决策统计失败: {e}")
            return {}


def create_decision_agent(knowledge_base_path: Optional[str] = None) -> DecisionAgent:
    """创建决策代理实例"""
    return DecisionAgent(knowledge_base_path)