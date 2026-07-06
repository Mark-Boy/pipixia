# Skills 索引

> 批量下载自多个优质 Skill 仓库，共 46 个 Skill

## 来源分布

| 来源 | 数量 | 仓库 |
|------|------|------|
| Anthropic 官方 | 12 | `github.com/anthropics/skills` |
| 中文精选 | 19 | `github.com/laolaoshiren/claude-code-skills-zh` |
| 社区精选 | 8 | `github.com/Kevinchamplin/claude-skills` |
| Matt Pocock | 7 | `github.com/mattpocock/skills` |

## Skill 列表

### 🎨 设计与创意
| Skill | 来源 | 用途 |
|-------|------|------|
| `algorithmic-art` | Official | 算法艺术生成 |
| `brand-guidelines` | Official | 品牌指南遵循 |
| `canvas-design` | Official | Canvas 画布设计 |
| `frontend-design` | Multi | 前端设计 |
| `theme-factory` | Official | 主题工厂 |
| `ux-designer` | Chinese/Community | UX 设计 |

### 📄 文档与文件
| Skill | 来源 | 用途 |
|-------|------|------|
| `docx` | Official | Word 文档处理 |
| `pdf` | Official | PDF 处理 |
| `pptx` | Official | PowerPoint 生成 |
| `xlsx` | Official | Excel 处理 |
| `zh-readme` | Chinese | README 中文生成 |
| `zh-docgen` | Chinese | 文档生成 |

### 🔧 开发与工程
| Skill | 来源 | 用途 |
|-------|------|------|
| `api-tester` | Chinese | API 测试 |
| `codebase-design` | Matt | 代码库设计 |
| `code-review` | Matt/Community | 代码审查 |
| `db-migrator` | Chinese | 数据库迁移 |
| `dep-auditor` | Chinese | 依赖审计 |
| `ds-mapper` | Chinese | 数据映射 |
| `env-manager` | Chinese | 环境变量管理 |
| `error-translator` | Chinese | 错误信息翻译 |
| `eslint-fix` | Chinese | ESLint 修复 |
| `github-actions-gen` | Chinese | GitHub Actions 生成 |
| `git-workflow` | Chinese | Git 工作流 |
| `i18n-helper` | Chinese | 国际化辅助 |
| `log-analyzer` | Chinese | 日志分析 |
| `perf-profiler` | Chinese | 性能分析 |
| `refactor-advisor` | Chinese | 重构建议 |
| `security-audit` | Chinese | 安全审计 |
| `test-generator` | Chinese | 测试生成 |
| `webapp-testing` | Official | Web 应用测试 |

### 🧠 思维与决策
| Skill | 来源 | 用途 |
|-------|------|------|
| `ask-matt` | Matt | 提问技巧 |
| `domain-modeling` | Matt | 领域建模 |
| `grill-me` / `grilling` | Matt | 批判性思考 |
| `handoff` | Matt | 任务交接 |
| `lean-context` | Chinese | 精简上下文 |
| `superteam` | Chinese/Community | 超级团队协作 |
| `teach` | Matt | 教学讲解 |
| `token-discipline` | Chinese/Community | Token 成本控制 |

### 🛠️ 工具与创作
| Skill | 来源 | 用途 |
|-------|------|------|
| `intro-trailer` | Chinese/Community | 介绍视频脚本 |
| `ai-commercial` | Chinese | AI 商用指导 |
| `mcp-builder` | Official | MCP 构建器 |
| `skill-creator` | Official | Skill 创建器 |

## 快速使用

```bash
# 查看某个 skill 的内容
cat downloads/<skill-name>/SKILL.md

# 列出所有 skill
ls downloads/*/SKILL.md | wc -l
```

## 更新

定期从源仓库 pull 更新：

```bash
cd /tmp/anthropic-official-skills && git pull
cd /tmp/chinese-skills && git pull
# ... 其他仓库同理
```
