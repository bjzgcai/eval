核心模块 (oss_audit.core)
==========================

核心模块包含OSS Audit 2.0的主要功能组件，负责项目检测、工具执行、报告生成等核心任务。

审计运行器 (AuditRunner)
------------------------

.. automodule:: oss_audit.core.audit_runner
   :members:
   :undoc-members:
   :show-inheritance:

项目检测器 (ProjectDetector)
----------------------------

.. automodule:: oss_audit.core.project_detector
   :members:
   :undoc-members:
   :show-inheritance:

工具执行器 (ToolExecutor)
-------------------------

.. automodule:: oss_audit.core.tool_executor
   :members:
   :undoc-members:
   :show-inheritance:

报告生成器 (ReportGenerator)
----------------------------

.. automodule:: oss_audit.core.report_generator
   :members:
   :undoc-members:
   :show-inheritance:

工具注册表 (ToolRegistry)
-------------------------

.. automodule:: oss_audit.core.tool_registry
   :members:
   :undoc-members:
   :show-inheritance:

使用示例
--------

审计运行器基本用法
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.core.audit_runner import AuditRunner
   
   # 初始化审计运行器
   runner = AuditRunner()
   
   # 运行完整项目审计
   results = runner.audit_project(
       project_path="/path/to/project",
       output_dir="./reports"
   )
   
   # 访问审计结果
   overall_score = results.get("overall_score")
   dimension_scores = results.get("dimension_scores", {})
   
   print(f"项目总体评分: {overall_score}")
   for dimension, score in dimension_scores.items():
       print(f"{dimension}: {score}")

项目检测器独立使用
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.core.project_detector import ProjectDetector
   
   # 创建项目检测器
   detector = ProjectDetector()
   
   # 检测项目信息
   project_info = detector.detect_project("/path/to/project")
   
   print(f"项目类型: {project_info.project_type}")
   print(f"主要语言: {project_info.languages}")
   print(f"结构类型: {project_info.structure_type}")

工具执行器自定义配置
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.core.tool_executor import ToolExecutor
   from oss_audit.core.tool_registry import ToolRegistry
   
   # 初始化工具注册表和执行器
   registry = ToolRegistry()
   executor = ToolExecutor(registry)
   
   # 自定义执行配置
   config = {
       "execution_mode": "parallel",
       "max_workers": 4,
       "timeout": 300
   }
   
   # 执行特定工具
   results = executor.execute_tools(
       project_path="/path/to/project",
       selected_tools=["pylint", "bandit", "pytest"],
       config=config
   )

数据结构
--------

ProjectInfo
~~~~~~~~~~~

项目信息数据类，包含检测到的项目详细信息：

.. code-block:: python

   @dataclass
   class ProjectInfo:
       name: str                           # 项目名称
       path: str                           # 项目路径
       languages: Dict[str, float]         # 语言分布
       structure_type: StructureType       # 结构类型
       project_type: ProjectType           # 项目类型
       dependencies: Dict[str, List[str]]  # 依赖列表
       build_tools: List[str]              # 构建工具
       size_metrics: SizeMetrics           # 大小指标
       confidence: float                   # 检测置信度

SizeMetrics
~~~~~~~~~~~

项目大小指标数据类：

.. code-block:: python

   @dataclass 
   class SizeMetrics:
       total_files: int     # 总文件数
       total_lines: int     # 总行数
       code_files: int      # 代码文件数
       code_lines: int      # 代码行数
       test_files: int      # 测试文件数
       test_lines: int      # 测试行数

枚举类型
--------

ProjectType (项目类型)
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class ProjectType(Enum):
       WEB_APPLICATION = "web_application"  # Web应用
       LIBRARY = "library"                  # 库
       CLI_TOOL = "cli_tool"               # CLI工具
       DATA_SCIENCE = "data_science"        # 数据科学
       MOBILE_APP = "mobile_app"           # 移动应用
       DESKTOP_APP = "desktop_app"         # 桌面应用

StructureType (结构类型)
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class StructureType(Enum):
       SINGLE_PROJECT = "single_project"    # 单一项目
       MULTI_PROJECT = "multi_project"      # 多项目
       MONOREPO = "monorepo"               # 单一仓库