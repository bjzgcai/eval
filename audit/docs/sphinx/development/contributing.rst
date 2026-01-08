开发者贡献指南
================

欢迎贡献OSS Audit 2.0！本指南将帮助您了解如何参与项目开发、提交代码和改进建议。

贡献方式
--------

我们欢迎以下类型的贡献：

- 🐛 **Bug修复** - 修复已知问题
- ✨ **新功能** - 添加工具支持、语言检测等
- 📚 **文档改进** - 完善文档、添加示例
- 🧪 **测试增强** - 提高测试覆盖率
- 🔧 **工具集成** - 集成新的代码分析工具
- 🌐 **多语言支持** - 添加新编程语言支持
- 🚀 **性能优化** - 提升执行效率
- 🎨 **UI/UX改进** - 改善报告界面

快速开始
--------

开发环境搭建
~~~~~~~~~~~~

.. code-block:: bash

   # 1. Fork并克隆仓库
   git clone https://github.com/your-username/oss-audit.git
   cd oss-audit
   
   # 2. 创建虚拟环境
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或 venv\Scripts\activate  # Windows
   
   # 3. 安装开发依赖
   pip install -r requirements-dev.txt
   pip install -e .
   
   # 4. 运行测试验证环境
   make test

开发工作流
~~~~~~~~~~

.. code-block:: bash

   # 1. 创建功能分支
   git checkout -b feature/your-feature-name
   
   # 2. 进行开发
   # 编写代码...
   
   # 3. 运行质量检查
   make format        # 代码格式化
   make lint         # 代码质量检查
   make test         # 运行测试
   make quick-check  # 快速完整检查
   
   # 4. 提交更改
   git add .
   git commit -m "feat(tools): add new security scanner integration"
   
   # 5. 推送并创建Pull Request
   git push origin feature/your-feature-name

代码规范
--------

代码风格
~~~~~~~~

我们遵循以下代码风格标准：

**Python代码:**

.. code-block:: python

   # ✅ 好的实践
   from typing import Dict, List, Optional
   import logging
   
   logger = logging.getLogger(__name__)
   
   
   class SecurityAnalyzer:
       """安全分析器类
       
       提供多种安全扫描工具的统一接口。
       
       Args:
           config: 分析器配置字典
           timeout: 工具执行超时时间(秒)
       """
       
       def __init__(self, config: Dict[str, Any], timeout: int = 300):
           self.config = config
           self.timeout = timeout
           self._tools = self._initialize_tools()
       
       def analyze_project(self, project_path: str) -> List[SecurityIssue]:
           """分析项目安全问题
           
           Args:
               project_path: 项目路径
               
           Returns:
               发现的安全问题列表
               
           Raises:
               SecurityAnalysisError: 分析失败时抛出
           """
           try:
               issues = []
               for tool in self._tools:
                   tool_issues = self._run_tool(tool, project_path)
                   issues.extend(tool_issues)
               
               return self._deduplicate_issues(issues)
               
           except Exception as e:
               logger.error(f"Security analysis failed: {e}")
               raise SecurityAnalysisError(f"Analysis failed: {e}") from e

**命名约定:**

- 类名：``PascalCase`` (如 ``ProjectDetector``)
- 函数/变量：``snake_case`` (如 ``detect_language``)
- 常量：``UPPER_CASE`` (如 ``MAX_TIMEOUT``)
- 私有方法：``_private_method`` (下划线前缀)

**文档字符串:**

.. code-block:: python

   def detect_project_type(project_path: str, config: Optional[Dict] = None) -> ProjectInfo:
       """检测项目类型和特征
       
       基于文件结构、依赖配置和代码特征自动识别项目类型。
       支持Web应用、CLI工具、库项目等多种类型。
       
       Args:
           project_path: 项目根目录路径
           config: 可选的检测配置，包含自定义规则和权重
       
       Returns:
           ProjectInfo: 包含项目类型、主要语言、构建系统等信息
       
       Raises:
           ProjectDetectionError: 当项目路径无效或检测失败时
       
       Example:
           >>> detector = ProjectDetector()
           >>> info = detector.detect_project_type("./my-python-app")
           >>> print(f"项目类型: {info.project_type}")
           >>> print(f"主要语言: {info.primary_language}")
       """

Git提交规范
~~~~~~~~~~~

我们采用 `Conventional Commits <https://www.conventionalcommits.org/>`_ 标准：

**提交格式:**

.. code-block::

   <type>(<scope>): <subject>
   
   [optional body]
   
   [optional footer]

**类型说明:**

- ``feat``: 新功能 
- ``fix``: Bug修复
- ``docs``: 文档更新
- ``style``: 代码格式调整
- ``refactor``: 重构
- ``test``: 测试相关
- ``chore``: 构建/工具链更新

**示例:**

.. code-block::

   feat(tools): add support for ESLint TypeScript analysis
   
   - Integrate ESLint with TypeScript parser
   - Add TypeScript-specific rule configurations
   - Update tool registry with TypeScript detection
   
   Closes #123

测试要求
--------

测试覆盖率
~~~~~~~~~~

- **最低要求**: 新增代码测试覆盖率 ≥ 80%
- **核心模块**: 关键路径覆盖率 = 100%
- **集成测试**: 主要工作流覆盖完整

测试类型
~~~~~~~~

**1. 单元测试**

.. code-block:: python

   import pytest
   from unittest.mock import Mock, patch
   from oss_audit.core.tool_executor import ToolExecutor
   
   
   class TestToolExecutor:
       """工具执行器测试套件"""
       
       @pytest.fixture
       def executor(self):
           return ToolExecutor(max_workers=2, timeout=30)
       
       def test_execute_tool_success(self, executor):
           """测试工具执行成功场景"""
           # 准备测试数据
           tool_config = {
               "name": "pylint",
               "command": "pylint {project_path}",
               "timeout": 60
           }
           
           # Mock外部依赖
           with patch("subprocess.run") as mock_run:
               mock_run.return_value.returncode = 0
               mock_run.return_value.stdout = '{"score": 8.5}'
               
               result = executor.execute_tool("pylint", "/test/project", tool_config)
               
               assert result.success is True
               assert result.score == 85.0
               mock_run.assert_called_once()

**2. 集成测试**

.. code-block:: python

   @pytest.mark.integration
   def test_full_audit_workflow():
       """测试完整审计工作流"""
       with tempfile.TemporaryDirectory() as temp_dir:
           # 创建测试项目
           create_test_python_project(temp_dir)
           
           # 执行完整审计
           runner = AuditRunner()
           results = runner.audit_project(temp_dir)
           
           # 验证结果
           assert results["success"] is True
           assert results["overall_score"] > 0
           assert "tool_results" in results
           assert len(results["tool_results"]) > 0

**3. 性能测试**

.. code-block:: python

   @pytest.mark.performance
   def test_large_project_performance():
       """测试大型项目性能"""
       large_project_path = "tests/fixtures/large_project"
       
       start_time = time.time()
       results = run_audit(large_project_path)
       execution_time = time.time() - start_time
       
       # 性能断言
       assert execution_time < 300  # 5分钟内完成
       assert results["success"] is True

运行测试
~~~~~~~~

.. code-block:: bash

   # 运行所有测试
   make test
   
   # 运行特定测试文件
   pytest tests/test_tool_executor.py -v
   
   # 运行带覆盖率的测试
   make test-cov
   
   # 运行性能测试
   pytest -m performance
   
   # 跳过集成测试
   pytest -m "not integration"

新工具集成
----------

添加新分析工具的完整流程：

1. 工具注册
~~~~~~~~~~~

在 ``src/oss_audit/config/tools_registry.yaml`` 中添加工具定义：

.. code-block:: yaml

   tools:
     security_tools:
       semgrep:
         name: "Semgrep"
         description: "Fast, offline, static analysis"
         languages: ["python", "javascript", "java", "go"]
         categories: ["security", "quality"]
         installation:
           pip: "semgrep"
           docker: "returntocorp/semgrep"
         execution:
           command: "semgrep --config=auto --json {project_path}"
           timeout: 300
           output_format: "json"
         scoring:
           base_score: 100
           error_penalty: 5
           warning_penalty: 2

2. 工具适配器
~~~~~~~~~~~~~

创建工具适配器类：

.. code-block:: python

   from oss_audit.core.base_tool import BaseTool
   from typing import Dict, Any, List
   
   
   class SemgrepAdapter(BaseTool):
       """Semgrep工具适配器"""
       
       def __init__(self):
           super().__init__("semgrep")
       
       def is_available(self) -> bool:
           """检查Semgrep是否可用"""
           return self._check_command_availability("semgrep")
       
       def parse_output(self, output: str, stderr: str) -> Dict[str, Any]:
           """解析Semgrep输出"""
           try:
               data = json.loads(output)
               results = data.get("results", [])
               
               issues = []
               for result in results:
                   issues.append({
                       "file": result.get("path"),
                       "line": result.get("start", {}).get("line"),
                       "rule": result.get("check_id"),
                       "message": result.get("extra", {}).get("message", ""),
                       "severity": self._map_severity(result.get("extra", {}).get("severity"))
                   })
               
               score = self._calculate_score(issues)
               
               return {
                   "success": True,
                   "score": score,
                   "issues_found": issues,
                   "statistics": {
                       "total_issues": len(issues),
                       "files_scanned": len(set(i["file"] for i in issues))
                   }
               }
               
           except json.JSONDecodeError as e:
               return {
                   "success": False,
                   "error": f"Failed to parse Semgrep output: {e}",
                   "score": 0
               }

3. 测试用例
~~~~~~~~~~~

为新工具创建测试：

.. code-block:: python

   class TestSemgrepAdapter:
       """Semgrep适配器测试"""
       
       @pytest.fixture
       def adapter(self):
           return SemgrepAdapter()
       
       def test_parse_output_success(self, adapter):
           """测试输出解析成功"""
           mock_output = json.dumps({
               "results": [
                   {
                       "path": "src/app.py",
                       "start": {"line": 42},
                       "check_id": "python.lang.security.sql-injection",
                       "extra": {
                           "message": "Potential SQL injection",
                           "severity": "ERROR"
                       }
                   }
               ]
           })
           
           result = adapter.parse_output(mock_output, "")
           
           assert result["success"] is True
           assert len(result["issues_found"]) == 1
           assert result["issues_found"][0]["rule"] == "python.lang.security.sql-injection"

新语言支持
----------

添加新编程语言支持的步骤：

1. 语言检测规则
~~~~~~~~~~~~~~~

在 ``src/oss_audit/config/language_detection.yaml`` 中添加：

.. code-block:: yaml

   languages:
     kotlin:
       name: "Kotlin"
       extensions: [".kt", ".kts"]
       build_files: ["build.gradle.kts", "pom.xml"]
       patterns:
         - pattern: "package\\s+[\\w.]+"
           weight: 0.8
         - pattern: "fun\\s+\\w+\\s*\\("
           weight: 0.7
         - pattern: "class\\s+\\w+.*\\{"
           weight: 0.6
       confidence_threshold: 0.6

2. 项目配置
~~~~~~~~~~~

在 ``src/oss_audit/config/project_profiles.yaml`` 中添加：

.. code-block:: yaml

   language_profiles:
     kotlin:
       tools:
         quality: ["ktlint", "detekt"]
         security: ["spotbugs", "semgrep"]
         testing: ["junit"]
       metrics:
         complexity_threshold: 10
         line_limit: 200
       best_practices:
         - "使用数据类减少样板代码"
         - "利用协程处理异步操作"
         - "遵循Kotlin编码约定"

3. 工具配置
~~~~~~~~~~~

为语言添加专用工具：

.. code-block:: yaml

   tools:
     quality_tools:
       ktlint:
         name: "ktlint"
         description: "Kotlin linter"
         languages: ["kotlin"]
         categories: ["quality", "style"]
         installation:
           manual: "https://github.com/pinterest/ktlint"
         execution:
           command: "ktlint --reporter=json {project_path}"
           timeout: 120

Pull Request流程
---------------

PR创建清单
~~~~~~~~~~

在提交PR之前，请确保：

- [ ] 代码通过所有现有测试
- [ ] 新功能包含相应测试
- [ ] 遵循代码风格规范
- [ ] 更新相关文档
- [ ] 提交信息符合规范
- [ ] 解决了CI/CD检查问题

PR模板
~~~~~~

创建PR时请填写以下信息：

.. code-block:: markdown

   ## 变更描述
   
   简要描述本PR的变更内容和目的。
   
   ## 变更类型
   
   - [ ] Bug修复
   - [ ] 新功能
   - [ ] 文档更新
   - [ ] 重构
   - [ ] 性能优化
   - [ ] 其他: ___________
   
   ## 测试
   
   - [ ] 已添加单元测试
   - [ ] 已运行现有测试套件
   - [ ] 已进行手动测试
   
   ## 相关Issue
   
   Closes #123
   Related to #456

代码审查
~~~~~~~~

审查重点：

**功能性:**
- 是否正确实现了需求？
- 边界情况是否处理得当？
- 错误处理是否完善？

**代码质量:**
- 是否遵循项目编码规范？
- 变量/函数命名是否清晰？
- 是否有重复代码？

**性能:**
- 是否引入性能瓶颈？
- 内存使用是否合理？
- 算法复杂度是否优化？

**安全性:**
- 是否存在安全漏洞？
- 输入验证是否充分？
- 敏感信息是否泄露？

文档贡献
--------

文档类型
~~~~~~~~

**API文档:**
- 使用Sphinx autodoc自动生成
- 包含完整的docstring
- 提供使用示例

**用户指南:**
- 安装和配置说明
- 使用场景和最佳实践
- 故障排除指南

**开发者文档:**
- 架构设计说明
- 扩展开发指南
- 发布流程文档

文档编写规范
~~~~~~~~~~~~

.. code-block:: rst

   标题层级
   ========
   
   一级标题使用 =====
   
   二级标题
   --------
   
   二级标题使用 -----
   
   三级标题
   ~~~~~~~~
   
   三级标题使用 ~~~~~
   
   **代码示例:**
   
   .. code-block:: python
   
      # 提供完整可运行的示例
      from oss_audit.core.audit_runner import AuditRunner
      
      runner = AuditRunner()
      results = runner.audit_project("./my-project")
      print(f"总分: {results['overall_score']}")

构建文档
~~~~~~~~

.. code-block:: bash

   # 安装文档依赖
   pip install -r docs/requirements.txt
   
   # 构建HTML文档
   cd docs/sphinx
   make html
   
   # 查看生成的文档
   open _build/html/index.html

社区参与
--------

讨论渠道
~~~~~~~~

- **GitHub Issues**: Bug报告、功能请求
- **GitHub Discussions**: 技术讨论、使用问题
- **项目Wiki**: 设计文档、会议记录

贡献者权益
~~~~~~~~~~

- 代码贡献者将在README中致谢
- 重大贡献者可获得项目维护者权限
- 定期发布贡献者统计报告

发布流程
~~~~~~~~

项目采用语义化版本控制：

- **主版本**: 不兼容的API变更
- **次版本**: 向后兼容的功能添加
- **修订版本**: 向后兼容的Bug修复

.. code-block:: bash

   # 发布新版本
   git tag v2.1.0
   git push origin v2.1.0
   
   # 自动化发布到PyPI
   # (通过GitHub Actions)

常见问题
--------

开发环境问题
~~~~~~~~~~~~

**Q: 虚拟环境创建失败**

.. code-block:: bash

   # 解决方案
   python -m pip install --upgrade pip
   python -m venv venv --clear

**Q: 依赖安装出错**

.. code-block:: bash

   # 清理pip缓存
   pip cache purge
   pip install --no-cache-dir -r requirements-dev.txt

**Q: 测试运行失败**

.. code-block:: bash

   # 检查Python路径
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
   pytest tests/ -v

代码问题
~~~~~~~~

**Q: 如何调试工具执行问题？**

.. code-block:: python

   # 启用详细日志
   import logging
   logging.basicConfig(level=logging.DEBUG)
   
   # 使用调试模式
   runner = AuditRunner(debug=True)

**Q: 如何添加自定义评分规则？**

参考 ``src/oss_audit/core/scoring/`` 目录下的示例。

获取帮助
--------

如需帮助，请：

1. 查阅项目Wiki和文档
2. 搜索已有Issues和Discussions
3. 创建详细的Issue描述问题
4. 在Discussion中询问使用问题

联系方式：
- GitHub: https://github.com/your-org/oss-audit
- 邮箱: maintainers@oss-audit.org

感谢您的贡献！🎉