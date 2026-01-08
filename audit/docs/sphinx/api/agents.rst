智能代理系统 (oss_audit.core.agents)
=====================================

智能代理系统是OSS Audit 2.0的核心创新，提供决策制定、自适应优化和智能推荐功能。

决策代理 (DecisionAgent)
------------------------

.. automodule:: oss_audit.core.decision_agent
   :members:
   :undoc-members:
   :show-inheritance:

自适应代理 (AdaptiveAgent)
--------------------------

.. automodule:: oss_audit.core.adaptive_agent
   :members:
   :undoc-members:
   :show-inheritance:

推荐代理 (RecommendationAgent)
------------------------------

.. automodule:: oss_audit.core.recommendation_agent
   :members:
   :undoc-members:
   :show-inheritance:

代理协作工作流
--------------

多代理协作示例
~~~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.core.decision_agent import DecisionAgent
   from oss_audit.core.adaptive_agent import AdaptiveAgent
   from oss_audit.core.recommendation_agent import RecommendationAgent
   
   # 初始化三个智能代理
   decision_agent = DecisionAgent()
   adaptive_agent = AdaptiveAgent()
   recommendation_agent = RecommendationAgent()
   
   # 步骤1: 决策代理分析项目复杂度
   complexity = decision_agent.analyze_project_complexity(project_info)
   print(f"项目复杂度: {complexity.complexity_level}")
   
   # 步骤2: 决策代理选择合适的工具
   selected_tools = decision_agent.make_tool_selection_decision(
       project_info=project_info,
       available_tools=available_tools
   )
   
   # 步骤3: 自适应代理创建优化的评分模型
   scoring_model = adaptive_agent.adapt_scoring_model(
       project_info=project_info,
       tool_results=tool_results
   )
   
   # 步骤4: 推荐代理生成智能建议
   recommendations = recommendation_agent.generate_intelligent_recommendations(
       analysis_results=analysis_results,
       project_info=project_info,
       scoring_model=scoring_model
   )

决策代理详细用法
~~~~~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.core.decision_agent import DecisionAgent, ComplexityLevel
   
   agent = DecisionAgent()
   
   # 项目复杂度分析
   complexity_analysis = agent.analyze_project_complexity(project_info)
   
   if complexity_analysis.complexity_level == ComplexityLevel.VERY_HIGH:
       print("检测到高复杂度项目，建议使用全面分析模式")
       print(f"识别的风险: {complexity_analysis.identified_risks}")
   
   # 风险评估
   risk_assessment = agent.assess_project_risks(
       project_info=project_info,
       available_tools=available_tools
   )
   
   print(f"风险等级: {risk_assessment.risk_level}")
   print(f"建议措施: {risk_assessment.mitigation_strategies}")
   
   # 创建执行计划
   execution_plan = agent.create_execution_plan(
       selected_tools=selected_tools,
       project_info=project_info,
       complexity=complexity_analysis
   )

自适应代理高级配置
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.core.adaptive_agent import AdaptiveAgent, AdaptationLevel
   
   # 创建自适应代理，使用激进优化策略
   agent = AdaptiveAgent(adaptation_level=AdaptationLevel.AGGRESSIVE)
   
   # 创建基础评分模型
   base_scoring_model = agent.adapt_scoring_model(
       project_info=project_info,
       tool_results=tool_results
   )
   
   # 分析质量差距
   quality_gaps = agent.analyze_quality_gaps(
       tool_results=tool_results,
       project_info=project_info,
       scoring_model=base_scoring_model
   )
   
   # 生成优化行动
   optimization_actions = agent.generate_optimization_actions(
       quality_gaps=quality_gaps,
       project_info=project_info,
       current_tools=current_tools
   )
   
   # 应用优化并创建更新的模型
   updated_model = agent.apply_optimizations(
       base_model=base_scoring_model,
       actions=optimization_actions,
       project_info=project_info
   )

推荐代理个性化建议
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.core.recommendation_agent import RecommendationAgent, AnalysisResults
   
   agent = RecommendationAgent()
   
   # 准备分析结果
   analysis_results = AnalysisResults(
       all_issues=extracted_issues,
       tool_results=tool_results,
       overall_score=85.2,
       dimension_scores={"security": 90, "quality": 80, "testing": 75}
   )
   
   # 生成智能推荐
   intelligent_recs = agent.generate_intelligent_recommendations(
       analysis_results=analysis_results,
       project_info=project_info,
       scoring_model=scoring_model
   )
   
   # 查看推荐结果
   print(f"推荐置信度: {intelligent_recs.confidence_level}")
   print(f"预期改进: {intelligent_recs.impact_predictions}")
   
   # 查看改进路线图
   roadmap = intelligent_recs.roadmap
   print(f"总预计周数: {roadmap.total_estimated_weeks}")
   
   for phase in roadmap.phases:
       print(f"阶段: {phase.name} ({phase.duration_weeks}周)")
       for rec in phase.recommendations:
           print(f"  - {rec.title}: {rec.estimated_effort}")

数据结构
--------

ComplexityAnalysis
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   @dataclass
   class ComplexityAnalysis:
       complexity_level: ComplexityLevel      # 复杂度等级
       identified_risks: List[RiskFactor]     # 识别的风险因素
       confidence: float                      # 分析置信度
       reasoning: str                         # 分析推理

ScoringModel
~~~~~~~~~~~~

.. code-block:: python

   @dataclass
   class ScoringModel:
       weights: Dict[str, float]               # 维度权重
       quality_adjustments: Dict[str, float]   # 质量调整
       historical_adjustments: Dict[str, float] # 历史调整
       confidence_level: float                 # 置信度

IntelligentRecommendations
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   @dataclass
   class IntelligentRecommendations:
       recommendations: List[Recommendation]    # 推荐列表
       roadmap: ImprovementRoadmap             # 改进路线图
       impact_predictions: Dict[str, Any]      # 影响预测
       confidence_level: float                 # 置信度

枚举类型
--------

ComplexityLevel
~~~~~~~~~~~~~~~

.. code-block:: python

   class ComplexityLevel(Enum):
       LOW = "low"                    # 低复杂度
       MODERATE = "moderate"          # 中等复杂度
       HIGH = "high"                 # 高复杂度
       VERY_HIGH = "very_high"       # 极高复杂度

AdaptationLevel
~~~~~~~~~~~~~~~

.. code-block:: python

   class AdaptationLevel(Enum):
       MINIMAL = "minimal"           # 最小适应
       MODERATE = "moderate"         # 适度适应
       AGGRESSIVE = "aggressive"     # 激进适应

RiskFactor
~~~~~~~~~~

.. code-block:: python

   class RiskFactor(Enum):
       LARGE_CODEBASE = "large_codebase"              # 大型代码库
       MULTIPLE_LANGUAGES = "multiple_languages"      # 多语言项目
       COMPLEX_DEPENDENCIES = "complex_dependencies"  # 复杂依赖
       LEGACY_CODE = "legacy_code"                    # 遗留代码
       SECURITY_SENSITIVE = "security_sensitive"      # 安全敏感