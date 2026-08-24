#!/usr/bin/env python3
"""LoomQ Web 界面（零依赖：只用 Python 标准库，无需联网、无需 npm）

「让不懂黑话的人，也能指挥最前沿的算力」——面向**零量子背景**用户的
可视化交互入口（L2 交互体验 + 新手引导/视觉叙事 Bonus）。

设计原则（对真小白友好）：
    - 「零基础入门」引导页：5 步走，全部用生活类比（旋转的硬币 / 魔法手套）
      讲清楚"是什么 / 为什么 / 怎么做"，并与经典计算机对比；
    - 每个实验都配：类比故事 + 你会看到什么 + 为什么有意思；
    - 每次结果都附带大白话解读 + 与经典计算的对比；
    - 模型服务未配置时给出友好中文提示（不是报错），实验/科普完全可用。

启动：
    python3 starter_kit/loomq_web.py            # 默认 http://127.0.0.1:8080
    python3 starter_kit/loomq_web.py --port 9000
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import adapter  # noqa: E402
import real_machine  # noqa: E402   # 真机接入（Web 一键上真实量子机）

REAL_BACKENDS = [
    ("spinq_cloud", "量旋超导/核磁真机", "真实量子计算机（2-8 比特）"),
    ("originq_wukong", "本源 180 超导真机", "真实量子计算机（180 比特）"),
]

BACKENDS = [
    ("spinq", "量旋本地模拟器", "最轻量，秒出结果"),
    ("originq", "本源本地模拟器", "国产框架，上限高"),
    ("braket", "AWS 本地模拟器", "免费无需账号"),
]

EXAMPLES = [
    {
        "title": "量子硬币：一个比特的真随机",
        "analogy": "类比：一枚在桌上旋转的硬币——在它倒下之前，正面和反面「同时」存在；"
                   "一旦你看它（测量），它才随机定格成其中一面。",
        "story": "把一枚硬币立在半空——它既不是正面也不是反面，直到你看它的那一刻。"
                 "这不是「我们不知道结果」，而是结果在测量前真的还没定。",
        "what_you_see": "你会看到：正面/反面各约一半（50% / 50%）。",
        "why_cool": "这是真随机——经典计算机的「随机」其实是用算法模拟出来的，而这是量子世界天然的真随机。",
        "qasm": 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\ncreg c[1];\n'
                'h q[0];\nmeasure q -> c;\n',
    },
    {
        "title": "Bell 态：两个比特的纠缠",
        "analogy": "类比：一副「魔法手套」——把左手套和右手套分装两个盒子，你打开一个看到"
                   "左手，立刻知道另一个一定是右手，不需要任何电话。",
        "story": "两枚硬币被「绑」在一起：看了其中一枚，另一枚立刻就定了，而且永远和它一样。"
                 "距离多远都成立。",
        "what_you_see": "你会看到：只会出现「00」或「11」两种结果，各约一半；"
                        "「01」「10」几乎不出现。",
        "why_cool": "经典计算机要模仿这个效果，必须事先「约好」两个比特相同；"
                    "而量子纠缠是测量瞬间自动一致的——不需要任何约定。这是被实验反复验证的真实物理。",
        "qasm": 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\n'
                'h q[0];\ncx q[0], q[1];\nmeasure q -> c;\n',
    },
    {
        "title": "GHZ 态：三个比特一起纠缠",
        "analogy": "类比：三只「魔法手套」——要么全是左手，要么全是右手，没有中间情况。",
        "story": "三枚硬币绑在一起：要么全是正面，要么全是反面，没有中间情况。"
                 "这是「纠缠」最经典的指纹。",
        "what_you_see": "你会看到：只会出现「000」或「111」，各约一半；其他 6 种组合几乎不出现。",
        "why_cool": "三个比特同时锁定——这是多比特纠缠，是量子计算并行能力的根基之一。",
        "qasm": 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[3];\ncreg c[3];\n'
                'h q[0];\ncx q[0], q[1];\ncx q[0], q[2];\nmeasure q -> c;\n',
    },
    {
        "title": "均匀叠加：三个比特各自独立随机",
        "analogy": "类比：三枚各自独立的硬币——互不影响，各转各的。",
        "story": "三枚硬币各自独立抛——8 种组合概率相同。和 GHZ 对比，"
                 "你就能直观看出「纠缠」和「独立」的差别。",
        "what_you_see": "你会看到：000 到 111 全部 8 种组合都出现，概率接近相同（各约 12.5%）。",
        "why_cool": "经典里三个独立随机数也是这个分布；但量子里每个比特都处于叠加态，"
                    "这里的区别在于：没有纠缠（上一个实验有）。",
        "qasm": 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[3];\ncreg c[3];\n'
                'h q[0];\nh q[1];\nh q[2];\nmeasure q -> c;\n',
    },
]

BASIC_STEPS = [
    ("先认识「量子比特」",
     "经典比特像一个电灯开关：要么开（1）要么关（0），任何时候只有一个状态。"
     "量子比特像一枚旋转中的硬币：在它倒下之前，正面和反面「同时」存在——"
     "这叫叠加态。倒下的那一刻叫测量。"),
    ("跑你的第一个实验",
     "点上方【现成实验】里的「量子硬币」并运行。你会看到 1 个比特测量 2000 次，"
     "正面/反面各约一半——这就是量子的真随机。先别管代码，看柱状图就好。"),
    ("看懂「纠缠」（重点）",
     "再跑「Bell 态」。你会看到永远只有「00」或「11」，绝不出现「01」「10」。"
     "就像一副魔法手套：看到一只，立刻知道另一只。经典计算机要模仿这个必须"
     "事先约定，而量子是测量瞬间自动一致——这是量子计算最独特的能力。"),
    ("用大白话造你自己的电路",
     "点【说人话生成电路】，输入类似「让三个量子比特纠缠在一起（GHZ 态），"
     "然后全部测量」，智能体会自动写成电路，一键运行看结果。你不需要会写代码。"),
    ("换平台再跑一次",
     "同一份电路，在量旋/本源/AWS 三个平台各跑一次，结果分布一致——"
     "这就是本工具的意义：一份电路，到处能跑，不用学任何平台的「黑话」。"),
    ("🚀 把第一个实验跑上「真实量子机」",
     "这是最激动人心的一步：点【现成实验】里的「Bell 态」，先本地跑一次看懂分布，"
     "再点「🚀 跑上量旋真机」或「🚀 跑上本源180真机」。"
     "等待几分钟（真机要排队），你会看到真实量子芯片返回的结果："
     "主峰和理想一致（00/11 最多），但带上了真实噪声（01/10 偶尔出现）——"
     "这就是「第一次指挥真实的量子计算机」的感觉。"),
    ("可选：配置模型服务（解锁 生成/纠错/选平台）",
     "上面的第 4 步需要模型服务。正式评测时组委会会自动注入，你无需操作。"
     "想在本地体验完整功能，先在终端执行三行命令，然后刷新本页面："
     "export LOOMQ_LLM_BASE_URL=\"https://api.deepseek.com\"；"
     "export LOOMQ_LLM_API_KEY=\"sk-你的密钥\"；"
     "export LOOMQ_LLM_MODEL=\"deepseek-chat\"。"
     "不配置也没关系：实验/科普/真机体验完全可用，评测时也能正常评分。"),
]

CONCEPTS = [
    ("量子比特是什么",
     "开关 vs 硬币。经典比特=电灯开关，要么开(1)要么关(0)，任何时候只有一个状态。"
     "量子比特=旋转中的硬币，倒下之前正面和反面「同时」存在。",
     "对比传统：经典逻辑非黑即白；量子逻辑在观察之前可以「既是又是」。"),
    ("叠加态是什么",
     "旋转中的硬币。注意：不是「一半概率正面」，而是「在观察之前，正面和反面"
     "同时存在于同一枚硬币上」。测量（看它）才让它随机定格成一个结果。",
     "对比传统：经典里一个比特任何时候都确定；量子里不确定是常态，确定是测量结果。"),
    ("纠缠是什么",
     "一副魔法手套。盒子里一副手套，你带走一只，朋友带走另一只；你打开看到左手，"
     "立刻知道朋友那只一定是右手——不需要打电话。量子纠缠：两个比特测量瞬间自动关联，"
     "无论距离多远。Bell 态里永远只出现 00 或 11。",
     "对比传统：经典里这叫「事先约定」；量子纠缠是测量瞬间自动一致的真实物理现象。"),
    ("测量是什么",
     "看硬币落下的那一刻。测量前是叠加（不确定），测量后得到确定结果（0 或 1），"
     "并且测量本身会改变量子态——这叫坍缩。",
     "对比传统：经典里「读」一个比特不改变它；量子里「读」（测量）会改变它，"
     "所以同一电路必须跑很多次做统计。"),
    ("量子门是什么",
     "摆弄硬币的手法。H 门=把硬币转起来（制造叠加）；X 门=把硬币翻面（0↔1）；"
     "CX 门=把两枚硬币绑在一起（制造纠缠）。",
     "对比传统：就像经典程序里的运算符（+、-、if），量子门是作用在量子态上的基本操作。"),
    ("量子计算 vs 经典计算",
     "经典计算机：一个一个地试（串行）。量子计算机：利用叠加「同时」探索所有可能，"
     "利用纠缠让答案之间产生关联。",
     "类比：经典=一个人一页一页翻书找答案；量子=整本书的所有页同时被翻开。"
     "这就是某些问题（如大数分解、搜索）量子有理论优势的原因。"),
    ("为什么要跑很多次（shots）",
     "掷硬币：掷一次看不出规律，掷 1000 次才看出约 50/50。量子测量同理："
     "每次结果随机，跑几千次统计出概率分布，才能看清电路真正的行为。"
     "结果页的柱状图就是这张「统计表」。"),
    ("本工具在做什么",
     "各家量子平台的指令格式互不相通（量旋、本源、AWS 各说一套「黑话」）。"
     "本工具把标准电路翻译成三家各自的格式，一份电路到处能跑；"
     "再配一个「会说人话」的智能体，让你用自然语言就能造电路。",
     "类比：就像「通用充电器」——不管什么插头，插上就能用。"),
]

PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LoomQ · 量子计算，像转硬币一样简单</title>
<style>
  :root{
    --bg0:#070b18; --bg1:#0c1330; --card:rgba(255,255,255,.045);
    --line:rgba(255,255,255,.10); --txt:#e8ecff; --dim:#9aa6d4;
    --acc:#7c5cff; --acc2:#00d4ff; --ok:#2dd4a7; --warn:#ffb84d; --err:#ff6b81;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html{scroll-behavior:smooth}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
       background:
         radial-gradient(1100px 500px at 85% -10%, rgba(124,92,255,.22), transparent 60%),
         radial-gradient(900px 480px at -10% 10%, rgba(0,212,255,.14), transparent 55%),
         linear-gradient(180deg,var(--bg0),var(--bg1));
       color:var(--txt); min-height:100vh; line-height:1.7}
  .wrap{max-width:1080px;margin:0 auto;padding:28px 22px 90px}
  header{text-align:center;padding:38px 0 8px}
  .logo{font-size:14px;letter-spacing:.35em;color:var(--acc2);font-weight:700;text-transform:uppercase}
  h1{font-size:clamp(24px,4.4vw,42px);font-weight:800;margin:12px 0 8px;
     background:linear-gradient(90deg,#fff,#b9a6ff 60%,#00d4ff);-webkit-background-clip:text;background-clip:text;color:transparent}
  .sub{color:var(--dim);font-size:clamp(14px,2vw,17px);max-width:700px;margin:0 auto}
  .analogy-strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin:22px auto 0;max-width:900px}
  .acard{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px;text-align:left;font-size:13px;color:var(--dim)}
  .acard b{color:var(--acc2);display:block;margin-bottom:4px;font-size:13.5px}
  nav{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin:26px 0 6px}
  nav button{border:1px solid var(--line);background:var(--card);color:var(--dim);padding:9px 15px;
       border-radius:12px;cursor:pointer;font-size:14px;transition:.18s}
  nav button:hover{color:var(--txt);border-color:rgba(255,255,255,.25);transform:translateY(-1px)}
  nav button.on{color:#fff;border-color:var(--acc);background:linear-gradient(135deg,rgba(124,92,255,.32),rgba(0,212,255,.18));box-shadow:0 4px 18px rgba(124,92,255,.25)}
  .panel{display:none;animation:fade .35s ease}
  .panel.on{display:block}
  @keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  .card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:22px;margin-top:18px}
  .card h3{font-size:17px;margin-bottom:8px}
  .card p{color:var(--dim);font-size:14px}
  textarea{width:100%;min-height:92px;background:rgba(0,0,0,.35);border:1px solid var(--line);color:var(--txt);
       border-radius:12px;padding:12px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13.5px;resize:vertical}
  textarea:focus{outline:none;border-color:var(--acc)}
  input[type=text]{width:100%;background:rgba(0,0,0,.35);border:1px solid var(--line);color:var(--txt);
       border-radius:12px;padding:12px;font-size:14.5px}
  input:focus{outline:none;border-color:var(--acc)}
  .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:12px}
  button.go{border:none;cursor:pointer;padding:11px 22px;border-radius:12px;font-size:14.5px;font-weight:700;
       color:#fff;background:linear-gradient(135deg,var(--acc),var(--acc2));box-shadow:0 6px 20px rgba(124,92,255,.35);
       transition:.18s}
  button.go:hover{transform:translateY(-1px);box-shadow:0 8px 26px rgba(124,92,255,.5)}
  button.go:disabled{opacity:.5;cursor:wait;transform:none}
  button.ghost{background:transparent;border:1px solid var(--line);color:var(--dim);padding:9px 16px;border-radius:12px;cursor:pointer;font-size:13.5px}
  button.ghost:hover{color:var(--txt);border-color:rgba(255,255,255,.3)}
  select{background:rgba(0,0,0,.35);border:1px solid var(--line);color:var(--txt);border-radius:12px;padding:10px 12px;font-size:14px}
  .out{margin-top:16px}
  pre.code{background:rgba(0,0,0,.42);border:1px solid var(--line);border-radius:12px;padding:14px;
       overflow:auto;font-size:12.8px;line-height:1.5;color:#c9e6ff;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
  .q{white-space:pre-wrap;color:var(--dim);font-size:14px;margin-top:10px;padding:10px 14px;border-left:3px solid var(--acc);background:rgba(124,92,255,.08);border-radius:0 10px 10px 0}
  .hist{margin-top:14px}
  .hbar{display:flex;align-items:center;gap:10px;margin:7px 0;font-size:13px}
  .hbar .lab{min-width:64px;font-family:ui-monospace,Menlo,monospace;color:var(--acc2)}
  .hbar .track{flex:1;height:20px;background:rgba(255,255,255,.05);border-radius:6px;overflow:hidden}
  .hbar .fill{height:100%;border-radius:6px;background:linear-gradient(90deg,var(--acc),var(--acc2));transition:width .5s ease}
  .hbar .num{min-width:120px;color:var(--dim);font-size:12.5px;text-align:right}
  .note{font-size:13px;color:var(--dim);margin-top:10px}
  .ok{color:var(--ok)} .warn{color:var(--warn)} .err{color:var(--err)}
  .chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
  .chip{border:1px solid var(--line);background:rgba(255,255,255,.03);color:var(--dim);padding:7px 13px;border-radius:999px;font-size:12.5px;cursor:pointer;transition:.15s}
  .chip:hover{color:#fff;border-color:var(--acc2)}
  .steps{counter-reset:s;margin:16px 0 4px}
  .step{display:flex;gap:12px;align-items:flex-start;margin:14px 0;color:var(--dim);font-size:14px}
  .step::before{counter-increment:s;content:counter(s);min-width:26px;height:26px;border-radius:8px;
       background:linear-gradient(135deg,var(--acc),var(--acc2));color:#fff;font-size:13px;font-weight:800;
       display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:2px}
  .step b{color:var(--txt);display:block;margin-bottom:3px}
  .grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin-top:16px}
  .exp{background:rgba(255,255,255,.03);border:1px solid var(--line);border-radius:14px;padding:16px;cursor:pointer;transition:.18s}
  .exp:hover{border-color:var(--acc2);transform:translateY(-2px)}
  .exp h4{font-size:15px;margin-bottom:6px}
  .exp p{font-size:13px;color:var(--dim)}
  .exp .tag{display:inline-block;font-size:11.5px;color:var(--acc2);border:1px solid rgba(0,212,255,.3);border-radius:999px;padding:2px 10px;margin-bottom:8px}
  .spin{display:inline-block;width:14px;height:14px;border:2px solid rgba(255,255,255,.25);border-top-color:#fff;
       border-radius:50%;animation:rot .7s linear infinite;vertical-align:-2px;margin-right:8px}
  @keyframes rot{to{transform:rotate(360deg)}}
  footer{margin-top:50px;text-align:center;color:var(--dim);font-size:12.5px}
  .banner{display:none;padding:12px 16px;border-radius:12px;font-size:13.5px;margin-top:14px;line-height:1.8}
  .banner.show{display:block}
  .banner.ok{background:rgba(45,212,167,.10);border:1px solid rgba(45,212,167,.3)}
  .banner.warn{background:rgba(255,184,77,.10);border:1px solid rgba(255,184,77,.3)}
  .banner.err{background:rgba(255,107,129,.10);border:1px solid rgba(255,107,129,.3)}
  .banner code{background:rgba(0,0,0,.4);padding:1px 6px;border-radius:6px;font-size:12px}
  .hint{color:var(--dim);font-size:13px;margin-top:8px}
  a{color:var(--acc2)}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="logo">LoomQ · 量子接入平权计划</div>
    <h1>量子计算，其实像转硬币一样简单</h1>
    <p class="sub">不用懂物理、不用写代码。我们用 4 个生活类比，让你 5 分钟看懂你在做什么、为什么有趣、和传统计算机有什么不同。</p>
    <div class="analogy-strip">
      <div class="acard"><b>🪙 量子比特</b>像旋转的硬币——倒下之前，正面反面同时存在</div>
      <div class="acard"><b>🧤 纠缠</b>像一副魔法手套——看到一只，立刻知道另一只</div>
      <div class="acard"><b>📊 测量</b>像看硬币落下的那一刻——结果才定格</div>
      <div class="acard"><b>🔌 本工具</b>像通用充电器——一份电路，三家平台都能跑</div>
    </div>
  </header>

  <nav id="nav">
    <button data-p="basic" class="on">🌱 零基础入门</button>
    <button data-p="gen">💬 说人话生成电路</button>
    <button data-p="fix">🩹 修一段报错代码</button>
    <button data-p="pick">🧭 帮我选平台</button>
    <button data-p="lab">🧪 现成实验（免配置）</button>
    <button data-p="learn">📚 大白话科普</button>
    <button data-p="cfg">⚙️ 配置（可选）</button>
  </nav>

  <div id="banner" class="banner"></div>

  <!-- 0 零基础入门 -->
  <section id="p-basic" class="panel on">
    <div class="card">
      <h3>🌱 5 分钟从零到第一次量子实验</h3>
      <p>跟着下面 5 步走，每一步都有生活类比。不需要任何背景知识。</p>
      <div class="steps" id="basic-steps"></div>
      <div class="row">
        <button class="go" onclick="goTab('lab')">🚀 现在就跑第一个实验</button>
        <button class="ghost" onclick="goTab('learn')">先看科普</button>
      </div>
    </div>
  </section>

  <!-- 1 生成 -->
  <section id="p-gen" class="panel">
    <div class="card">
      <h3>用自己的话描述你想要的电路</h3>
      <p>例如：「让三个量子比特纠缠在一起，然后全部测量」或「做一个两比特的随机数发生器」。</p>
      <div class="chips">
        <span class="chip" data-tpl="让三个量子比特纠缠在一起（GHZ 态），然后全部测量">3 比特纠缠态</span>
        <span class="chip" data-tpl="生成一个 2 比特的贝尔态并测量">2 比特贝尔态</span>
        <span class="chip" data-tpl="让三个量子比特各自处于均匀叠加态并测量">3 比特均匀叠加</span>
        <span class="chip" data-tpl="制备一个 1 比特的 |1> 态并测量">制备 |1> 态</span>
      </div>
      <textarea id="gen-in" placeholder="用大白话说出你想要什么……"></textarea>
      <div class="row">
        <button class="go" id="gen-go">✨ 生成电路</button>
        <select id="gen-backend">
          <option value="spinq">量旋本地模拟器</option>
          <option value="originq">本源本地模拟器</option>
          <option value="braket">AWS 本地模拟器</option>
        </select>
        <input type="number" id="gen-shots" value="2048" min="100" max="8192" style="width:110px" title="采样次数">
        <button class="ghost" id="gen-run" disabled>▶ 运行并看结果</button>
      </div>
      <div class="out" id="gen-out"></div>
    </div>
  </section>

  <!-- 2 纠错 -->
  <section id="p-fix" class="panel">
    <div class="card">
      <h3>修一段有问题的电路</h3>
      <p>把代码粘进来，再说一句你原本想做什么。它会保持你的意图，修到能跑为止。</p>
      <input type="text" id="fix-intent" placeholder="你想做的是？（例如：一个贝尔态）">
      <textarea id="fix-in" style="margin-top:10px" placeholder="把报错的代码粘在这里……"></textarea>
      <div class="row">
        <button class="go" id="fix-go">🩹 修复并自验</button>
        <button class="ghost" id="fix-run" disabled>▶ 运行修复结果</button>
      </div>
      <div class="out" id="fix-out"></div>
    </div>
  </section>

  <!-- 3 选后端 -->
  <section id="p-pick" class="panel">
    <div class="card">
      <h3>告诉我你的约束，我帮你选平台</h3>
      <p>支持：比特数、是否排队、费用、是否注册账号、真机或模拟器。</p>
      <div class="chips">
        <span class="chip" data-tpl="我要跑 15 个比特，不想排队">15 比特 · 零排队</span>
        <span class="chip" data-tpl="用免费的真机跑一个小电路">免费真机</span>
        <span class="chip" data-tpl="不需要注册账号，跑 5 比特">免注册 · 5 比特</span>
        <span class="chip" data-tpl="想用最大的免费模拟器">最大免费模拟器</span>
      </div>
      <textarea id="pick-in" placeholder="例如：我需要运行一个 15 比特电路，且零排队等待……"></textarea>
      <div class="row"><button class="go" id="pick-go">🧭 推荐平台</button></div>
      <div class="out" id="pick-out"></div>
    </div>
  </section>

  <!-- 4 实验 -->
  <section id="p-lab" class="panel">
    <div class="card">
      <h3>现成实验（不需要密钥，直接能跑）</h3>
      <p>每个实验都配了类比故事和「你会看到什么」。第一次用就从这里开始。</p>
      <div class="grid2" id="lab-grid"></div>
      <div class="out" id="lab-out"></div>
    </div>
  </section>

  <!-- 5 科普 -->
  <section id="p-learn" class="panel">
    <div class="card">
      <h3>量子概念讲解（大白话 + 类比 + 与经典对比）</h3>
      <div class="grid2" id="learn-grid"></div>
      <div class="out" id="learn-out"></div>
    </div>
  </section>

  <!-- 6 配置 -->
  <section id="p-cfg" class="panel">
    <div class="card">
      <h3>⚙️ 配置（可选，全部可跳过）</h3>
      <p>在页面里直接填，不用碰命令行。配置仅保存在<b>本机内存</b>（不写入任何文件、不提交到仓库），
         重启服务后需重新填写。正式评测时组委会会自动注入模型服务，无需任何配置。</p>

      <h3 style="margin-top:20px">① 模型服务（解锁 生成电路 / 纠错 / 选平台）</h3>
      <div class="row">
        <input type="text" id="cfg-llm-base" placeholder="https://api.deepseek.com" style="flex:2">
        <input type="text" id="cfg-llm-model" placeholder="deepseek-chat" style="flex:1">
      </div>
      <div class="row">
        <input type="password" id="cfg-llm-key" placeholder="sk- 开头的 API Key（点小眼睛可显示）" style="flex:3">
      </div>

      <h3 style="margin-top:20px">② 量旋真机凭证（解锁「🚀 跑上量旋真机」）</h3>
      <div class="row">
        <input type="text" id="cfg-spinq-user" placeholder="量旋云用户名（cloud.spinq.cn 注册）" style="flex:1">
        <input type="text" id="cfg-spinq-keyfile" placeholder="私钥文件路径，如 /Users/xxx/.ssh/spinq_cloud" style="flex:2">
      </div>

      <h3 style="margin-top:20px">③ 本源量子云凭证（解锁「🚀 跑上本源180真机」）</h3>
      <div class="row">
        <input type="password" id="cfg-originq-token" placeholder="API Token（qcloud.originqc.com.cn 个人中心→账号设置）" style="flex:3">
      </div>

      <div class="row">
        <button class="go" id="cfg-save">💾 保存配置</button>
        <button class="ghost" id="cfg-clear">🗑 清除配置</button>
        <span class="note" id="cfg-status-note"></span>
      </div>
      <div class="out" id="cfg-out"></div>
    </div>
  </section>

  <footer>LoomQ · SheNicest 2026 量子赛道 · 命令行版：<code>python3 starter_kit/loomq_cli.py</code></footer>
</div>

<script>
const $ = id => document.getElementById(id);
const EXAMPLES = __EXAMPLES__;
const CONCEPTS = __CONCEPTS__;
const BACKENDS = __BACKENDS__;
const REAL_BACKENDS = __REAL_BACKENDS__;
const BASIC_STEPS = __BASIC_STEPS__;

/* 导航 */
function goTab(name) {
  document.querySelectorAll('#nav button').forEach(x => x.classList.remove('on'));
  document.querySelectorAll('.panel').forEach(x => x.classList.remove('on'));
  document.querySelector('#nav button[data-p="' + name + '"]').classList.add('on');
  $('p-' + name).classList.add('on');
}
document.querySelectorAll('#nav button').forEach(b => b.onclick = () => goTab(b.dataset.p));

/* 模型服务状态 */
let llmReady = false, spinqReady = false, originqReady = false;
async function checkConfig() {
  try {
    const r = await fetch('/api/config-status');
    const d = await r.json();
    llmReady = d.llm;
    spinqReady = d.spinq;
    originqReady = d.originq;
    const cfgBlock = '<code>export LOOMQ_LLM_BASE_URL="https://api.deepseek.com"</code> '
      + '<code>export LOOMQ_LLM_API_KEY="sk-..."</code> '
      + '<code>export LOOMQ_LLM_MODEL="deepseek-chat"</code>';
    if (!llmReady) {
      banner('🔑 <b>第 1 步建议：配置模型服务（可选）</b><br>'
        + '不配置：<b>现成实验 / 科普 / 零基础入门 / 真机体验</b> 完全可用。<br>'
        + '配置后解锁：<b>生成电路 / 纠错 / 选平台</b>（正式评测时组委会自动注入，无需操作）。<br>'
        + '两种方式任选：① 点上方【⚙️ 配置】在页面里直接填；② 终端执行后刷新：<br>' + cfgBlock
        + '<br><button class="ghost" onclick="goTab(\'cfg\')">⚙️ 打开配置面板</button> '
        + '<button class="ghost" onclick="copyCfg()">📋 复制终端命令</button>', 'warn', false);
    } else {
      banner('✅ 模型服务已连接（' + esc(d.model || '') + '），所有功能可用！', 'ok', true);
    }
    updateCfgStatus();
  } catch (e) { /* 忽略 */ }
}

function updateCfgStatus() {
  const parts = [];
  parts.push('模型服务: ' + (llmReady ? '✅ 已配置' : '⬜ 未配置'));
  parts.push('量旋真机: ' + (spinqReady ? '✅ 已配置' : '⬜ 未配置'));
  parts.push('本源真机: ' + (originqReady ? '✅ 已配置' : '⬜ 未配置'));
  const el = $('cfg-status-note');
  if (el) el.innerHTML = parts.join('　·　');
}

$('cfg-save').onclick = async () => {
  const payload = {
    llm: {
      base_url: $('cfg-llm-base').value.trim(),
      api_key: $('cfg-llm-key').value.trim(),
      model: $('cfg-llm-model').value.trim(),
    },
    spinq: {
      username: $('cfg-spinq-user').value.trim(),
      keyfile: $('cfg-spinq-keyfile').value.trim(),
    },
    originq: { api_token: $('cfg-originq-token').value.trim() },
  };
  const r = await post('/api/config', payload);
  if (r.ok) {
    banner('✅ 配置已保存（仅内存）。' + (r.llm ? ' 模型服务已就绪，可刷新使用生成/纠错。' : '')
      + (r.spinq ? ' 量旋真机已就绪。' : '') + (r.originq ? ' 本源真机已就绪。' : ''), 'ok', true);
    checkConfig();
  } else {
    banner('⚠️ 配置保存失败：' + esc(r.error || ''), 'err');
  }
};
$('cfg-clear').onclick = async () => {
  const r = await post('/api/config-clear', {});
  banner('🗑 已清除页面配置（进程内）。', 'ok', true);
  ['cfg-llm-base', 'cfg-llm-key', 'cfg-llm-model', 'cfg-spinq-user', 'cfg-spinq-keyfile', 'cfg-originq-token']
    .forEach(id => { const el = $(id); if (el) el.value = ''; });
  checkConfig();
};

function copyCfg() {
  const text = 'export LOOMQ_LLM_BASE_URL="https://api.deepseek.com"\n'
    + 'export LOOMQ_LLM_API_KEY="sk-你的密钥"\n'
    + 'export LOOMQ_LLM_MODEL="deepseek-chat"';
  if (navigator.clipboard) navigator.clipboard.writeText(text).then(() => banner('✅ 配置命令已复制，粘贴到终端执行后刷新本页', 'ok', true));
  else prompt('复制下面的配置命令：', text);
}

function banner(msg, kind, autoHide) {
  const el = $('banner');
  el.innerHTML = msg + (autoHide === false ? '<br><button class="ghost" onclick="this.parentNode.classList.remove(\'show\')">✕ 知道了</button>' : '');
  el.className = 'banner show ' + (kind || '');
  if (autoHide !== false) setTimeout(() => el.classList.remove('show'), 30000);
}

async function post(url, body) {
  const r = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  return r.json();
}

function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

/* 渲染柱状图 + 大白话解读（含经典对比） */
function renderHist(out, result, shots) {
  const counts = result.counts || {};
  const total = shots || Object.values(counts).reduce((a, b) => a + b, 0) || 1;
  const peak = Math.max(...Object.values(counts), 1);
  let html = '<div class="hist">';
  for (const [state, n] of Object.entries(counts).sort((a, b) => b[1] - a[1])) {
    const pct = (n / total * 100).toFixed(1);
    html += `<div class="hbar"><span class="lab">|${esc(state)}⟩</span>
      <span class="track"><span class="fill" style="width:${(n / peak * 100).toFixed(1)}%"></span></span>
      <span class="num">${n} 次 · ${pct}%</span></div>`;
  }
  html += '</div>';
  html += `<div class="note">后端：${esc(result.backend || '')} · shots：${result.shots || total} · job_id：${esc(result.job_id || '')}</div>`;
  html += interpretText(counts, total);
  out.innerHTML = html;
}

function interpretText(counts, shots) {
  if (!counts) return '';
  const states = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
  const top = states[0];
  const n = top.length;
  let msg = '', classic = '';
  if (states.length === 1) {
    msg = `结果完全确定——每次都是 |${top}⟩，这个电路没有随机性（就像一枚被胶带固定的硬币）。`;
    classic = '经典对比：这和经典比特的输出一模一样（确定值），但这里的确定性来自量子门设计。';
  } else if (states.length === 2 && states.every(s => /^(0+|1+)$/.test(s)) && n > 1) {
    msg = `只出现「全 0」和「全 1」两种结果，各占一半——这就是<b>纠缠</b>的指纹：这些比特的测量结果被锁死在一起了（魔法手套）。`;
    classic = '经典对比：经典计算机要模仿这个效果，必须事先「约好」所有比特相同；量子纠缠是测量瞬间自动一致的——不需要任何约定。';
  } else if (states.length === Math.pow(2, n)) {
    msg = `${states.length} 种组合都出现了，概率接近相同——这些比特各自独立随机，彼此没有关联（各自旋转的硬币），和纠缠正好相反。`;
    classic = '经典对比：经典里 n 个独立随机数也是这个分布；区别在于量子里每个比特都处于叠加态，且没有纠缠。';
  } else {
    msg = `出现了 ${states.length} 种结果，最常见的是 |${top}⟩（${(counts[top] / shots * 100).toFixed(1)}%）。`;
    classic = '经典对比：这是一个概率性电路——经典计算机每次也会得到不同结果，需要统计才能看清规律。';
  }
  return `<div class="note" style="padding:10px 14px;background:rgba(45,212,167,.08);border-left:3px solid var(--ok);border-radius:0 10px 10px 0">
    💡 这说明什么：${msg}<br><span style="color:var(--dim)">${classic}</span></div>`;
}

/* 实验卡片：类比 + 你会看到 + 为什么有意思 */
function renderExampleResult(i) {
  const e = EXAMPLES[i];
  return `<div class="note" style="padding:12px 14px;background:rgba(124,92,255,.07);border-left:3px solid var(--acc);border-radius:0 10px 10px 0;margin-top:10px">
    <b>🪙 ${esc(e.analogy)}</b><br>
    <span class="ok">👀 ${esc(e.what_you_see)}</span><br>
    <span class="warn">✨ ${esc(e.why_cool)}</span></div>`;
}

/* ---------- 生成 ---------- */
$('gen-go').onclick = async () => {
  const p = $('gen-in').value.trim();
  if (!p) return banner('先描述一下你想要什么～', 'warn');
  if (!llmReady) return banner('🔑 模型服务未配置，生成功能暂不可用。先玩【现成实验】和【科普】吧！', 'warn');
  const btn = $('gen-go'); btn.disabled = true; btn.textContent = '⏳ 智能体正在生成并自验…';
  $('gen-out').innerHTML = '<div class="spin"></div>请稍候，智能体生成后会先用无噪声模拟器自验一遍…';
  try {
    const r = await post('/api/chat', {prompt: p});
    if (r.error) { banner(r.error, 'err'); $('gen-out').innerHTML = ''; return; }
    const qasm = r.qasm;
    if (!qasm) { $('gen-out').innerHTML = `<div class="q">${esc(r.reply || '没有拿到电路')}</div>`; return; }
    $('gen-out').innerHTML =
      `<div class="q">${esc(r.reply.split('```')[0] || '')}</div>` +
      `<pre class="code">${esc(qasm)}</pre>`;
    $('gen-run').disabled = false; $('gen-run').dataset.qasm = qasm;
  } finally { btn.disabled = false; btn.textContent = '✨ 生成电路'; }
};
$('gen-run').onclick = async () => {
  const qasm = $('gen-run').dataset.qasm;
  const backend = $('gen-backend').value;
  const shots = parseInt($('gen-shots').value) || 2048;
  const btn = $('gen-run'); btn.disabled = true; btn.textContent = '⏳ 运行中…';
  $('gen-out').insertAdjacentHTML('beforeend', '<div class="spin" style="margin-top:12px"></div>');
  try {
    const r = await post('/api/run', {qasm, backend, shots});
    if (r.error) { banner(r.error, 'err'); return; }
    renderHist($('gen-out'), r.result, shots);
  } finally { btn.disabled = false; btn.textContent = '▶ 运行并看结果'; }
};
document.querySelectorAll('#p-gen .chip').forEach(c => c.onclick = () => $('gen-in').value = c.dataset.tpl);

/* ---------- 纠错 ---------- */
$('fix-go').onclick = async () => {
  const code = $('fix-in').value.trim();
  const intent = $('fix-intent').value.trim();
  if (!code) return banner('请把报错的代码粘进来', 'warn');
  if (!llmReady) return banner('🔑 模型服务未配置，纠错功能暂不可用。先玩【现成实验】和【科普】吧！', 'warn');
  const btn = $('fix-go'); btn.disabled = true; btn.textContent = '⏳ 修复并自验中…';
  $('fix-out').innerHTML = '<div class="spin"></div>正在诊断错误并保持你的意图修复…';
  try {
    const prompt = intent ? `我想做的是${intent}，但这段代码有问题，请修好它：\n${code}` : `这段代码报错了，帮我修好并保持原意图：\n${code}`;
    const r = await post('/api/chat', {prompt});
    if (r.error) { banner(r.error, 'err'); $('fix-out').innerHTML = ''; return; }
    if (!r.qasm) { $('fix-out').innerHTML = `<div class="q">${esc(r.reply || '')}</div>`; return; }
    $('fix-out').innerHTML = `<pre class="code">${esc(r.qasm)}</pre>`;
    $('fix-run').disabled = false; $('fix-run').dataset.qasm = r.qasm;
  } finally { btn.disabled = false; btn.textContent = '🩹 修复并自验'; }
};
$('fix-run').onclick = async () => {
  const qasm = $('fix-run').dataset.qasm;
  const btn = $('fix-run'); btn.disabled = true; btn.textContent = '⏳ 运行中…';
  try {
    const r = await post('/api/run', {qasm, backend: 'originq', shots: 2048});
    if (r.error) { banner(r.error, 'err'); return; }
    renderHist($('fix-out'), r.result, 2048);
  } finally { btn.disabled = false; btn.textContent = '▶ 运行修复结果'; }
};

/* ---------- 选后端 ---------- */
$('pick-go').onclick = async () => {
  const p = $('pick-in').value.trim();
  if (!p) return banner('说一下你的约束吧，比如比特数和是否愿意排队', 'warn');
  if (!llmReady) return banner('🔑 模型服务未配置，选平台功能暂不可用。先玩【现成实验】和【科普】吧！', 'warn');
  const btn = $('pick-go'); btn.disabled = true; btn.textContent = '⏳ 按官方能力表求解中…';
  try {
    const r = await post('/api/chat', {prompt: p});
    if (r.error) { banner(r.error, 'err'); return; }
    $('pick-out').innerHTML = `<div class="q">${esc(r.reply || '')}</div>`;
  } finally { btn.disabled = false; btn.textContent = '🧭 推荐平台'; }
};
document.querySelectorAll('#p-pick .chip').forEach(c => c.onclick = () => $('pick-in').value = c.dataset.tpl);

/* ---------- 现成实验 ---------- */
const labGrid = $('lab-grid');
EXAMPLES.forEach((e, i) => {
  const d = document.createElement('div');
  d.className = 'exp';
  d.innerHTML = `<span class="tag">实验 ${i + 1}</span><h4>${esc(e.title)}</h4>
    <p>🪙 ${esc(e.analogy)}</p>`;
  d.onclick = () => runExample(i);
  labGrid.appendChild(d);
});
async function runExample(i) {
  const e = EXAMPLES[i];
  const out = $('lab-out');
  out.innerHTML = `<div class="spin"></div>正在 ${BACKENDS[0][1]} 上运行 ${e.title}…`;
  const r = await post('/api/run', {qasm: e.qasm, backend: BACKENDS[0][0], shots: 2048});
  if (r.error) { banner(r.error, 'err'); out.innerHTML = ''; return; }
  out.innerHTML = `<h3 style="margin-top:6px">${esc(e.title)}</h3>` +
    `<div class="q">${esc(e.story)}</div>` +
    renderExampleResult(i) +
    `<pre class="code">${esc(e.qasm)}</pre>`;
  renderHist(out, r.result, 2048);
  out.insertAdjacentHTML('beforeend',
    '<div class="row"><button class="ghost" onclick="rerunExample(' + i + ',1)">换量旋再跑</button>' +
    '<button class="ghost" onclick="rerunExample(' + i + ',2)">换本源再跑</button>' +
    '<button class="ghost" onclick="rerunExample(' + i + ',0)">换 AWS 再跑</button></div>');
  out.insertAdjacentHTML('beforeend',
    '<div class="row" style="margin-top:14px;padding-top:14px;border-top:1px dashed var(--line)">' +
    '<span class="note" style="margin:0">🚀 想体验真实量子计算机？</span>' +
    '<button class="go" onclick="runReal(' + i + ',0)">🚀 跑上量旋真机</button>' +
    '<button class="go" onclick="runReal(' + i + ',1)">🚀 跑上本源180真机</button></div>');
}

async function runReal(i, ri) {
  const e = EXAMPLES[i];
  const out = $('lab-out');
  const [bid, name, desc] = REAL_BACKENDS[ri];
  out.insertAdjacentHTML('beforeend',
    `<div id="real-box" style="margin-top:14px;padding:14px;border:1px solid rgba(0,212,255,.35);border-radius:14px;background:rgba(0,212,255,.06)">
      <b style="color:var(--acc2)">🚀 正在 ${name} 上运行……</b>
      <div class="note">${esc(desc)}。真机任务需要排队，通常几分钟到十几分钟，请勿关闭页面。提交前会先在本地模拟器自验主峰。</div>
      <div class="spin" style="margin-top:10px"></div></div>`);
  try {
    const r = await post('/api/run-real', {backend: bid, qasm: e.qasm, shots: 2048});
    const box = $('real-box');
    if (!box) return;
    if (r.error) {
      box.innerHTML = `<b style="color:var(--err)">😕 真机运行未成功：</b><div class="note">${esc(r.error)}</div>`;
      return;
    }
    box.innerHTML = `<b style="color:var(--ok)">✅ ${name} 真机任务完成！</b>
      <div class="note">这是真实量子计算机返回的结果——和上面的本地模拟相比：主峰一致（00/11 最多），但多了真实噪声（01/10 偶尔出现）。这就是「量子世界本来带噪声」的样子。</div>`;
    renderHist(box, r.result, 2048);
    box.insertAdjacentHTML('beforeend',
      `<div class="note ok">✓ 你的第一个实验已经跑在真实量子计算机上了！job_id：${esc(r.result.job_id || '')}</div>`);
  } catch (err) {
    const box = $('real-box');
    if (box) box.innerHTML = `<b style="color:var(--err)">😕 真机运行失败：</b><div class="note">${esc(String(err))}</div>`;
  }
}
async function rerunExample(i, bi) {
  const e = EXAMPLES[i]; const out = $('lab-out');
  out.insertAdjacentHTML('beforeend', `<div class="spin" style="margin-top:12px"></div>`);
  const r = await post('/api/run', {qasm: e.qasm, backend: BACKENDS[bi][0], shots: 2048});
  if (r.error) { banner(r.error, 'err'); return; }
  const div = document.createElement('div'); div.style.marginTop = '14px';
  div.innerHTML = `<div class="note" style="color:var(--acc2)">同一份电路在 ${BACKENDS[bi][1]} 上重跑：</div>`;
  out.appendChild(div); renderHist(div, r.result, 2048);
  out.insertAdjacentHTML('beforeend', '<div class="note ok">✓ 未改一个字符，不同厂商的平台得到了一致的结果分布——这就是「统一中间层」（通用充电器）。</div>');
}

/* ---------- 零基础入门步骤 ---------- */
const stepsEl = $('basic-steps');
BASIC_STEPS.forEach((s, i) => {
  const d = document.createElement('div');
  d.className = 'step';
  d.innerHTML = `<div><b>${esc(s[0])}</b>${esc(s[1])}</div>`;
  stepsEl.appendChild(d);
});

/* ---------- 科普 ---------- */
const learnGrid = $('learn-grid');
CONCEPTS.forEach((c, i) => {
  const d = document.createElement('div');
  d.className = 'exp';
  d.innerHTML = `<span class="tag">概念 ${i + 1}</span><h4>${esc(c[0])}</h4><p>点击展开讲解</p>`;
  d.onclick = () => {
    $('learn-out').innerHTML = `<h3 style="margin-top:6px">${esc(c[0])}</h3>
      <div class="q">${esc(c[1])}</div>
      <div class="note" style="padding:10px 14px;background:rgba(0,212,255,.07);border-left:3px solid var(--acc2);border-radius:0 10px 10px 0">🔁 ${esc(c[2])}</div>`;
  };
  learnGrid.appendChild(d);
});

checkConfig();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # 静默访问日志
        pass

    def _send(self, code: int, body: bytes, ctype: str = "application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/config-status":
            self._config_status()
            return
        if self.path in ("/", "/index.html"):
            page = (PAGE
                    .replace("__EXAMPLES__", json.dumps(EXAMPLES, ensure_ascii=False))
                    .replace("__CONCEPTS__", json.dumps(CONCEPTS, ensure_ascii=False))
                    .replace("__BACKENDS__", json.dumps(BACKENDS, ensure_ascii=False))
                    .replace("__REAL_BACKENDS__", json.dumps(REAL_BACKENDS, ensure_ascii=False))
                    .replace("__BASIC_STEPS__", json.dumps(BASIC_STEPS, ensure_ascii=False)))
            self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain")

    def _config_status(self):
        import os
        self._send(200, json.dumps({
            "llm": bool(os.environ.get("LOOMQ_LLM_BASE_URL") and os.environ.get("LOOMQ_LLM_API_KEY")),
            "spinq": bool(os.environ.get("SPINQ_CLOUD_USERNAME") and os.environ.get("SPINQ_CLOUD_KEYFILE")),
            "originq": bool(os.environ.get("ORIGINQ_API_TOKEN")),
            "model": os.environ.get("LOOMQ_LLM_MODEL", ""),
        }).encode("utf-8"))

    def _save_config(self, payload):
        """把页面填的配置写入进程环境变量（仅内存，不落盘、不入库）。"""
        import os
        llm = payload.get("llm") or {}
        spinq = payload.get("spinq") or {}
        originq = payload.get("originq") or {}
        if llm.get("base_url"):
            os.environ["LOOMQ_LLM_BASE_URL"] = str(llm["base_url"]).rstrip("/")
        if llm.get("api_key"):
            os.environ["LOOMQ_LLM_API_KEY"] = str(llm["api_key"])
        if llm.get("model"):
            os.environ["LOOMQ_LLM_MODEL"] = str(llm["model"])
        if spinq.get("username"):
            os.environ["SPINQ_CLOUD_USERNAME"] = str(spinq["username"])
        if spinq.get("keyfile"):
            keyfile = str(spinq["keyfile"]).replace("~", str(Path.home()))
            os.environ["SPINQ_CLOUD_KEYFILE"] = keyfile
        if originq.get("api_token"):
            os.environ["ORIGINQ_API_TOKEN"] = str(originq["api_token"])
        self._send(200, json.dumps({
            "ok": True,
            "llm": bool(os.environ.get("LOOMQ_LLM_API_KEY")),
            "spinq": bool(os.environ.get("SPINQ_CLOUD_KEYFILE")),
            "originq": bool(os.environ.get("ORIGINQ_API_TOKEN")),
        }).encode("utf-8"))

    def _clear_config(self):
        import os
        for name in ("LOOMQ_LLM_BASE_URL", "LOOMQ_LLM_API_KEY", "LOOMQ_LLM_MODEL",
                     "SPINQ_CLOUD_USERNAME", "SPINQ_CLOUD_KEYFILE", "ORIGINQ_API_TOKEN"):
            os.environ.pop(name, None)
        self._send(200, json.dumps({"ok": True}).encode("utf-8"))

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self._send(400, json.dumps({"error": "bad request"}).encode("utf-8"))
            return
        if self.path == "/api/chat":
            self._handle_chat(payload)
        elif self.path == "/api/run":
            self._handle_run(payload)
        elif self.path == "/api/run-real":
            self._handle_run_real(payload)
        elif self.path == "/api/config":
            self._save_config(payload)
        elif self.path == "/api/config-clear":
            self._clear_config()
        else:
            self._send(404, json.dumps({"error": "unknown api"}).encode("utf-8"))

    def _handle_run_real(self, payload):
        """在真实量子机上运行电路（零基础用户一键上真机）。"""
        import os
        backend = str(payload.get("backend", "spinq_cloud"))
        qasm = str(payload.get("qasm", ""))
        shots = int(payload.get("shots", 2048))
        if backend == "spinq_cloud":
            if not (os.environ.get("SPINQ_CLOUD_USERNAME") and os.environ.get("SPINQ_CLOUD_KEYFILE")):
                self._send(200, json.dumps({"error": "量旋真机凭证未配置。主办方/团队在启动本服务前设置 "
                                                     "SPINQ_CLOUD_USERNAME 与 SPINQ_CLOUD_KEYFILE 即可（见 HARDWARE_ACCESS.md）。"},
                                           ensure_ascii=False).encode("utf-8"))
                return
            cfg = json.loads((HERE / "evidence" / "config_spinq_cloud.json").read_text(encoding="utf-8"))
            cfg["shots"] = shots
            try:
                result = real_machine._run_spinq_cloud(qasm, cfg, None)
            except Exception as exc:  # noqa: BLE001
                self._send(200, json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8"))
                return
        elif backend == "originq_wukong":
            if not os.environ.get("ORIGINQ_API_TOKEN"):
                self._send(200, json.dumps({"error": "本源量子云凭证未配置。团队在启动本服务前设置 "
                                                     "ORIGINQ_API_TOKEN 即可（见 HARDWARE_ACCESS.md）。"},
                                           ensure_ascii=False).encode("utf-8"))
                return
            cfg = json.loads((HERE / "evidence" / "config_originq_wukong.json").read_text(encoding="utf-8"))
            cfg["shots"] = shots
            cfg.setdefault("chip_id", 180)  # 本源180 当前在线（悟空72 维护中）
            try:
                result = real_machine._run_originq_wukong(qasm, cfg, None)
            except Exception as exc:  # noqa: BLE001
                self._send(200, json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8"))
                return
        else:
            self._send(400, json.dumps({"error": "unknown real backend"}).encode("utf-8"))
            return
        self._send(200, json.dumps({"result": result}, ensure_ascii=False).encode("utf-8"))

    def _handle_chat(self, payload):
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            self._send(400, json.dumps({"error": "prompt 不能为空"}).encode("utf-8"))
            return
        try:
            reply = adapter.agent_chat(prompt)
            qasm = _extract_qasm(reply)
            self._send(200, json.dumps({"reply": reply, "qasm": qasm}, ensure_ascii=False).encode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            self._send(200, json.dumps({"error": _friendly_llm_error(exc)}, ensure_ascii=False).encode("utf-8"))

    def _handle_run(self, payload):
        qasm = str(payload.get("qasm", ""))
        backend = str(payload.get("backend", "spinq"))
        shots = int(payload.get("shots", 2048))
        if backend not in adapter.SUPPORTED_TARGETS:
            self._send(400, json.dumps({"error": "unknown backend"}).encode("utf-8"))
            return
        try:
            result = adapter.run(qasm, backend, shots)
            self._send(200, json.dumps({"result": result}, ensure_ascii=False).encode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            self._send(200, json.dumps({"error": f"{type(exc).__name__}: {exc}"},
                                       ensure_ascii=False).encode("utf-8"))


def _friendly_llm_error(exc: Exception) -> str:
    msg = str(exc)
    if "LOOMQ_LLM" in msg or "环境变量" in msg or "模型调用失败" in msg:
        return ("🔑 模型服务未配置或调用失败（正式评测时由组委会自动注入，无需操作）。\n"
                "现在你可以先玩【现成实验】和【科普】（完全离线）。\n"
                "本地体验完整功能请先设置：\n"
                '  export LOOMQ_LLM_BASE_URL="https://api.deepseek.com"\n'
                '  export LOOMQ_LLM_API_KEY="sk-你的密钥"\n'
                '  export LOOMQ_LLM_MODEL="deepseek-chat"')
    return f"模型服务调用失败：{type(exc).__name__}: {msg}"


def _extract_qasm(text: str) -> str | None:
    import re
    if not isinstance(text, str):
        return None
    fenced = re.search(r"```(?:qasm|openqasm)?\s*(OPENQASM\s+2\.0;.*?)```",
                       text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    bare = re.search(r"(OPENQASM\s+2\.0;.*)", text, re.DOTALL)
    return bare.group(1).strip() if bare else None


def main() -> int:
    parser = argparse.ArgumentParser(description="LoomQ Web 界面（零依赖，零基础友好）")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("=" * 60)
    print("LoomQ Web 界面已启动（零基础友好版）")
    print(f"  打开浏览器访问：http://{args.host}:{args.port}")
    print("  推荐从【零基础入门】开始；实验与科普无需任何配置。")
    print("  生成/纠错/选平台需要模型服务：")
    print("    export LOOMQ_LLM_BASE_URL=... LOOMQ_LLM_API_KEY=... LOOMQ_LLM_MODEL=...")
    print("  按 Ctrl+C 退出")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n再见。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
