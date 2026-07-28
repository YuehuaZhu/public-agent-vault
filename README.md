# public-agent-vault

公司内部的 **AI Agent 配置库**。把「指令规范(CLAUDE.md / AGENTS.md)+ 技能(skills)」打包好，你只要按**用的工具**拷到本机，打开 VSCode 就能用上一套统一的高效工作环境。

---

## 开始之前（IT 已帮你配好）

在读这份文档前，默认你的电脑已经由公司/IT 准备好：

- ✅ 装好 **VSCode**
- ✅ 装好 **Claude Code** 插件 或 **Codex** 插件（看你用哪个）
- ✅ 配好 **API 密钥**（不用你自己申请）

如果上面还没弄好，先找 IT，不要往下走。

---

## 第 1 步：把项目拉到本机

```bash
git clone https://github.com/YuehuaZhu/public-agent-vault.git
cd public-agent-vault
```

（不会用 git 也没关系：在 GitHub 页面点绿色的 **Code → Download ZIP**，下载后解压，再用终端 `cd` 进解压出来的文件夹。）

---

## 第 2 步：按你用的工具安装

找到你用的工具，复制对应命令到终端执行。**首次安装前，如果 `~/.claude` 或 `~/.codex` 里已有旧文件，建议先备份。**

### A. Claude Code
```bash
mkdir -p ~/.claude
cp -R builder/claude/.claude/. ~/.claude/
```

### B. Codex
```bash
mkdir -p ~/.codex ~/.agents
cp -R builder/codex/.codex/.  ~/.codex/
cp -R builder/codex/.agents/. ~/.agents/
```

> **为什么 Codex 要拷两个目录？** Codex 从 `~/.codex/` 读指令规范（AGENTS.md），从 `~/.agents/skills/` 发现技能，两者缺一不可。Claude Code 则全部在 `~/.claude/` 下。

---

## 第 3 步：验证生效

1. 在 VSCode 里打开 Claude Code / Codex，新开一个对话。
2. 随便发一个能触发 skill 的请求试试，例如：
   - 发一个微信公众号文章链接，让它总结 → 触发 `chinese-content-extract`
   - 说「帮我查一下飞书某个文档」 → 触发 `lark-router`
3. 它能识别并按 skill 干活，就说明装好了。

---

## 目录说明

```
public-agent-vault/
└── builder/                   # 配置主体
    ├── claude/.claude/        #   → 铺到 ~/.claude/
    ├── codex/.codex/          #   → 铺到 ~/.codex/（AGENTS.md）
    └── codex/.agents/         #   → 铺到 ~/.agents/（skills）
```

库里含写作、调研、飞书操作、内容总结等通用 skill，以及 git 协同、CI、代码审查、TDD 等研发类 skill。

---

## 进阶：沉淀你自己的 skill

用熟之后，你会有一些反复用到的固定套路。可以把它写成自己的 skill，助手下次就能自动复用：

- 直接让助手「用 writing-skills 帮我把 XX 流程写成一个 skill」
- 你的个人 skill 放在 `~/.claude/skills/<名字>/`（Claude Code）或 `~/.agents/skills/<名字>/`（Codex），会被自动发现

好用的个人 skill 欢迎反馈给管理员，评估后会收进这个库供大家共用。

---

## 更新

库会持续更新。想拿到最新版：

```bash
cd public-agent-vault
git pull
```

然后重新执行第 2 步里你那一格的安装命令即可覆盖更新。
