"""
规则 AI — 基于启发式规则的决策。

策略优先级：
1. 能一手出完 → 直接出完
2. 必须接牌 → 出最小的合法牌组
3. 自由出牌 → 优先出单张/对子/顺子（从最小开始）
4. 农民模式 → 队友出牌时倾向过牌
5. 保留炸弹和大牌到最后
"""
from typing import List, Optional
from src.engine.cards import Card, sort_cards
from src.engine.rules import get_all_playable
from src.engine.patterns import identify_pattern, Pattern
from src.ai.base import BaseAI, GameContext


class RuleAI(BaseAI):
    """规则 AI"""

    def __init__(self):
        super().__init__("规则AI")

    def decide(
        self,
        hand: List[Card],
        last_play: Optional[List[Card]],
        context: GameContext,
    ) -> Optional[List[Card]]:
        options = get_all_playable(hand, last_play)

        if not options:
            return None  # 必须过牌

        # 自由出牌
        if last_play is None:
            return self._free_play(hand, options, context)

        # 必须接牌
        return self._respond_play(hand, options, last_play, context)

    def _free_play(self, hand, options, context):
        """自由出牌：优先出小牌/弱牌组合"""
        # 1. 检查能否一手出完
        for opt in options:
            if set(c.rank for c in opt) == set(c.rank for c in hand) and len(opt) == len(hand):
                return opt  # 直接赢了

        # 2. 优先选择出牌数最少的组合（保留更多牌）
        # 但在单张/对子中优先出小的
        singles = [o for o in options if len(o) == 1]
        if singles:
            # 出最小的单张
            return sorted(singles, key=lambda o: o[0].rank.value)[0]

        pairs = [o for o in options if len(o) == 2 and identify_pattern(o)[0] == Pattern.PAIR]
        if pairs:
            return sorted(pairs, key=lambda o: o[0].rank.value)[0]

        # 顺子：优先出（减少复杂度）
        straights = [o for o in options if identify_pattern(o)[0] == Pattern.STRAIGHT]
        if straights:
            # 出小顺子
            return sorted(straights, key=lambda o: identify_pattern(o)[1])[0]

        # 其他情况：选点数最小的
        options_sorted = sorted(
            options,
            key=lambda o: (
                -len(o),  # 出牌多的优先（更快出完）
                identify_pattern(o)[1]  # 同长度选点数小的
            )
        )
        return options_sorted[0]

    def _respond_play(self, hand, options, last_play, context):
        """必须接牌时的决策"""

        # 1. 如果能一手出完所有手牌，直接出
        for opt in options:
            if set(c.rank for c in opt) == set(c.rank for c in hand) and len(opt) == len(hand):
                return opt

        # 2. 农民模式：如果队友出牌且队友剩余牌不多，倾向过牌
        if context.position == "farmer":
            last_player = self._get_last_player(context)
            if last_player is not None and last_player != context.my_idx:
                # 判断出牌者是否是队友（都不是地主就是队友）
                is_teammate = last_player != context.landlord_idx
                if is_teammate:
                    # 队友出的牌，考虑过牌
                    # 除非手牌很好能压死地主
                    tar_pat, _ = identify_pattern(last_play)
                    if tar_pat not in (Pattern.BOMB, Pattern.ROCKET):
                        return None

        # 3. 出最小的合法组合
        # 排除炸弹（不用急着炸）
        non_bombs = [o for o in options if identify_pattern(o)[0] != Pattern.BOMB]
        if non_bombs:
            # 选点数最小的
            target = sorted(non_bombs, key=lambda o: identify_pattern(o)[1])
            return target[0]

        # 4. 只剩炸弹了
        if context.players_hand_count[context.my_idx] <= 6:
            # 手牌不多，可以炸
            return sorted(options, key=lambda o: identify_pattern(o)[1])[0]

        # 手牌还多，先不过
        return None

    def _get_last_player(self, context):
        """从历史中找最后一个出牌的人"""
        for record in reversed(context.history):
            if record.action == "play":
                return record.player_idx
        return None
