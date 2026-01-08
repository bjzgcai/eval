# OSS Audit 2.0 - 最终设计方案

## 方案综述

基于对现有1.0版本的分析，OSS Audit 2.0采用**精简Agent + 传统组件的混合架构**，解决四个核心限制：

1. ✅ **解决固定tools扫描** → DecisionAgent智能工具选择
2. ✅ **解决Python项目局限** → 插件化多语言支持
3. ✅ **解决单仓库限制** → 智能项目结构检测
4. ✅ **解决缺乏自适应能力** → AdaptiveAgent动态评估

## 核心设计原则

- **智能决策**: 3个精简Agent负责智能决策
- **简洁执行**: 传统组件负责具体执行
- **渐进演进**: 基于现有代码逐步改进，保持向后兼容
- **配置驱动**: 通过YAML配置实现灵活性
- **开源生态**: 100%基于开源/免费工具

## 混合架构设计

```
OSS Audit 2.0 - 精简Agent混合架构
├── Core Components (传统组件 - 负责执行)
│   ├── ProjectDetector     # 项目检测器 - 数据收集
│   ├── ToolExecutor       # 工具执行器 - 工具运行
│   └── ReportGenerator    # 报告生成器 - 报告生成
│
├── Intelligent Agents (智能Agent - 负责决策)
│   ├── DecisionAgent      # 决策Agent - 工具选择与策略
│   ├── AdaptiveAgent      # 自适应Agent - 评分与优化
│   └── RecommendationAgent # 推荐Agent - 智能建议
│
├── Plugin System (插件系统)
│   ├── PythonPlugin       # Python语言插件
│   ├── JavaScriptPlugin   # JS/TS插件 
│   ├── JavaPlugin         # Java插件
│   └── ...                # 其他语言插件
│
└── Configuration (配置系统)
    ├── tools_registry.yaml # 工具注册表
    ├── language_configs/   # 语言配置
    └── .oss-audit.yaml    # 项目配置
```

## 核心组件详细设计

### 传统组件 (负责执行)

#### 1. ProjectDetector (项目检测器)

**解决问题**: 单仓库限制 + 缺乏自适应能力

```python
@dataclass
class ProjectInfo:
    """项目信息数据模型"""
    path: str
    languages: Dict[str, float]        # 语言名称 -> 占比
    structure_type: StructureType      # 单项目/多项目/monorepo  
    project_type: ProjectType          # web/library/cli/data等
    dependencies: Dict[str, List[str]]  # 语言 -> 依赖列表
    size_metrics: SizeMetrics          # 代码规模指标
    build_tools: List[str]             # 检测到的构建工具

class ProjectDetector:
    """一站式项目信息检测"""
    
    def detect_project_info(self, path: str) -> ProjectInfo:
        """检测项目完整信息"""
        return ProjectInfo(
            path=path,
            languages=self._detect_languages(path),
            structure_type=self._detect_structure_type(path),
            project_type=self._infer_project_type(path),
            dependencies=self._analyze_dependencies(path),
            size_metrics=self._calculate_size_metrics(path),
            build_tools=self._detect_build_tools(path)
        )
```

#### 语言检测配置
```yaml
# language_detection.yaml
languages:
  python:
    file_extensions: [".py", ".pyx", ".pyi"]
    key_files: ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile"]
    weight_multiplier: 1.0
    
  javascript:
    file_extensions: [".js", ".jsx", ".mjs"]
    key_files: ["package.json", "yarn.lock"]
    weight_multiplier: 1.0
    
  typescript:
    file_extensions: [".ts", ".tsx"]
    key_files: ["tsconfig.json"]
    weight_multiplier: 1.2  # TS权重稍高于JS
    
  java:
    file_extensions: [".java"]
    key_files: ["pom.xml", "build.gradle", "build.xml"]
    weight_multiplier: 1.0
    
  go:
    file_extensions: [".go"]
    key_files: ["go.mod", "go.sum"]
    weight_multiplier: 1.0
    
  rust:
    file_extensions: [".rs"]
    key_files: ["Cargo.toml", "Cargo.lock"]
    weight_multiplier: 1.0
```

#### 项目结构类型检测
```python
class StructureType(Enum):
    SINGLE_PROJECT = "single_project"    # 单一项目
    MULTI_PROJECT = "multi_project"      # 多项目仓库
    MONOREPO = "monorepo"               # Monorepo结构

def _detect_structure_type(self, path: str) -> StructureType:
    """检测项目结构类型"""
    
    # Monorepo标志
    monorepo_indicators = [
        "lerna.json", "nx.json", "rush.json", "workspace.json",
        "packages/*/package.json", "apps/*/package.json",
        "projects/*/package.json"
    ]
    
    # 多项目标志  
    multi_project_indicators = [
        "*/setup.py", "*/pom.xml", "*/Cargo.toml", "*/go.mod"
    ]
    
    if self._has_indicators(path, monorepo_indicators):
        return StructureType.MONOREPO
    elif self._has_indicators(path, multi_project_indicators):
        return StructureType.MULTI_PROJECT
    else:
        return StructureType.SINGLE_PROJECT
```

#### 2. ToolExecutor (工具执行器)

**解决问题**: 执行效率和资源管理

```python
class ToolExecutor:
    """工具执行器 - 负责具体的工具执行和资源管理"""
    
    def __init__(self, tools_registry_path: str):
        self.registry = ToolRegistry.load(tools_registry_path)
        self.plugin_manager = PluginManager()
        self.execution_pool = ExecutionPool()
        
    def discover_available_tools(self, project_info: ProjectInfo) -> List[Tool]:
        """发现项目可用的工具"""
        available_tools = []
        
        for language, percentage in project_info.languages.items():
            if percentage < 0.05:  # 忽略占比低于5%的语言
                continue
                
            lang_tools = self.registry.get_language_tools(language)
            # 检查工具可用性
            for tool in lang_tools:
                if self._is_tool_available(tool):
                    available_tools.append(tool)
                    
        return available_tools
        
    def execute_tools(self, execution_plan: ExecutionPlan, project_path: str) -> Dict[str, Any]:
        """根据执行计划运行工具"""
        results = {}
        
        # 按阶段执行
        for phase in execution_plan.phases:
            if phase.parallel:
                # 并行执行
                phase_results = self._execute_parallel(phase.tools, project_path)
            else:
                # 串行执行
                phase_results = self._execute_sequential(phase.tools, project_path)
                
            results.update(phase_results)
            
            # 检查是否需要提前终止
            if self._should_early_terminate(results, execution_plan):
                break
                
        return results
        
    def _execute_parallel(self, tools: List[Tool], project_path: str) -> Dict[str, Any]:
        """并行执行工具"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        async def run_tool_async(tool: Tool) -> Tuple[str, Any]:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(
                    executor, self._run_single_tool, tool, project_path)
                return tool.name, result
                
        async def run_all():
            tasks = [run_tool_async(tool) for tool in tools]
            return await asyncio.gather(*tasks)
            
        results_list = asyncio.run(run_all())
        return dict(results_list)
        
    def _execute_sequential(self, tools: List[Tool], project_path: str) -> Dict[str, Any]:
        """串行执行工具"""
        results = {}
        
        for tool in tools:
            try:
                result = self._run_single_tool(tool, project_path)
                results[tool.name] = result
                
                # 如果工具执行失败且是关键工具，记录但继续
                if not result.get('success', False):
                    self._log_tool_failure(tool, result)
                    
            except Exception as e:
                results[tool.name] = {
                    'success': False,
                    'error': str(e),
                    'execution_time': 0
                }
                
        return results
        
    def _run_single_tool(self, tool: Tool, project_path: str) -> Dict[str, Any]:
        """执行单个工具"""
        start_time = time.time()
        
        try:
            # 通过插件系统执行工具
            plugin = self.plugin_manager.get_plugin_for_tool(tool)
            if plugin:
                result = plugin.execute_tool(tool, project_path)
            else:
                # 直接执行工具命令
                result = self._execute_tool_command(tool, project_path)
                
            execution_time = time.time() - start_time
            
            return {
                'success': True,
                'result': result,
                'execution_time': execution_time,
                'tool_info': tool.get_info()
            }
            
        except TimeoutError:
            return {
                'success': False,
                'error': f'Tool {tool.name} timed out after {tool.timeout}s',
                'execution_time': time.time() - start_time
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time
            }
```

#### 工具注册表配置
```yaml
# tools_registry.yaml
version: "2.0"

languages:
  python:
    quality_tools:
      - name: "pylint"
        command: ["python", "-m", "pylint"]
        args: ["--output-format=json", "--score=yes"]
        install: ["pip", "install", "pylint"]
        priority: 1
        estimated_time: 60
        categories: ["quality", "style"]
        
      - name: "flake8" 
        command: ["python", "-m", "flake8"]
        args: ["--format=json"]
        install: ["pip", "install", "flake8"]
        priority: 2
        estimated_time: 20
        categories: ["quality", "style"]
        
    security_tools:
      - name: "bandit"
        command: ["python", "-m", "bandit"]
        args: ["-r", ".", "-f", "json"]
        install: ["pip", "install", "bandit"]
        priority: 1
        estimated_time: 30
        categories: ["security"]
        
      - name: "safety"
        command: ["python", "-m", "safety"]
        args: ["check", "--json"]
        install: ["pip", "install", "safety"]
        priority: 2
        estimated_time: 20
        categories: ["security", "dependencies"]
        
  javascript:
    quality_tools:
      - name: "eslint"
        command: ["npx", "eslint"]
        args: [".", "--format=json"]
        install: ["npm", "install", "eslint"]
        priority: 1
        estimated_time: 30
        categories: ["quality", "style"]
        
    security_tools:
      - name: "npm-audit"
        command: ["npm", "audit"]
        args: ["--json"]
        install: []  # npm内置
        priority: 1
        estimated_time: 15
        categories: ["security", "dependencies"]
        
  java:
    quality_tools:
      - name: "checkstyle"
        command: ["java", "-jar", "/opt/checkstyle.jar"]
        args: ["-f", "xml"]
        install: ["download_checkstyle"]
        priority: 1
        estimated_time: 45
        categories: ["quality", "style"]
        
    security_tools:
      - name: "spotbugs"
        command: ["/opt/spotbugs/bin/spotbugs"]
        args: ["-textui", "-xml"]
        install: ["download_spotbugs"]
        priority: 1
        estimated_time: 60
        categories: ["security", "quality"]
```

### 智能Agent系统 (负责决策)

#### 1. DecisionAgent (决策Agent)

**解决问题**: 固定工具扫描 + 缺乏智能决策

```python
class DecisionAgent:
    """决策Agent - 负责智能工具选择和执行策略制定"""
    
    def __init__(self):
        self.knowledge_base = ToolKnowledgeBase()  # 工具知识库
        self.strategy_engine = StrategyEngine()    # 策略引擎
        self.learning_model = SimpleMLModel()      # 简单学习模型
        
    def make_tool_selection_decision(self, project_info: ProjectInfo, 
                                   available_tools: List[Tool]) -> ToolSelectionStrategy:
        """智能决策：选择什么工具，用什么策略"""
        
        # 1. 分析项目特征
        project_complexity = self._analyze_complexity(project_info)
        risk_factors = self._identify_risk_factors(project_info)
        
        # 2. 预测工具效果
        tool_effectiveness = self.knowledge_base.predict_effectiveness(
            available_tools, project_info)
        
        # 3. 考虑资源约束
        time_budget = self._estimate_time_budget(project_info)
        
        # 4. 制定选择策略
        strategy = self.strategy_engine.create_strategy(
            complexity=project_complexity,
            risks=risk_factors,
            effectiveness=tool_effectiveness, 
            time_budget=time_budget
        )
        
        return strategy
        
    def make_execution_decision(self, tools: List[Tool], 
                               project_info: ProjectInfo) -> ExecutionPlan:
        """智能决策：如何执行这些工具"""
        
        # 分析工具依赖关系
        dependencies = self._analyze_tool_dependencies(tools)
        
        # 预测资源需求
        resource_requirements = self._predict_resource_needs(tools, project_info)
        
        # 决定执行策略
        execution_plan = ExecutionPlan(
            phases=self._create_execution_phases(tools, dependencies),
            parallel_groups=self._group_parallel_tools(tools, dependencies),
            timeout_strategy=self._create_timeout_strategy(resource_requirements),
            fallback_plan=self._create_fallback_plan(tools)
        )
        
        return execution_plan
        
    def _analyze_complexity(self, project_info: ProjectInfo) -> ComplexityLevel:
        """分析项目复杂度"""
        if project_info.size_metrics.loc > 100000:
            return ComplexityLevel.HIGH
        elif project_info.size_metrics.loc > 10000:
            return ComplexityLevel.MEDIUM
        else:
            return ComplexityLevel.LOW
            
    def _identify_risk_factors(self, project_info: ProjectInfo) -> List[RiskFactor]:
        """识别风险因素"""
        risks = []
        
        if project_info.project_type == ProjectType.WEB_APPLICATION:
            risks.extend([RiskFactor.SECURITY, RiskFactor.PERFORMANCE])
            
        if "web" in project_info.dependencies.get("python", []):
            risks.append(RiskFactor.WEB_SECURITY)
            
        if project_info.has_database_access():
            risks.append(RiskFactor.SQL_INJECTION)
            
        return risks
```

#### 2. AdaptiveAgent (自适应Agent)

**解决问题**: 缺乏自适应audit能力

```python
class AdaptiveAgent:
    """自适应Agent - 负责动态评分优化和持续改进"""
    
    def __init__(self):
        self.scoring_models = {}  # 不同项目类型的评分模型
        self.benchmark_db = BenchmarkDatabase()
        self.adaptation_engine = AdaptationEngine()
        
    def adapt_scoring_model(self, project_info: ProjectInfo, 
                          tool_results: Dict[str, Any]) -> ScoringModel:
        """根据项目特征自适应评分模型"""
        
        # 1. 选择基础评分模型
        base_model = self._select_base_model(project_info.project_type)
        
        # 2. 根据项目特征调整权重
        adapted_weights = self._adapt_dimension_weights(
            base_model.weights, project_info)
        
        # 3. 考虑工具结果质量
        quality_adjustments = self._analyze_tool_result_quality(tool_results)
        
        # 4. 历史数据学习调整
        historical_adjustments = self._learn_from_similar_projects(project_info)
        
        return ScoringModel(
            weights=adapted_weights,
            quality_adjustments=quality_adjustments,
            historical_adjustments=historical_adjustments,
            confidence_level=self._calculate_confidence(project_info, tool_results)
        )
        
    def optimize_analysis_process(self, current_results: Dict[str, Any],
                                project_info: ProjectInfo) -> OptimizationActions:
        """基于当前结果优化分析过程"""
        
        actions = OptimizationActions()
        
        # 如果发现高风险问题，建议启用额外工具
        if self._detect_high_risk_issues(current_results):
            actions.additional_tools = self._recommend_additional_security_tools()
            
        # 如果工具结果冲突，建议仲裁工具
        conflicts = self._detect_tool_conflicts(current_results)
        if conflicts:
            actions.arbitration_tools = self._suggest_arbitration_tools(conflicts)
            
        # 如果结果不确定，建议补充分析
        uncertainty = self._measure_result_uncertainty(current_results)
        if uncertainty > 0.3:
            actions.supplementary_analysis = self._design_supplementary_analysis()
            
        return actions
        
    def _adapt_dimension_weights(self, base_weights: Dict[str, float], 
                               project_info: ProjectInfo) -> Dict[str, float]:
        """自适应调整维度权重"""
        adapted = base_weights.copy()
        
        # Web应用提高安全权重
        if project_info.project_type == ProjectType.WEB_APPLICATION:
            adapted["security"] *= 1.5
            adapted["performance"] *= 1.2
            
        # 库项目提高文档和API质量权重  
        elif project_info.project_type == ProjectType.LIBRARY:
            adapted["documentation"] *= 1.4
            adapted["api_design"] *= 1.3
            
        # 数据科学项目提高可复现性权重
        elif project_info.project_type == ProjectType.DATA_SCIENCE:
            adapted["reproducibility"] *= 1.6
            adapted["data_quality"] *= 1.4
            
        # 重新归一化权重
        total = sum(adapted.values())
        return {k: v/total for k, v in adapted.items()}
```

#### 3. RecommendationAgent (推荐Agent)

**解决问题**: 缺乏智能化建议和改进路线图

```python
class RecommendationAgent:
    """推荐Agent - 负责生成智能建议和改进路线图"""
    
    def __init__(self):
        self.recommendation_engine = RecommendationEngine()
        self.best_practices_db = BestPracticesDatabase()
        self.improvement_planner = ImprovementPlanner()
        
    def generate_intelligent_recommendations(self, 
                                           analysis_results: AnalysisResults,
                                           project_info: ProjectInfo,
                                           team_context: TeamContext) -> IntelligentRecommendations:
        """生成智能化建议"""
        
        # 1. 问题优先级智能排序
        prioritized_issues = self._prioritize_issues_intelligently(
            analysis_results.all_issues, project_info)
        
        # 2. 生成针对性建议
        targeted_recommendations = []
        for issue in prioritized_issues[:10]:  # 前10个最重要问题
            recommendation = self._generate_targeted_recommendation(
                issue, project_info, team_context)
            targeted_recommendations.append(recommendation)
            
        # 3. 制定改进路线图
        roadmap = self._create_intelligent_roadmap(
            targeted_recommendations, team_context)
        
        # 4. 预测改进效果
        impact_predictions = self._predict_improvement_impact(
            targeted_recommendations, project_info)
        
        return IntelligentRecommendations(
            recommendations=targeted_recommendations,
            roadmap=roadmap,
            impact_predictions=impact_predictions,
            success_metrics=self._define_success_metrics(targeted_recommendations)
        )
        
    def _prioritize_issues_intelligently(self, issues: List[Issue], 
                                       project_info: ProjectInfo) -> List[Issue]:
        """智能优先级排序"""
        
        def calculate_priority_score(issue: Issue) -> float:
            score = 0.0
            
            # 基础严重程度
            severity_weights = {"critical": 10, "high": 7, "medium": 4, "low": 1}
            score += severity_weights.get(issue.severity, 1)
            
            # 项目类型相关调整
            if project_info.project_type == ProjectType.WEB_APPLICATION:
                if issue.category == "security":
                    score *= 1.8  # Web应用安全问题优先级很高
                elif issue.category == "performance":
                    score *= 1.3
                    
            # 修复成本考虑
            fix_cost = self._estimate_fix_cost(issue)
            if fix_cost == "low":
                score *= 1.2  # 低成本修复优先级提高
            elif fix_cost == "high":
                score *= 0.8  # 高成本修复优先级降低
                
            return score
            
        return sorted(issues, key=calculate_priority_score, reverse=True)
        
    def _create_intelligent_roadmap(self, recommendations: List[Recommendation],
                                  team_context: TeamContext) -> ImprovementRoadmap:
        """创建智能改进路线图"""
        
        phases = []
        
        # Phase 1: 快速胜利 (1-2周)
        quick_wins = [r for r in recommendations 
                     if r.estimated_effort <= 2 and r.impact_level >= 0.7]
        if quick_wins:
            phases.append(RoadmapPhase(
                name="Quick Wins",
                duration_weeks=2,
                recommendations=quick_wins,
                rationale="快速提升项目质量，建立改进信心"
            ))
            
        # Phase 2: 高影响改进 (3-6周)  
        high_impact = [r for r in recommendations
                      if r.impact_level >= 0.8 and r not in quick_wins]
        if high_impact:
            phases.append(RoadmapPhase(
                name="High Impact Improvements", 
                duration_weeks=4,
                recommendations=high_impact,
                rationale="解决最重要的质量问题"
            ))
            
        # Phase 3: 系统性改进 (7-12周)
        systematic = [r for r in recommendations
                     if r not in quick_wins and r not in high_impact]
        if systematic:
            phases.append(RoadmapPhase(
                name="Systematic Improvements",
                duration_weeks=6, 
                recommendations=systematic,
                rationale="建立长期质量保障机制"
            ))
            
        return ImprovementRoadmap(phases=phases)
```

### 传统组件与Agent协作

#### 主控制器设计

```python
class OSSAudit2:
    """主控制器 - 协调Agent和传统组件"""
    
    def __init__(self):
        # 传统组件 - 负责执行
        self.project_detector = ProjectDetector()
        self.tool_executor = ToolExecutor() 
        self.report_generator = ReportGenerator()
        
        # 智能Agent - 负责决策
        self.decision_agent = DecisionAgent()
        self.adaptive_agent = AdaptiveAgent()
        self.recommendation_agent = RecommendationAgent()
        
    def audit_project(self, project_path: str) -> AuditResult:
        """主审计流程 - Agent与组件协作"""
        
        # 1. 传统组件：收集项目信息
        project_info = self.project_detector.detect_project_info(project_path)
        available_tools = self.tool_executor.discover_available_tools(project_info)
        
        # 2. Agent决策：选择工具和策略
        tool_strategy = self.decision_agent.make_tool_selection_decision(
            project_info, available_tools)
        execution_plan = self.decision_agent.make_execution_decision(
            tool_strategy.selected_tools, project_info)
        
        # 3. 传统组件：执行分析
        raw_results = self.tool_executor.execute_tools(execution_plan, project_path)
        
        # 4. Agent优化：自适应评分
        scoring_model = self.adaptive_agent.adapt_scoring_model(project_info, raw_results)
        optimization_actions = self.adaptive_agent.optimize_analysis_process(
            raw_results, project_info)
        
        # 5. 执行优化建议（如果有）
        if optimization_actions.additional_tools:
            additional_results = self.tool_executor.execute_tools(
                optimization_actions.additional_tools, project_path)
            raw_results.update(additional_results)
            
        # 6. Agent推荐：生成智能建议
        recommendations = self.recommendation_agent.generate_intelligent_recommendations(
            raw_results, project_info, team_context=None)
        
        # 7. 传统组件：生成报告
        report = self.report_generator.generate_adaptive_report(
            raw_results, scoring_model, recommendations)
        
        return AuditResult(
            project_info=project_info,
            analysis_results=raw_results,
            scoring_model=scoring_model,
            recommendations=recommendations,
            report=report
        )
```

### Plugin System (插件系统)

**解决问题**: Python项目局限

```python
class LanguagePlugin(ABC):
    """语言插件基类"""
    
    @property
    @abstractmethod
    def supported_languages(self) -> List[str]:
        """支持的语言列表"""
        
    @abstractmethod
    def execute_tools(self, tools: List[Tool], project_path: str) -> Dict[str, Any]:
        """执行该语言的工具分析"""
        
    @abstractmethod  
    def parse_results(self, raw_results: Dict[str, Any]) -> StandardizedResults:
        """将工具原始结果标准化"""

class PythonPlugin(LanguagePlugin):
    """Python语言插件"""
    
    @property
    def supported_languages(self) -> List[str]:
        return ["python"]
        
    def execute_tools(self, tools: List[Tool], project_path: str) -> Dict[str, Any]:
        """执行Python工具"""
        results = {}
        
        # 分类执行：快速工具并行，慢速工具串行
        fast_tools = [t for t in tools if t.estimated_time < 30]
        slow_tools = [t for t in tools if t.estimated_time >= 30]
        
        # 并行执行快速工具
        if fast_tools:
            fast_results = asyncio.run(self._execute_parallel(fast_tools, project_path))
            results.update(fast_results)
        
        # 串行执行慢速工具
        for tool in slow_tools:
            try:
                result = tool.execute(project_path)
                results[tool.name] = result
            except Exception as e:
                results[tool.name] = {"error": str(e), "success": False}
                
        return results
        
    def parse_results(self, raw_results: Dict[str, Any]) -> StandardizedResults:
        """标准化Python工具结果"""
        standardized = StandardizedResults()
        
        for tool_name, result in raw_results.items():
            if tool_name == "pylint":
                standardized.add_issues(self._parse_pylint_results(result))
            elif tool_name == "bandit":
                standardized.add_issues(self._parse_bandit_results(result))
            elif tool_name == "safety":
                standardized.add_vulnerabilities(self._parse_safety_results(result))
                
        return standardized

class JavaScriptPlugin(LanguagePlugin):
    """JavaScript/TypeScript插件"""
    
    @property  
    def supported_languages(self) -> List[str]:
        return ["javascript", "typescript"]
        
    def execute_tools(self, tools: List[Tool], project_path: str) -> Dict[str, Any]:
        """执行JavaScript工具"""
        results = {}
        
        # 检查node_modules是否存在，不存在则跳过某些工具
        node_modules_exists = os.path.exists(os.path.join(project_path, "node_modules"))
        
        for tool in tools:
            if not node_modules_exists and tool.requires_dependencies:
                results[tool.name] = {
                    "error": "node_modules not found, run 'npm install' first",
                    "success": False
                }
                continue
                
            try:
                result = tool.execute(project_path)
                results[tool.name] = result
            except Exception as e:
                results[tool.name] = {"error": str(e), "success": False}
                
        return results
```

### 4. Configuration System (配置系统)

**解决问题**: 固定工具扫描 + 缺乏自适应能力

#### 项目配置文件
```yaml
# .oss-audit.yaml (项目根目录可选)
project:
  name: "MyProject"
  type: "web_application"  # 影响维度权重和工具选择
  
# 工具配置覆盖
tools:
  disabled: ["pylint", "tslint"]     # 全局禁用
  enabled: ["mypy", "prettier"]      # 额外启用
  
  configs:
    bandit:
      args: ["-r", ".", "-f", "json", "-ll"]
      exclude: ["tests/", "migrations/"]
    eslint:
      config_file: ".eslintrc.custom.js"

# 维度权重自定义  
dimensions:
  security:
    weight: 0.4      # Web应用提高安全权重
    enabled: true
  performance:
    enabled: false   # 禁用性能检查

# 排除配置
exclude:
  paths: ["node_modules/", "vendor/", "build/", "__pycache__/"]
  files: ["*.min.js", "*_pb2.py", "migrations/*.py"]

# 报告配置
reports:
  formats: ["html", "json"]
  output_dir: "audit_reports/"
  
# CI集成
ci:
  fail_on_score: 60         # 低于60分CI失败
  fail_on_security: true    # 发现安全问题CI失败
```

#### 项目类型配置模板
```yaml
# project_profiles/web_application.yaml
name: "Web Application"
description: "Web应用项目配置"

dimensions:
  security: 0.3        # Web应用安全最重要
  quality: 0.25
  performance: 0.2     # 性能也重要
  testing: 0.15
  documentation: 0.1

recommended_tools:
  python: ["bandit", "safety", "pylint"]
  javascript: ["eslint", "npm-audit"]
  
special_checks:
  - "sql_injection_check"
  - "xss_vulnerability_check" 
  - "https_usage_check"
```

## 多语言开源工具支持

### 完全开源工具生态
```yaml
supported_languages:
  python:
    tools: [pylint, flake8, bandit, safety, mypy, black, pytest, coverage]
    
  javascript:
    tools: [eslint, prettier, npm-audit, jest, typescript]
    
  java: 
    tools: [checkstyle, spotbugs, pmd, jacoco, junit]
    
  go:
    tools: [golint, go-vet, gosec, go-test]
    
  rust:
    tools: [clippy, rustfmt, cargo-audit, cargo-test]
    
  cpp:
    tools: [cppcheck, clang-tidy, clang-format, googletest]
    
universal_tools:
  security: [semgrep, gitleaks, trivy]
  dependencies: [syft, ort, licensee]
  quality: [sonarqube-community]
```

## 渐进式实现计划

### Phase 1: 传统组件基础 (4-6周)

**Week 1-2: 配置系统重构**
- 创建工具注册表YAML配置
- 重构现有硬编码工具配置
- 实现配置加载和合并逻辑
- 添加项目配置文件支持

**Week 3-4: ProjectDetector实现**
- 实现智能多语言检测
- 添加项目结构类型识别
- 实现项目类型推断算法
- 支持Monorepo/多项目检测

**Week 5-6: ToolExecutor实现**
- 实现工具发现和可用性检测
- 添加工具并行/串行执行引擎
- 实现工具超时和错误处理
- 优化工具执行性能

### Phase 2: 插件系统 + 简单Agent (4-6周)

**Week 1-2: 插件框架**
- 设计和实现LanguagePlugin基类
- 创建插件注册和加载机制
- 重构Python分析为PythonPlugin
- 实现插件错误隔离

**Week 3-4: 多语言插件**
- 实现JavaScriptPlugin
- 实现JavaPlugin
- 添加GoPlugin(基础版)
- 统一插件结果格式

**Week 5-6: DecisionAgent基础版**
- 实现简单的工具选择决策逻辑
- 基于项目特征的工具过滤
- 实现基础执行计划生成
- 集成到主流程中

### Phase 3: 智能Agent系统 (6-8周)

**Week 1-2: DecisionAgent完整版**
- 实现复杂度分析和风险识别
- 添加工具效果预测模型
- 实现智能执行策略制定
- 集成工具知识库

**Week 3-4: AdaptiveAgent实现**
- 实现动态评分模型适配
- 添加项目类型权重调整
- 实现分析过程优化
- 支持历史数据学习

**Week 5-6: RecommendationAgent实现**
- 实现智能问题优先级排序
- 添加针对性建议生成
- 实现智能路线图规划
- 集成改进效果预测

**Week 7-8: 系统优化集成**
- Agent间协作优化
- 性能调优和缓存策略
- 完善错误处理和降级
- 全流程集成测试

## 部署方案

### 1. 单机部署
```bash
# PyPI安装
pip install oss-audit==2.0.0

# 直接使用
oss-audit /path/to/project
```

### 2. 容器化部署
```dockerfile
FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git curl wget nodejs npm openjdk-11-jre \
    && rm -rf /var/lib/apt/lists/*

# 安装开源工具
RUN pip install --no-cache-dir \
    pylint flake8 bandit safety mypy black pytest coverage \
    && npm install -g eslint prettier jest

# 安装应用
COPY . /app
WORKDIR /app
RUN pip install -e .

ENTRYPOINT ["oss-audit"]
```

## 质量保障

### 测试策略
- **单元测试**: 每个组件100%覆盖
- **集成测试**: 插件系统端到端测试
- **实际项目测试**: 在多个开源项目上验证

### CI/CD流水线
```yaml
name: OSS Audit 2.0 CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]
        test-project: [python-project, js-project, java-project, mixed-project]
        
    steps:
    - uses: actions/checkout@v3
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        
    - name: Install dependencies
      run: |
        pip install -r requirements-dev.txt
        pip install -e .
        
    - name: Run unit tests
      run: pytest tests/ --cov=oss_audit --cov-report=xml
      
    - name: Test on real projects
      run: oss-audit tests/fixtures/${{ matrix.test-project }}/
```

## 成功标准

### 功能目标
- ✅ 支持5+主流编程语言 (Python, JS, Java, Go, Rust)
- ✅ 智能识别单项目/多项目/Monorepo结构
- ✅ 100%开源工具，0商业依赖
- ✅ 配置驱动，支持项目个性化定制
- ✅ 执行时间不超过现有版本2倍

### 技术目标  
- 代码覆盖率 > 90%
- 插件系统支持热插拔
- 向后兼容现有API
- 支持Docker一键部署
- 文档完整，示例丰富

## 精简Agent架构优势总结

OSS Audit 2.0通过**精简Agent + 传统组件混合架构**成功解决了1.0版本的四个核心限制：

### 核心问题解决方案

1. **固定tools扫描** → **DecisionAgent** 智能工具选择和执行策略制定
2. **Python项目局限** → **Plugin System** 支持多语言生态扩展
3. **单仓库限制** → **ProjectDetector** 智能识别各种项目结构
4. **缺乏自适应能力** → **AdaptiveAgent** 动态评分优化和持续改进

### 混合架构优势

#### ✅ 获得Agent模式优点
- **智能决策**: DecisionAgent基于项目特征智能选择工具
- **自适应能力**: AdaptiveAgent动态调整评分权重和策略  
- **智能推荐**: RecommendationAgent生成个性化改进建议
- **学习能力**: 简单ML模型积累项目分析经验

#### ✅ 避免Agent模式缺点
- **复杂度可控**: 只有3个Agent + 3个传统组件
- **职责清晰**: Agent负责决策，组件负责执行
- **易于维护**: 没有复杂的消息传递和状态管理
- **渐进实施**: 可以先实现组件，后续加入Agent

#### ✅ 保持系统简洁性
- **架构简单**: 混合架构清晰易懂
- **代码简洁**: 传统OOP + 少量Agent逻辑
- **部署简单**: 单机部署，无需复杂协调
- **调试友好**: 直接方法调用，问题定位容易

### 技术创新点

1. **混合决策模式**: Agent做决策 + 组件做执行的分工模式
2. **渐进式智能化**: 可以逐步从传统组件演进到智能Agent
3. **配置驱动灵活性**: 通过YAML配置实现大部分定制需求
4. **开源工具生态**: 100%基于开源工具，无商业依赖

### 实施风险控制

- **向后兼容**: 保持现有API不变，用户无感知升级
- **分阶段实施**: 14周分3个阶段，每阶段都有可验证成果
- **降级策略**: Agent失效时可降级到传统逻辑
- **充分测试**: 多层次测试保障系统稳定性

### 成功预期

通过这个精简Agent混合架构，OSS Audit 2.0将实现：

- **功能显著增强**: 支持5+主流语言，智能项目结构识别
- **智能化水平提升**: 自适应评分，个性化建议，智能路线图
- **用户体验改善**: 更准确的分析，更实用的建议，更友好的报告
- **系统可维护性**: 架构清晰，代码简洁，易于扩展和维护

这个方案在解决现有问题的基础上，通过引入适量的智能化能力，为开源软件成熟度评估提供了更加智能、实用、可靠的解决方案。