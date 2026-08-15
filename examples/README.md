# 示例产出

本目录收录 business-facts-extractor 在真实项目上的运行结果，供评估输出质量。

## microblog/

目标项目：[miguelgrinberg/microblog](https://github.com/miguelgrinberg/microblog)（Flask Mega-Tutorial 最终代码，51 个源文件：Jinja 模板 + WTForms 前端、Flask 蓝图 + REST API 后端、SQLAlchemy + 9 个 Alembic migration）。

走的是 **fan-out 路径**：侦察后划分 5 个业务域（auth / posts / social / messaging / api），每域一个 subagent 并行深读，主 agent 汇总校验后成文。

- `facts.json` — 101 条事实（rule 34 · edge_case 23 · user_flow 18 · constraint 12 · relationship 6 · entity 5 · discrepancy 3），每条带 `file:lines` 出处，`validate_facts.py` 校验通过
- `BUSINESS_FACTS.md` — 人读手册：角色×任务矩阵、用户流程（Mermaid 流程图）、ER 图、业务规则全书、边界与异常、覆盖报告（28 条路由 + 18 个模板，零盲区）

亮点：抓出 3 个真实存在的前后端不一致（discrepancy），例如「私信翻页按钮链接硬编码为 `#`，后端算好的翻页 URL 未被模板使用，用户实际无法翻页」（F-0080）。

> 注：文件内的 `file:lines` 出处对应 microblog 仓库的源码，需 clone 原项目对照查看。
