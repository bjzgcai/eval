安装指南
========

系统要求
--------

* Python 3.8+ 
* Git (用于版本控制检测)
* Docker (可选，用于容器化工具)

核心安装
--------

使用pip安装
~~~~~~~~~~~

.. code-block:: bash

   # 安装最新稳定版本
   pip install oss-audit
   
   # 安装开发版本
   pip install git+https://github.com/your-org/oss-audit.git

从源码安装
~~~~~~~~~~

.. code-block:: bash

   # 克隆仓库
   git clone https://github.com/your-org/oss-audit.git
   cd oss-audit
   
   # 安装依赖
   pip install -r requirements.txt
   
   # 安装项目
   pip install -e .

开发环境设置
~~~~~~~~~~~~

.. code-block:: bash

   # 创建虚拟环境
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate     # Windows
   
   # 安装开发依赖
   pip install -r requirements-dev.txt
   
   # 安装预提交钩子
   pre-commit install

Docker安装
----------

使用预构建镜像
~~~~~~~~~~~~~~

.. code-block:: bash

   # 拉取官方镜像
   docker pull oss-audit:2.0
   
   # 运行容器
   docker run -it oss-audit:2.0

构建本地镜像
~~~~~~~~~~~~

.. code-block:: bash

   # 构建镜像
   docker build -t oss-audit:local .
   
   # 使用docker-compose
   docker-compose up --build

验证安装
--------

命令行验证
~~~~~~~~~~

.. code-block:: bash

   # 检查版本
   oss-audit --version
   
   # 查看帮助
   oss-audit --help
   
   # 运行测试项目
   oss-audit ./test-project

Python API验证
~~~~~~~~~~~~~~

.. code-block:: python

   # 测试导入
   from oss_audit.core.audit_runner import AuditRunner
   
   # 创建审计运行器
   runner = AuditRunner()
   print("OSS Audit 2.0 安装成功！")

工具依赖
--------

Python工具
~~~~~~~~~~

以下工具将自动安装：

* **pylint** - 代码质量检查
* **flake8** - 代码风格检查  
* **bandit** - 安全漏洞扫描
* **black** - 代码格式化检查
* **mypy** - 类型检查
* **pytest** - 测试框架
* **semgrep** - 静态分析

JavaScript/Node.js工具
~~~~~~~~~~~~~~~~~~~~~~

需要Node.js环境：

.. code-block:: bash

   # 安装Node.js工具
   npm install -g eslint typescript

可选工具
--------

高级分析工具
~~~~~~~~~~~~

.. code-block:: bash

   # SonarQube (用于高级代码分析)
   docker run -d --name sonarqube -p 9000:9000 sonarqube:community
   
   # Dependency-Track (用于依赖安全分析)  
   docker run -d --name dependency-track -p 8081:8080 dependencytrack/bundled

AI分析配置
~~~~~~~~~~

设置AI分析功能的API密钥：

.. code-block:: bash

   # OpenAI API密钥
   export OPENAI_API_KEY="your-api-key"
   
   # Gemini API密钥  
   export GEMINI_API_KEY="your-api-key"
   
   # DeepSeek API密钥
   export DEEPSEEK_API_KEY="your-api-key"

配置文件
~~~~~~~~

创建 ``config.yaml`` 配置文件：

.. code-block:: yaml

   # AI配置
   ai:
     enabled: true
     provider: "openai"  # 或 "gemini", "deepseek"
     model: "gpt-3.5-turbo"
     
   # 工具配置
   tools:
     timeout: 300
     parallel_execution: true
     max_workers: 4
     
   # 输出配置  
   output:
     formats: ["html", "json"]
     include_raw_results: false

故障排除
--------

常见问题
~~~~~~~~

**ImportError: No module named 'oss_audit'**

.. code-block:: bash

   # 确保正确安装
   pip install --upgrade oss-audit
   
   # 或从源码重新安装
   pip install -e .

**Docker权限错误**

.. code-block:: bash

   # Linux/Mac - 添加用户到docker组
   sudo usermod -aG docker $USER
   
   # 重新登录或使用
   newgrp docker

**工具执行超时**

修改配置文件中的超时设置：

.. code-block:: yaml

   tools:
     timeout: 600  # 增加到10分钟

**内存不足错误**

.. code-block:: bash

   # 减少并行工作进程
   oss-audit --max-workers 2 /path/to/project

支持和帮助
----------

* **文档**: https://oss-audit.readthedocs.io/
* **GitHub Issues**: https://github.com/your-org/oss-audit/issues
* **讨论社区**: https://github.com/your-org/oss-audit/discussions

版本兼容性
----------

+----------+------------------+------------------+
| 组件     | 最低版本         | 推荐版本         |
+==========+==================+==================+
| Python   | 3.8              | 3.11+            |
+----------+------------------+------------------+
| Docker   | 20.10            | 24.0+            |
+----------+------------------+------------------+
| Node.js  | 16.0             | 18.0+ (LTS)      |
+----------+------------------+------------------+
| Git      | 2.25             | 2.40+            |
+----------+------------------+------------------+