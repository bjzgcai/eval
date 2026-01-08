快速开始
========

本指南将帮助您快速上手OSS Audit 2.0，完成第一次项目审计。

5分钟快速体验
-------------

1. **安装OSS Audit 2.0**

   .. code-block:: bash
   
      pip install oss-audit

2. **审计示例项目**

   .. code-block:: bash
   
      # 审计当前目录
      oss-audit .
      
      # 审计指定项目
      oss-audit /path/to/your/project

3. **查看报告**

   审计完成后，在 ``reports/`` 目录下查看生成的HTML报告。

基本使用方式
------------

命令行界面
~~~~~~~~~~

.. code-block:: bash

   # 基本审计
   oss-audit /path/to/project
   
   # 指定输出目录
   oss-audit /path/to/project --output ./my-reports
   
   # 启用详细输出
   oss-audit /path/to/project --verbose
   
   # 只运行特定工具
   oss-audit /path/to/project --tools pylint,bandit
   
   # 设置超时时间
   oss-audit /path/to/project --timeout 600

Python API
~~~~~~~~~~

.. code-block:: python

   from oss_audit.core.audit_runner import AuditRunner
   
   # 创建审计运行器
   runner = AuditRunner()
   
   # 运行审计
   results = runner.audit_project("/path/to/project")
   
   # 查看结果
   print(f"总体评分: {results['overall_score']}")
   print(f"安全评分: {results['dimension_scores']['security']}")

Docker使用
~~~~~~~~~~

.. code-block:: bash

   # 使用预构建镜像
   docker run -v /path/to/project:/workspace/project oss-audit:2.0
   
   # 使用docker-compose
   git clone https://github.com/your-org/oss-audit.git
   cd oss-audit
   ./scripts/run_audit.sh /path/to/project

配置文件
--------

创建 ``.oss-audit.yaml`` 配置文件来自定义审计行为：

.. code-block:: yaml

   # 基本配置
   project:
     name: "My Project"
     version: "1.0.0"
   
   # 工具配置
   tools:
     enabled:
       - pylint
       - bandit 
       - pytest
       - eslint
     
     timeout: 300
     parallel_execution: true
     max_workers: 4
   
   # 特定工具配置
   tool_configs:
     pylint:
       rcfile: ".pylintrc"
       disable: "C0114,C0115"
     
     bandit:
       confidence_level: "medium"
       severity_level: "low"
     
     pytest:
       coverage_threshold: 80
   
   # AI分析配置
   ai:
     enabled: true
     provider: "openai"
     model: "gpt-3.5-turbo"
   
   # 输出配置
   output:
     formats: ["html", "json"]
     include_raw_results: false
     theme: "default"

环境变量配置
~~~~~~~~~~~~

.. code-block:: bash

   # AI API密钥
   export OPENAI_API_KEY="your-openai-key"
   export GEMINI_API_KEY="your-gemini-key"
   export DEEPSEEK_API_KEY="your-deepseek-key"
   
   # 日志级别
   export OSS_AUDIT_LOG_LEVEL="INFO"
   
   # 缓存配置
   export OSS_AUDIT_CACHE_DIR="/tmp/oss-audit-cache"
   export OSS_AUDIT_CACHE_TTL="3600"

实际项目示例
------------

Python项目审计
~~~~~~~~~~~~~~

.. code-block:: bash

   # 审计Python Flask项目
   oss-audit ./my-flask-app --output ./reports
   
   # 查看生成的报告
   ls reports/my-flask-app/
   # ├── audit_report.html
   # ├── audit_results.json
   # └── raw_results/

**预期输出结构:**

.. code-block::

   ✅ 项目检测
   📁 项目类型: Web应用
   🐍 主要语言: Python (85%)
   🔧 构建工具: setup.py, requirements.txt
   
   🔍 工具执行
   ✅ pylint: 78/100 (发现 15 个问题)
   ✅ bandit: 92/100 (发现 2 个安全问题)
   ✅ black: 95/100 (代码格式良好)
   ✅ pytest: 85/100 (测试覆盖率 72%)
   
   📊 综合评分: 85/100
   
   🔗 详细报告: reports/my-flask-app/audit_report.html

JavaScript项目审计
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # 审计React项目
   oss-audit ./my-react-app --tools eslint,typescript,jest
   
**预期结果:**

.. code-block::

   ✅ 项目检测
   📁 项目类型: Web应用
   📜 主要语言: JavaScript (65%), TypeScript (35%)
   📦 包管理: package.json, package-lock.json
   
   🔍 工具执行
   ✅ eslint: 82/100
   ✅ typescript: 89/100  
   ✅ jest: 76/100 (覆盖率 68%)
   
   📊 综合评分: 82/100

多语言项目审计
~~~~~~~~~~~~~~

.. code-block:: bash

   # 审计包含前后端的全栈项目
   oss-audit ./fullstack-project --verbose

**预期结果:**

.. code-block::

   ✅ 项目检测
   📁 项目类型: Web应用
   🔧 结构类型: 单一仓库 (Monorepo)
   🌐 语言分布: Python (45%), JavaScript (35%), TypeScript (20%)
   
   🔍 工具执行
   后端 (Python):
     ✅ pylint: 75/100
     ✅ bandit: 88/100
     ✅ pytest: 79/100
   
   前端 (JavaScript/TypeScript):
     ✅ eslint: 83/100
     ✅ typescript: 91/100
     ✅ jest: 72/100
   
   📊 综合评分: 81/100

理解审计结果
------------

评分体系
~~~~~~~~

OSS Audit 2.0使用100分制评分系统：

- **90-100分**: 优秀 (Excellent) - 生产就绪
- **80-89分**: 良好 (Good) - 基本符合标准
- **70-79分**: 一般 (Fair) - 需要改进
- **60-69分**: 较差 (Poor) - 存在明显问题
- **0-59分**: 严重 (Critical) - 需要立即处理

14个评估维度
~~~~~~~~~~~~

1. **代码质量** (Code Quality) - 代码规范、复杂度
2. **安全性** (Security) - 安全漏洞、最佳实践
3. **测试覆盖** (Testing) - 测试完整性、质量
4. **文档** (Documentation) - 文档完整性、质量
5. **依赖管理** (Dependencies) - 依赖安全、版本管理
6. **性能** (Performance) - 性能优化、资源使用
7. **可维护性** (Maintainability) - 代码结构、可读性
8. **许可证** (License) - 许可证兼容性、合规性
9. **版本控制** (Version Control) - Git最佳实践
10. **构建系统** (Build System) - 构建配置、自动化
11. **配置管理** (Configuration) - 配置安全、管理
12. **错误处理** (Error Handling) - 异常处理、日志
13. **国际化** (Internationalization) - 多语言支持
14. **可访问性** (Accessibility) - 无障碍访问支持

报告解读
~~~~~~~~

**HTML报告结构:**

.. code-block::

   📋 执行摘要
   ├── 总体评分
   ├── 项目信息
   └── 关键指标
   
   📊 维度评分
   ├── 雷达图
   ├── 详细分数
   └── 改进建议
   
   🔧 工具结果
   ├── 各工具详细输出
   ├── 问题列表
   └── 执行统计
   
   🗺️ 改进路线图
   ├── 优先级排序
   ├── 预期效果
   └── 时间估算

**JSON结果结构:**

.. code-block:: json

   {
     "overall_score": 85.2,
     "dimension_scores": {
       "security": 78,
       "quality": 82,
       "testing": 76
     },
     "tool_results": {
       "pylint": {
         "success": true,
         "score": 78,
         "issues_found": [...]
       }
     },
     "recommendations": [...],
     "project_info": {...}
   }

常见使用场景
------------

CI/CD集成
~~~~~~~~~

**GitHub Actions示例:**

.. code-block:: yaml

   name: OSS Audit
   
   on: [push, pull_request]
   
   jobs:
     audit:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v2
         
         - name: Set up Python
           uses: actions/setup-python@v2
           with:
             python-version: '3.11'
         
         - name: Install OSS Audit
           run: pip install oss-audit
         
         - name: Run Audit
           run: oss-audit . --output ./audit-results
           env:
             OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
         
         - name: Upload Results
           uses: actions/upload-artifact@v2
           with:
             name: audit-results
             path: ./audit-results/

定期审计
~~~~~~~~

.. code-block:: bash

   # 创建定期审计脚本
   cat > daily_audit.sh << 'EOF'
   #!/bin/bash
   
   PROJECT_PATH="/path/to/project"
   REPORT_DIR="/var/reports/$(date +%Y%m%d)"
   
   # 运行审计
   oss-audit "$PROJECT_PATH" --output "$REPORT_DIR"
   
   # 发送通知（如果评分低于阈值）
   SCORE=$(grep -o '"overall_score": [0-9.]*' "$REPORT_DIR/audit_results.json" | cut -d' ' -f2)
   if (( $(echo "$SCORE < 80" | bc -l) )); then
       echo "Warning: Project score ($SCORE) below threshold" | mail -s "Audit Alert" admin@company.com
   fi
   EOF
   
   chmod +x daily_audit.sh
   
   # 添加到crontab
   echo "0 2 * * * /path/to/daily_audit.sh" | crontab -

团队协作
~~~~~~~~

.. code-block:: bash

   # 团队标准审计配置
   cat > .oss-audit.yaml << 'EOF'
   project:
     team: "Backend Team"
     standards: "company-python-standards-v2.1"
   
   tools:
     enabled:
       - pylint
       - bandit
       - black
       - mypy
       - pytest
   
   thresholds:
     overall_score: 80
     security: 85
     testing_coverage: 75
   
   notifications:
     slack_webhook: "${SLACK_WEBHOOK_URL}"
     email_recipients:
       - "tech-lead@company.com"
       - "team@company.com"
   EOF

故障排除
--------

常见问题及解决方案
~~~~~~~~~~~~~~~~~~

**Q: 工具执行超时**

.. code-block:: bash

   # 增加超时时间
   oss-audit . --timeout 900
   
   # 或在配置文件中设置
   tools:
     timeout: 900

**Q: 内存不足**

.. code-block:: bash

   # 减少并发执行
   oss-audit . --max-workers 1 --serial-execution

**Q: Docker权限问题**

.. code-block:: bash

   # 确保用户在docker组中
   sudo usermod -aG docker $USER
   # 重新登录生效

**Q: AI分析失败**

.. code-block:: bash

   # 检查API密钥
   echo $OPENAI_API_KEY
   
   # 禁用AI分析
   oss-audit . --no-ai

获取帮助
--------

.. code-block:: bash

   # 查看版本信息
   oss-audit --version
   
   # 查看详细帮助
   oss-audit --help
   
   # 查看工具列表
   oss-audit --list-tools
   
   # 检查系统环境
   oss-audit --check-env

下一步
------

现在您已经掌握了OSS Audit 2.0的基本使用，建议继续了解：

- :doc:`configuration` - 详细配置选项
- :doc:`api/core` - Python API参考
- :doc:`examples/advanced_usage` - 高级使用示例
- :doc:`development/contributing` - 参与贡献