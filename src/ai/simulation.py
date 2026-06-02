"""
蒙特卡洛模拟辅助类。

在模拟中，对手手牌是未知的。我们通过以下方式估算：
1. 统计已出的牌
2. 将未知牌随机分配给对手
3. 用规则 AI 模拟对手决策
4. 直到游戏结束
"""
import random
from typing import List, Optional
from src.engine.cards import Card, Deck, sort_cards, Rank
from src.engine.rules import get_all_playable, can_beat
from src.engine.patterns import identify_pattern, Pattern
from src.ai.base import GameContext
from src.ai.rule_ai import RuleAI


class SimulationState:
    """单次模拟状态"""

    def __init__(
        self,
        my_hand: List[Card],
        my_play: List[Card],
        last_play_original: Optional[List[Card]],
        context: GameContext,
        rng: random.Random,
    ):
        self.rng = rng
        self.my_idx = context.my_idx
        self.landlord_idx = context.landlord_idx
        self._rule_ai = RuleAI()

        # 计算对手索引
        all_indices = [0, 1, 2]
        self.opponents = [i for i in all_indices if i != self.my_idx]

        # 已知牌：我的手牌 + 底牌 + 已出的牌
        known_cards = set(my_hand)
        known_cards.update(context.bottom_cards)
        for record in context.history:
            known_cards.update(record.cards)

        # 未知牌：整副牌 - 已知牌
        full_deck = set(Deck.create())
        unknown_cards = list(full_deck - known_cards)

        # 随机分配给对手
        self.rng.shuffle(unknown_cards)

        # 计算每个对手应分配的牌数（手牌数 - 已出的牌数）
        opp_counts = []
        for opp_idx in self.opponents:
            orig_count = context.players_hand_count[opp_idx]
            played = sum(len(r.cards) for r in context.history if r.player_idx == opp_idx)
            opp_counts.append(orig_count - played)

        self.hands = {}
        self.hands[self.my_idx] = [c for c in my_hand if c not in my_play]  # 出牌后的手牌

        idx = 0
        for opp_idx, count in zip(self.opponents, opp_counts):
            assigned = unknown_cards[idx:idx + count]
            self.hands[opp_idx] = sort_cards(assigned)
            idx += count

        # 初始出牌
        self.current_player = (self.my_idx + 1) % 3  # 轮到我下家
        self.last_play = my_play if my_play else last_play_original
        if my_play is None:
            # 我过牌了
            self.last_player = self.my_idx  # 上一个人出的牌还在
        else:
            self.last_player = self.my_idx
        self.pass_count = 0

    def run(self) -> bool:
        """运行模拟直到游戏结束。返回 True 如果我方获胜。"""
        max_turns = 500  # 防止无限循环
        for _ in range(max_turns):
            # 检查我是否已出完
            if len(self.hands[self.my_idx]) == 0:
                return self.my_idx == self.landlord_idx or (
                    self._get_player_role(self.my_idx) == "farmer"
                )
            if any(len(self.hands[i]) == 0 for i in self.opponents):
                # 对手出完了
                winner = next(i for i in [0, 1, 2] if len(self.hands[i]) == 0)
                if self.my_idx == self.landlord_idx:
                    return winner == self.my_idx
                else:
                    return winner != self.landlord_idx  # 农民只要有一个出完就赢

            player = self.current_player
            hand = self.hands[player]
            ctx = self._make_context(player)

            # 用规则 AI 决策
            decision = self._rule_ai.decide(hand, self.last_play, ctx)

            if decision is None:
                # 过牌
                self.pass_count += 1
                if self.pass_count >= 2:
                    self.last_play = None
                    self.last_player = None
                    self.pass_count = 0
                self.current_player = (player + 1) % 3
            else:
                # 出牌
                self._remove_from_hand(player, decision)
                self.last_play = decision
                self.last_player = player
                self.pass_count = 0
                self.current_player = (player + 1) % 3

        # 超时：保守判定为输
        return False

    def _remove_from_hand(self, player: int, cards: List[Card]):
        hand = self.hands[player]
        to_remove = set(cards)
        self.hands[player] = [c for c in hand if c not in to_remove]

    def _make_context(self, player: int) -> GameContext:
        return GameContext(
            position=self._get_player_role(player),
            players_hand_count=[len(self.hands.get(i, [])) for i in range(3)],
            history=[],
            bottom_cards=[],
            landlord_idx=self.landlord_idx,
            my_idx=player,
            pass_count=self.pass_count,
        )

    def _get_player_role(self, idx: int) -> str:
        return "landlord" if idx == self.landlord_idx else "farmer"
