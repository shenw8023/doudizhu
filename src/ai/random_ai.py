"""
随机 AI — 从合法出牌中随机选一组。
作为 AI 水平基线。
"""
import random
from typing import List, Optional
from src.engine.cards import Card
from src.engine.rules import get_all_playable
from src.ai.base import BaseAI, GameContext


class RandomAI(BaseAI):
    """随机 AI"""

    def __init__(self, pass_rate: float = 0.3, seed: int = None):
        """
        pass_rate: 当必须接牌时，过牌的概率（0-1）
        seed: 随机种子（用于复现测试）
        """
        super().__init__(f"随机AI({pass_rate:.0%})")
        self.pass_rate = pass_rate
        self._rng = random.Random(seed)

    def decide(
        self,
        hand: List[Card],
        last_play: Optional[List[Card]],
        context: GameContext,
    ) -> Optional[List[Card]]:
        options = get_all_playable(hand, last_play)

        if not options:
            return None  # 没有合法出牌，必须过牌

        # 如果是自由出牌，必须出
        if last_play is None:
            return self._rng.choice(options)

        # 必须接牌时，有 pass_rate 概率过牌
        if self._rng.random() < self.pass_rate:
            return None

        return self._rng.choice(options)
