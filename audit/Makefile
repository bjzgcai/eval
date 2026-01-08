.PHONY: help install install-dev test test-cov lint format clean build docs venv

# 检测操作系统
ifeq ($(OS),Windows_NT)
    PYTHON := python
    VENV_ACTIVATE := venv\Scripts\activate
    RM := rmdir /s /q
    FIND := dir /s /b
    PYTHON_FILES := *.py
else
    PYTHON := python3
    VENV_ACTIVATE := source venv/bin/activate
    RM := rm -rf
    FIND := find . -name
    PYTHON_FILES := *.py
endif

# 默认目标
help:
	@echo "OSS Audit 开发命令:"
	@echo "  venv         - 创建虚拟环境"
	@echo "  install      - 安装生产依赖"
	@echo "  install-dev  - 安装开发依赖"
	@echo "  test         - 运行测试"
	@echo "  test-cov     - 运行测试并生成覆盖率报告"
	@echo "  lint         - 运行代码质量检查"
	@echo "  format       - 格式化代码"
	@echo "  clean        - 清理临时文件"
	@echo "  build        - 构建包"
	@echo "  docs         - 构建文档"
	@echo "  audit        - 运行项目自审计"
	@echo "  setup-dev    - 完整开发环境设置"
	@echo ""
	@echo "Docker相关命令:"
	@echo "  docker-build     - 构建Docker镜像"
	@echo "  docker-audit     - 使用Docker运行项目审计"
	@echo "  docker-audit-advanced - 使用Docker运行项目审计（包含高级服务）"
	@echo "  docker-clean     - 清理Docker镜像和容器"

# 创建虚拟环境
venv:
	@echo "创建虚拟环境..."
	$(PYTHON) -m venv venv
	@echo "虚拟环境创建完成!"
	@echo "激活虚拟环境:"
ifeq ($(OS),Windows_NT)
	@echo "  venv\\Scripts\\activate"
else
	@echo "  source venv/bin/activate"
endif

# 安装依赖
install: venv
	@echo "安装生产依赖..."
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -e .

install-dev: venv
	@echo "安装开发依赖..."
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements-dev.txt
	$(PYTHON) -m pip install -e .

# 测试
test:
	@echo "运行测试..."
	$(PYTHON) -m pytest tests/ -v

test-cov:
	@echo "运行测试并生成覆盖率报告..."
	$(PYTHON) -m pytest tests/ -v --cov=src/oss_audit --cov-report=html --cov-report=term-missing

# 代码质量检查
lint:
	@echo "运行 pylint..."
	$(PYTHON) -m pylint src/ oss_audit.py
	@echo "运行 flake8..."
	$(PYTHON) -m flake8 src/ oss_audit.py
	@echo "运行 mypy..."
	$(PYTHON) -m mypy src/
	@echo "运行 bandit..."
	$(PYTHON) -m bandit -r src/
	@echo "运行 safety..."
	$(PYTHON) -m safety check

# 代码格式化
format:
	@echo "运行 black..."
	$(PYTHON) -m black src/ oss_audit.py tests/
	@echo "运行 isort..."
	$(PYTHON) -m isort src/ oss_audit.py tests/

# 清理
clean:
	@echo "清理临时文件..."
ifeq ($(OS),Windows_NT)
	@if exist build rmdir /s /q build
	@if exist dist rmdir /s /q dist
	@if exist *.egg-info rmdir /s /q *.egg-info
	@if exist htmlcov rmdir /s /q htmlcov
	@if exist .coverage del .coverage
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@if exist .mypy_cache rmdir /s /q .mypy_cache
	@for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
	@for /r . %%f in (*.pyc) do @if exist "%%f" del "%%f"
else
	$(RM) build/
	$(RM) dist/
	$(RM) *.egg-info/
	$(RM) htmlcov/
	$(RM) .coverage
	$(RM) .pytest_cache/
	$(RM) .mypy_cache/
	$(FIND) __pycache__ -type d -delete
	$(FIND) "*.pyc" -delete
endif

# 构建
build: clean
	@echo "构建包..."
	$(PYTHON) -m build

# 文档
docs:
	@echo "构建文档..."
	$(PYTHON) -m mkdocs build

# 项目自审计
audit:
	@echo "运行项目自审计..."
	$(PYTHON) oss_audit.py .

# 开发环境设置
setup-dev: install-dev
	@echo "设置 pre-commit hooks..."
	$(PYTHON) -m pre_commit install
	@echo "开发环境设置完成!"

# 快速检查
quick-check: format lint test

# 完整检查
full-check: clean format lint test-cov build

# Docker相关
docker-build:
	@echo "构建Docker镜像..."
	docker build -t oss-audit:2.0 .

docker-audit:
	@echo "使用Docker运行项目审计..."
ifeq ($(OS),Windows_NT)
	powershell -ExecutionPolicy Bypass -File scripts/run_audit.ps1
else
	./scripts/run_audit.sh
endif

docker-audit-advanced:
	@echo "使用Docker运行项目审计（包含高级服务）..."
ifeq ($(OS),Windows_NT)
	powershell -ExecutionPolicy Bypass -File scripts/run_audit.ps1 -Advanced
else
	./scripts/run_audit.sh --advanced
endif

docker-clean:
	@echo "清理Docker镜像和容器..."
	docker system prune -f
	docker rmi oss-audit:2.0 2>/dev/null || true

# 发布准备
release-prep: clean format lint test-cov build
	@echo "发布准备完成!"

# 使用脚本
setup-script:
	@echo "使用Python脚本设置环境..."
	$(PYTHON) scripts/setup_dev_env.py

install-script:
	@echo "使用Python脚本安装依赖..."
	$(PYTHON) scripts/install_deps.py --env dev

test-script:
	@echo "使用Python脚本运行测试..."
	$(PYTHON) scripts/run_tests.py
