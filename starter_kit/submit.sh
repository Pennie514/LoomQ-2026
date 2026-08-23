#!/usr/bin/env bash
# LoomQ 一键提交助手：push → 预检 → 打印 Issue 表单
# 用法：bash starter_kit/submit.sh <你的GitHub用户名>
set -euo pipefail

TEAM_ID="${1:-}"
if [ -z "$TEAM_ID" ]; then
  echo "用法: bash starter_kit/submit.sh <你的GitHub用户名>" >&2
  exit 1
fi

cd "$(dirname "$0")/.."

echo "==> 1/4 提交全部改动"
git add -A
if git diff --cached --quiet; then
  echo "    没有新改动，跳过 commit"
else
  git commit -m "LoomQ submission: unified transpiler + agent + hybrid compiler" || true
fi

echo "==> 2/4 推送到你的 fork"
git push -u origin main || git push -u origin master

echo "==> 3/4 本地预检"
python3 starter_kit/prepare_submission.py --team-id "$TEAM_ID"

echo "==> 4/4 完成"
echo "下一步：打开上面预检输出的 Submission form 链接，"
echo "填写 Team ID / Fork repository / Commit SHA / Levels(L1+L2+L3) 后创建 Issue。"
echo "等自动校验打上 submission:accepted 标签即提交成功。"
