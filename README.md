# 🂡 斗地主 AI-TUI

> 终端斗地主游戏 — AI 驱动的 TUI (Terminal UI) 版本

你扮演玩家，对抗两个 AI 农民（其中一个是蒙特卡洛搜索 AI，另一个是规则 AI）。

## 快速开始

```bash
cd /ubuntu/doudizhu
source .venv/bin/activate
python main.py
```

## 目录结构

```
doudizhu/
├── main.py                  # 入口
├── requirements.txt         # Python 依赖
├── IMPLEMENTATION_PLAN.md   # 实施计划
├── docs/
│   ├── DESIGN.md            # 技术设计文档（算法、架构）
│   └── USER_GUIDE.md        # 详细使用手册
├── src/
│   ├── engine/              # 核心引擎（零依赖）
│   │   ├── cards.py         #   牌面数据结构
│   │   ├── patterns.py      #   15种牌型识别
│   │   ├── rules.py         #   出牌规则 + 合法组合枚举
│   │   └── game.py          #   游戏状态机
│   ├── ai/                  # AI 引擎
│   │   ├── base.py          #   AI 基类接口
│   │   ├── random_ai.py     #   随机 AI（基线）
│   │   ├── rule_ai.py       #   规则 AI（启发式）
│   │   ├── mcts_ai.py       #   蒙特卡洛搜索 AI（主力）
│   │   └── simulation.py    #   蒙特卡洛模拟器
│   └── ui/                  # 界面
│       ├── display.py       #   牌面渲染（rich库）
│       └── tui.py           #   交互循环
└── tests/                   # 测试（82个用例）
```

## 操作

| 操作 | 按键 |
|------|------|
| 选牌/取消选牌 | `1` - `17` (牌序号，可多选如 `1 3 5` 或 `1-5`) |
| 确认出牌 | `Enter` |
| 过牌 | `P` |
| 退出 | `Q` |

## AI 对手

| AI | 策略 | 特点 |
|----|------|------|
| **AI-1** (MCTS) | 蒙特卡洛搜索 | 模拟100局选最优，≈中级玩家 |
| **AI-2** (Rule) | 启发式规则 | 保守策略，队友配合 |

## 牌型说明

15种牌型完整支持：单张、对子、三不带、三带一、三带二、顺子(≥5)、连对(≥3连)、飞机、飞机带单、飞机带双、四带二单、四带二对、炸弹、火箭

## 命令行选项

```bash
python main.py --mcts-sims 200    # MCTS 模拟次数（越大AI越强）
python main.py --seed 42          # 固定随机种子
```

## 依赖

- Python 3.11+
- `rich` — 终端渲染
- `pytest` — 测试

## 运行测试

```bash
cd /ubuntu/doudizhu
source .venv/bin/activate
python -m pytest tests/ -v
```
