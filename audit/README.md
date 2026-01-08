# OSS Audit 2.0 - 开源软件成熟度评估工具

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)](https://gitee.com/oss-audit/oss-audit)

智能评估多语言开源项目的14个关键维度，支持零配置运行、容器化工具执行和AI增强分析。

## ✨ 核心特性

- 🔍 **14维度全面评估** - 代码质量、安全性、测试覆盖、文档完整性等
- 🌐 **多语言支持** - Python、JavaScript、TypeScript、Java、Go、Rust、C++
- 🐳 **容器化执行** - 预装工具链，一键启动，环境隔离
- 🤖 **AI智能分析** - 可选的OpenAI/Gemini增强分析
- 📊 **可视化报告** - HTML总览 + JSON详细数据

## 🚀 快速开始

### 一键启动（推荐）
```bash
# 零配置运行 - 自动构建镜像、启动容器、执行分析
python main.py /path/to/your/project

# 程序会自动：
# 1. 检测Docker环境
# 2. 构建工具镜像（首次运行）
# 3. 启动工具服务容器
# 4. 执行项目分析
```

### 手动方式
```bash
# 手动构建和启动（可选）
docker-compose up -d oss-audit-tools
python main.py /path/to/your/project

# 本地工具方式
pip install -e .
oss-audit /path/to/your/project
```

## 🐳 Docker架构

**双模式统一架构**: 主程序在宿主机运行，工具通过容器执行，实现开发友好和环境隔离的平衡。

### 自动化流程
程序启动时会自动：
1. **检测容器引擎** - 支持Docker、Podman、nerdctl
2. **构建工具镜像** - 首次运行时自动构建1.09GB优化镜像
3. **启动服务容器** - 创建并启动长时间运行的工具服务容器
4. **项目分析** - 通过容器执行工具，结果返回宿主机

### 架构特点
- **零手动操作** - 无需手动构建镜像或启动容器
- **服务化设计** - 长时间运行的工具服务容器，避免重复启动开销
- **智能回退** - 容器不可用时自动回退到本地工具

### 预装工具
- **Python**: pylint, flake8, bandit, black, pytest
- **JavaScript/TypeScript**: eslint, typescript
- **通用安全**: semgrep

### AI配置（可选）
```bash
# 环境变量方式
export OPENAI_API_KEY="your-key"
export GEMINI_API_KEY="your-key"

# 或编辑 config.yaml
cp config.yaml.example config.yaml
```

## 📋 评估维度

OSS Audit 2.0 评估 14 个关键维度：

| 维度 | 内容 | 工具示例 |
|------|------|----------|
| 代码结构与可维护性 | 代码组织、命名规范、复杂度 | pylint, eslint |
| 测试覆盖与质量保障 | 测试完整性、覆盖率 | pytest, jest |
| 构建与工程可重复性 | 构建自动化、环境一致性 | black, prettier |
| 依赖与许可证合规 | 依赖管理、许可证兼容性 | safety, npm-audit |
| 安全性与敏感信息防护 | 安全漏洞、敏感信息检查 | bandit, semgrep |
| CI/CD 自动化保障 | 持续集成配置 | 配置文件检查 |
| 使用文档与复现性 | 文档完整性 | 文档文件检查 |
| 接口与平台兼容性 | API规范、跨平台支持 | 静态分析 |
| 协作流程与代码规范 | 贡献指南、代码规范 | 配置检查 |
| 开源协议与法律合规 | 开源协议、法律合规性 | 许可证检查 |
| 社区治理与贡献机制 | 社区治理、维护者信息 | 治理文件检查 |
| 舆情与风险监控 | 风险控制、监控策略 | 策略文件检查 |
| 数据与算法合规审核 | 数据处理规范 | 合规性检查 |
| IP（知识产权） | 专利风险、商标使用 | 知识产权检查 |

## 📊 输出报告

审计完成后生成：
- **HTML报告**: 可视化总览，包含得分、建议和详细分析
- **JSON数据**: 详细的原始数据，便于程序化处理
- **推荐报告**: 智能改进建议和实施路径

报告位置：`reports/<项目名>/`

## 🛠️ 开发与贡献

```bash
# 环境设置
pip install -r requirements-dev.txt
pip install -e .

# 运行测试
pytest tests/ -v

# 代码质量检查
make lint
make format
```

## 🤝 相关链接

- [问题反馈](https://gitee.com/oss-audit/oss-audit/issues)
- [贡献指南](CONTRIBUTING.md)
- [变更日志](CHANGELOG.md)

## 📄 许可证

MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情
