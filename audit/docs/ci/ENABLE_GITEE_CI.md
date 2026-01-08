# 启用 Gitee CI（Gitee Go）指南 / Enable Gitee CI (Gitee Go)

本指南提供在 Gitee 上为本项目启用最小化 CI 的步骤与建议，避免侵入式改动（仓库中仅提供 docs 模板，不提交流水线配置）。

## 推荐流程
- 新建流水线（Gitee Go 控制台）
- 选择 Linux 运行器或 Docker 运行器（内置 `python:3.11` 更佳）
- 复制 `docs/ci/gitee-go-example.yml` 内容到“自定义 YAML”区域，视实际运行器语法做小幅调整
- 保存并手动触发一次，确认能成功安装依赖与运行 `make quick-check`

## 变量与缓存
- Pipeline 变量（可选）
  - `OPENAI_API_KEY` / `GEMINI_API_KEY`（启用 AI 能力时需要，并在安装时加上 `.[ai]`）
- 缓存
  - 启用 Pip 缓存目录：`~/.cache/pip` 以加速后续构建

## 任务建议
- Lint & Test
  - `python -m pip install --upgrade pip`
  - `pip install -e .[dev]`（AI 需改为 `.[dev,ai]`）
  - `make quick-check`（包含格式化、静态检查、测试）
  - 工件：`htmlcov/**`（覆盖率 HTML）
- Build Package（可选）
  - `python -m pip install --upgrade pip build`
  - `python -m build`
  - 工件：`dist/**`

## Docker 与权限
- 若需容器化工具链（可选），确保运行器具备 Docker 权限；默认流水线不调用 Docker，仅跑 Python 任务。
- 本仓库的 `docker-compose.yml` 已简化为单服务，结合 `scripts/run_audit.*` 可另建独立流水线；建议待项目稳定后再启用。

## 常见问题
- 运行器镜像差异：如 YAML 字段与贵司运行器不符，请在控制台使用可视化步骤改造相同 Shell 命令。
- 网络与私有源：若需内网镜像/代理，请在第一步注入自有 `pip.conf` 或环境变量。
- 依赖最小化：项目运行时仅需 `PyYAML`、`requests`；测试/质量依赖在 `.[dev]`，AI 依赖在 `.[ai]`。

---
English (Summary)
- Create a new Gitee Go pipeline; use a Linux runner (Docker-enabled preferred).
- Copy `docs/ci/gitee-go-example.yml` and adapt to your runner syntax.
- Set `OPENAI_API_KEY` / `GEMINI_API_KEY` if enabling AI and install with `pip install -e .[dev,ai]`.
- Cache `~/.cache/pip`; publish artifacts `htmlcov/**` and optionally `dist/**`.

