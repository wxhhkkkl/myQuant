<!--
  Sync Impact Report
  ==================
  Version change: 0.0.0 → 1.0.0 (initial constitution)
  Modified principles: N/A (all new)
  Added sections:
    - I. Think Before Coding
    - II. Simplicity First
    - III. Test-Driven Development
    - IV. Focused Changes
    - V. Goal-Driven & Verifiable Results
    - Section: Code Quality Standards
    - Section: Development Workflow
    - Governance
  Removed sections: None
  Templates requiring updates:
    - .specify/templates/plan-template.md ✅ (Constitution Check gate aligns with principles)
    - .specify/templates/spec-template.md ✅ (already aligns)
    - .specify/templates/tasks-template.md ✅ (updated: changed "Tests are OPTIONAL" to "MANDATORY")
    - CLAUDE.md ✅ (runtime guidance, no conflict)
  Follow-up TODOs: None
-->

# myQuant Project Constitution

## Core Principles

### I. Think Before Coding

**先思考，再编码。** 在写任何代码之前，必须先理清思路：要解决什么问题、有哪些可行方案、各自的权衡是什么。遇到不明确的
需求，必须主动提出问题而非盲目猜测实现。每项任务开始前，用简短的文字确认目标与范围，避免方向偏差。

**Why**: 代码是思考的产物，不是思考的替代品。在没有想清楚的情况下编码，产出的代码往往需要大量返工。

### II. Simplicity First

**简单至上。** 代码必须通俗易懂——命名自解释、逻辑直白、结构扁平。拒绝过度抽象和不必要的设计模式。当选择有三行
重复代码还是引入一个间接层时，选三行重复代码。一个看了就能改的新手是最成功的设计。

**Why**: 简单代码更少 Bug、更容易维护、更方便扩展。复杂是量化系统的敌人——策略逻辑、数据管线、交易执行每一步都可能
引入错误，唯有保持简单才能让系统可信。

### III. Test-Driven Development (NON-NEGOTIABLE)

**测试驱动开发。** 每个功能模块在实现前必须先写测试用例。遵循 Red-Green-Refactor 循环：先写失败的测试 → 用最少代码
让测试通过 → 重构优化。测试不是可选项，是编码流程的强制步骤。

- 单元测试：覆盖所有核心业务逻辑（策略信号计算、数据处理、指标运算）
- 集成测试：覆盖数据管线（数据源→存储→计算→输出）
- 回测验证：量化模型的结果必须与手动计算结果一致

**Why**: 量化系统处理真金白银，一个计算错误可能造成实质损失。TDD 不是风格偏好，是风险控制。

### IV. Focused Changes

**聚焦变更，不做顺手优化。** 每次代码变更只做一件事——修复一个 Bug、实现一个功能、或完成一个重构。严格禁止在修复
Bug 时顺便重构无关代码，在实现功能时顺手优化不相干的模块。PR / commit 的 diff 应该只讲一个故事。

**Why**: 混合变更模糊了意图，代码审查困难，排查问题时难以追溯 root cause。聚焦让每一步都可回退、可审计。

### V. Goal-Driven & Verifiable Results

**每一步都是目标驱动，结果要可验证。** 任务开始前定义清晰的验收条件（Acceptance Criteria），完成后用可观测的方式
确认目标达成。无论是新功能还是 Bug 修复，必须有可量化的验证方式：测试通过、数据准确、页面可操作。

**Why**: 没有验证的工作只是"看起来完成了"。在量化工具中，"收益率为 12.5%" 比 "看起来差不多" 重要得多。

## Code Quality Standards

- **可读性优先**: 代码是写给人看的。使用有意义的命名，函数短小精悍（不超过 50 行为佳），避免深层嵌套。
- **消灭重复**: 同一逻辑出现第三次时才考虑抽取，但不为"未来的复用"提前抽象。
- **数据即真理**: 量化系统中数据准确性高于一切。任何数据转换必须有明确的来源和计算逻辑可追溯。
- **先纠错，后推进**: 发现 Bug 时，立即修复或记录为待办项，不允许带着已知问题继续开发。

## Development Workflow

### 任务执行流程

1. **明确目标**: 用一句话描述本次变更的目的
2. **写出测试**: 先写测试用例（TDD），确认测试在当前代码上失败
3. **最小实现**: 用最少的代码让测试通过
4. **验证结果**: 运行全量测试 + 手动验证关键路径
5. **提交变更**: 单次 commit 聚焦同一主题

### 提交规范

- `feat:` — 新功能
- `fix:` — Bug 修复
- `refactor:` — 重构（无功能变化）
- `test:` — 测试相关
- `docs:` — 文档变更
- `chore:` — 构建/工具变更

### 质量门禁

- 所有测试必须通过才能合并代码
- 核心计算逻辑必须有单元测试覆盖
- 量化模型变更必须附带回测结果对比
- 禁止提交包含已知 Bug 的代码

## Governance

本宪法是 myQuant 项目开发的最高准则，所有开发活动、代码审查和技术决策必须以本宪法为基准。

- **修正程序**: 宪法的修改需要记录修正原因、影响范围，并更新版本号。
- **版本规则**: 采用语义化版本 MAJOR.MINOR.PATCH。删除或重新定义原则为 MAJOR 升级；新增原则或显著扩展为 MINOR 升级；
  措辞优化、修正笔误为 PATCH 升级。
- **合规审查**: 每次代码审查必须确认变更符合宪法原则。违反 NON-NEGOTIABLE 原则的代码不得合并。

**Version**: 1.0.0 | **Ratified**: 2026-05-03 | **Last Amended**: 2026-05-03
