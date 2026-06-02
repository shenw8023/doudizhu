#!/usr/bin/env python3
"""
斗地主 AI-TUI 游戏入口。

用法:
    cd /ubuntu/doudizhu
    source .venv/bin/activate
    python main.py

选项:
    python main.py --mcts-sims 200    # MCTS 模拟次数（默认100）
    python main.py --seed 42          # 随机种子
"""
import sys
import os
import argparse

# Ensure the project directory is on the path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from src.ui.tui import main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="🂡 斗地主 AI-TUI — 终端斗地主游戏",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mcts-sims", type=int, default=100,
        help="MCTS AI 模拟次数 (默认: 100, 越大越强)"
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="随机种子 (用于复现)"
    )
    args = parser.parse_args()

    # Override MCTS settings via env (read by tui.py)
    if args.mcts_sims != 100:
        os.environ["DOUDIZHU_MCTS_SIMS"] = str(args.mcts_sims)
    if args.seed is not None:
        os.environ["DOUDIZHU_SEED"] = str(args.seed)

    main()
