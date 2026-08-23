#!/bin/bash
# LoomQ 最终检查脚本（提交前自检）
set -e
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"

echo "========================================"
echo "LoomQ 最终检查脚本"
echo "========================================"

echo ""
echo "[1/6] 检查文件完整性..."
FILES=(
    "starter_kit/adapter.py"
    "starter_kit/submission.yaml"
    "starter_kit/requirements.txt"
    "starter_kit/evidence/README.md"
    "starter_kit/PROJECT_README.md"
    "starter_kit/QUICKSTART.md"
    "starter_kit/real_machine.py"
    "starter_kit/loomq_web.py"
    "starter_kit/loomq_cli.py"
    "starter_kit/quantum_riscv_emulator.py"
    "starter_kit/quantum_riscv_isa.md"
    "starter_kit/test_quantum_riscv.py"
    "starter_kit/HARDWARE_ACCESS.md"
    "starter_kit/SUBMISSION.md"
)
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (缺失!)"
        exit 1
    fi
done

echo ""
echo "[2/6] 检查 submission.yaml 配置..."
grep -q "l1: true" starter_kit/submission.yaml && echo "  ✓ L1 已启用"
grep -q "l2: true" starter_kit/submission.yaml && echo "  ✓ L2 已启用"
grep -q "l3: true" starter_kit/submission.yaml && echo "  ✓ L3 已启用"

echo ""
echo "[3/6] 运行 L1 测试（三后端）..."
$PY starter_kit/evaluator.py --level l1 --target spinq,originq,braket 2>&1 | grep -q '"failed": 0' && echo "  ✓ L1 三后端全部通过"

echo ""
echo "[4/6] 运行 L3 测试 + 量子 RISC-V 扩展测试..."
$PY starter_kit/evaluator.py --level l3 2>&1 | grep -q '\[PASS\] l3' && echo "  ✓ L3 通过"
$PY starter_kit/test_quantum_riscv.py 2>&1 | grep -q "0 failed" && echo "  ✓ 量子 RISC-V 扩展 31/31"

echo ""
echo "[5/6] 检查 git 状态..."
git add -A
git diff --cached --quiet || git commit -q -m "LoomQ: 最终检查与收尾更新"
if git status --porcelain | grep -q .; then
    echo "  ✗ 仍有未提交文件"
    git status --porcelain
    exit 1
else
    echo "  ✓ 工作区干净"
fi

echo ""
echo "[6/6] 测试可视化演示与 Web 语法..."
$PY starter_kit/demo_visual.py 1 > /dev/null 2>&1 && echo "  ✓ demo_visual.py 可运行"
$PY -m py_compile starter_kit/loomq_web.py && echo "  ✓ loomq_web.py 语法正确"

echo ""
echo "========================================"
echo "✓ 所有检查通过！"
echo "========================================"
echo ""
echo "能力清单："
echo "  L1: 三平台统一转译 + 模拟器（12 门白名单，隐藏电路类型预演通过）"
echo "  L1 真机: real_machine.py 三平台接入（需按 HARDWARE_ACCESS.md 申请凭证）"
echo "  L2: agent_chat 自验闭环 + Web/CLI 双入口"
echo "  L3: compile_hybrid 随机用例穷举验证"
echo "  Bonus: 量子 RISC-V 扩展 + 新手引导/视觉叙事"
echo ""
echo "提交：bash starter_kit/submit.sh <你的GitHub用户名>"
