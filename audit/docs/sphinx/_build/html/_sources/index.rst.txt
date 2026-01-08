OSS Audit 2.0 API文档
========================

欢迎使用OSS Audit 2.0 API文档！这是一个全面的开源软件成熟度评估工具，支持智能项目检测和AI增强分析。

.. toctree::
   :maxdepth: 2
   :caption: 快速开始:

   installation
   quickstart
   configuration

.. toctree::
   :maxdepth: 2
   :caption: API参考:

   api/core
   api/agents
   api/utils
   api/plugins

.. toctree::
   :maxdepth: 2
   :caption: 开发者指南:

   development/contributing
   development/architecture
   development/testing

.. toctree::
   :maxdepth: 2
   :caption: 示例和教程:

   examples/basic_usage
   examples/advanced_usage
   examples/custom_tools

特性概览
--------

OSS Audit 2.0 提供以下核心功能：

🔍 **智能项目检测**
   - 多语言项目自动识别 (Python, JavaScript, Java, Go, Rust, C++)
   - 项目结构类型智能推断 (单项目, 多项目, 单一仓库)
   - 自动项目类型分类 (Web应用, 库, CLI工具, 数据科学)

🤖 **AI增强分析**
   - 集成OpenAI/DeepSeek和Gemini模型
   - 智能问题优先级排序
   - 自适应评分模型优化
   - 针对性改进建议生成

🛠️ **综合工具支持**
   - 14个评估维度覆盖
   - 多种静态分析工具集成
   - Docker容器化工具支持
   - 并行和串行执行模式

📊 **详细报告生成**
   - HTML可视化报告
   - JSON数据导出
   - 维度评分分析
   - 改进路线图规划

核心组件
--------

.. autosummary::
   :toctree: _autosummary
   :caption: 核心模块

   oss_audit.core.audit_runner
   oss_audit.core.project_detector
   oss_audit.core.tool_executor
   oss_audit.core.report_generator

.. autosummary::
   :toctree: _autosummary  
   :caption: 智能代理

   oss_audit.core.decision_agent
   oss_audit.core.adaptive_agent
   oss_audit.core.recommendation_agent

.. autosummary::
   :toctree: _autosummary
   :caption: 工具和插件

   oss_audit.utils.ai_analyzer
   oss_audit.core.tool_registry
   oss_audit.plugins

快速开始
--------

安装OSS Audit 2.0:

.. code-block:: bash

   pip install oss-audit

基本使用:

.. code-block:: python

   from oss_audit.core.audit_runner import AuditRunner
   
   # 创建审计运行器
   runner = AuditRunner()
   
   # 运行项目审计
   results = runner.audit_project("/path/to/project")
   
   # 查看结果
   print(f"总体评分: {results['overall_score']}")

Docker使用:

.. code-block:: bash

   # 构建Docker镜像
   docker build -t oss-audit:2.0 .
   
   # 运行审计
   docker run -v /path/to/project:/workspace/project oss-audit:2.0

搜索和索引
----------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`