配置指南
========

OSS Audit 2.0提供灵活的配置系统，支持项目级配置、环境变量和命令行参数。

配置优先级
----------

配置加载顺序（优先级从高到低）：

1. **命令行参数** - ``--timeout 600``
2. **环境变量** - ``OSS_AUDIT_TIMEOUT=600``
3. **项目配置文件** - ``.oss-audit.yaml``
4. **用户配置** - ``~/.config/oss-audit/config.yaml``
5. **系统默认值**

项目配置文件
------------

在项目根目录创建 ``.oss-audit.yaml`` 配置文件：

基础配置
~~~~~~~~

.. code-block:: yaml

   # 项目信息
   project:
     name: "My Amazing Project"
     version: "2.1.0"
     description: "A comprehensive web application"
     team: "Backend Development Team"
     contact: "backend-team@company.com"
   
   # 全局设置
   settings:
     log_level: "INFO"          # DEBUG, INFO, WARNING, ERROR
     verbose: false             # 详细输出
     quiet: false              # 静默模式
     color: true               # 彩色输出

工具配置
~~~~~~~~

.. code-block:: yaml

   # 工具配置
   tools:
     # 启用的工具列表
     enabled:
       - pylint
       - bandit
       - black
       - mypy
       - pytest
       - eslint
       - typescript
     
     # 禁用的工具列表
     disabled:
       - flake8  # 与pylint重复
       - jshint  # 使用eslint替代
     
     # 执行配置
     execution:
       mode: "parallel"         # parallel, serial, hybrid
       timeout: 300            # 单个工具超时时间（秒）
       max_workers: 4          # 最大并发数
       retry_count: 1          # 失败重试次数
       continue_on_error: true  # 工具失败时是否继续
     
     # 工具发现
     discovery:
       auto_detect: true       # 自动检测可用工具
       require_all: false      # 是否要求所有工具都可用
       fallback_tools: true   # 启用备用工具

特定工具配置
~~~~~~~~~~~~

.. code-block:: yaml

   # 工具特定配置
   tool_configs:
     # Python工具
     pylint:
       rcfile: ".pylintrc"
       disable:
         - "C0114"  # missing-module-docstring
         - "C0115"  # missing-class-docstring
       enable:
         - "W0613"  # unused-argument
       output_format: "json"
       score_threshold: 7.0
     
     bandit:
       config_file: ".bandit"
       confidence_level: "medium"  # low, medium, high
       severity_level: "low"       # low, medium, high
       skip_tests:
         - "B101"  # assert_used
       include_paths:
         - "src/"
       exclude_paths:
         - "tests/"
         - "migrations/"
     
     black:
       line_length: 88
       target_versions: ["py38", "py39", "py310"]
       skip_string_normalization: false
       exclude: |
         /(
             \.eggs
           | \.git
           | \.mypy_cache
           | \.tox
           | \.venv
           | _build
           | build
           | dist
         )/
     
     mypy:
       config_file: "mypy.ini"
       python_version: "3.10"
       warn_return_any: true
       warn_unused_configs: true
       disallow_untyped_defs: true
       ignore_missing_imports: true
     
     pytest:
       config_file: "pytest.ini"
       coverage_threshold: 80
       coverage_fail_under: 75
       coverage_report: "html"
       test_paths:
         - "tests/"
         - "src/tests/"
       markers:
         - "slow: marks tests as slow"
         - "integration: marks tests as integration"
     
     # JavaScript/TypeScript工具
     eslint:
       config_file: ".eslintrc.json"
       ignore_path: ".eslintignore"
       max_warnings: 10
       fix: false
       cache: true
       extensions:
         - ".js"
         - ".jsx"
         - ".ts"
         - ".tsx"
     
     typescript:
       config_file: "tsconfig.json"
       no_emit: true
       strict: true
       skip_lib_check: true

AI配置
~~~~~~

.. code-block:: yaml

   # AI分析配置
   ai:
     enabled: true
     
     # 提供商配置
     providers:
       openai:
         api_key: "${OPENAI_API_KEY}"
         base_url: "https://api.openai.com/v1"
         model: "gpt-3.5-turbo"
         max_tokens: 4000
         temperature: 0.2
         timeout: 30
       
       gemini:
         api_key: "${GEMINI_API_KEY}"
         model: "gemini-1.5-flash"
         max_tokens: 2000
         temperature: 0.1
       
       deepseek:
         api_key: "${DEEPSEEK_API_KEY}"
         base_url: "https://api.deepseek.com/v1"
         model: "deepseek-coder"
         max_tokens: 8000
     
     # 默认提供商
     default_provider: "openai"
     
     # 模型选择策略
     model_selection:
       strategy: "balanced"  # performance, cost, balanced
       auto_fallback: true   # 主模型失败时自动切换
       
     # 分析配置
     analysis:
       enable_code_review: true
       enable_security_analysis: true
       enable_performance_suggestions: true
       max_file_size: 10240  # KB
       exclude_file_types:
         - ".min.js"
         - ".bundle.js"
         - ".map"

输出配置
~~~~~~~~

.. code-block:: yaml

   # 输出配置
   output:
     # 输出目录
     directory: "./reports"
     
     # 输出格式
     formats:
       - "html"
       - "json"
       - "xml"    # 可选
       - "csv"    # 可选
       - "junit"  # CI/CD集成
     
     # HTML报告配置
     html:
       theme: "default"        # default, dark, minimal
       include_source_code: true
       include_diff: false
       responsive: true
       custom_css: "custom.css"
       favicon: "favicon.ico"
     
     # JSON输出配置
     json:
       pretty_print: true
       include_raw_results: false
       include_metadata: true
     
     # 压缩配置
     compression:
       enabled: true
       format: "gzip"  # gzip, zip
     
     # 历史记录
     history:
       enabled: true
       max_reports: 50
       retention_days: 90

过滤和排除
~~~~~~~~~~

.. code-block:: yaml

   # 文件和目录过滤
   filters:
     # 包含模式
     include:
       extensions:
         - ".py"
         - ".js"
         - ".ts"
         - ".jsx"
         - ".tsx"
       paths:
         - "src/"
         - "lib/"
         - "app/"
     
     # 排除模式
     exclude:
       patterns:
         - "*/node_modules/*"
         - "*/__pycache__/*"
         - "*/venv/*"
         - "*/env/*"
         - "*.pyc"
         - "*.min.js"
         - "*.bundle.js"
       paths:
         - "build/"
         - "dist/"
         - ".git/"
         - "coverage/"
       files:
         - "webpack.config.js"
         - "babel.config.js"
     
     # 最大文件大小 (KB)
     max_file_size: 1024
     
     # 最大目录深度
     max_depth: 10

阈值和警告
~~~~~~~~~~

.. code-block:: yaml

   # 评分阈值
   thresholds:
     # 总体评分阈值
     overall_score:
       excellent: 90
       good: 80
       fair: 70
       poor: 60
     
     # 维度评分阈值
     dimensions:
       security: 85
       quality: 80
       testing: 75
       documentation: 70
       performance: 75
     
     # 工具评分阈值
     tools:
       pylint: 8.0
       bandit: 90
       pytest_coverage: 80
     
     # 问题数量阈值
     issues:
       critical: 0
       high: 5
       medium: 20
       low: 50
     
     # 退出码配置
     exit_codes:
       fail_on_threshold: true
       fail_on_critical: true
       fail_on_error: false

通知配置
~~~~~~~~

.. code-block:: yaml

   # 通知配置
   notifications:
     enabled: true
     
     # 触发条件
     triggers:
       - "score_below_threshold"
       - "critical_issues"
       - "new_security_issues"
       - "coverage_drop"
     
     # 邮件通知
     email:
       enabled: true
       smtp_server: "smtp.company.com"
       smtp_port: 587
       username: "${SMTP_USERNAME}"
       password: "${SMTP_PASSWORD}"
       from_email: "oss-audit@company.com"
       recipients:
         - "team-lead@company.com"
         - "security@company.com"
       template: "email_template.html"
     
     # Slack通知
     slack:
       enabled: true
       webhook_url: "${SLACK_WEBHOOK_URL}"
       channel: "#code-quality"
       username: "OSS Audit Bot"
       icon_emoji: ":robot_face:"
       template: |
         :warning: OSS Audit Alert
         Project: {{project.name}}
         Score: {{overall_score}}/100
         Issues: {{critical_issues}} critical, {{high_issues}} high
     
     # 自定义webhook
     webhook:
       enabled: false
       url: "https://api.company.com/webhooks/audit"
       method: "POST"
       headers:
         Authorization: "Bearer ${WEBHOOK_TOKEN}"
         Content-Type: "application/json"

环境变量
--------

OSS Audit 2.0支持以下环境变量：

基本配置
~~~~~~~~

.. code-block:: bash

   # 基本设置
   export OSS_AUDIT_LOG_LEVEL="INFO"
   export OSS_AUDIT_VERBOSE="true"
   export OSS_AUDIT_QUIET="false"
   export OSS_AUDIT_COLOR="true"
   
   # 执行配置
   export OSS_AUDIT_TIMEOUT="300"
   export OSS_AUDIT_MAX_WORKERS="4"
   export OSS_AUDIT_PARALLEL="true"
   
   # 输出配置
   export OSS_AUDIT_OUTPUT_DIR="./reports"
   export OSS_AUDIT_OUTPUT_FORMAT="html,json"

AI配置
~~~~~~

.. code-block:: bash

   # API密钥
   export OPENAI_API_KEY="sk-your-openai-key"
   export GEMINI_API_KEY="your-gemini-key"
   export DEEPSEEK_API_KEY="your-deepseek-key"
   
   # 模型配置
   export OSS_AUDIT_AI_PROVIDER="openai"
   export OSS_AUDIT_AI_MODEL="gpt-3.5-turbo"
   export OSS_AUDIT_AI_TEMPERATURE="0.2"
   
   # 启用/禁用AI
   export OSS_AUDIT_AI_ENABLED="true"

缓存配置
~~~~~~~~

.. code-block:: bash

   # 缓存设置
   export OSS_AUDIT_CACHE_ENABLED="true"
   export OSS_AUDIT_CACHE_DIR="/tmp/oss-audit-cache"
   export OSS_AUDIT_CACHE_TTL="3600"
   export OSS_AUDIT_CACHE_MAX_SIZE="1000"

命令行参数
----------

完整的命令行参数列表：

基本参数
~~~~~~~~

.. code-block:: bash

   oss-audit [OPTIONS] PROJECT_PATH
   
   # 基本选项
   --output, -o          输出目录 (默认: ./reports)
   --config, -c          配置文件路径
   --verbose, -v         详细输出
   --quiet, -q           静默模式
   --help, -h            显示帮助
   --version             显示版本信息

工具选择
~~~~~~~~

.. code-block:: bash

   # 工具控制
   --tools               指定运行的工具 (逗号分隔)
   --exclude-tools       排除的工具 (逗号分隔)
   --list-tools          列出所有可用工具
   --check-tools         检查工具可用性

执行控制
~~~~~~~~

.. code-block:: bash

   # 执行配置
   --timeout             超时时间 (秒)
   --max-workers         最大并发数
   --serial              串行执行
   --parallel            并行执行
   --retry               重试次数
   --fail-fast           遇到错误立即停止

输出控制
~~~~~~~~

.. code-block:: bash

   # 输出配置
   --format              输出格式 (html,json,xml,csv)
   --theme               HTML主题 (default,dark,minimal)
   --no-html             不生成HTML报告
   --no-json             不生成JSON报告
   --compress            压缩输出文件

AI和高级功能
~~~~~~~~~~~~

.. code-block:: bash

   # AI配置
   --ai-provider         AI提供商 (openai,gemini,deepseek)
   --ai-model            AI模型名称
   --no-ai               禁用AI分析
   
   # 缓存控制
   --no-cache            禁用缓存
   --clear-cache         清除缓存
   --cache-dir           缓存目录

高级配置示例
------------

企业级配置
~~~~~~~~~~

.. code-block:: yaml

   # 企业级配置示例
   project:
     organization: "ACME Corporation"
     compliance: "SOX, GDPR, HIPAA"
     criticality: "high"
   
   tools:
     execution:
       timeout: 900
       max_workers: 8
       retry_count: 2
   
   thresholds:
     overall_score:
       fail_below: 85
     security:
       fail_below: 95
     critical_issues: 0
   
   notifications:
     email:
       recipients:
         - "ciso@company.com"
         - "compliance@company.com"
     slack:
       channel: "#security-alerts"
   
   audit_trail:
     enabled: true
     retention_years: 7
     encryption: true

开源项目配置
~~~~~~~~~~~~

.. code-block:: yaml

   # 开源项目配置示例
   project:
     type: "open_source"
     license: "MIT"
     repository: "https://github.com/user/project"
   
   tools:
     enabled:
       - pylint
       - bandit
       - black
       - pytest
       - safety
   
   thresholds:
     overall_score: 75
     security: 80
     testing: 70
   
   output:
     formats: ["html", "json", "badge"]
     public: true
     
   badges:
     enabled: true
     style: "flat-square"
     logo: "python"

CI/CD集成配置
~~~~~~~~~~~~~

.. code-block:: yaml

   # CI/CD优化配置
   tools:
     execution:
       mode: "parallel"
       timeout: 600
       max_workers: 2  # 限制资源使用
   
   output:
     formats: ["json", "junit"]
     compression:
       enabled: true
   
   thresholds:
     fail_on_threshold: true
     overall_score: 80
   
   cache:
     enabled: true
     ttl: 86400  # 24小时
   
   notifications:
     webhook:
       enabled: true
       url: "${CI_WEBHOOK_URL}"

配置验证
--------

验证配置文件
~~~~~~~~~~~~

.. code-block:: bash

   # 验证配置文件语法
   oss-audit --validate-config .oss-audit.yaml
   
   # 显示合并后的配置
   oss-audit --show-config
   
   # 测试配置
   oss-audit --dry-run --config .oss-audit.yaml

配置迁移
~~~~~~~~

.. code-block:: bash

   # 从旧版本迁移配置
   oss-audit --migrate-config old-config.yaml
   
   # 生成示例配置
   oss-audit --generate-config > .oss-audit.yaml

故障排除
--------

配置问题诊断
~~~~~~~~~~~~

.. code-block:: bash

   # 检查配置加载
   oss-audit --debug --show-config-source
   
   # 验证工具可用性
   oss-audit --check-env
   
   # 测试AI连接
   oss-audit --test-ai-connection

常见配置错误
~~~~~~~~~~~~

1. **YAML语法错误**
   
   .. code-block:: yaml
   
      # 错误: 缩进不一致
      tools:
        enabled:
        - pylint  # 应该缩进4个空格
      
      # 正确:
      tools:
        enabled:
          - pylint

2. **环境变量未设置**
   
   .. code-block:: bash
   
      # 检查环境变量
      echo $OPENAI_API_KEY
      
      # 设置环境变量
      export OPENAI_API_KEY="your-key-here"

3. **工具路径问题**
   
   .. code-block:: bash
   
      # 检查工具是否在PATH中
      which pylint
      which eslint
      
      # 添加到PATH
      export PATH="/usr/local/bin:$PATH"