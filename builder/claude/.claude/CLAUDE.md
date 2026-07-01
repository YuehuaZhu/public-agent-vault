## 称呼规范
每次回复时都叫我老大


## 开发规范

**设计阶段**：常规查资料用 `WebSearch`/`WebFetch`；`deep-research` 只在老大显式说"deep-research"/"对抗式核查"时用，不自动嵌入流程。如果需要写代码，代码方案设计前先 GitHub 调研（`WebSearch` 搜开源实现），能复用就复用；调研结果简要告知，不要只给结论不给来源。

**开发阶段**：按改动复杂度选轨道——小修/Hotfix（≤30min）走 `+quick` 起 `hotfix/<slug>`；功能或重大 Bug 走 `+issue` → `+branch`。

**验证阶段**：自验优先——能跑命令就跑、能读日志就读、能自修就修，直到本轮问题全部解决，再把"需要老大确认的事"一次性列出，不要每验一步都问老大。

**发布阶段**：写完跑 `+ci`，绿了之后如果老大说"提交"/"push"/"合并"/"ship" 即使用 team-collab 自动推到 main（规则见 team-collab skill）。`+review` 只在老大显式说时触发，不自动嵌入。

## 会话启动检查

仓库下静默检查 `CLAUDE.md` / `PLAN.md`，缺就问要不要 `/repo-init`。
