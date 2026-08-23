# LoomQ 最终提交流程（GitHub 提交指南）

> 截止时间：**2026-08-25 12:00 (UTC+8)**，以 GitHub 服务器记录的 Issue
> `created_at` 为准。整个流程约 15 分钟，只做一次，之后可重复提交覆盖。

---

## 0. 你要准备的东西

| 项目 | 说明 |
|---|---|
| GitHub 账号 | **用户名就是 Team ID**（如 `pennie514`）。没有就去 https://github.com 注册 |
| 报名 | 若还没填报名表：https://my.feishu.cn/share/base/form/shrcnJcMDs843ZKPUzsxhD25rxc |
| 本机 git | macOS 自带；检查：`git --version` |

---

## 1. Fork 官方仓库（1 分钟）

1. 打开 https://github.com/QAIDAO/LoomQ-2026
2. 点右上角 **Fork** → 创建到你自己的账号下
3. 记下你的 fork 地址：`https://github.com/<你的用户名>/LoomQ-2026`

> 必须 fork，不能直接 push 到官方仓库。Team ID = fork 所有者用户名。

---

## 2. 把作品代码放进 fork（两种方式任选）

### 方式 A（推荐，最简单）：直接把本目录变成你的 fork 工作区

在**本机这个项目目录**里执行（把 `<你的用户名>` 换成你的 GitHub 用户名）：

```bash
# 1. 初始化 git（如果还没有 .git）
git init
git add -A
git commit -m "LoomQ submission: unified transpiler + agent + hybrid compiler"

# 2. 指向你自己的 fork（替换成你的地址）
git remote add origin https://github.com/<你的用户名>/LoomQ-2026.git
git branch -M main

# 3. 推送（需要输入 GitHub 用户名 + Personal Access Token，见第 3 节）
git push -u origin main
```

### 方式 B：重新克隆 fork 再拷贝

```bash
git clone https://github.com/<你的用户名>/LoomQ-2026.git
cd LoomQ-2026
# 把本机的 starter_kit/ 整个覆盖过去（保留官方其它文件）
cp -R /Users/pennie/Desktop/LoomQ-2026/starter_kit/ starter_kit/
git add -A
git commit -m "LoomQ submission: unified transpiler + agent + hybrid compiler"
git push -u origin main
```

---

## 3. GitHub 推送认证（HTTPS + Personal Access Token）

`git push` 时密码框不要填 GitHub 登录密码，要填 **Personal Access Token (PAT)**：

1. GitHub 右上角头像 → **Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. **Generate new token (classic)**，勾选权限：`repo`（全选即可）
3. 复制生成的 `ghp_...` 字符串
4. push 时用户名填你的 GitHub 用户名，密码粘贴这个 token

> 也可以配置一次性记住：
> ```bash
> git config --global credential.helper osxkeychain   # macOS 钥匙串记住
> ```

---

## 4. 本地预检（1 分钟）

在 fork 根目录（本目录）运行，**Team ID 填你的 GitHub 用户名**：

```bash
python3 starter_kit/prepare_submission.py --team-id <你的用户名>
```

预检会确认：
- ✅ 工作区干净（没有未提交改动）
- ✅ HEAD 已 push 到 origin（`git push` 成功后才能通过）
- ✅ origin 所有者 = Team ID
- ✅ 必需文件齐全（submission.yaml / adapter.py / Dockerfile / README.md）

通过后它会输出：**Team ID、Fork repository、Commit SHA、Submission form 链接**。
把这三项抄下来填进第 5 步的 Issue。

---

## 5. 创建最终提交 Issue（2 分钟）

1. 打开预检输出的表单链接（或 https://github.com/QAIDAO/LoomQ-2026/issues/new?template=final-submission.yml ）
2. 按下表填写：

| 字段 | 填什么 |
|---|---|
| Team ID | 你的 GitHub 用户名 |
| Fork repository | `https://github.com/<你的用户名>/LoomQ-2026` |
| Commit SHA | 预检输出的 40 位 SHA |
| Levels | ✅ L1 ✅ L2 ✅ L3 全勾 |
| Hardware evidence | 如申报真机分：`starter_kit/evidence/hardware/`（跑完真机后填） |
| Declarations | 三个声明全勾 |

3. **创建 Issue**。几分钟内自动校验：
   - 通过 → Issue 获得 `submission:accepted` 标签 + 回执评论（含归档 SHA-256 与 Artifact ID）
   - 失败 → 按回执里的原因修复，**重新创建一个新 Issue**（不要编辑旧 Issue）

> ✅ **只有拿到 `submission:accepted` 标签才算提交成功。**
> 截止前可反复用新 Issue 重新提交，最后一次通过校验的生效。

---

## 6. 提交后还能改吗？

可以。改代码 → `git add -A && git commit && git push` → 重新跑预检 →
**新建**一个最终提交 Issue（不要编辑旧的）。截止前最后一次通过的提交生效。

---

## 常见问题

**Q: 我没有 GitHub 账号 / 忘记用户名？**
用户名 = 你的 Team ID，注册后把用户名填进所有 `<你的用户名>` 位置。

**Q: 预检报「工作区不干净」？**
先 `git add -A && git commit -m "update" && git push`，再重跑预检。

**Q: 预检报「Team ID 必须与 origin fork 的所有者一致」？**
你的 GitHub 用户名打错了，或 remote 指向的不是你的 fork。

**Q: 提交超过 100 MiB？**
归档只包含 `starter_kit/`；`.venv`、密钥、视频等不要入库（.gitignore 已处理）。

**Q: 需要真机证据吗？**
不是必须。要拿 L1 真机 +10 分就先按 `HARDWARE_ACCESS.md` 申请 API 并跑通
`real_machine.py`，再把结果文件放进 `starter_kit/evidence/files/`。
