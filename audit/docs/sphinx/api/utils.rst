工具和实用程序 (oss_audit.utils)
=================================

工具模块提供了OSS Audit 2.0的辅助功能，包括AI分析、配置管理、日志记录等实用程序。

AI分析器 (AIAnalyzer)
---------------------

.. automodule:: oss_audit.utils.ai_analyzer
   :members:
   :undoc-members:
   :show-inheritance:

使用示例
--------

AI分析集成
~~~~~~~~~~

.. code-block:: python

   from oss_audit.utils.ai_analyzer import AIAnalyzer
   
   # 初始化AI分析器
   analyzer = AIAnalyzer()
   
   # 配置AI提供商
   config = {
       "provider": "openai",
       "model": "gpt-3.5-turbo",
       "api_key": "your-api-key"
   }
   
   # 分析项目问题
   issues = [
       {"severity": "high", "message": "SQL injection vulnerability"},
       {"severity": "medium", "message": "Missing input validation"}
   ]
   
   analysis_result = analyzer.analyze_issues(
       issues=issues,
       project_info=project_info,
       config=config
   )
   
   print(f"AI建议: {analysis_result.recommendations}")
   print(f"优先级排序: {analysis_result.prioritized_issues}")

智能模型选择
~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.utils.ai_analyzer import ModelSelector
   
   # 创建模型选择器
   selector = ModelSelector()
   
   # 获取可用模型
   available_models = selector.get_available_models()
   
   # 选择最佳模型（基于任务类型和性能）
   best_model = selector.select_optimal_model(
       task_type="code_analysis",
       requirements={
           "max_tokens": 4000,
           "response_time": "fast",
           "cost_preference": "balanced"
       }
   )
   
   print(f"推荐模型: {best_model.name}")
   print(f"预期成本: {best_model.estimated_cost}")

配置管理
~~~~~~~~

.. code-block:: python

   from oss_audit.utils.config_manager import ConfigManager
   
   # 加载配置
   config_manager = ConfigManager()
   
   # 读取项目配置
   project_config = config_manager.load_project_config("./oss-audit.yaml")
   
   # 获取工具配置
   tool_config = config_manager.get_tool_config("pylint")
   print(f"Pylint超时: {tool_config.get('timeout', 300)}秒")
   
   # 动态更新配置
   config_manager.update_config({
       "tools": {
           "pylint": {"timeout": 600},
           "bandit": {"confidence_level": "high"}
       }
   })

日志和监控
~~~~~~~~~~

.. code-block:: python

   from oss_audit.utils.logger import setup_logger
   from oss_audit.utils.metrics import MetricsCollector
   
   # 设置日志
   logger = setup_logger(
       name="oss_audit",
       level="INFO",
       format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
   )
   
   # 收集指标
   metrics = MetricsCollector()
   
   # 记录工具执行指标
   with metrics.timer("tool_execution"):
       # 执行工具
       tool_result = execute_tool("pylint", project_path)
       
       # 记录结果指标
       metrics.record_gauge("tool_score", tool_result.score)
       metrics.record_counter("issues_found", len(tool_result.issues))
   
   # 生成指标报告
   report = metrics.generate_report()
   logger.info(f"执行统计: {report}")

缓存和性能优化
~~~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.utils.cache import ResultCache
   from oss_audit.utils.performance import PerformanceProfiler
   
   # 设置结果缓存
   cache = ResultCache(
       backend="file",  # 或 "redis", "memory"
       ttl=3600  # 1小时缓存
   )
   
   # 缓存工具结果
   cache_key = f"pylint_{project_hash}"
   
   if cache.exists(cache_key):
       result = cache.get(cache_key)
       print("使用缓存结果")
   else:
       result = run_pylint(project_path)
       cache.set(cache_key, result)
       print("缓存新结果")
   
   # 性能分析
   profiler = PerformanceProfiler()
   
   with profiler.profile("full_audit"):
       audit_result = run_full_audit(project_path)
   
   # 生成性能报告
   perf_report = profiler.get_report()
   print(f"总执行时间: {perf_report.total_time}秒")
   print(f"内存峰值: {perf_report.peak_memory}MB")

文件处理和验证
~~~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.utils.file_processor import FileProcessor
   from oss_audit.utils.validator import ResultValidator
   
   # 文件处理
   processor = FileProcessor()
   
   # 扫描项目文件
   files = processor.scan_project(
       project_path="/path/to/project",
       extensions=[".py", ".js", ".ts"],
       exclude_patterns=["*/node_modules/*", "*/__pycache__/*"]
   )
   
   print(f"找到 {len(files)} 个文件")
   
   # 计算项目指标
   metrics = processor.calculate_metrics(files)
   print(f"代码行数: {metrics.code_lines}")
   print(f"注释行数: {metrics.comment_lines}")
   
   # 结果验证
   validator = ResultValidator()
   
   # 验证工具输出
   validation_result = validator.validate_tool_output(
       tool_name="pylint",
       output_data=tool_result,
       expected_format="json"
   )
   
   if validation_result.is_valid:
       print("工具输出格式正确")
   else:
       print(f"验证错误: {validation_result.errors}")

数据结构和类型
--------------

AIAnalysisResult
~~~~~~~~~~~~~~~~

.. code-block:: python

   @dataclass
   class AIAnalysisResult:
       recommendations: List[str]           # AI推荐建议
       prioritized_issues: List[Issue]      # 优先级排序的问题
       confidence_score: float              # 分析置信度
       reasoning: str                       # 分析推理过程
       estimated_improvement: Dict[str, float]  # 预期改进

ModelInfo
~~~~~~~~~

.. code-block:: python

   @dataclass
   class ModelInfo:
       name: str                    # 模型名称
       provider: str                # 提供商
       max_tokens: int             # 最大token数
       cost_per_1k_tokens: float   # 每1k tokens成本
       speed_rating: str           # 速度评级
       quality_rating: str         # 质量评级

CacheConfig
~~~~~~~~~~~

.. code-block:: python

   @dataclass
   class CacheConfig:
       backend: str                # 缓存后端
       ttl: int                   # 生存时间
       max_size: Optional[int]    # 最大缓存大小
       compression: bool          # 是否压缩
       encryption: bool           # 是否加密

PerformanceMetrics
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   @dataclass
   class PerformanceMetrics:
       total_time: float          # 总执行时间
       cpu_time: float           # CPU时间
       peak_memory: float        # 内存峰值
       disk_io: Dict[str, int]   # 磁盘IO统计
       network_io: Dict[str, int] # 网络IO统计

高级用法
--------

自定义AI提供商
~~~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.utils.ai_analyzer import BaseAIProvider
   
   class CustomAIProvider(BaseAIProvider):
       """自定义AI提供商实现"""
       
       def __init__(self, api_endpoint: str, api_key: str):
           self.api_endpoint = api_endpoint
           self.api_key = api_key
       
       async def analyze_code(self, code: str, context: Dict) -> str:
           """分析代码并返回建议"""
           headers = {"Authorization": f"Bearer {self.api_key}"}
           
           payload = {
               "code": code,
               "context": context,
               "task": "code_review"
           }
           
           async with aiohttp.ClientSession() as session:
               async with session.post(
                   f"{self.api_endpoint}/analyze",
                   json=payload,
                   headers=headers
               ) as response:
                   result = await response.json()
                   return result["analysis"]
   
   # 注册自定义提供商
   ai_analyzer = AIAnalyzer()
   ai_analyzer.register_provider("custom", CustomAIProvider)

结果后处理器
~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.utils.post_processor import ResultPostProcessor
   
   class SecurityFocusedProcessor(ResultPostProcessor):
       """安全专注的结果后处理器"""
       
       def process(self, results: Dict[str, Any]) -> Dict[str, Any]:
           processed_results = results.copy()
           
           # 提升安全问题优先级
           for tool_name, tool_result in processed_results.items():
               if "security" in tool_name.lower():
                   tool_result["priority_boost"] = 1.5
               
               # 重新计算安全得分权重
               if "issues_found" in tool_result:
                   security_issues = [
                       issue for issue in tool_result["issues_found"]
                       if issue.get("category") == "security"
                   ]
                   
                   if security_issues:
                       # 安全问题加权
                       tool_result["security_weighted_score"] = (
                           tool_result.get("score", 0) * 0.7 + 
                           (100 - len(security_issues) * 10) * 0.3
                       )
           
           return processed_results
   
   # 使用后处理器
   processor = SecurityFocusedProcessor()
   enhanced_results = processor.process(audit_results)