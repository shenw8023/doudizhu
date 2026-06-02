"""
蒙特卡洛搜索 AI — 主引擎。

对每种合法出牌模拟 N 局完整游戏，选胜率最高的选项。
模拟中用规则 AI 填充决策（比纯随机更真实）。
"""
import random
from typing import List, Optional
from src.engine.cards import Card, sort_cards
from src.engine.rules import get_all_playable
from src.engine.patterns import identify_pattern, Pattern
from src.ai.base import BaseAI, GameContext
from src.ai.simulation import SimulationState


class MCTSAI(BaseAI):
    """蒙特卡洛搜索 AI"""

    def __init__(self, num_simulations: int = 100, seed: int = None):
        """
        num_simulations: 每种出牌选项模拟的次数
        seed: 随机种子
        """
        super().__init__(f"MCTS AI({num_simulations})")
        self.num_simulations = num_simulations
        self._rng = random.Random(seed)

    def decide(
        self,
        hand: List[Card],
        last_play: Optional[List[Card]],
        context: GameContext,
    ) -> Optional[List[Card]]:
        options = get_all_playable(hand, last_play)

        if not options:
            return None

        # 只有一个选项，直接返回
        if len(options) == 1:
            return options[0]

        # 如果手牌少（≤5张），尝试精确计算
        if len(hand) <= 5:
            result = self._exact_decide(hand, last_play, context, options)
            if result is not None:
                return result

        # 蒙特卡洛模拟
        scores = []
        for play in options:
            wins = self._simulate_option(hand, play, last_play, context)
            scores.append(wins)

        # 选胜率最高的
        best_idx = max(range(len(scores)), key=lambda i: scores[i])

        # 如果最佳选项胜率太低（<20%），考虑过牌
        best_rate = scores[best_idx] / self.num_simulations
        if last_play is not None and best_rate < 0.2:
            return None

        return options[best_idx]

    def _exact_decide(self, hand, last_play, context, options):
        """手牌少时的快速决策"""
        # 1. 能一手出完 → 直接出
        for opt in options:
            remaining = [c for c in hand if c not in opt]
            if not remaining:
                return opt

        # 2. 保留火箭到最后
        rockets = [o for o in options if identify_pattern(o)[0] == Pattern.ROCKET]
        non_rocket = [o for o in options if o not in rockets]
        if non_rocket and len(hand) > 3 and last_play is None:
            return non_rocket[0]

        return None  # 回退到 MCTS

    def _simulate_option(self, hand, play, last_play, context):
        """模拟一种出牌选项 N 次，返回胜利次数"""
        wins = 0
        for _ in range(self.num_simulations):
            if self._run_simulation(hand, play, last_play, context):
                wins += 1
        return wins

    def _run_simulation(self, my_hand, my_play, last_play, context):
        """
        运行一次完整的游戏模拟。

        返回 True 表示使用 my_play 后最终获胜。
        """
        # 构建模拟状态
        sim = SimulationState(my_hand, my_play, last_play, context, self._rng)
        return sim.run()
