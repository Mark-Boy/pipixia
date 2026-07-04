# 项目 Skills 总览

> 所有 skills 安装信息集中在此处。项目迁移时按下方说明复现。

## 📅 里程碑记录

- **2026-07-04**: 初始化项目骨架，搭建 Next.js Dashboard（含 8 个页面布局），安装 82 个 AI Skills

## 安装方式

### 首次安装（在其他电脑上复现此项目时）

在项目根目录下执行：

```bash
# 1. 克隆所有 skill 仓库
git clone --depth 1 https://github.com/mattpocock/skills.git /tmp/mp-skills
git clone --depth 1 https://github.com/OthmanAdi/planning-with-files.git /tmp/pwf
git clone --depth 1 https://github.com/anthropics/skills.git /tmp/anthro-skills
git clone --depth 1 https://github.com/laolaoshiren/claude-code-skills-zh.git /tmp/skills-zh
git clone --depth 1 https://github.com/Kevinchamplin/claude-skills.git /tmp/kc-skills
git clone --depth 1 https://github.com/TechyMT/claude-code-superpowers.git /tmp/sp

# 2. 安装 mattpocock/skills
cp -r /tmp/mp-skills/skills/* .agents/skills/

# 3. 安装 third-party skills
mkdir -p .agents/skills/third-party/{official,community,laolaoshiren,kevinchamplin,othmanadi}

# official (Anthropic 官方)
cp -r /tmp/anthro-skills/skills/webapp-testing /tmp/anthro-skills/skills/mcp-builder /tmp/anthro-skills/skills/pptx /tmp/anthro-skills/skills/skill-creator .agents/skills/third-party/official/

# othmanadi
cp -r /tmp/pwf/skills/planning-with-files .agents/skills/third-party/othmanadi/

# laolaoshiren
cp -r /tmp/skills-zh/skills/{refactor-advisor,api-tester,db-migrator,zh-readme,log-analyzer,github-actions-gen,changelog-gen,dep-auditor,security-audit} .agents/skills/third-party/laolaoshiren/

# kevinchamplin
cp -r /tmp/kc-skills/{frontend-design,lean-context,review,superteam,ux-designer} .agents/skills/third-party/kevinchamplin/

# community (TechyMT superpowers + 其他社区 skill)
cp -r /tmp/sp/skills/* .agents/skills/third-party/community/

# 4. 清理临时文件
rm -rf /tmp/mp-skills /tmp/pwf /tmp/anthro-skills /tmp/skills-zh /tmp/kc-skills /tmp/sp
```

### 从 `.agents/skills/README-INSTALL.md` 获取更详细的安装说明

详见 `.agents/skills/README-INSTALL.md`。

---

## 已安装的 Skills（共 82 个）

### 一、Matt Pocock Skills（38 个）— `.agents/skills/`

来源: [mattpocock/skills](https://github.com/mattpocock/skills) | 许可证: MIT

#### Engineering (16 个)

| Skill | 说明 | 类型 |
|-------|------|------|
| `ask-matt` | 路由到合适的 skill | User-invoked |
| `codebase-design` | 设计深层模块 | Model-invoked |
| `code-review` | 双轴代码审查 | Model-invoked |
| `diagnosing-bugs` | 系统化调试 | Model-invoked |
| `domain-modeling` | 领域模型 | Model-invoked |
| `grill-with-docs` | 调研+领域模型+ADR | User-invoked |
| `implement` | 实现功能 | - |
| `improve-codebase-architecture` | 代码库架构优化 | User-invoked |
| `prototype` | 构建原型 | Model-invoked |
| `research` | 研究调查 | Model-invoked |
| `resolving-merge-conflicts` | 合并冲突解决 | - |
| `setup-matt-pocock-skills` | 配置技能仓库 | User-invoked |
| `tdd` | 测试驱动开发 | Model-invoked |
| `to-issues` | PRD 转 Issue | User-invoked |
| `to-prd` | 生成 PRD | User-invoked |
| `triage` | Issue 分类 | User-invoked |

#### Productivity (5 个)

| Skill | 说明 | 类型 |
|-------|------|------|
| `grilling` | 无情调研循环 | Model-invoked |
| `grill-me` | 设计方案调研 | User-invoked |
| `handoff` | 交接文档 | User-invoked |
| `teach` | 分节教学 | User-invoked |
| `writing-great-skills` | 编写 skill 参考 | Model-invoked |

#### Deprecated (4 个)

`design-an-interface`, `qa`, `request-refactor-plan`, `ubiquitous-language`

#### In-Progress (7 个)

`claude-handoff`, `loop-me`, `wayfinder`, `wizard`, `writing-beats`, `writing-fragments`, `writing-shape`

#### Misc (4 个)

`git-guardrails-claude-code`, `migrate-to-shoehorn`, `scaffold-exercises`, `setup-pre-commit`

#### Personal (2 个)

`edit-article`, `obsidian-vault`

---

### 二、Third-Party Skills（44 个）— `.agents/skills/third-party/`

#### official — Anthropic 官方 Skills（4 个）

来源: [anthropics/skills](https://github.com/anthropics/skills)

| Skill | 说明 |
|-------|------|
| `webapp-testing` | Web 应用测试 |
| `mcp-builder` | MCP 协议构建器 |
| `pptx` | PPT 生成 |
| `skill-creator` | Skill 创建器 |

#### othmanadi — Othman Adi（1 个）

来源: [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files)

| Skill | 说明 |
|-------|------|
| `planning-with-files` | 基于文件的规划 |

#### laolaoshiren — 中文精选集（9 个）

来源: [laolaoshiren/claude-code-skills-zh](https://github.com/laolaoshiren/claude-code-skills-zh)

| Skill | 说明 |
|-------|------|
| `refactor-advisor` | 代码简化 / 重构建议 |
| `api-tester` | API 测试 |
| `db-migrator` | 数据库迁移 |
| `zh-readme` | 中文文档生成 |
| `log-analyzer` | 终端日志分析 |
| `github-actions-gen` | CI/CD 工作流生成 |
| `changelog-gen` | 更新日志生成 |
| `dep-auditor` | 依赖安全检查 |
| `security-audit` | 安全审计 |

#### kevinchamplin — 社区精选集（5 个）

来源: [Kevinchamplin/claude-skills](https://github.com/Kevinchamplin/claude-skills)

| Skill | 说明 |
|-------|------|
| `frontend-design` | UI/UX 前端设计 |
| `lean-context` | 上下文精简 |
| `review` | 代码审查 / 发布检查 |
| `superteam` | 多 Agent 协作 |
| `ux-designer` | UX 设计 |

#### community — 其他社区 Skill（25 个）

来源: 多个 GitHub 仓库

| Skill | 来源 | 说明 |
|-------|------|------|
| `superpowers` | TechyMT/claude-code-superpowers | 超级技能集合 |
| `repo-cartographer` | sergeylopukhov/context-cartographer | 代码库地图 |
| `playwright-scout` | 社区 | Playwright 测试探索 |
| `data-cleaner` | 社区 | 数据清洗 |
| `screenshot-qa` | 社区 | 截图质量检查 |
| `review-router` | wayne45/claude-skill-code-review-router | 审查路由 |
| `decision-log` | sananthanarayan/skilldrop | 决策日志 |
| `knowledge-base` | PleasePrompto/notebooklm-skill | 知识库 |
| `retro-bot` | cometogather/retro-bot | 复盘机器人 |
| `async-concurrency` | TechyMT/superpowers | 异步并发 |
| `build-tool-factory` | TechyMT/superpowers | 构建工具工厂 |
| `creating-skills` | TechyMT/superpowers | Skill 创建 |
| `domain-model` | TechyMT/superpowers | 领域模型 |
| `error-handling` | TechyMT/superpowers | 错误处理 |
| `hot-paths` | TechyMT/superpowers | 热路径优化 |
| `module-organisation` | TechyMT/superpowers | 模块组织 |
| `naming-conventions` | TechyMT/superpowers | 命名规范 |
| `observability` | TechyMT/superpowers | 可观测性 |
| `permission-system` | TechyMT/superpowers | 权限系统 |
| `skill-and-command-dispatch` | TechyMT/superpowers | 命令分发 |
| `state-management` | TechyMT/superpowers | 状态管理 |
| `system-boundaries` | TechyMT/superpowers | 系统边界 |
| `task-system` | TechyMT/superpowers | 任务系统 |
| `tool-definition` | TechyMT/superpowers | 工具定义 |
| `types-and-interfaces` | TechyMT/superpowers | 类型与接口 |

---

## 未找到的 Skill（跳过）

以下 skill 在 GitHub 上未找到匹配的公开仓库，已跳过：

| Skill | 原因 |
|-------|------|
| `Ralph Loop` | 未找到公开仓库 |
| `Nightly Runner` | 未找到公开仓库 |
| `PR Narrator` | 未找到公开仓库 |
| `Issue Gardener` | 未找到公开仓库 |
| `Onboarding Map` | 未找到公开仓库 |
| `Prompt Harness` | 未找到公开仓库 |
| `Superpowers` | 原版 TechyMT/claude-code-superpowers 已安装为社区版 |

---

## 使用方式

在 pi 中通过 `/skill:<name>` 调用，例如：

```
/skill:tdd
/skill:grill-me
/skill:code-review
/skill:planning-with-files
/skill:mcp-builder
/skill:pptx
```

首次使用前建议运行 `/setup-matt-pocock-skills` 配置 Issue Tracker。
