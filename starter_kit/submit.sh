#!/usr/bin/env bash
# LoomQ 一键提交助手：push → 预检 → 打印 Issue 表单
# 用法：bash starter_kit/submit.sh <你的GitHub用户名>
set -uo pipefail

TEAM_ID="${1:-}"
if [ -z "$TEAM_ID" ]; then
  echo "用法: bash starter_kit/submit.sh <你的GitHub用户名>" >&2
  exit 1
fi

cd "$(dirname "$0")/.."

BRANCH="$(git branch --show-current 2>/dev/null || echo main)"
if [ -z "$BRANCH" ]; then BRANCH=main; fi

echo "==> 1/4 提交全部改动（当前分支：$BRANCH）"
git add -A
if git diff --cached --quiet; then
  echo "    没有新改动，跳过 commit"
else
  git commit -m "LoomQ submission: unified transpiler + agent + hybrid compiler" || true
fi

echo "==> 2/4 推送到你的 fork（$BRANCH 分支）"
if ! git push -u origin "$BRANCH"; then
  echo ""
  echo "⚠️  推送失败。常见原因与解决："
  echo "  1) 网络连不上 github.com（国内常见）："
  echo "     - 本机有代理（如 Clash/V2Ray 7890 端口）时，先执行："
  echo "         git config --global http.https://github.com.proxy http://127.0.0.1:7890"
  echo "         git config --global https.https://github.com.proxy http://127.0.0.1:7890"
  echo "       然后重跑本脚本；"
  echo "     - 或改用 SSH（需先添加 SSH 公钥到 GitHub）："
  echo "         git remote set-url origin git@github.com:${TEAM_ID}/LoomQ-2026.git"
  echo "         ssh -T git@github.com   # 验证连通"
  echo "       然后重跑本脚本；"
  echo "  2) 提示输入密码时，密码框填 Personal Access Token（不是登录密码）："
  echo "     GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)"
  echo "     生成时勾选 repo 权限。"
  exit 1
fi

echo "==> 3/4 本地预检"
python3 starter_kit/prepare_submission.py --team-id "$TEAM_ID"

echo "==> 4/4 完成"
echo "下一步：打开上面预检输出的 Submission form 链接，"
echo "填写 Team ID / Fork repository / Commit SHA / Levels(L1+L2+L3) 后创建 Issue。"
echo "等自动校验打上 submission:accepted 标签即提交成功。"
