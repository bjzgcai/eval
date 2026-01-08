# PR-0001: Typed Models & Reporting Refactor / 模型与报告重构（草案）

## Summary / 摘要
- Introduce typed domain models for plans, tool specs/results, findings, and reports.
- Modularize reporting into exporters/renderers (HTML/JSON) with a versioned schema.
- No behavior change yet; this PR only scaffolds models and reporting adapters.
- 引入审计领域模型（计划、工具规格/结果、发现、报告），并模块化报告（HTML/JSON 导出），提供版本化模式；本 PR 仅提供骨架，不改变现有行为。

## Motivation / 动机
- Improve maintainability, testability, and external consumption of reports.
- Decouple large modules (e.g., report_generator) and enable future exporters (SARIF/CycloneDX).
- 提升可维护性与可测试性，便于外部系统消费结果；解耦大文件，便于扩展导出格式。

## Scope / 范围
- Add `core/models.py` (dataclasses-based, pydantic-ready).
- Add `core/reporting/{exporters.py, renderers.py}` minimal adapters.
- Add proposal doc (this file). No integration into runtime flow yet.
- 新增模型与报告适配器文件，仅文档与骨架，不接入现有执行流。

## Non-Goals / 非目标
- Replace current `ReportGenerator` in this PR.
- Change CLI UX or introduce new dependencies.
- 本 PR 不替换现有报告生成、也不改 CLI 或新增依赖。

## Design / 设计
- Models: ToolSpec, ToolRun, Finding, AuditPlan, ReportMeta, AuditReport.
- Exporters: `export_json`, `export_html` using Jinja2 template or default.
- Schema version: `report.schema_version = "1.0.0"` to enable compatibility checks.
- 模型定义如上；导出器支持 JSON/HTML；报告包含 `schema_version`。

## Migration Plan / 迁移计划
- Phase 1 (this PR): land models + exporters; add unit tests and snapshot samples.
- Phase 2: adapt `ReportGenerator` to emit `AuditReport` and call exporters.
- Phase 3: decompose current generator into collectors/aggregators/renderers.
- 阶段化迁移：落地骨架→适配旧生成器→按组件解耦。

## Risks & Mitigations / 风险与缓解
- Divergence between old/new structures → add snapshot tests + schema contract.
- Future pydantic adoption → keep constructors compatible.
- 旧新结构偏离：用快照测试与 schema 约束；后续可平滑引入 pydantic。

## Tasks / 任务
- [ ] Add unit tests for models serialization.
- [ ] Provide sample JSON/HTML fixtures under `tests/reports/`.
- [ ] Wire optional use behind feature flag (e.g., `USE_NEW_REPORTING`).
- [ ] Document schema in `docs/`.

