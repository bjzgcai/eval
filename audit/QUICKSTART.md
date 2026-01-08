# OSS Audit 2.0 快速开始指南

## 🚀 30秒开始使用

### Docker方式（推荐）

真正的"一行命令"分析，预装所有工具：

```bash
# Linux/Mac
./scripts/run_audit.sh

# Windows
.\scripts\run_audit.ps1
```

### 本地方式

```bash
# 需要手动安装各语言工具
python main.py .
```

## 📝 详细步骤

### 1. 准备环境

#### 选项A：Docker（推荐）
- 安装 [Docker Desktop](https://docs.docker.com/get-docker/)
- 无需安装Python、Node.js、Java等环境
- 真正的零配置

#### 选项B：本地运行
```bash
# 安装Python 3.8+
python --version

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
pip install -e .
```

### 2. 运行分析

#### Docker方式
```bash
# 分析当前目录
./scripts/run_audit.sh

# 分析指定项目
./scripts/run_audit.sh ./my-project

# 自定义输出目录
./scripts/run_audit.sh ./my-project ./custom-reports

# 重新构建镜像（获取最新工具）
./scripts/run_audit.sh --build ./my-project

# 启用高级服务（SonarQube等）
./scripts/run_audit.sh --advanced ./my-project
```

#### 本地方式
```bash
# 基本使用
python main.py ./my-project

# 指定输出目录
python main.py ./my-project ./reports

# 查看帮助
python main.py --help
```

### 3. 查看结果

分析完成后，报告将保存在：
```
reports/
└── 项目名/
    ├── 项目名_audit_report.html    # 📊 主报告（在浏览器中打开）
    ├── 项目名_audit_report.json    # 📋 详细数据
    └── dimensions/                  # 📁 各维度详细分析
        ├── dimension_1_代码结构与可维护性.json
        └── ...
```

## 🎯 支持的项目类型

| 语言 | 文件类型 | 支持工具 |
|------|----------|----------|
| Python | `.py` | pylint, mypy, bandit, pytest |
| JavaScript | `.js` | eslint, prettier, jest |
| TypeScript | `.ts` | tsc, eslint, jest |
| Java | `.java` | checkstyle, spotbugs |
| Go | `.go` | golint, gosec |
| Rust | `.rs` | clippy, cargo-audit |
| C++ | `.cpp`, `.hpp` | cppcheck, clang-tidy |

## 🔧 配置AI分析（可选）

如果需要AI增强分析：

```bash
# 1. 复制配置模板
cp config.yaml.example config.yaml

# 2. 编辑配置文件，填入API密钥
# Windows: notepad config.yaml
# Linux/Mac: nano config.yaml

# 3. 或使用环境变量
export OPENAI_API_KEY="your-key"
export GEMINI_API_KEY="your-key"
```

## ❓ 常见问题

### Q: Docker镜像太大怎么办？
A: 首次下载需要时间，后续使用会很快。镜像包含所有语言环境和工具。

### Q: 没有Docker可以用吗？
A: 可以，但需要手动安装各语言的分析工具，无法做到"零配置"。

### Q: 支持哪些项目结构？
A: 支持单项目、多项目和Monorepo结构，自动识别。

### Q: 如何获取帮助？
```bash
# Docker方式
./scripts/run_audit.sh --help

# 本地方式  
python main.py --help
```

## 🚀 立即开始

选择一种方式开始使用：

1. **Docker方式**（推荐）：
   ```bash
   ./scripts/run_audit.sh ./your-project
   ```

2. **本地方式**：
   ```bash
   python main.py ./your-project
   ```

3. **使用Makefile**：
   ```bash
   make docker-audit
   ```

享受智能的开源软件成熟度评估体验！ 🎉