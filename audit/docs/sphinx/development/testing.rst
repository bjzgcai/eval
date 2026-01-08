测试框架和模式
================

OSS Audit 2.0采用多层次测试策略，确保代码质量和系统可靠性。本文档详细说明了测试架构、模式和最佳实践。

测试架构
--------

测试金字塔
~~~~~~~~~~

.. code-block::

   ┌─────────────────────────────────────┐
   │           E2E Tests (5%)            │  端到端测试
   │         用户场景验证                 │
   ├─────────────────────────────────────┤
   │      Integration Tests (15%)        │  集成测试
   │        组件协作验证                  │
   ├─────────────────────────────────────┤
   │        Unit Tests (80%)             │  单元测试
   │         组件独立验证                 │
   └─────────────────────────────────────┘

**测试分层说明:**

- **单元测试 (80%)**: 测试独立函数和类方法
- **集成测试 (15%)**: 测试组件间交互和数据流  
- **端到端测试 (5%)**: 测试完整用户工作流

测试配置
~~~~~~~~

项目使用pytest作为主要测试框架，配置文件 ``pytest.ini``：

.. code-block:: ini

   [tool:pytest]
   testpaths = tests
   python_files = test_*.py *_test.py
   python_classes = Test*
   python_functions = test_*
   
   # 测试标记
   markers =
       unit: Unit tests  
       integration: Integration tests
       e2e: End-to-end tests
       slow: Slow running tests
       docker: Tests requiring Docker
       ai: Tests requiring AI providers
   
   # 覆盖率配置
   addopts = 
       --strict-markers
       --strict-config
       --cov=src/oss_audit
       --cov-branch
       --cov-report=term-missing
       --cov-report=html:htmlcov
       --cov-fail-under=80
   
   # 并行执行
   # addopts = -n auto  # 需要pytest-xdist

单元测试
--------

核心组件测试
~~~~~~~~~~~~

**ProjectDetector测试示例:**

.. code-block:: python

   import pytest
   from unittest.mock import patch, mock_open
   from pathlib import Path
   
   from oss_audit.core.project_detector import ProjectDetector, ProjectInfo
   from oss_audit.core.types import StructureType, ProjectType
   
   
   class TestProjectDetector:
       """项目检测器单元测试"""
       
       @pytest.fixture
       def detector(self):
           """测试固件：创建检测器实例"""
           return ProjectDetector()
       
       @pytest.fixture
       def python_project_files(self):
           """Python项目文件模拟"""
           return {
               "setup.py": "from setuptools import setup\nsetup(name='test')",
               "requirements.txt": "flask==2.0.0\npytest==7.0.0", 
               "src/app.py": "def main():\n    print('Hello')",
               "tests/test_app.py": "def test_main():\n    assert True"
           }
       
       def test_detect_python_project(self, detector, python_project_files):
           """测试Python项目检测"""
           with patch('pathlib.Path.exists') as mock_exists, \
                patch('pathlib.Path.glob') as mock_glob, \
                patch('builtins.open', mock_open()) as mock_file:
               
               # 配置mock行为
               mock_exists.return_value = True
               mock_glob.return_value = [Path("src/app.py"), Path("tests/test_app.py")]
               mock_file.return_value.read.side_effect = python_project_files.values()
               
               # 执行检测
               result = detector.detect_project("/test/project")
               
               # 验证结果
               assert result.primary_language == "python"
               assert result.project_type == ProjectType.WEB_APPLICATION
               assert "flask" in result.dependencies.get("python", [])
               assert result.confidence > 0.8
       
       @pytest.mark.parametrize("files,expected_language", [
           (["package.json", "src/index.js"], "javascript"),
           (["pom.xml", "src/Main.java"], "java"), 
           (["go.mod", "main.go"], "go"),
           (["Cargo.toml", "src/lib.rs"], "rust")
       ])
       def test_detect_different_languages(self, detector, files, expected_language):
           """参数化测试：多语言检测"""
           with patch('pathlib.Path.exists') as mock_exists:
               mock_exists.side_effect = lambda path: path.name in files
               
               result = detector.detect_project("/test/project") 
               assert result.primary_language == expected_language
       
       def test_detect_monorepo_structure(self, detector):
           """测试Monorepo结构检测"""
           monorepo_structure = [
               "frontend/package.json",
               "backend/setup.py", 
               "mobile/build.gradle",
               "shared/package.json"
           ]
           
           with patch('pathlib.Path.rglob') as mock_rglob:
               mock_rglob.return_value = [Path(p) for p in monorepo_structure]
               
               result = detector.detect_project("/test/monorepo")
               assert result.structure_type == StructureType.MONOREPO
               assert len(result.language_distribution) > 1

**Mock和Fixture模式:**

.. code-block:: python

   @pytest.fixture
   def mock_subprocess_success():
       """Mock成功的subprocess执行"""
       with patch('subprocess.run') as mock_run:
           mock_run.return_value.returncode = 0
           mock_run.return_value.stdout = '{"score": 8.5, "issues": []}'
           mock_run.return_value.stderr = ''
           yield mock_run
   
   @pytest.fixture
   def temp_project_dir(tmp_path):
       """创建临时项目目录"""
       project_dir = tmp_path / "test_project"
       project_dir.mkdir()
       
       # 创建Python项目结构
       (project_dir / "src").mkdir()
       (project_dir / "src" / "__init__.py").write_text("")
       (project_dir / "src" / "main.py").write_text("def hello(): return 'world'")
       (project_dir / "setup.py").write_text("from setuptools import setup")
       
       return str(project_dir)

Agent系统测试
~~~~~~~~~~~~~

**AdaptiveAgent测试示例:**

.. code-block:: python

   import pytest
   from unittest.mock import Mock, MagicMock
   
   from oss_audit.agents.adaptive_agent import AdaptiveAgent
   from oss_audit.core.types import ProjectInfo, ScoringModel
   
   
   class TestAdaptiveAgent:
       """自适应Agent测试"""
       
       @pytest.fixture
       def agent(self):
           return AdaptiveAgent()
       
       @pytest.fixture  
       def sample_project_info(self):
           return ProjectInfo(
               project_name="test-project",
               primary_language="python", 
               project_type=ProjectType.WEB_APPLICATION,
               complexity_score=0.7
           )
       
       @pytest.fixture
       def sample_tool_results(self):
           return {
               "pylint": {"score": 75, "issues_found": []},
               "bandit": {"score": 92, "issues_found": []},
               "pytest": {"score": 68, "issues_found": []}
           }
       
       def test_adapt_scoring_model_web_app(self, agent, sample_project_info, sample_tool_results):
           """测试Web应用评分模型适应"""
           adapted_model = agent.adapt_scoring_model(
               project_info=sample_project_info,
               tool_results=sample_tool_results
           )
           
           # 验证Web应用的权重调整
           assert adapted_model.weights["security"] > 0.25  # 安全权重增加
           assert adapted_model.weights["quality"] > 0.20   # 质量权重保持
           assert adapted_model.confidence_level > 0.7      # 置信度合理
       
       def test_complexity_adjustment(self, agent):
           """测试复杂度调整逻辑"""
           high_complexity_project = ProjectInfo(
               project_name="complex-project", 
               complexity_score=0.9,
               project_type=ProjectType.LIBRARY
           )
           
           tool_results = {
               "pylint": {"score": 60, "issues_found": []},
               "mypy": {"score": 55, "issues_found": []}
           }
           
           adapted_model = agent.adapt_scoring_model(
               project_info=high_complexity_project,
               tool_results=tool_results
           )
           
           # 高复杂度项目应降低期望得分
           assert adapted_model.complexity_adjustment < 1.0
           assert adapted_model.adapted_weights != agent.base_weights

**Agent协作测试:**

.. code-block:: python

   @pytest.mark.integration
   class TestAgentCoordination:
       """Agent协作集成测试"""
       
       def test_decision_to_adaptive_flow(self):
           """测试决策Agent到自适应Agent的流程"""
           # 1. DecisionAgent选择工具
           decision_agent = DecisionAgent()
           execution_plan = decision_agent.create_execution_plan(
               project_info=sample_project_info,
               available_tools=["pylint", "bandit", "pytest"]
           )
           
           # 2. 模拟工具执行结果
           mock_results = {"pylint": {"score": 78}, "bandit": {"score": 95}}
           
           # 3. AdaptiveAgent调整评分
           adaptive_agent = AdaptiveAgent() 
           adapted_model = adaptive_agent.adapt_scoring_model(
               project_info=sample_project_info,
               tool_results=mock_results
           )
           
           # 4. 验证协作效果
           assert execution_plan.selected_tools == ["pylint", "bandit", "pytest"]
           assert adapted_model.confidence_level > 0.6

集成测试
--------

组件集成测试
~~~~~~~~~~~~

**AuditRunner集成测试:**

.. code-block:: python

   @pytest.mark.integration
   class TestAuditRunnerIntegration:
       """AuditRunner集成测试"""
       
       @pytest.fixture
       def runner(self):
           """创建AuditRunner实例"""
           return AuditRunner()
       
       @pytest.fixture 
       def mock_tools_available(self):
           """Mock工具可用性"""
           with patch.multiple(
               'oss_audit.core.tool_executor',
               check_tool_availability=Mock(return_value=True),
               execute_tool=Mock(return_value={"success": True, "score": 85})
           ):
               yield
       
       def test_full_audit_workflow(self, runner, temp_project_dir, mock_tools_available):
           """测试完整审计工作流"""
           # 执行完整审计
           results = runner.audit_project(temp_project_dir)
           
           # 验证结果结构
           assert "project_info" in results
           assert "tool_results" in results  
           assert "overall_score" in results
           assert "recommendations" in results
           
           # 验证评分合理性
           assert 0 <= results["overall_score"] <= 100
           
           # 验证各组件协作
           assert results["project_info"]["primary_language"] is not None
           assert len(results["tool_results"]) > 0
       
       def test_error_recovery(self, runner, temp_project_dir):
           """测试错误恢复机制"""
           with patch('oss_audit.core.tool_executor.ToolExecutor.execute_tool') as mock_execute:
               # 模拟部分工具失败
               mock_execute.side_effect = [
                   {"success": True, "score": 80},   # pylint成功
                   Exception("Tool failed"),         # bandit失败
                   {"success": True, "score": 75}    # pytest成功
               ]
               
               results = runner.audit_project(temp_project_dir)
               
               # 验证错误恢复
               assert results["success"] is True  # 总体仍成功
               assert "error_summary" in results  # 包含错误信息
               assert len(results["tool_results"]) == 2  # 只包含成功的工具

**数据库集成测试:**

.. code-block:: python

   @pytest.mark.integration 
   class TestDatabaseIntegration:
       """数据库集成测试（如果有持久化需求）"""
       
       @pytest.fixture
       def test_db(self):
           """创建测试数据库"""
           db_url = "sqlite:///:memory:"
           engine = create_engine(db_url)
           Base.metadata.create_all(engine)
           yield engine
           engine.dispose()
       
       def test_audit_result_persistence(self, test_db):
           """测试审计结果持久化"""
           # 创建测试数据
           audit_result = AuditResult(
               project_path="/test/project",
               overall_score=85.5,
               created_at=datetime.utcnow()
           )
           
           # 保存和查询
           with Session(test_db) as session:
               session.add(audit_result)
               session.commit()
               
               retrieved = session.query(AuditResult).first()
               assert retrieved.overall_score == 85.5

端到端测试
----------

CLI端到端测试
~~~~~~~~~~~~~

.. code-block:: python

   @pytest.mark.e2e
   class TestCLIEndToEnd:
       """CLI端到端测试"""
       
       def test_cli_basic_audit(self, temp_project_dir):
           """测试基本CLI审计功能"""
           # 执行CLI命令
           result = subprocess.run([
               "python", "-m", "oss_audit.cli",
               temp_project_dir,
               "--output", "/tmp/test_output"
           ], capture_output=True, text=True, timeout=300)
           
           # 验证命令执行成功
           assert result.returncode == 0
           assert "Audit completed" in result.stdout
           
           # 验证输出文件生成
           assert Path("/tmp/test_output/audit_report.html").exists()
           assert Path("/tmp/test_output/audit_results.json").exists()
       
       @pytest.mark.parametrize("output_format", ["html", "json", "xml"])
       def test_cli_different_formats(self, temp_project_dir, output_format):
           """测试不同输出格式"""
           result = subprocess.run([
               "python", "-m", "oss_audit.cli",
               temp_project_dir,
               "--format", output_format
           ], capture_output=True, text=True)
           
           assert result.returncode == 0
           # 验证特定格式的输出特征

Docker端到端测试
~~~~~~~~~~~~~~~

.. code-block:: python

   @pytest.mark.e2e
   @pytest.mark.docker
   class TestDockerEndToEnd:
       """Docker端到端测试"""
       
       @pytest.fixture(scope="class")
       def docker_client(self):
           """Docker客户端"""
           import docker
           return docker.from_env()
       
       def test_docker_basic_audit(self, docker_client, temp_project_dir):
           """测试Docker基本审计"""
           # 构建镜像
           image = docker_client.images.build(
               path=".",
               tag="oss-audit:test"
           )[0]
           
           try:
               # 运行容器
               container = docker_client.containers.run(
                   image.id,
                   [temp_project_dir],
                   volumes={temp_project_dir: {"bind": "/workspace", "mode": "ro"}},
                   detach=True
               )
               
               # 等待完成
               result = container.wait(timeout=300)
               logs = container.logs().decode('utf-8')
               
               # 验证结果
               assert result["StatusCode"] == 0
               assert "Audit completed" in logs
               
           finally:
               # 清理
               container.remove(force=True)
               docker_client.images.remove(image.id, force=True)

性能测试
--------

性能基线测试
~~~~~~~~~~~~

.. code-block:: python

   @pytest.mark.performance
   class TestPerformance:
       """性能测试"""
       
       def test_large_project_performance(self):
           """测试大型项目性能"""
           large_project = create_large_test_project(
               files_count=1000,
               avg_file_size=500  # 行
           )
           
           start_time = time.time()
           runner = AuditRunner()
           
           # 执行审计
           results = runner.audit_project(large_project)
           
           execution_time = time.time() - start_time
           
           # 性能断言
           assert execution_time < 300  # 5分钟内完成
           assert results["success"] is True
           
           # 记录性能指标
           pytest.performance_metrics = {
               "execution_time": execution_time,
               "files_processed": 1000,
               "throughput": 1000 / execution_time
           }
       
       def test_concurrent_audits(self):
           """测试并发审计性能"""
           projects = [create_test_project(f"project_{i}") for i in range(5)]
           
           start_time = time.time()
           
           # 并发执行审计
           with ThreadPoolExecutor(max_workers=5) as executor:
               futures = [
                   executor.submit(AuditRunner().audit_project, project)
                   for project in projects
               ]
               
               results = [future.result() for future in futures]
           
           total_time = time.time() - start_time
           
           # 验证并发效果
           assert all(r["success"] for r in results)
           assert total_time < 600  # 10分钟内完成5个项目

内存使用测试
~~~~~~~~~~~~

.. code-block:: python

   import psutil
   import os
   
   
   def test_memory_usage():
       """测试内存使用情况"""
       process = psutil.Process(os.getpid())
       initial_memory = process.memory_info().rss
       
       # 执行内存密集型操作
       runner = AuditRunner()
       results = runner.audit_project("large_project")
       
       peak_memory = process.memory_info().rss
       memory_increase = (peak_memory - initial_memory) / 1024 / 1024  # MB
       
       # 内存使用应该合理
       assert memory_increase < 500  # 小于500MB增长
       assert results["success"] is True

测试数据管理
------------

测试固件(Fixtures)
~~~~~~~~~~~~~~~~~

.. code-block:: python

   @pytest.fixture(scope="session")
   def test_projects_root(tmp_path_factory):
       """会话级测试项目根目录"""
       return tmp_path_factory.mktemp("test_projects")
   
   @pytest.fixture
   def python_web_project(test_projects_root):
       """Python Web项目固件"""
       project_dir = test_projects_root / "python_web"
       project_dir.mkdir()
       
       # 创建Flask项目结构
       create_flask_project_structure(project_dir)
       return str(project_dir)
   
   @pytest.fixture  
   def javascript_spa_project(test_projects_root):
       """JavaScript SPA项目固件"""
       project_dir = test_projects_root / "js_spa"
       project_dir.mkdir()
       
       # 创建React项目结构
       create_react_project_structure(project_dir)
       return str(project_dir)
   
   def create_flask_project_structure(project_dir: Path):
       """创建Flask项目结构"""
       # 创建目录
       (project_dir / "app").mkdir()
       (project_dir / "tests").mkdir()
       
       # 创建文件
       (project_dir / "app" / "__init__.py").write_text(
           "from flask import Flask\napp = Flask(__name__)"
       )
       (project_dir / "app" / "routes.py").write_text(
           "@app.route('/')\ndef index():\n    return 'Hello World'"
       )
       (project_dir / "requirements.txt").write_text("flask==2.0.0")
       (project_dir / "setup.py").write_text("from setuptools import setup")

Mock数据生成
~~~~~~~~~~~~

.. code-block:: python

   class TestDataGenerator:
       """测试数据生成器"""
       
       @staticmethod
       def generate_tool_result(tool_name: str, score: float = None, 
                              issues_count: int = 0) -> Dict[str, Any]:
           """生成工具结果数据"""
           if score is None:
               score = random.uniform(60, 95)
           
           issues = [
               TestDataGenerator.generate_issue() 
               for _ in range(issues_count)
           ]
           
           return {
               "tool_name": tool_name,
               "success": True,
               "score": score,
               "issues_found": issues,
               "execution_time": random.uniform(10, 120),
               "resource_usage": {
                   "cpu_time": random.uniform(5, 60),
                   "memory_peak": random.randint(50, 500)
               }
           }
       
       @staticmethod  
       def generate_issue(severity: str = None) -> Dict[str, Any]:
           """生成问题数据"""
           if severity is None:
               severity = random.choice(["low", "medium", "high", "critical"])
           
           return {
               "category": random.choice(["security", "quality", "performance"]),
               "severity": severity,
               "message": f"Test issue message for {severity} severity",
               "file_path": f"src/test_file_{random.randint(1, 100)}.py",
               "line_number": random.randint(1, 1000),
               "rule_id": f"TEST_{random.randint(100, 999)}"
           }

测试环境配置
------------

CI/CD测试配置
~~~~~~~~~~~~~

**GitHub Actions配置** (``.github/workflows/test.yml``):

.. code-block:: yaml

   name: Tests
   
   on: [push, pull_request]
   
   jobs:
     test:
       runs-on: ubuntu-latest
       strategy:
         matrix:
           python-version: [3.9, 3.10, 3.11]
   
       steps:
       - uses: actions/checkout@v3
       
       - name: Set up Python ${{ matrix.python-version }}
         uses: actions/setup-python@v4
         with:
           python-version: ${{ matrix.python-version }}
       
       - name: Cache dependencies
         uses: actions/cache@v3
         with:
           path: ~/.cache/pip
           key: ${{ runner.os }}-pip-${{ hashFiles('requirements-dev.txt') }}
       
       - name: Install dependencies
         run: |
           pip install -r requirements-dev.txt
           pip install -e .
       
       - name: Run unit tests
         run: pytest tests/unit -v --cov=src/oss_audit
       
       - name: Run integration tests
         run: pytest tests/integration -v
       
       - name: Upload coverage
         uses: codecov/codecov-action@v3
         if: matrix.python-version == '3.11'

Docker测试环境
~~~~~~~~~~~~~~

**测试用Docker Compose** (``docker-compose.test.yml``):

.. code-block:: yaml

   version: '3.8'
   
   services:
     test-runner:
       build:
         context: .
         dockerfile: Dockerfile.test
       volumes:
         - .:/app
         - /var/run/docker.sock:/var/run/docker.sock
       environment:
         - PYTHONPATH=/app/src
         - OSS_AUDIT_LOG_LEVEL=DEBUG
       command: |
         sh -c "
           pytest tests/unit -v &&
           pytest tests/integration -v --maxfail=5 &&
           pytest tests/e2e -v -x
         "
     
     redis-cache:
       image: redis:alpine
       ports:
         - "6379:6379"
     
     test-database:
       image: postgres:13
       environment:
         POSTGRES_DB: oss_audit_test
         POSTGRES_PASSWORD: test_password
       ports:
         - "5432:5432"

测试最佳实践
------------

测试编写原则
~~~~~~~~~~~~

**FIRST原则:**

- **Fast (快速)**: 单元测试应该快速执行
- **Independent (独立)**: 测试之间不应相互依赖
- **Repeatable (可重复)**: 在任何环境中都能重复执行
- **Self-Validating (自验证)**: 测试结果明确(通过/失败)
- **Timely (及时)**: 与生产代码同时编写

**测试命名规范:**

.. code-block:: python

   def test_should_return_python_when_setup_py_exists():
       """测试：当存在setup.py文件时应该返回Python语言"""
       pass
   
   def test_should_raise_exception_when_project_path_invalid():
       """测试：当项目路径无效时应该抛出异常"""  
       pass
   
   def test_should_adapt_weights_when_web_application_detected():
       """测试：当检测到Web应用时应该调整权重"""
       pass

**测试结构模式 (AAA):**

.. code-block:: python

   def test_project_detection_with_multiple_languages(self):
       """测试多语言项目检测"""
       
       # Arrange (准备)
       detector = ProjectDetector()
       project_files = {
           "backend/setup.py": "# Python backend",
           "frontend/package.json": "# JavaScript frontend", 
           "mobile/build.gradle": "# Java mobile"
       }
       
       # Act (执行)
       with mock_file_system(project_files):
           result = detector.detect_project("/test/project")
       
       # Assert (验证)
       assert result.structure_type == StructureType.MONOREPO
       assert "python" in result.language_distribution
       assert "javascript" in result.language_distribution
       assert "java" in result.language_distribution

代码覆盖率
~~~~~~~~~~

**覆盖率目标:**

.. code-block:: python

   # pytest.ini 中的覆盖率配置
   [tool:pytest]
   addopts = 
       --cov=src/oss_audit
       --cov-branch          # 分支覆盖率
       --cov-fail-under=80   # 最低80%覆盖率
       --cov-report=term-missing
       --cov-report=html
       --cov-report=xml      # CI/CD集成

**覆盖率报告解读:**

.. code-block::

   Name                                 Stmts   Miss  Cover   Missing
   ------------------------------------------------------------------
   src/oss_audit/__init__.py               4      0   100%
   src/oss_audit/core/audit_runner.py   156     12    92%   45-48, 67
   src/oss_audit/core/project_detector.py 89      8    91%   112-115
   src/oss_audit/agents/decision_agent.py 67      5    93%   89-92
   ------------------------------------------------------------------
   TOTAL                                 642     51    92%

**提高覆盖率策略:**

.. code-block:: python

   # 识别未覆盖代码
   pytest --cov=src --cov-report=html
   # 查看 htmlcov/index.html 找到未覆盖的行
   
   # 添加针对性测试
   def test_edge_case_that_was_missed():
       """测试之前遗漏的边界情况"""
       pass
   
   # 使用覆盖率排除标记
   def _internal_helper():  # pragma: no cover
       """内部辅助函数，不需要测试覆盖"""
       pass

测试调试和故障排除
----------------

调试技巧
~~~~~~~~

**使用pytest调试标志:**

.. code-block:: bash

   # 详细输出
   pytest -v
   
   # 显示print语句输出
   pytest -s
   
   # 遇到第一个失败就停止
   pytest -x
   
   # 显示最慢的10个测试
   pytest --durations=10
   
   # 运行特定测试
   pytest tests/test_project_detector.py::TestProjectDetector::test_detect_python
   
   # 使用pdb调试器
   pytest --pdb

**日志调试:**

.. code-block:: python

   import logging
   
   def test_with_logging(caplog):
       """使用日志调试测试"""
       with caplog.at_level(logging.DEBUG):
           # 执行被测试的代码
           detector = ProjectDetector()
           result = detector.detect_project("/test/path")
           
           # 检查日志输出
           assert "Detecting project language" in caplog.text
           assert caplog.records[0].levelname == "DEBUG"

常见问题解决
~~~~~~~~~~~~

**测试间状态污染:**

.. code-block:: python

   # 问题：全局状态影响测试
   class TestWithGlobalState:
       def test_first(self):
           global_cache.clear()  # 清理全局状态
           # ... 测试逻辑
       
       def test_second(self):
           global_cache.clear()  # 每个测试都清理
           # ... 测试逻辑
   
   # 解决方案：使用fixture自动清理
   @pytest.fixture(autouse=True)
   def clean_global_state():
       """自动清理全局状态"""
       global_cache.clear()
       yield
       global_cache.clear()

**异步代码测试:**

.. code-block:: python

   import pytest
   import asyncio
   
   @pytest.mark.asyncio
   async def test_async_function():
       """测试异步函数"""
       result = await some_async_function()
       assert result == expected_value
   
   # 或使用同步方式
   def test_async_function_sync():
       """同步方式测试异步函数"""
       loop = asyncio.get_event_loop()
       result = loop.run_until_complete(some_async_function())
       assert result == expected_value

**Mock失效问题:**

.. code-block:: python

   # 问题：Mock路径不正确
   # 错误的Mock路径
   @patch('some_module.function')  # 如果在被测试模块中import了function
   
   # 正确的Mock路径
   @patch('module_under_test.function')  # 应该Mock导入的位置
   
   def test_with_correct_mock():
       pass

测试报告和分析
--------------

测试报告生成
~~~~~~~~~~~~

.. code-block:: bash

   # 生成HTML测试报告
   pytest --html=reports/test_report.html --self-contained-html
   
   # 生成JUnit XML报告（CI/CD集成）
   pytest --junitxml=reports/junit.xml
   
   # 生成覆盖率报告
   pytest --cov=src --cov-report=html:reports/coverage

**自定义测试报告:**

.. code-block:: python

   # conftest.py
   def pytest_html_report_title(report):
       """自定义HTML报告标题"""
       report.title = "OSS Audit 2.0 Test Report"
   
   def pytest_html_results_summary(prefix, summary, postfix):
       """自定义测试摘要"""
       prefix.extend([html.h2("Test Environment")])
       prefix.extend([html.p(f"Python Version: {sys.version}")])

持续测试改进
~~~~~~~~~~~~

**测试指标监控:**

.. code-block:: python

   class TestMetrics:
       """测试指标收集器"""
       
       def __init__(self):
           self.metrics = {
               'total_tests': 0,
               'passed_tests': 0,
               'failed_tests': 0,
               'execution_time': 0,
               'coverage_percentage': 0
           }
       
       def collect_metrics(self, test_session):
           """收集测试指标"""
           self.metrics['total_tests'] = test_session.testscollected
           self.metrics['passed_tests'] = test_session.testspassed
           self.metrics['failed_tests'] = test_session.testsfailed
           
       def generate_trend_report(self):
           """生成趋势报告"""
           # 与历史数据对比，识别测试质量趋势
           pass

这个测试框架确保了OSS Audit 2.0的高质量和可靠性，为持续集成和发布提供了坚实的保障。