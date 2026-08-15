# business-facts-extractor

一个 agent skill：从项目代码（前端 + 后端 + 数据库 schema）中识别业务逻辑，输出**可审计的项目业务事实**——以用户视角描述系统怎么用、实体之间什么关系、有哪些业务规则和边界异常。

与普通"读代码写总结"的区别：**每条业务事实都强制携带代码出处（file:line）**，可验证、可审计，代码变更后也能定位受影响的事实。

## 输出物

对目标项目运行后，在项目根目录生成两份**同源**产物：

| 产物 | 消费者 | 内容 |
|---|---|---|
| `BUSINESS_FACTS.md` | 人（新人 onboarding / PM / QA） | 项目概述、角色×用户任务（含 Mermaid 流程图）、实体关系（Mermaid ER 图）、业务规则全书、边界与异常、附录（覆盖报告 + 盲区清单） |
| `facts.json` | agent / 工具 | 结构化事实库：7 种事实类型，每条带 `sources: [{file, lines, kind}]`、`enforcement`、`confidence` |

事实类型：`entity` / `relationship` / `user_flow` / `rule` / `constraint` / `edge_case` / `discrepancy`（前后端规则冲突时**如实记录双方出处，绝不擅自调和**）。

## 工作原理

5 阶段流水线：

```
Phase 0 侦察     技术栈探测 → 项目地图（路由表/模型清单/页面清单）→ 业务域划分
                 规模判定：≤30 源文件或 ≤2 域 → 降级路径（单 agent 顺序分析）
                          否则              → 扇出路径（每域一个 subagent 并行深读）
Phase 1 数据模型  自底向上：schema / migrations / ORM models → 实体 + 关系事实
Phase 2 分域深读  API 契约、校验规则、权限中间件、前端表单/联动、状态机、错误分支
Phase 3 汇总验证  去重 → id 重排 → 覆盖检查（路由反向比对）→ 出处抽查 → 脚本校验
Phase 4 成文      散文由 agent 撰写；ER 图 / 规则清单由脚本从 facts.json 渲染（同源不漂移）
```

## 防幻觉机制

- **No source, no fact**：每条事实至少一个 `file:lines` 出处，schema 硬校验
- **`validate_facts.py`**：校验 schema + 出处文件真实存在、行号区间不越界、路径不逃逸项目根
- **出处抽查**：校验脚本保证行号"存在"，Phase 3 再由 agent 随机抽查 ≥5% 事实确认行号"内容相关"
- **覆盖检查**：侦察阶段的路由表 vs 事实出处反向比对，未覆盖的进入附录盲区清单（诚实标注，不靠编）
- **置信度分级**：`high`（代码明示）/ `medium`（多线索推断）/ `low`（弱证据推测，手册中 ⚠️ 标注——但仍需出处）

## 安装

```bash
# pi / 兼容的 agent 环境：放入 skills 目录
git clone git@github.com:beck6lee/business-facts-extractor.git ~/.agents/skills/business-facts-extractor
```

无第三方依赖（Python 3 标准库）。

## 使用

在任意项目目录下，对 agent 说：

> 识别这个项目的业务逻辑，输出业务事实

agent 加载 skill 后自动执行流水线，产出 `BUSINESS_FACTS.md` + `facts.json`。

也可以手动使用两个校验/渲染脚本：

```bash
# 校验事实库（schema + 出处存在性）
python3 scripts/validate_facts.py /path/to/project/facts.json --root /path/to/project

# 渲染机械内容（嵌入手册，保证 md 与 json 同源）
python3 scripts/render_md.py /path/to/project/facts.json --section er
python3 scripts/render_md.py /path/to/project/facts.json --section rules
```

## 实测效果

| 目标项目 | 路径 | 结果 |
|---|---|---|
| 单文件 HTML 入职登记表（1503 行纯前端） | 降级 | 48 条事实，6 个真实 discrepancy（如 `novalidate` 使全部 `required` 失效、草稿步骤恢复为死代码） |
| [microblog](https://github.com/miguelgrinberg/microblog)（Flask 全栈） | 扇出（5 域 subagent 并行） | 101 条事实，路由/模板覆盖零盲区，3 个 discrepancy（[完整产出见 examples/microblog](examples/microblog/)） |

## 仓库结构

```
SKILL.md                 # 主 SOP（agent 入口）
references/
  fact-schema.md         # 事实类型定义 + 每类示例
  recon.md               # 各技术栈侦察手册（Node/Python/Java/Go/Ruby，含 monorepo）
  authoring.md           # 手册写作规范 + Mermaid 模板
scripts/
  validate_facts.py      # schema + 出处存在性校验
  render_md.py           # facts.json → ER 图 / 规则清单渲染
tests/                   # 26 个 unittest（stdlib，无依赖）
```

## 开发

```bash
python3 -m unittest discover -s tests -v   # 运行测试
```

## Roadmap

- [ ] 增量更新：代码变更后只重分析受影响业务域（依赖 facts.json 的出处映射反向定位）
- [ ] `check` 模式：不重写文档，只验证现有事实是否仍与代码一致，输出失效事实清单
- [ ] 非代码事实源（PRD、接口文档）融合
